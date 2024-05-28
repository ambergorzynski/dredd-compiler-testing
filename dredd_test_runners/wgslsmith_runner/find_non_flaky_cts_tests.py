import sys
import os

sys.path.append('../..')

from dredd_test_runners.common.constants import DEFAULT_COMPILATION_TIMEOUT, DEFAULT_RUNTIME_TIMEOUT
from dredd_test_runners.common.run_process_with_timeout import ProcessResult, run_process_with_timeout
from dredd_test_runners.wgslsmith_runner.webgpu_cts_utils import kill_gpu_processes, get_tests, get_single_tests_from_stdout

from pathlib import Path

def main():
    
    dawn_path : Path = Path('/data/dev/dawn_mutated')
    cts_path : Path = Path('/data/dev/webgpu_cts')
    output_path : Path = Path('/data/dev/dredd-compiler-testing/cts_test_info')
    n_runs : int = 3

    # Get file-level CTS queries
    base_query_string = 'webgpu'
    cts_queries = get_tests(Path(cts_path,'src/webgpu'), base_query_string)

    # Temporary
    cts_queries = ['webgpu:shader,execution,expression,call,builtin,textureDimensions:*']

    results = []
    single_tests = []

    # Run CTS three times to determine which tests always pass
    for i in range(n_runs):
    
        output_file = Path(output_path, f'test_output_{i}.txt')
 
        if output_file.exists():
            os.remove(output_file)

        for query in cts_queries:        
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
            kill_gpu_processes('node')
            
        # Parse stdout to get a list of individual tests and their statuses
        single_tests.append(get_single_tests_from_stdout(output_file))   

        # Keep the individual tests that pass
        results.append(set([query for (query, status) in single_tests[i].items() if status == 'pass']))

    # Find the tests that pass on all three runs
    reliable_tests = results[0]

    for i in range (1, n_runs):
        reliable_tests &= results[i]

    # Check
    print('Tests:')
    for test in reliable_tests:
        print(test)
        for i in range(n_runs):
            assert single_tests[i][test] == 'pass'

    print(f'Found {len(reliable_tests)} reliable tests out of a possible {len(single_tests[0])}')


if __name__=="__main__":
    main()
