from enum import Enum
import platform
import sys
import os
import json
import argparse

sys.path.append('../..')

from dredd_test_runners.common.constants import DEFAULT_COMPILATION_TIMEOUT, DEFAULT_RUNTIME_TIMEOUT
from dredd_test_runners.common.run_process_with_timeout import ProcessResult, run_process_with_timeout
from dredd_test_runners.wgslsmith_runner.webgpu_cts_utils import kill_gpu_processes, get_single_tests_from_stdout, get_single_tests_from_file

from pathlib import Path

class Plat(Enum):
    LINUX=1
    MACOS=2

def main():

    parser = argparse.ArgumentParser()

    parser.add_argument("dawn_path",
                        help="Absolute file path to Dawn.",
                        type=Path)
    parser.add_argument("cts_path",
                        help="Absolute file path to WebGPU CTS.",
                        type=Path)
    parser.add_argument("output_path",
                        help="Absolute file path to output location where results should be stored.",
                        type=Path),
    parser.add_argument("query_file",
                        help="Absolute file path to list of individual CTS queries.",
                        type=Path)
    parser.add_argument("--update_queries",
                        default=False,
                        action=argparse.BooleanOptionalAction,
                        help="Update CTS individual tests instead of getting from existing list. Default is false.")
    parser.add_argument("--n_runs",
                        default=3,
                        help="Number of times to run the CTS to check stability. Default is 3.",
                        type=int)
    args = parser.parse_args()

    if not args.query_file.exists() and not args.update_queries:
        print('Query file does not exist! You must update queries if your query file does not yet exist!')
        exit(1)                    

    system = Plat.LINUX if 'Linux' in platform.platform() else Plat.MACOS
    
    manual_check_file : Path = Path(args.output_path, 'manual_checks.txt')
    
    individual_queries_file :Path = Path(args.output_path, 'individual_queries.json')

    if args.update_queries:

        #cts_queries = ['webgpu:*']
        cts_queries = ['webgpu:shader,execution,expression,call,builtin,textureDimensions:*']
        #cts_queries = ['webgpu:shader,execution,expression,call,builtin,textureDimensions:sampled_and_multisampled:format="r32sint";aspect="all";samples=1']

        individual_cts_queries = []

        if manual_check_file.exists():
            os.remove(manual_check_file)

        for query in cts_queries:        
            cmd = [f'{args.dawn_path}/tools/run',
                'run-cts', 
                '--verbose',
                f'--bin={args.dawn_path}/out/Debug',
                f'--cts={args.cts_path}',
                query]

            print(f'Get individual tests from query:\n{query}')
            result: ProcessResult = run_process_with_timeout(
                    cmd=cmd, timeout_seconds=None)
    
            if args.query_file.exists():
                os.remove(args.query_file)

            with open(args.query_file, 'w') as f:
                f.write(result.stderr.decode('utf-8'))
                f.write(result.stdout.decode('utf-8'))

            # Kill gpu processes - sometimes this is not done automatically
            # when running tests individually, which messes up
            # future tests
            if 'Linux' in platform.platform():
                kill_gpu_processes('node')
            
            # Parse stdout to get a list of individual tests and their statuses
            queries = list(get_single_tests_from_file(args.query_file).keys())
            individual_cts_queries.extend(queries) 
            print(f'Number of individual tests: {len(queries)}')
            print(f'Running total of individual tests: {len(individual_cts_queries)}')

            # Record any file level queries that resulted in zero individual queries
            # for manual checking. This can happen if a file exists that does not export
            # any tests, e.g. while it is still under development
            if len(queries) == 0:
                with open(manual_check_file, 'a') as f:
                    f.write(f'Query: {query}')
                    f.write(result.stderr.decode('utf-8'))
                    f.write(result.stdout.decode('utf-8'))


    # Exit if there are no individual queries to run
    if len(individual_cts_queries) == 0:
        print('No individual queries to run!')
        exit()

    results = []
    single_tests = []

    # Save individual queries
    with open(individual_queries_file, 'w') as f:
        json.dump(individual_cts_queries, f, indent=2)

    # Run CTS three times to determine which tests always pass
    for i in range(args.n_runs):
    
        output_file = Path(args.output_path, f'test_stdout_{i}.txt')
        summary_file = Path(args.output_path, f'test_summary_{i}.txt')
 
        if output_file.exists():
            os.remove(output_file)
        
        if summary_file.exists():
            os.remove(summary_file)

        for query in individual_cts_queries:        
            cmd = [f'{args.dawn_path}/tools/run',
                'run-cts', 
                '--verbose',
                f'--bin={args.dawn_path}/out/Debug',
                f'--cts={args.cts_path}',
                query]
        
            print(f'Run {i} query: {query}')
            result: ProcessResult = run_process_with_timeout(
                    cmd=cmd, timeout_seconds=None)

            # Kill gpu processes - this is not always done automatically
            # when running tests individually, which messes up
            # future tests
            if 'Linux' in platform.platform():
                kill_gpu_processes('node')

            # Record stdout and outcomes
            with open(output_file, 'a') as f:
                f.write(result.stderr.decode('utf-8'))
                f.write(result.stdout.decode('utf-8'))

            output = result.stdout.decode('utf-8').split('\n')

            query_status = get_single_tests_from_stdout(output)

            with open(summary_file, 'a') as f:
                for (query,status) in query_status.items():
                    f.write(f'{query} - {status}\n')      
            
        # Parse stdout to get a list of individual tests and their statuses
        single_tests.append(get_single_tests_from_file(output_file))   

        # Keep the individual tests that pass
        results.append(set([query for (query, status) in single_tests[i].items() if status == 'pass']))

    # Find the tests that pass on all three runs
    reliable_tests = results[0]

    for i in range (1, n_runs):
        print(f'{len(results[i])} tests pass in run {i}')
        reliable_tests &= results[i]

    # Check
    print('Tests:')
    for test in reliable_tests:
        for i in range(n_runs):
            assert single_tests[i][test] == 'pass'

    print(f'Found {len(reliable_tests)} reliable tests out of a possible {len(single_tests[0])}')


if __name__=="__main__":
    main()
