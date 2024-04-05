import argparse
import shutil
import subprocess

import json
import os
import random
import tempfile
import time

from dredd_test_runners.common.constants import DEFAULT_COMPILATION_TIMEOUT, DEFAULT_RUNTIME_TIMEOUT
from dredd_test_runners.common.hash_file import hash_file
from dredd_test_runners.common.mutation_tree import MutationTree
from dredd_test_runners.common.run_process_with_timeout import ProcessResult, run_process_with_timeout
from dredd_test_runners.common.run_test_with_mutants import run_webgpu_cts_test_with_mutants, KillStatus, CTSKillStatus
from dredd_test_runners.wgslsmith_runner.webgpu_cts_utils import get_tests

from pathlib import Path
from typing import List, Set


def still_testing(start_time_for_overall_testing: float,
                  time_of_last_kill: float,
                  total_test_time: int,
                  maximum_time_since_last_kill: int) -> bool:
    if 0 < total_test_time < int(time.time() - start_time_for_overall_testing):
        return False
    if 0 < maximum_time_since_last_kill < int(time.time() - time_of_last_kill):
        return False
    return True


def main():
    start_time_for_overall_testing: float = time.time()
    time_of_last_kill: float = start_time_for_overall_testing

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
    parser.add_argument("mutated_compiler_executable",
                        help="Path to the executable for the Dredd-mutated compiler.",
                        type=Path)
    parser.add_argument("mutant_tracking_compiler_executable",
                        help="Path to the executable for the compiler instrumented to track mutants.",
                        type=Path)
    parser.add_argument("wgslsmith_root", help="Path to a checkout of WGSLsmith", #TODO: check build exe location
                        type=Path)
    parser.add_argument("--generator_timeout",
                        default=20,
                        help="Time in seconds to allow for generation of a program.",
                        type=int)
    parser.add_argument("--compile_timeout",
                        default=DEFAULT_COMPILATION_TIMEOUT,
                        help="Time in seconds to allow for compilation of a generated program (without mutation).",
                        type=int)
    parser.add_argument("--run_timeout",
                        default=DEFAULT_RUNTIME_TIMEOUT,
                        help="Time in seconds to allow for running a generated program (without mutation).",
                        type=int)
    parser.add_argument("--seed",
                        help="Seed for random number generator.",
                        type=int)
    parser.add_argument("--total_test_time",
                        default=86400,
                        help="Total time to allow for testing, in seconds. Default is 24 hours. To test indefinitely, "
                             "pass 0.",
                        type=int)
    parser.add_argument("--maximum_time_since_last_kill",
                        default=86400,
                        help="Cease testing if a kill has not occurred for this length of time. Default is 24 hours. "
                             "To test indefinitely, pass 0.",
                        type=int)
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

    
    if args.seed is not None:
        random.seed(args.seed)

    #with tempfile.TemporaryDirectory() as temp_dir_for_generated_code:
    with Path('/data/work/tint_mutation_testing/temp') as temp_dir_for_generated_code:
        wgslsmith_generated_program: Path = Path(temp_dir_for_generated_code, '__prog.wgsl')
        wgslsmith_reconditioned_program: Path = Path(temp_dir_for_generated_code, '__reconditioned.wgsl')
        dredd_covered_mutants_path: Path = Path(temp_dir_for_generated_code, '__dredd_covered_mutants')
        generated_program_exe_compiled_with_no_mutants = Path(temp_dir_for_generated_code, '__regular.exe')
        generated_program_exe_compiled_with_mutant_tracking = Path(temp_dir_for_generated_code, '__tracking.exe')
        mutant_exe = Path(temp_dir_for_generated_code, '__mutant.exe')
        wgslsmith_input : Path = Path(temp_dir_for_generated_code, '__inputs.json')

        killed_mutants: Set[int] = set()
        unkilled_mutants: Set[int] = set(range(0, mutation_tree.num_mutations))

        # Make a work directory in which information about the mutant killing process will be stored. If this already
        # exists that's OK - there may be other processes working on mutant killing, or we may be continuing a job that
        # crashed previously.
        Path("work").mkdir(exist_ok=True)
        Path("work/tests").mkdir(exist_ok=True)
        Path("work/killed_mutants").mkdir(exist_ok=True)


        # Get WebGPU CTS test queries as list
        #TODO: test_queries = get_test_queries()
        webgpu_cts_path = Path('/data/dev/webgpu_cts/src/webgpu')
    
        base_query_string = 'webgpu'

        test_queries = get_tests(webgpu_cts_path, base_query_string)
        #test_queries = ['webgpu:examples:gpu,buffers:*']
        
        # Loop over tests
        for query in test_queries:
            if dredd_covered_mutants_path.exists():
                os.remove(dredd_covered_mutants_path)
            if wgslsmith_generated_program.exists():
                os.remove(wgslsmith_generated_program)
            if generated_program_exe_compiled_with_no_mutants.exists():
                os.remove(generated_program_exe_compiled_with_no_mutants)
            if generated_program_exe_compiled_with_mutant_tracking.exists():
                os.remove(generated_program_exe_compiled_with_mutant_tracking)
           
            # Run tests with unmutated Dawn to check if test passes
            #TODO: pass arguments
            run_unmutated_cmd = ['/data/dev/latest_dawn/tools/run',
                    'run-cts', 
                    '--verbose',
                    '--bin=/data/dev/latest_dawn/out/Debug',
                    '--cts=/data/dev/webgpu_cts',
                    query]
            
            print("Running with unmutated Dawn...")
            run_time_start: float = time.time()
            regular_execution_result: ProcessResult = run_process_with_timeout(
                cmd=run_unmutated_cmd, timeout_seconds=args.run_timeout)
            run_time_end: float = time.time()
            run_time = run_time_end - run_time_start
        
            if regular_execution_result is None:
                print("Runtime timeout.")
                continue
            if regular_execution_result.returncode != 0:
                print(f"Std out:\n {regular_execution_result.stdout.decode('utf-8')}\n")
                print(f"Std err:\n {regular_execution_result.stderr.decode('utf-8')}\n")
                print("Execution of generated program failed without mutants.")
                continue
            else:
                print("Execution of generated program succeeded without mutants.")

            print(f"Std out:\n {regular_execution_result.stdout.decode('utf-8')}\n")
            print(f"Std err:\n {regular_execution_result.stderr.decode('utf-8')}\n")
            
            # Compile the program with the mutant tracking compiler.
            print("Running with mutant tracking compiler...")
            tracking_environment = os.environ.copy()
            tracking_environment["DREDD_MUTANT_TRACKING_FILE"] = str(dredd_covered_mutants_path)
            tracking_compile_cmd = ['/data/dev/dawn_mutant_tracking/tools/run',
                    'run-cts', 
                    '--verbose',
                    '--bin=/data/dev/dawn_mutant_tracking/out/Debug',
                    '--cts=/data/dev/webgpu_cts',
                    query]            
            mutant_tracking_result : ProcessResult = run_process_with_timeout(cmd=tracking_compile_cmd, timeout_seconds=args.compile_timeout, env=tracking_environment) 
            #mutant_tracking_result = subprocess.run(tracking_compile_cmd, env=tracking_environment)

            if mutant_tracking_result is None:
                print("Mutant tracking compilation timed out.")
                continue
            elif not dredd_covered_mutants_path.exists():
                print(f"Std out:\n {mutant_tracking_result.stdout.decode('utf-8')}\n")
                print(f"Std err:\n {mutant_tracking_result.stderr.decode('utf-8')}\n")
                print("No mutant tracking file created.")
                continue
            else:
                print("Mutant tracking compilation complete")
 
            print(f"Std out:\n {mutant_tracking_result.stdout.decode('utf-8')}\n")
            print(f"Std err:\n {mutant_tracking_result.stderr.decode('utf-8')}\n")
            
          
            # Try to create a directory for this WGSLsmith test. It is very unlikely that it already exists, but this could
            # happen if two test workers pick the same seed. If that happens, this worker will skip the test.
            cts_test_name: str = "query_" + query #TODO: some of these names are likely too long to be file names; assign an id instead
            test_output_directory: Path = Path("work/tests/" + cts_test_name)
            try:
                test_output_directory.mkdir()
            except FileExistsError:
                print(f"Skipping test {cts_test_name} as a directory for it already exists")
                continue
            #TODO: copy test into output directory (or just query string?)
            #shutil.copy(src=wg, dst=test_output_directory / "prog.wgsl")

            # Load file contents into a list. We go from list to set to list to eliminate duplicates.
            covered_by_this_test: List[int] = list(set([int(line.strip()) for line in
                                                        open(dredd_covered_mutants_path, 'r').readlines()]))
            covered_by_this_test.sort()
            candidate_mutants_for_this_test: List[int] = ([m for m in covered_by_this_test if m not in killed_mutants])
            print("Number of mutants to try: " + str(len(candidate_mutants_for_this_test)))
            
            already_killed_by_other_tests: List[int] = ([m for m in covered_by_this_test if m in killed_mutants])
            killed_by_this_test: List[int] = []
            covered_but_not_killed_by_this_test: List[int] = []
            
            for mutant in candidate_mutants_for_this_test:

                mutant_path = Path("work/killed_mutants/" + str(mutant))
                if mutant_path.exists():
                    print("Skipping mutant " + str(mutant) + " as it is noted as already killed.")
                    unkilled_mutants.remove(mutant)
                    killed_mutants.add(mutant)
                    already_killed_by_other_tests.append(mutant)
                    continue
                
                print("Trying mutant " + str(mutant))
                
                mutated_cmd = ['/data/dev/dawn_mutated/tools/run',
                    'run-cts', 
                    '--verbose',
                    '--bin=/data/dev/dawn_mutated/out/Debug',
                    '--cts=/data/dev/webgpu_cts',
                    query]    

                mutant_result = run_webgpu_cts_test_with_mutants(mutants=[mutant],
                        mutated_cmd=mutated_cmd,
                        timeout=args.compile_timeout)
                print("Mutant result: " + str(mutant_result))
                 
                if mutant_result == CTSKillStatus.SURVIVED:
                    covered_but_not_killed_by_this_test.append(mutant)
                    continue

                unkilled_mutants.remove(mutant)
                killed_mutants.add(mutant)
                killed_by_this_test.append(mutant)
                time_of_last_kill = time.time()
                print(f"Kill! Mutants killed so far: {len(killed_mutants)}")
                try:
                    mutant_path.mkdir()
                    print("Writing kill info to file.")
                    with open(mutant_path / "kill_info.json", "w") as outfile:
                        json.dump({"killing_test": cts_test_name,
                                   "kill_type": str(mutant_result)}, outfile)
                except FileExistsError:
                    print(f"Mutant {mutant} was independently discovered to be killed.")
                    continue

            all_considered_mutants = killed_by_this_test \
                + covered_but_not_killed_by_this_test \
                + already_killed_by_other_tests
            all_considered_mutants.sort()

            killed_by_this_test.sort()
            covered_but_not_killed_by_this_test.sort()
            already_killed_by_other_tests.sort()
            with open(test_output_directory / "kill_summary.json", "w") as outfile:
                json.dump({"terminated_early": terminated_early,
                           "covered_mutants": covered_by_this_test,
                           "killed_mutants": killed_by_this_test,
                           "skipped_mutants": already_killed_by_other_tests,
                           "survived_mutants": covered_but_not_killed_by_this_test}, outfile)
if __name__ == '__main__':
    main()
