from pathlib import Path
import subprocess

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
    if base == 'webgpu':
        return base + ':' + directory
    return base + ',' + directory

def file_query(base : str, filename : str) -> str:
    separator = ':' if base == 'webgpu' else ','
    return base + separator + filename.removesuffix('.spec.ts') + ':*'

def test():
    run_test('webgpu:examples:gpu,buffers:*')

def main():
    webgpu_cts_path = Path('/data/dev/webgpu_cts/src/webgpu')
    
    base_query_string = 'webgpu'

    tests = get_tests(webgpu_cts_path, base_query_string)
    
    print(f'Tests are:')

    for t in tests:
        print(t)

    #run_test(tests[0])

if __name__=="__main__":
    main()
