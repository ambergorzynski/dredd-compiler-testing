#!/bin/sh

BASE=/data/dev

MUTATED_PATH="${BASE}/dawn_mutated"
TRACKING_PATH="${BASE}/dawn_mutant_tracking"

MUTATION_INFO_FILE="${MUTATED_PATH}/dawn_mutated.json"
MUTATION_INFO_FILE_FOR_MUTANT_COVERAGE_TRACKING="${TRACKING_PATH}/dawn_tracking.json"
MUTANT_KILL_PATH="/data/work/tint_mutation_testing/results_dredd_assignment_check"

export PYTHONPATH=${BASE}/dredd-compiler-testing

python3 ${BASE}/dredd-compiler-testing/dredd_test_runners/wgslsmith_runner/webgpu_cts_test.py \
    $MUTATED_PATH \
    $TRACKING_PATH \
    $MUTATION_INFO_FILE \
    $MUTATION_INFO_FILE_FOR_MUTANT_COVERAGE_TRACKING \
    $MUTANT_KILL_PATH \
    --run_timeout 600 \
    --compile_timeout 600 \
    --cts_only
