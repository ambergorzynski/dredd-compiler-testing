from pathlib import Path
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

if __name__=="__main__":
    path = Path("/data/work/tint_mutation_testing/spirv_ast_printer/killed_mutants")
    info = get_mutant_info(path)
    print(f"Example mutant info for mutant 10: {info['10']}")
    
    total_mutants_killed = len(info)
    mutants_killed_by_cts = len([k for k, v in info.items() if 'webgpu' in v['killing_test']])
    mutants_killed_by_wgslsmith = len({k for k, v in info.items() if 'wgslsmith' in v['killing_test']})

    assert mutants_killed_by_cts + mutants_killed_by_wgslsmith == total_mutants_killed

    print(f'Mutants killed by cts: {mutants_killed_by_cts}')
    print(f'Mutants killed by wgslsmith: {mutants_killed_by_wgslsmith}')

    wgslsmith_crashes = len({k for k, v in info.items() if 'wgslsmith' in v['killing_test'] 
        and 'CRASH' in v['kill_type']})

    wgslsmith_mismatch = len({k for k, v in info.items() if 'wgslsmith' in v['killing_test'] 
        and 'DIFFERENT' in v['kill_type']})

    print(f'Of the mutants killed by wgslsmith: \n {wgslsmith_mismatch} were stdout/stderr mismatches \n {wgslsmith_crashes} were crashes')
