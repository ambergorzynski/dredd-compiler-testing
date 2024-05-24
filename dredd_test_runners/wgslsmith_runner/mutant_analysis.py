from pathlib import Path
import subprocess
import itertools
import json


def get_mutant_info(filepath : Path) -> dict:

    mutants = [d for d in filepath.iterdir() if d.is_dir()]

    mutant_info = {}

    for mutant in mutants:
        f = open(f'{str(mutant)}/kill_info.json')
        info = json.load(f)
        mutant_info[mutant.stem] = info
        f.close()

    return mutant_info

def get_test_summary_info(filepath : Path) -> dict:

    tests = [d for d in filepath.iterdir() if not d.is_dir()]

    test_info = {}

    for test in tests:
        f = open(test)
        info = json.load(f)
        test_info[test.stem] = info
        f.close()

    return test_info



def get_tracking_info(filepath : Path):

    tracking_info = {}
    no_tracking_info = {}

    for file in filepath.iterdir():
        with open(file, 'r') as f:
            query = f.readline()

        if 'no_tracking_file' in file.stem:
            no_tracking_info[query] = file.stem

        else:
            tracking_info[query] = file.stem

    return (tracking_info, no_tracking_info)

def print_tracking_info(cts_path : Path, mutants_killed_by_cts : list):

    print('\nTracking info for cts:')

    (track, no_track) = get_tracking_info(cts_path)

    print(f'Out of {len(track) + len(no_track)} WebGPU CTS tests, {len(track)} track at least 1 mutant and {len(no_track)} track no mutants')

    tracking_categories = [k[k.index(':')+1:k.index(',')] 
            if ',' in k 
            else k[k.index(':'):]
            for k, v in track.items()]
    
    no_tracking_categories = [k[k.index(':')+1:k.index(',')] 
            if ',' in k 
            else k[k.index(':'):]
            for k, v in no_track.items()]
    
    all_categories = list(set(tracking_categories + no_tracking_categories))

    print('\nTotal tests in each category that track mutants:')
    for i in all_categories:
        print(f'{i} : {tracking_categories.count(i)}')

    print('\nTotal tests in each category that do not track mutants:')
    for i in all_categories:
        print(f'{i} : {no_tracking_categories.count(i)}')

def flatten(somelist : list) -> list:
    return [i for item in somelist for i in item]

if __name__=="__main__":

    base = Path("/data/work/tint_mutation_testing/spirv_ast_printer_cts")
    info = get_mutant_info(Path(base, 'killed_mutants'))
    print(f"Example mutant info for mutant 8: {info['8']}")
    
    total_mutants_killed = len(info)
    mutants_killed_by_cts = {k:v for k, v in info.items() if 'webgpu' in v['killing_test']}
    mutants_killed_by_wgslsmith = {k:v for k, v in info.items() if 'wgslsmith' in v['killing_test']}
    
    assert len(mutants_killed_by_cts) + len(mutants_killed_by_wgslsmith) == total_mutants_killed

    print(f'Mutants killed by cts: {len(mutants_killed_by_cts)}')
    print(f'Mutants killed by wgslsmith: {len(mutants_killed_by_wgslsmith)}')

    wgslsmith_crashes = len({k for k, v in mutants_killed_by_wgslsmith.items() if 'CRASH' in v['kill_type']})

    wgslsmith_mismatch = len({k for k, v in mutants_killed_by_wgslsmith.items() if 'DIFFERENT' in v['kill_type']})

    print(f'Of the mutants killed by wgslsmith: \n {wgslsmith_mismatch} were stdout/stderr mismatches \n {wgslsmith_crashes} were crashes')

    print_tracking_info(Path(base,'tracking'), mutants_killed_by_cts)

    test_info = get_test_summary_info(Path(base))

    covered_mutants = [v['covered_mutants'] for k, v in test_info.items()]

    unique_covered_mutants = list(set(flatten(covered_mutants)))    
    
    print(f'\nNumber of covered mutants is {len(unique_covered_mutants)}')

    print(f'Covered mutants are: {unique_covered_mutants}')

    tests_that_cover_15 = [v['query'] for k, v in test_info.items() if 15 in v['covered_mutants']]

    print(f'Tests that cover 15: {len(tests_that_cover_15)}')

    '''
    cts_mutant_ids = [k for k, v in mutants_killed_by_cts.items()]

    for i in cts_mutant_ids[:5]:
        print(f'Mutant: {i} Kill info: {mutants_killed_by_cts[i]}')
 
    wgslsmith_mutant_ids = [k for k, v in mutants_killed_by_wgslsmith.items() if 'DIFFERENT' in v['kill_type']]

    for i in wgslsmith_mutant_ids:
        print(f'Mutant: {i} Kill info: {mutants_killed_by_wgslsmith[i]}')
    '''

