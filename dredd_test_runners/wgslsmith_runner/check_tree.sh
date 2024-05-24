#!/bin/sh

BASE=/data/dev

MUTATION_INFO_FILE="${BASE}/dawn_mutated_transform/dawn_mutated.json"
MUTATION_INFO_FILE_FOR_MUTANT_COVERAGE_TRACKING="${BASE}/dawn_mutant_tracking_transform/dawn_tracking.json"
MUTANT_KILL_PATH="/data/work/tint_mutation_testing/transform_cts"

export PYTHONPATH=${BASE}/dredd-compiler-testing

python3 ${BASE}/dredd-compiler-testing/dredd_test_runners/wgslsmith_runner/check_mutation_tree.py \
    $MUTATION_INFO_FILE \
    $MUTATION_INFO_FILE_FOR_MUTANT_COVERAGE_TRACKING \
    $MUTANT_KILL_PATH \
    --run_timeout 600 \
    --compile_timeout 600 \
    --cts_only
