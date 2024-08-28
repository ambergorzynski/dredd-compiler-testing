import json
from pathlib import Path

def main():
    
    base_path = Path('/data/work/tint_mutation_testing/output/spirv_ast_printer')

    info : dict[str,list[int]] = {}

    # Load covered mutants for each test
    for file in base_path.iterdir():
        if 'kill_summary_cts' in str(file):
            with open(file, 'r') as f:
                test_summary = json.load(f)
                info[test_summary['query']] = test_summary['covered_mutants']

    print(f'dict size is {len(info)}')

    # Check whether covered mutants are all the same
    (q, mutants) = list(info.items())[0]

    for (query, mut) in info.items():
        print(query)
        if mut != mutants:
            print('Entries do not match!')
            print(f'Query: {query}')
            print(f'Mutants: {mutants}')
            print(f'Mut: {mut}')

    





if __name__=="__main__":
    main()