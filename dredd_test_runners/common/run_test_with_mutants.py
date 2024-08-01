from enum import Enum
import os
from pathlib import Path
from typing import List

from dredd_test_runners.common.constants import (MIN_TIMEOUT_FOR_MUTANT_COMPILATION,
                                                 MIN_TIMEOUT_FOR_MUTANT_EXECUTION,
                                                 TIMEOUT_MULTIPLIER_FOR_MUTANT_COMPILATION,
                                                 TIMEOUT_MULTIPLIER_FOR_MUTANT_EXECUTION)
from dredd_test_runners.common.hash_file import hash_file
from dredd_test_runners.common.run_process_with_timeout import ProcessResult, run_process_with_timeout
from dredd_test_runners.wgslsmith_runner.webgpu_cts_utils import get_failures, get_single_tests_from_stdout

class CTSKillStatus(Enum):
    SURVIVED = 1
    KILL_TEST_FAIL = 2
    TEST_TIMEOUT = 3

class KillStatus(Enum):
    SURVIVED_IDENTICAL = 1
    SURVIVED_BINARY_DIFFERENCE = 2
    KILL_COMPILER_CRASH = 3
    KILL_COMPILER_TIMEOUT = 4
    KILL_RUNTIME_TIMEOUT = 5
    KILL_DIFFERENT_EXIT_CODES = 6
    KILL_DIFFERENT_STDOUT = 7
    KILL_DIFFERENT_STDERR = 8


def run_test_with_mutants(mutants: List[int],
                          compiler_path: str,
                          compiler_args: List[str],
                          compile_time: float,
                          run_time: float,
                          binary_hash_non_mutated: str,
                          execution_result_non_mutated: ProcessResult,
                          mutant_exe_path: Path) -> KillStatus:
    mutated_environment = os.environ.copy()
    mutated_environment["DREDD_ENABLED_MUTATION"] = ','.join([str(m) for m in mutants])
    if mutant_exe_path.exists():
        os.remove(mutant_exe_path)
    mutated_cmd = [compiler_path] + compiler_args + ['-o', str(mutant_exe_path)]
    mutated_result: ProcessResult = run_process_with_timeout(
        cmd=mutated_cmd,
        timeout_seconds=int(max(
            MIN_TIMEOUT_FOR_MUTANT_COMPILATION,
            TIMEOUT_MULTIPLIER_FOR_MUTANT_COMPILATION * compile_time)),
        env=mutated_environment)
    if mutated_result is None:
        return KillStatus.KILL_COMPILER_TIMEOUT

    if mutated_result.returncode != 0:
        return KillStatus.KILL_COMPILER_CRASH

    if binary_hash_non_mutated == hash_file(str(mutant_exe_path)):
        return KillStatus.SURVIVED_IDENTICAL

    mutated_execution_result: ProcessResult = run_process_with_timeout(
        cmd=[str(mutant_exe_path)],
        timeout_seconds=int(max(MIN_TIMEOUT_FOR_MUTANT_EXECUTION,
                                TIMEOUT_MULTIPLIER_FOR_MUTANT_EXECUTION * run_time)))
    if mutated_execution_result is None:
        return KillStatus.KILL_RUNTIME_TIMEOUT

    if execution_result_non_mutated.returncode != mutated_execution_result.returncode:
        return KillStatus.KILL_DIFFERENT_EXIT_CODES

    if execution_result_non_mutated.stdout != mutated_execution_result.stdout:
        return KillStatus.KILL_DIFFERENT_STDOUT

    if execution_result_non_mutated.stderr != mutated_execution_result.stderr:
        return KillStatus.KILL_DIFFERENT_STDERR

    return KillStatus.SURVIVED_BINARY_DIFFERENCE

def run_wgslsmith_test_with_mutants(mutants: List[int],
                          compiler_path: str,
                          compiler_args: List[str],
                          compile_time: float,
                          run_time: float,
                          execution_result_non_mutated: ProcessResult,
                          mutant_exe_path: Path,
                          env=None) -> tuple[KillStatus, ProcessResult]:
    if env:
        mutated_environment = env
    else:
        mutated_environment = os.environ.copy()
    mutated_environment["DREDD_ENABLED_MUTATION"] = ','.join([str(m) for m in mutants])
    
    if mutant_exe_path.exists():
        os.remove(mutant_exe_path)
    
    mutated_cmd = [compiler_path] + compiler_args

    mutated_result: ProcessResult = run_process_with_timeout(
            cmd = mutated_cmd,
            timeout_seconds=compile_time,
            env=mutated_environment)
    

    if mutated_result is None:
        return (KillStatus.KILL_COMPILER_TIMEOUT, None)

    if mutated_result.returncode != 0:
        return (KillStatus.KILL_COMPILER_CRASH, mutated_result)

    if execution_result_non_mutated.returncode != mutated_result.returncode:
        return (KillStatus.KILL_DIFFERENT_EXIT_CODES, mutated_result)

    if execution_result_non_mutated.stdout != mutated_result.stdout:

        non_mutated_output = get_wgslsmith_output(execution_result_non_mutated.stdout)
        mutated_output = get_wgslsmith_output(mutated_result.stdout)
        
        if mutated_output is None:
            return (KillStatus.KILL_RUNTIME_TIMEOUT, mutated_result)

        if non_mutated_output != mutated_output:
            print(f'Unmutated:\n {execution_result_non_mutated.stdout.decode("utf-8")}')
            print(f'Mutated:\n {mutated_result.stdout.decode("utf-8")}')
            
            return (KillStatus.KILL_DIFFERENT_STDOUT, mutated_result)

        # if stdouts differ but not for timeout or different output array reasons,
        # then the mutant is not being killed

    if execution_result_non_mutated.stderr != mutated_result.stderr:
        return (KillStatus.KILL_DIFFERENT_STDERR, mutated_result)
    
    return (KillStatus.SURVIVED_IDENTICAL, mutated_result)

def run_webgpu_cts_test_with_mutants(mutants: List[int],
                          mutated_cmd : str,
                          timeout_seconds : int,
                          unmutated_results : dict[str, str],
                          reliable_tests : list[str],
                          env = None) -> tuple[CTSKillStatus, list]:

    if env:
        mutated_environment = env
    else:
        mutated_environment = os.environ.copy()
    mutated_environment["DREDD_ENABLED_MUTATION"] = ','.join([str(m) for m in mutants])
    
    mutated_result: ProcessResult = run_process_with_timeout(
            cmd = mutated_cmd,
            env=mutated_environment,
            timeout_seconds=timeout_seconds)

    if mutated_result is None:
        return (CTSKillStatus.TEST_TIMEOUT, [])
    
    # Check test results against unmutated test results
    # If any previously passing test fails, then the mutant is killed
    mutated_results = get_single_tests_from_stdout(mutated_result.stdout.decode('utf-8').split('\n'))

    mutated_fail = set([test for (test,status) in mutated_results.items() if status=='fail'])

    unmutated_pass = set([test for (test,status) in unmutated_results.items() if status=='pass'])

    unmutated_reliable_pass = unmutated_pass.intersection(set(reliable_tests))

    if len(unmutated_reliable_pass.intersection(mutated_fail)) != 0:
        return (CTSKillStatus.KILL_TEST_FAIL, unmutated_reliable_pass.intersection(mutated_fail))

    return (CTSKillStatus.SURVIVED, [])

def get_wgslsmith_output(stdout) -> list[int]:
    
    output = stdout.decode("utf-8")
    
    if output.find('timeout') != -1:
        return None

    output_start_index = output.find('outputs') + 18
    output_end_index = output.rfind(']')
    output = output[output_start_index:output_end_index].split(", ")
    output = [int(o) for o in output]

    return output
