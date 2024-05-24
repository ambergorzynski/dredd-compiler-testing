from pathlib import Path
import subprocess
import re
from enum import Enum

class TestStatus(Enum):
    PASS = 1
    FAIL = 2
    SKIP = 3

def kill_gpu_processes(id : str):
    print("Killing mutant GPU processes")
                            
    nvidia_smi = subprocess.Popen(
            ["nvidia-smi"], 
            stdout=subprocess.PIPE
            )
    processes = subprocess.Popen(
            ["grep",id], 
            stdin=nvidia_smi.stdout, 
            stdout=subprocess.PIPE, 
            text=True
            )

    p_output, p_error = processes.communicate()
    print(f'Node return code: {processes.returncode}')

    if processes.returncode == 0:

        nvidia_smi = subprocess.Popen(
                ["nvidia-smi"], 
                stdout=subprocess.PIPE
                )
        processes = subprocess.Popen(
                ["grep","node"], 
                stdin=nvidia_smi.stdout, 
                stdout=subprocess.PIPE, 
                text=True
                )
        pid_to_kill = subprocess.Popen(
                ["awk","{ print $5 }"],
                stdin=processes.stdout,
                stdout=subprocess.PIPE,
                text=True
                )
        kill = subprocess.Popen(
                ["xargs", "-n1", "kill", "-9"],
                stdin=pid_to_kill.stdout,
                stdout=subprocess.PIPE,
                text=True
                )
        
        output, error = kill.communicate()
        print('Dead!') 

def get_single_tests_from_stdout(filename : Path) -> dict[str,str]:
    '''
    Parses stdout from running the WebGPU CTS to retrieve a 
    dictionary containing all individual tests and their
    status (pass; fail; skip)
    '''
    
    with open(filename, 'r') as f:
        lines = f.readlines()

    test_lines = [i for i in lines if 'pass:' in i or 'fail:' in i or 'skip:' in i]

    tests = {t[:t.index(' ')] : t[t.index(' - ')+3:].replace(':','').strip() for t in test_lines}

    # Check that the only values are pass/fail/skip
    check = {k:v for (k,v) in tests.items() if v != 'pass' and v != 'fail' and v != 'skip'}

    assert(len(check) == 0)

    return tests


def get_unrun_tests() -> list:

    webgpu_cts_path = Path('/data/dev/webgpu_cts/src/webgpu')
    cts_base_query_string = 'webgpu'

    cts_tests = get_tests(webgpu_cts_path, cts_base_query_string)
    
    tests_that_ran = get_test_info(Path('/data/work/tint_mutation_testing/spirv_ast_printer_cts/tracking'))

    tests_that_did_not_run =[t for t in cts_tests if t not in tests_that_ran]

    return tests_that_did_not_run

def get_test_info(filepath : Path):

    tests = []

    for file in filepath.iterdir():
        with open(file, 'r') as f:
            query = f.readline()            
            tests.append(query[:query.index('*')+1])

    return tests

def run_test(query : str) -> None:

    #TODO: pass filepaths as arguments 
    cmd = ['/data/dev/dawn_mutated/tools/run',
            'run-cts', 
            '--verbose',
            '--bin=/data/dev/dawn_mutated/out/Debug',
            '--cts=/data/dev/webgpu_cts',
            query]
            #            'webgpu:examples:gpu,buffers:*']

    result = subprocess.run(cmd)

    print('Finish')

def get_tests(path : Path, base : str) -> list[str]:
    ''' 
        Function returns a list of query strings for
        all tests in the directory (including sub-
        directories)
    '''

    # Get all test filenames in current directory
    filenames = [f.name for f in path.iterdir() if f.is_file()
            and f.suffixes == ['.spec','.ts']]

    # Convert filenames to queries
    queries = [file_query(base, f) for f in filenames]

    # Loop over subdirectories and get tests
    subdirectories = [d for d in path.iterdir() if d.is_dir()]

    for sub in subdirectories:
        query_base = dir_query(base, sub.name)
        queries.extend(get_tests(sub, query_base))

    return queries

def dir_query(base : str, directory :str) -> str:
    if base == 'webgpu' or base == 'unittests':
        return base + ':' + directory
    return base + ',' + directory

def file_query(base : str, filename : str) -> str:
    separator = ':' if base == 'webgpu' or base == 'unittests' else ','
    return base + separator + filename.removesuffix('.spec.ts') + ':*'

def test():
    run_test('webgpu:examples:gpu,buffers:*')

def get_failures(stdout : str) -> int:

    matched = re.search(r'(?<=FAIL: )\d+',stdout)

    return int(matched.group())

def get_passes(stdout : str) -> int:

    matched = re.search(r'(?<=PASS: )\d+',stdout)

    return int(matched.group())

def main():
    webgpu_cts_path = Path('/data/dev/webgpu_cts/src/webgpu')
    cts_base_query_string = 'webgpu'

    cts_tests = get_tests(webgpu_cts_path, cts_base_query_string)
    
    print(f'CTS tests are:')

    for t in cts_tests:
        print(t)

    #run_test(cts_tests[0])

    unittest_path = Path('/data/dev/webgpu_cts/src/unittests')
    unit_base_query_string = 'unittests'

    unit_tests = get_tests(unittest_path, unit_base_query_string)
    
    print(f'Unit tests are:')

    for t in unit_tests:
        print(t)

    #run_test(unit_tests[0])

    print(f'\nThere are {len(cts_tests)} CTS tests and {len(unit_tests)} unit tests')

    with open('/data/dev/dredd-compiler-testing/dredd_test_runners/wgslsmith_runner/cts_test_scripts/out.txt', 'r') as f:
        stdout = f.read()

    regex = get_failures('3 FAIL: 33 4')
    
    stdout_regex = get_failures(stdout)
    
    print(stdout_regex)

    '''
    tests_that_ran = get_test_info(Path('/data/work/tint_mutation_testing/spirv_ast_printer_cts/tracking'))

    print(tests_that_ran)

    tests_that_did_not_run =[t for t in cts_tests if t not in tests_that_ran]

    print(tests_that_did_not_run)

    print(f'\nOut of {len(cts_tests)}, {len(tests_that_ran)} tests ran and {len(tests_that_did_not_run)} did not run')
    '''

def getlines():
    
    path = Path('/data/dev/dredd-compiler-testing/dredd_test_runners/wgslsmith_runner/cts_test_scripts/attempt1.txt')

    get_single_tests_from_stdout(path) 

if __name__=="__main__":
    #main()
    getlines()
