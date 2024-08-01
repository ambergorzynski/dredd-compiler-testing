from pathlib import Path
import subprocess
import re
from enum import Enum

class TestStatus(Enum):
    PASS = 1
    FAIL = 2
    SKIP = 3

def get_completed_queries(log : Path) -> list[str]:
    
    with open(log, 'r') as f:
        log_info = f.readlines()

    queries = [line[7:].strip() for line in log_info if line[:6] == "Query:"]
    
    # Remove final query since it will be unfinished
    return queries[:-1]

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
        print('GPU processes dead!') 

def get_single_tests_from_file(filename : Path) -> dict[str,str]:
    '''
    Parses file containing stdout from running the WebGPU CTS to retrieve a 
    dictionary containing all individual tests and their
    status (pass; fail; skip)
    '''
    
    with open(filename, 'r') as f:
        lines = f.readlines()

    return get_single_tests_from_stdout(lines)



def get_single_tests_from_stdout(stdout : list) -> dict[str,str]:
    '''
    Parses list containing stdout from running the WebGPU CTS to retrieve a 
    dictionary containing all individual tests and their
    status (pass; fail; skip)
    '''
    test_lines = [i for i in stdout if ' - pass' in i or ' - fail' in i or ' - skip' in i]

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

def get_tests(src : Path, query : str) -> list[str]:
    '''
        Function returns a list of query strings for
        all tests in the directory (including sub-
        directories)

        src is the path to the WebGPU CTS e.g. /data/dev/webgpu_cts/src
        query is the query for which we want to find all individual tests
            e.g. 'webgpu:*', 'webgpu:shader,*', 'unittests:*'
    '''

    # Get base directory for query
    # If the query ends with :* then the final item is a file, return immediately
    #   except for top-level queries webgpu:* and unittests:*
    # If the query ends with ,* then the final item is a folder, continue searching
    if query != 'webgpu:*' and query != 'unittests:*' and query[-2:] == ':*':
        return [query]

    folders_string = query.replace('*','').replace(':','/').replace(',','/')
    
    base_dir = Path(src, folders_string)
    

    # Get all test filenames in current directory
    filenames = [f.name for f in base_dir.iterdir() if f.is_file()
            and f.suffixes == ['.spec','.ts']]
    

    # Convert filenames to queries
    queries = [file_query(query, f) for f in filenames]


    subdirectories = [d for d in base_dir.iterdir() if d.is_dir()]

    for sub in subdirectories:
        sub_query = dir_query(query, sub)
        queries.extend(get_tests(src, sub_query))
    
    return queries

def dir_query(base : str, directory : Path) -> str:
    directory = str(directory).split('/')[-1]
    return base.replace('*','') + directory + ',*'


def file_query(base_query : str, filename : str) -> str:     
    return base_query.replace('*','') + filename.removesuffix('.spec.ts') + ':*'

def test():
    run_test('webgpu:examples:gpu,buffers:*')

def get_failures(stdout : str) -> int:

    matched = re.search(r'(?<=FAIL: )\d+',stdout)

    return int(matched.group())

def get_passes(stdout : str) -> int:

    matched = re.search(r'(?<=PASS: )\d+',stdout)

    return int(matched.group())

def check_queries():
    base = Path('/data/dev/webgpu_cts/src')
    queries = ['webgpu:*',
            'webgpu:shader,*',
            'webgpu:shader,execution,flow_control,complex:*',
            'unittests:*']

    for q in queries:
        tests = get_tests_new(base,q)
        print(f'Query: {q}')
        print(f'Tests: {tests}')

def main():
    log_path = Path('/data/work/tint_mutation_testing/output/spirv_ast_printer/info.log')
    queries = get_completed_queries(log_path)

    print(f'\n\n{queries}')

def getlines():
    
    path = Path('/data/dev/dredd-compiler-testing/output/query_file.txt')

    return get_single_tests_from_file(path) 

def check_query_stability(query : str):

    get_single_tests_from_file(file)

    pass_tests

if __name__=="__main__":
    main()
    #output = getlines()
