from pathlib import Path
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

if __name__=="__main__":
    path = Path("/data/work/tint_mutation_testing/spirv_ast_printer/killed_mutants")
    info = get_mutant_info(path)
    print(f"Example mutant info for mutant 10: {info['10']}")
    
    total_mutants_killed = len(info)
    mutants_killed_by_cts = {k:v for k, v in info.items() if 'webgpu' in v['killing_test']}
    mutants_killed_by_wgslsmith = {k:v for k, v in info.items() if 'wgslsmith' in v['killing_test']}

    assert len(mutants_killed_by_cts) + len(mutants_killed_by_wgslsmith) == total_mutants_killed

    print(f'Mutants killed by cts: {len(mutants_killed_by_cts)}')
    print(f'Mutants killed by wgslsmith: {len(mutants_killed_by_wgslsmith)}')

    wgslsmith_crashes = len({k for k, v in mutants_killed_by_wgslsmith.items() if 'CRASH' in v['kill_type']})

    wgslsmith_mismatch = len({k for k, v in mutants_killed_by_wgslsmith.items() if 'DIFFERENT' in v['kill_type']})

    print(f'Of the mutants killed by wgslsmith: \n {wgslsmith_mismatch} were stdout/stderr mismatches \n {wgslsmith_crashes} were crashes')
    
    cts_mutant_ids = [k for k, v in mutants_killed_by_cts.items()]

    for i in cts_mutant_ids[:5]:
        print(f'Mutant: {i} Kill info: {mutants_killed_by_cts[i]}')
 
    wgslsmith_mutant_ids = [k for k, v in mutants_killed_by_wgslsmith.items() if 'DIFFERENT' in v['kill_type']]

    for i in wgslsmith_mutant_ids:
        print(f'Mutant: {i} Kill info: {mutants_killed_by_wgslsmith[i]}')


    print('\nTracking info for cts:')

    cts_path = Path("/data/work/tint_mutation_testing/spirv_ast_printer_cts/tracking")
    (track, no_track) = get_tracking_info(cts_path)

    print('Tracked:')
    for v, k in track.items():
        print(f'{v} : {k}')

    print('\nNot tracked:')
    for v, k in no_track.items():
        print(f'{v} : {k}')
