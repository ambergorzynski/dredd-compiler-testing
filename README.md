# dredd-compiler-testing
Scripts to allow the Dredd mutation testing framework to be used for compiler testing






Scripts to figure out which Dredd-induced mutants are killed by the
LLVM test suite.

You point it at:

- A checkout of the LLVM test suite
- A compilation database for the test suite
- The mutated compiler and mutant tracking compiler
- Associated JSON files with mutation info

It considers the tests in the suite in turn and determines which
mutants they kill.

Command to invoke llvm-test-suite-runner on Ally's machine:

llvm-test-suite-runner /home/afd/dev/llvm-project/dredd.json /home/afd/dev/llvm-project-mutation-tracking/dredd.json /home/afd/dev/llvm-project/build/bin/clang /home/afd/dev/llvm-project-mutation-tracking/build/bin/clang /home/afd/dev/llvm-test-suite /home/afd/dev/llvm-test-suite/build/compile_commands.json