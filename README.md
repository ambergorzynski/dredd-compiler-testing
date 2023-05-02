# dredd-compiler-testing

Scripts to allow the Dredd mutation testing framework to be used to generate test cases that improve mutation coverage.

## Build mutated versions of clang

* TODO: clone LLVM into llvm-project-mutated
* TODO: clone the clone into llvm-project-mutant-tracking
* TODO: check out a suitable tag for each repo
* TODO: cmake with compile commands in mutated repo
* TODO: build core components of mutated repo
* TODO: run dredd on mutated repo
* TODO: build entire LLVM project in mutated repo
* TODO: cmake with compile commands in tracking repo
* TODO: build core components of tracking repo
* TODO: run dredd on tracking repo
* TODO: build entire LLVM project in tracking repo




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
llvm-test-suite-runner $MUTATED_ROOT/dredd.json $TRACKING_ROOT/dredd.json $MUTATED_ROOT/build/bin $TRACKING_ROOT/build/bin $LLVM_TEST_SUITE_ROOT $LLVM_TEST_SUITE_ROOT/build/compile_commands.json
```

To run many instances in parallel (16):

```
for i in `seq 1 16`; do llvm-test-suite-runner $MUTATED_ROOT/dredd.json $TRACKING_ROOT/dredd.json $MUTATED_ROOT/build/bin $TRACKING_ROOT/build/bin $LLVM_TEST_SUITE_ROOT $LLVM_TEST_SUITE_ROOT/build/compile_commands.json & done
```

To kill them:

```
pkill -9 -f llvm-test-suite
```

Watch out for left over `clang` processes!






```
FILES=""
for f in `find llvm/lib/Transforms/InstCombine -name "*.cpp"`; do FILES="$FILES $f"; done
```

```
/data/afd/dredd/third_party/clang+llvm/bin/dredd -p build/compile_commands.json --mutation-info-file dredd.json $FILES
```

```
/data/afd/dredd/third_party/clang+llvm/bin/dredd -p build/compile_commands.json --mutation-info-file dredd.json --only-track-mutant-coverage $FILES
```









for i in `seq 1 4`; do llvm-regression-tests-runner $MUTATED_ROOT/dredd.json $TRACKING_ROOT/dredd.json $MUTATED_ROOT/build/bin $TRACKING_ROOT/build/bin $MUTATED_ROOT/llvm/test/Transforms/InstCombine $TRACKING_ROOT/llvm/test/Transforms/InstCombine & done
