# dredd-compiler-testing
Scripts to allow the Dredd mutation testing framework to be used for compiler testing

## Build and interactive install steps

```
python -m build
python -m pip install -e .
```

## Scripts to figure out which Dredd-induced mutants are killed by the LLVM test suite

You point it at:

- A checkout of the LLVM test suite
- A compilation database for the test suite
- The mutated compiler and mutant tracking compiler
- Associated JSON files with mutation info

It considers the tests in the suite in turn and determines which
mutants they kill.

Command to invoke llvm-test-suite-runner on Ally's machine:

```
llvm-test-suite-runner /home/afd/dev/llvm-project/dredd.json /home/afd/dev/llvm-project-mutation-tracking/dredd.json /home/afd/dev/llvm-project/build/bin /home/afd/dev/llvm-project-mutation-tracking/build/bin /home/afd/dev/llvm-test-suite /home/afd/dev/llvm-test-suite/build/compile_commands.json
```

To run many instances in parallel (16):

```
for i in `seq 1 16`; do llvm-test-suite-runner /home/afd/dev/llvm-project/dredd.json /home/afd/dev/llvm-project-mutation-tracking/dredd.json /home/afd/dev/llvm-project/build/bin /home/afd/dev/llvm-project-mutation-tracking/build/bin /home/afd/dev/llvm-test-suite /home/afd/dev/llvm-test-suite/build/compile_commands.json & done
```

To kill them:

```
pkill -9 -f llvm-test-suite
```

Watch out for left over `clang` processes!



