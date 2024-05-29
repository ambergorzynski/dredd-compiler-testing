from enum import Enum
import platform
import sys
import os
import json

sys.path.append('../..')

from dredd_test_runners.common.constants import DEFAULT_COMPILATION_TIMEOUT, DEFAULT_RUNTIME_TIMEOUT
from dredd_test_runners.common.run_process_with_timeout import ProcessResult, run_process_with_timeout
from dredd_test_runners.wgslsmith_runner.webgpu_cts_utils import kill_gpu_processes, get_tests, get_single_tests_from_stdout

from pathlib import Path

class Plat(Enum):
    LINUX=1
    MACOS=2

def main():
    print(platform.platform())
    system = Plat.LINUX if 'Linux' in platform.platform() else Plat.MACOS
    base : Path = Path('/data/dev/') if system == Plat.LINUX else Path('/Users/ambergorzynski/dev')
    dawn_path : Path=Path(base, 'dawn')
    #dawn_path : Path = Path(base, 'dawn_mutated') if system == Plat.LINUX else Path(base, 'dawn')
    cts_path : Path = Path(base, 'webgpu_cts')
    output_path : Path = Path(base, 'dredd-compiler-testing/cts_test_info')
    get_tests_file :Path = Path(output_path, 'test_info.txt')
    manual_check_file : Path = Path(output_path, 'manual_checks.txt')
    individual_queries_file :Path = Path(output_path, 'individual_queries.json')
    n_runs : int = 10 

    # Get file-level CTS queries
    base_query_string = 'webgpu'
    cts_queries = get_tests(Path(cts_path,'src/webgpu'), base_query_string)

    # Temporary
    #cts_queries = ['webgpu:shader,execution,expression,call,builtin,textureDimensions:*']
    #cts_queries = ['webgpu:shader,execution,expression,call,builtin,textureDimensions:sampled_and_multisampled:format="r32sint";aspect="all";samples=1']

    individual_cts_queries = []

    if manual_check_file.exists():
        os.remove(get_tests_file)

    # Run file-level test once to get individual tests
    for query in cts_queries:        
        cmd = [f'{dawn_path}/tools/run',
            'run-cts', 
            '--verbose',
            f'--bin={dawn_path}/out/Debug',
            f'--cts={cts_path}',
            query]

        print(f'Get individual tests from file query:\n{query}')
        result: ProcessResult = run_process_with_timeout(
                cmd=cmd, timeout_seconds=None)
 
        if get_tests_file.exists():
            os.remove(get_tests_file)

        with open(get_tests_file, 'w') as f:
            f.write(result.stderr.decode('utf-8'))
            f.write(result.stdout.decode('utf-8'))

        # Kill gpu processes - sometimes this is not done automatically
        # when running tests individually, which messes up
        # future tests
        if 'Linux' in platform.platform():
            kill_gpu_processes('node')
        
        # Parse stdout to get a list of individual tests and their statuses
        queries = list(get_single_tests_from_stdout(get_tests_file).keys())
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
    for i in range(n_runs):
    
        output_file = Path(output_path, f'test_output_{i}.txt')
 
        if output_file.exists():
            os.remove(output_file)

        for query in individual_cts_queries:        
            cmd = [f'{dawn_path}/tools/run',
                'run-cts', 
                '--verbose',
                f'--bin={dawn_path}/out/Debug',
                f'--cts={cts_path}',
                query]
        
            print(f'Run {i} query: {query}')
            result: ProcessResult = run_process_with_timeout(
                    cmd=cmd, timeout_seconds=None)

            with open(output_file, 'a') as f:
                f.write(result.stderr.decode('utf-8'))
                f.write(result.stdout.decode('utf-8'))

            # Kill gpu processes - this is not done automatically
            # when running tests individually, which messes up
            # future tests
            if 'Linux' in platform.platform():
                kill_gpu_processes('node')
            
        # Parse stdout to get a list of individual tests and their statuses
        single_tests.append(get_single_tests_from_stdout(output_file))   

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
