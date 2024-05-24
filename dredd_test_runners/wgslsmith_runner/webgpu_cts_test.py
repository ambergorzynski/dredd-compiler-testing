import argparse
import shutil
import subprocess
import logging

import json
import os
import random
import tempfile
import time
import datetime

from dredd_test_runners.common.constants import DEFAULT_COMPILATION_TIMEOUT, DEFAULT_RUNTIME_TIMEOUT
from dredd_test_runners.common.hash_file import hash_file
from dredd_test_runners.common.mutation_tree import MutationTree
from dredd_test_runners.common.run_process_with_timeout import ProcessResult, run_process_with_timeout
from dredd_test_runners.common.run_test_with_mutants import run_webgpu_cts_test_with_mutants, KillStatus, CTSKillStatus
from dredd_test_runners.wgslsmith_runner.webgpu_cts_utils import kill_gpu_processes, get_tests, get_passes, get_failures, get_unrun_tests

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
    parser.add_argument("mutated_path",
                        type=Path)
    parser.add_argument("tracking_path",
                        type=Path),
    parser.add_argument("mutation_info_file",
                        help="File containing information about mutations, generated when Dredd was used to actually "
                             "mutate the source code.",
                        type=Path)
    parser.add_argument("mutation_info_file_for_mutant_coverage_tracking",
                        help="File containing information about mutations, generated when Dredd was used to "
                             "instrument the source code to track mutant coverage; this will be compared against the "
                             "regular mutation info file to ensure that tracked mutants match applied mutants.",
                        type=Path)
    parser.add_argument("mutant_kill_path",
                        help="Directory in which to record mutant kill info and mutant killing tests.",
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
    parser.add_argument("--unittests_only",
                        action=argparse.BooleanOptionalAction,
                        help="Run unit tests only. Default is false.")
    parser.add_argument("--cts_only",
                        action=argparse.BooleanOptionalAction,
                        help="Run CTS tests only. Default is false.")
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

    with tempfile.TemporaryDirectory() as temp_dir_for_generated_code:
        #with Path('/data/dev/dredd-compiler-testing/dredd_test_runners/wgslsmith_runner/temp') as temp_dir_for_generated_code:
        dredd_covered_mutants_path: Path = Path(temp_dir_for_generated_code, '__dredd_covered_mutants')

        killed_mutants: Set[int] = set()
        unkilled_mutants: Set[int] = set(range(0, mutation_tree.num_mutations))

        # Make a work directory in which information about the mutant killing process will be stored. If this already
        # exists that's OK - there may be other processes working on mutant killing, or we may be continuing a job that
        # crashed previously.
        Path(args.mutant_kill_path).mkdir(exist_ok=True)
        Path(args.mutant_kill_path,"killed_mutants").mkdir(exist_ok=True)
        Path(args.mutant_kill_path,"tracking").mkdir(exist_ok=True)
        
                 
        logger = logging.getLogger(__name__)
        logging.basicConfig(filename=Path(args.mutant_kill_path, 'info.log'), 
                format='%(asctime)s - %(message)s',
                datefmt=('%Y-%m-%d %H:%M:%S'),
                encoding='utf-8', 
                level=logging.INFO)

        logging.info('Start')

        # Get WebGPU CTS test queries as list
        #TODO: test_queries = get_test_queries()
        webgpu_cts_path = Path('/data/dev/webgpu_cts/src/webgpu') 
        base_query_string = 'webgpu'

        cts_queries = get_tests(webgpu_cts_path, base_query_string)
        '''
        test_queries = ['webgpu:shader,execution,flow_control,loop:*']
        test_queries = ['webgpu:api,operation,buffers,map_oom:*']

        # Shader queries only
        test_queries = [t for t in test_queries if 'webgpu:shader,validation,expression,call,builtin,asinh' in t]
        
        cts_queries = ['webgpu:shader,execution,expression,call,builtin,textureDimensions:*'] 
        ''' 
        # Get WebGPU unit test queries as list
        unittests_path = Path('/data/dev/webgpu_cts/src/unittests')
        unittest_query_string = 'unittests'

        unittest_queries = get_tests(unittests_path, unittest_query_string)

        if args.unittests_only:
            test_queries = unittest_queries
        elif args.cts_only:
            test_queries = cts_queries
        else:
            test_queries = unittest_queries + cts_queries

        #test_queries = get_unrun_tests()
        #test_queries = ['webgpu:shader,validation,expression,call,builtin,abs:*']

        # Loop over tests
        for query in test_queries:

            test_id = hash(query)

            test_name = 'unit' if 'unittests:' in query else 'cts'
            
            if dredd_covered_mutants_path.exists():
                os.remove(dredd_covered_mutants_path)

            # Log that this test has been started
            logger.info(f'\nQuery: {query}')
            logger.info(f'test_type: {test_name}')
            logger.info(f'test_id: {test_id}')
            
            
            # Run tests with unmutated Dawn to check if test passes
            #TODO: pass arguments
            run_unmutated_cmd = [f'{args.mutated_path}/tools/run',
                    'run-cts', 
                    '--verbose',
                    f'--bin={args.mutated_path}/out/Debug',
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
                logger.info('Runtime timeout')
                continue

            # Stdout contains 'FAIL:' if at least one test fails, else it does not
            # contain this string
            out = regular_execution_result.stdout.decode('utf-8')
        
            if 'FAIL:' in out:
                print(f"Std out:\n {regular_execution_result.stdout.decode('utf-8')}\n")
                print(f"Std err:\n {regular_execution_result.stderr.decode('utf-8')}\n")
                print("Execution of generated program failed without mutants.")
                print(f'The result included {get_failures(out)} failed tests.')
                logger.info(f'Execution of generated program failed without mutants: {get_failures(out)} failed tests')
                failed_tests = get_failures(out)
            
            else:
                failed_tests = 0
                print("Execution of generated program succeeded without mutants.")
                logger.info('Execution of generated program succeeded without mutants')

            print(f"Std out:\n {regular_execution_result.stdout.decode('utf-8')}\n")
            print(f"Std err:\n {regular_execution_result.stderr.decode('utf-8')}\n")
            
            # Compile the program with the mutant tracking compiler.
            print("Running with mutant tracking compiler...")
            tracking_environment = os.environ.copy()
            tracking_environment["DREDD_MUTANT_TRACKING_FILE"] = str(dredd_covered_mutants_path)
            tracking_compile_cmd = [f'{args.tracking_path}/tools/run',
                    'run-cts', 
                    '--verbose',
                    f'--bin={args.tracking_path}/out/Debug',
                    '--cts=/data/dev/webgpu_cts',
                    query]            
            mutant_tracking_result : ProcessResult = run_process_with_timeout(cmd=tracking_compile_cmd, timeout_seconds=args.compile_timeout, env=tracking_environment) 
            #mutant_tracking_result = subprocess.run(tracking_compile_cmd, env=tracking_environment)
            
            if mutant_tracking_result is None:
                print("Mutant tracking compilation timed out.")
                logger.info('Mutant tracking compilation timed out')
                continue
            elif not dredd_covered_mutants_path.exists():
                print(f"Std out:\n {mutant_tracking_result.stdout.decode('utf-8')}\n")
                print(f"Std err:\n {mutant_tracking_result.stderr.decode('utf-8')}\n")
                print("No mutant tracking file created.")
                logger.info('No mutant tracking file created')
                with open(Path(args.mutant_kill_path,f'tracking/no_tracking_file_{test_name}_{test_id}.txt'), 'w') as f:
                    f.write(query)
                continue
            else:
                print("Mutant tracking compilation complete")
                with open(dredd_covered_mutants_path, 'r') as f:
                    covered_mutants_info = f.read()
                with open(Path(args.mutant_kill_path,f'tracking/mutant_tracking_file_{test_name}_{test_id}.txt'), 'w') as f:
                    f.write(query)
                    f.write(covered_mutants_info)

            print(f"Std out:\n {mutant_tracking_result.stdout.decode('utf-8')}\n")
            print(f"Std err:\n {mutant_tracking_result.stderr.decode('utf-8')}\n")
            
            # Load file contents into a list. We go from list to set to list to eliminate duplicates.
            covered_by_this_test: List[int] = list(set([int(line.strip()) for line in
                                                        open(dredd_covered_mutants_path, 'r').readlines()]))
            covered_by_this_test.sort()
            candidate_mutants_for_this_test: List[int] = ([m for m in covered_by_this_test if m not in killed_mutants])
            
            print("Number of mutants to try: " + str(len(candidate_mutants_for_this_test)))
            already_killed_by_other_tests: List[int] = ([m for m in covered_by_this_test if m in killed_mutants])
            killed_by_this_test: List[int] = []
            covered_but_not_killed_by_this_test: List[int] = []

            # TESTING HERE
            print(f'Mutation tree: {mutation_tree.num_mutations}')
            print(f'Mutation tracking tree: {mutation_tree_for_coverage_tracking.num_mutations}')
            print(f'Covered: {covered_by_this_test}')
            #continue
            
            assignment_mutants = [95,96,97,98,99,100,101,102,103,104]
            candidate_mutants_for_this_test = [m for m in assignment_mutants if m not in killed_mutants]
            print("Number of mutants to try (short): " + str(len(candidate_mutants_for_this_test)))
            
            logger.info(f'Number of mutants to try: {str(len(candidate_mutants_for_this_test))}')
            for mutant in candidate_mutants_for_this_test:

                mutant_path = Path(args.mutant_kill_path,f'killed_mutants/{str(mutant)}')
                if mutant_path.exists():
                    print("Skipping mutant " + str(mutant) + " as it is noted as already killed.")
                    print(f'Unkilled mutants: {unkilled_mutants}')
                    unkilled_mutants.remove(mutant)
                    killed_mutants.add(mutant)
                    already_killed_by_other_tests.append(mutant)
                    continue
                
                print("Trying mutant " + str(mutant))
                
                mutated_cmd = [f'{args.mutated_path}/tools/run',
                    'run-cts', 
                    '--verbose',
                    f'--bin={args.mutated_path}/out/Debug',
                    '--cts=/data/dev/webgpu_cts',
                    query]    

                (mutant_result, mutant_stdout) = run_webgpu_cts_test_with_mutants(mutants=[mutant],
                        mutated_cmd=mutated_cmd,
                        timeout_seconds=args.compile_timeout,
                        failed_tests=failed_tests)
                
                kill_gpu_processes('node')

                if mutant_result == CTSKillStatus.SURVIVED or mutant_result == CTSKillStatus.TEST_TIMEOUT:
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
                        json.dump({"killing_test": query,
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
            with open(args.mutant_kill_path / f'kill_summary_{test_name}_{test_id}.json', "w") as outfile:
                json.dump({"query": query,
                           "covered_mutants": covered_by_this_test,
                           "killed_mutants": killed_by_this_test,
                           "skipped_mutants": already_killed_by_other_tests,
                           "survived_mutants": covered_but_not_killed_by_this_test}, outfile)
            
            logger.info('Query complete')

if __name__ == '__main__':
    main()
