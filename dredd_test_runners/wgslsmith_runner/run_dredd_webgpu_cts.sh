#!/bin/sh

BASE=/data/dev

MUTATION_INFO_FILE="${BASE}/dawn_mutated/dawn_mutated.json"
MUTATION_INFO_FILE_FOR_MUTANT_COVERAGE_TRACKING="${BASE}/dawn_mutant_tracking/dawn_tracking.json"
MUTATED_COMPILER_EXE="${BASE}/wgslsmith_mutated_dawn/target/release/wgslsmith"
MUTATED_TRACKING_COMPILER_EXE="${BASE}/wgslsmith_mutant_coverage_dawn/target/release/wgslsmith"
WGSLSMITH_ROOT="${BASE}/wgslsmith/target/release"

export PYTHONPATH=${BASE}/dredd-compiler-testing

python3 ${BASE}/dredd-compiler-testing/dredd_test_runners/wgslsmith_runner/webgpu_cts_test.py \
    $MUTATION_INFO_FILE \
    $MUTATION_INFO_FILE_FOR_MUTANT_COVERAGE_TRACKING \
    $MUTATED_COMPILER_EXE \
    $MUTATED_TRACKING_COMPILER_EXE \
    $WGSLSMITH_ROOT \
    --run_timeout 100
