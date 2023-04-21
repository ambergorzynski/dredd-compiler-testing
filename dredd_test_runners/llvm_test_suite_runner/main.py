import argparse
import json
import os
import subprocess
import signal
import time
import random

from collections import deque
from pathlib import Path
from dredd_test_runners.common.hash_file import hash_file
from dredd_test_runners.common.mutation_tree import MutationTree
from enum import Enum
from typing import AnyStr, Dict, List, Set, Optional

REGULAR_EXE_NAME: str = '__exe'
MUTANT_EXE_NAME: str = '__mutant_exe'
MUTANT_TRACKING_EXE_NAME: str = '__mutant_exe'

DREDD_COVERED_MUTANTS: str = '__dredd_covered_mutants'

BATCH_SIZE: int = 1

class ProcessResult:
    def __init__(self, returncode: int, stdout: bytes, stderr: bytes):
        self.returncode: bytes = returncode
        self.stdout: bytes = stdout
        self.stderr: bytes = stderr


class KillStatus(Enum):
    SURVIVED_IDENTICAL = 1
    SURVIVED_BINARY_DIFFERENCE = 2
    KILL_COMPILER_CRASH = 3
    KILL_COMPILER_TIMEOUT = 4
    KILL_RUNTIME_TIMEOUT = 5
    KILL_DIFFERENT_EXIT_CODES = 6
    KILL_DIFFERENT_STDOUT = 7
    KILL_DIFFERENT_STDERR = 8


def run_process_with_timeout(cmd: List[str], timeout_seconds: int, env: Optional[Dict[AnyStr, AnyStr]] = None) -> Optional[ProcessResult]:
    try:
        process = subprocess.Popen(cmd, start_new_session=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=env)
        process_stdout, process_stderr = process.communicate(timeout=timeout_seconds)
        return ProcessResult(returncode=process.returncode, stdout=process_stdout, stderr=process_stderr)
    except subprocess.TimeoutExpired:
        os.killpg(os.getpgid(process.pid), signal.SIGTERM)
        return None


def run_test_with_mutants(mutants: List[int],
                          compiler_path: str,
                          compiler_args: List[str],
                          compile_time: float,
                          run_time: float,
                          binary_hash_non_mutated: str,
                          execution_result_non_mutated: ProcessResult) -> KillStatus:
    mutated_environment = os.environ.copy()
    mutated_environment["DREDD_ENABLED_MUTATION"] = ','.join([str(m) for m in mutants])
    if os.path.exists(MUTANT_EXE_NAME):
        os.remove(MUTANT_EXE_NAME)
    mutated_cmd = [compiler_path] + compiler_args + ['-o', MUTANT_EXE_NAME]
    mutated_result: ProcessResult = run_process_with_timeout(cmd=mutated_cmd,
                                                             timeout_seconds=int(max(1.0, 5.0 * compile_time)),
                                                             env=mutated_environment)
    if mutated_result is None:
        return KillStatus.KILL_COMPILER_TIMEOUT

    if mutated_result.returncode != 0:
        return KillStatus.KILL_COMPILER_CRASH

    if binary_hash_non_mutated == hash_file(MUTANT_EXE_NAME):
        return KillStatus.SURVIVED_IDENTICAL

    mutated_execution_result: ProcessResult = run_process_with_timeout(cmd=["./" + MUTANT_EXE_NAME],
                                                                       timeout_seconds=int(max(1.0, 5.0 * run_time)))
    if mutated_execution_result is None:
        return KillStatus.KILL_RUNTIME_TIMEOUT

    if execution_result_non_mutated.returncode != mutated_execution_result.returncode:
        return KillStatus.KILL_DIFFERENT_EXIT_CODES

    if execution_result_non_mutated.stdout != mutated_execution_result.stdout:
        return KillStatus.KILL_DIFFERENT_STDOUT

    if execution_result_non_mutated.stderr != mutated_execution_result.stderr:
        return KillStatus.KILL_DIFFERENT_STDERR

    return KillStatus.SURVIVED_BINARY_DIFFERENCE


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("mutation_info_file",
                        help="File containing information about mutations, generated when Dredd was used to actually "
                             "mutate the source code.",
                        type=Path)
    parser.add_argument("mutation_info_file_for_mutant_coverage_tracking",
                        help="File containing information about mutations, generated when Dredd was used to "
                             "instrument the source code to track mutant coverage; this will be compared against the "
                             "regular mutation info file to ensure that tracked mutants match applied mutants.",
                        type=Path)
    parser.add_argument("mutated_compiler_bin_dir",
                        help="Path to the bin directory of the Dredd-mutated compiler.",
                        type=Path)
    parser.add_argument("mutant_tracking_compiler_bin_dir",
                        help="Path to the bin directory of the compiler instrumented to track mutants.",
                        type=Path)
    parser.add_argument("llvm_test_suite_root", help="Path to a checkout of the LLVM test suite.",
                        type=Path)
    parser.add_argument("llvm_test_suite_compilation_database",
                        help="Path to a compilation database for the LLVM test suite (generated using CMake).",
                        type=Path)
    args = parser.parse_args()

    assert args.mutation_info_file != args.mutation_info_file_for_mutant_coverage_tracking

    print("Building the real mutation tree...")
    with open(args.mutation_info_file, 'r') as json_input:
        mutation_tree = MutationTree(json.load(json_input))
    print("Built!")
    print("Building the mutation tree associated with mutant coverage tracking...")
    with open(args.mutation_info_file_for_mutant_coverage_tracking, 'r') as json_input:
        mutation_tree_for_coverage_tracking = MutationTree(json.load(json_input))
    print("Built!")
    print("Checking that the two mutation trees match...")
    assert mutation_tree.mutation_id_to_node_id == mutation_tree_for_coverage_tracking.mutation_id_to_node_id
    assert mutation_tree.parent_map == mutation_tree_for_coverage_tracking.parent_map
    assert mutation_tree.num_nodes == mutation_tree_for_coverage_tracking.num_nodes
    assert mutation_tree.num_mutations == mutation_tree_for_coverage_tracking.num_mutations
    print("Check complete!")

    killed_mutants: Set[int] = set()
    unkilled_mutants: Dict[int, int] = {mutant: 0 for mutant in range(0, mutation_tree.num_mutations)}

    llvm_test_suite_compile_commmands = json.load(open(args.llvm_test_suite_compilation_database, 'r'))
    regression_prefix = str(args.llvm_test_suite_root) + "/SingleSource/Regression"
    unit_tests_prefix = str(args.llvm_test_suite_root) + "/SingleSource/UnitTests"
    for test in llvm_test_suite_compile_commmands:
        test_filename = test["file"]
        if not test_filename.startswith(regression_prefix) and not test_filename.startswith(unit_tests_prefix):
            print("Skipping test " + test_filename + " as it is not in a relevant directory")
            continue

        print("Analysing kills for test " + test_filename)
        print("Remaining unkilled mutants: " + str(len(unkilled_mutants)))
        print("Mutants killed so far:       " + str(len(killed_mutants)))

        is_c: bool = os.path.splitext(test_filename)[1] == ".c"

        compiler_args = []
        components = test["command"].split(' ')
        index = 0
        while index < len(components):
            component = components[index]
            if component == '-I':
                compiler_args.append[component]
                compiler_args.append[components[index + 1]]
                index += 2
                continue
            if component.startswith('-I') or component.startswith('-D') or component.startswith(
                    '-w') or component.startswith('-W') or component.startswith('-O'):
                compiler_args.append(component)
            index += 1
        compiler_args.append(test_filename)
        if is_c:
            compiler_args.append('-lm')

        if os.path.exists(REGULAR_EXE_NAME):
            os.remove(REGULAR_EXE_NAME)
        if os.path.exists(DREDD_COVERED_MUTANTS):
            os.remove(DREDD_COVERED_MUTANTS)

        regular_cmd = [str(args.mutated_compiler_bin_dir) + os.sep
                       + "clang" if is_c else str(args.mutated_compiler_bin_dir) + os.sep + "clang++"] + compiler_args \
                      + ['-o', REGULAR_EXE_NAME]
        print("Compile command:")
        print(' '.join(regular_cmd))
        compile_time_start: float = time.time()
        regular_result: ProcessResult = run_process_with_timeout(cmd=regular_cmd, timeout_seconds=60)
        assert regular_result is not None  # We do not expect regular compilation to time out.
        compile_time_end: float = time.time()
        compile_time = compile_time_end - compile_time_start

        if regular_result.returncode != 0:
            print("Skipping test " + test_filename + " as it failed to compile. Details:")
            print(' '.join(regular_cmd))
            print(regular_result.stdout.decode('utf-8'))
            print(regular_result.stderr.decode('utf-8'))
            continue

        regular_hash = hash_file(REGULAR_EXE_NAME)

        run_time_start: float = time.time()
        regular_execution_result: ProcessResult = run_process_with_timeout(cmd=["./" + REGULAR_EXE_NAME], timeout_seconds=60)
        assert regular_execution_result is not None  # We do not expect regular compilation to time out.
        run_time_end: float = time.time()
        run_time = run_time_end - run_time_start

        tracking_environment: dict[AnyStr, AnyStr] = os.environ.copy()
        tracking_environment["DREDD_MUTANT_TRACKING_FILE"] = DREDD_COVERED_MUTANTS
        mutant_tracking_cmd = [str(args.mutant_tracking_compiler_bin_dir) + os.sep + "clang" if is_c else str(
            args.mutant_tracking_compiler_bin_dir) + os.sep + "clang++"] + compiler_args + ['-o', MUTANT_TRACKING_EXE_NAME]
        mutant_tracking_result: ProcessResult = run_process_with_timeout(cmd=mutant_tracking_cmd, timeout_seconds=60,
                                                                             env=tracking_environment)

        # Sanity check: confirm that the mutant tracking exe is no different to the regular exe.
        assert regular_hash == hash_file(MUTANT_TRACKING_EXE_NAME)

        # Load file contents into a set
        covered_mutants: Set[int] = set([int(line.strip()) for line in
                                         open(DREDD_COVERED_MUTANTS, 'r').readlines()])
        covered_mutants_shuffled: List[int] = list(covered_mutants)
        random.shuffle(covered_mutants_shuffled)

        candidate_mutants: deque = deque([m for m in covered_mutants_shuffled if m not in killed_mutants])
        print("Number of mutants to try: " + str(len(candidate_mutants)))

        batched_mutants = []
        while len(candidate_mutants) > 0:
            incompatible_with_batch: Set[int] = set()
            batch: List[int] = []
            relegated_mutants = deque()
            while len(candidate_mutants) > 0 and len(batch) < BATCH_SIZE:
                mutant = candidate_mutants.pop()
                if mutant in incompatible_with_batch:
                    relegated_mutants.append(mutant)
                    continue
                batch.append(mutant)
                incompatible_with_batch.update(mutation_tree.get_incompatible_mutation_ids(mutant))

            batched_mutants.append(batch)

            while len(relegated_mutants) > 0:
                candidate_mutants.append(relegated_mutants.pop())

        print("Number of batches: " + str(len(batched_mutants)))

        for batch in batched_mutants:
            if len(batch) > 1:
                print("Trying batch of mutants of size " + str(len(batch)) + ": " + str(batch))
                batch_result = run_test_with_mutants(mutants=batch,
                                                     compiler_path=str(args.mutated_compiler_bin_dir) + os.sep + "clang" if is_c else str(args.mutated_compiler_bin_dir) + os.sep + "clang++",
                                                     compiler_args=compiler_args,
                                                     compile_time=compile_time,
                                                     run_time=run_time,
                                                     binary_hash_non_mutated=regular_hash,
                                                     execution_result_non_mutated=regular_execution_result)
                print("Batch result: " + str(batch_result))
                if batch_result == KillStatus.SURVIVED_IDENTICAL or batch_result == KillStatus.SURVIVED_BINARY_DIFFERENCE:
                    print("Batch survived: moving on.")
                    continue

                print("Batch was killed, enumerating its mutants.")

            for mutant in batch:
                print("Trying mutant " + str(mutant))
                mutant_result = run_test_with_mutants(mutants=[mutant],
                                                      compiler_path=str(args.mutated_compiler_bin_dir) + os.sep + "clang" if is_c else str(args.mutated_compiler_bin_dir) + os.sep + "clang++",
                                                      compiler_args=compiler_args,
                                                      compile_time=compile_time,
                                                      run_time=run_time,
                                                      binary_hash_non_mutated=regular_hash,
                                                      execution_result_non_mutated=regular_execution_result)
                print("Mutant result: " + str(mutant_result))
                if mutant_result == KillStatus.SURVIVED_IDENTICAL or mutant_result == KillStatus.SURVIVED_BINARY_DIFFERENCE:
                    continue

                unkilled_mutants.pop(mutant)
                killed_mutants.add(mutant)
                print("Kill! Mutants killed so far: " + str(len(killed_mutants)))


if __name__ == '__main__':
    main()
