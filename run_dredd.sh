#!/bin/sh

BASE=/data/dev

MUTATION_INFO_FILE=${BASE}/dawn_mutated/out/Debug/compile_commands.json
MUTATION_INFO_FILE_FOR_MUTANT_COVERAGE_TRACKING=${BASE}/dawn_mutant_tracking/out/Debug/compile_commands.json
MUTATED_COMPILER_EXE=${BASE}/dawn_mutated/out/Debug/tint
MUTATED_TRACKING_COMPILER_EXE=${BASE}/dawn_mutant_tracking/out/Debug/tint
WGSLSMITH_EXE=${BASE}/wgslsmith_updated_dawn/target/release/wgslsmith

python3 ${BASE}/dredd-compiler-testing/dredd_test_runners/wgslsmith_runner/main.py /
    $MUTATION_INFO_FILE /
    $MUTATION_INFO_FILE_FOR_MUTANT_COVERAGE_TRACKING /
    $MUTATED_COMPILER_EXE /
    $MUTATED_TRACKING_COMPILER_EXE /
    $WGSLSMITH_EXE
