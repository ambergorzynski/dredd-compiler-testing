#!/bin/sh

BASE=/data/dev

MUTATED_PATH="${BASE}/dawn_mutated"
TRACKING_PATH="${BASE}/dawn_mutant_tracking"
LAVAPIPE="data/dev/mesa/build/install/share/vulkan/icd.d/lvp_icd.x86_64.json" 
MUTATION_INFO_FILE="${MUTATED_PATH}/dawn_mutated.json"
MUTATION_INFO_FILE_FOR_MUTANT_COVERAGE_TRACKING="${TRACKING_PATH}/dawn_tracking.json"
MUTANT_KILL_PATH="/data/work/tint_mutation_testing/spirv_ast_printer_individual_cts"

QUERY_FILE="${BASE}/dredd-compiler-testing/output/reliable_tests.json"

export PYTHONPATH=${BASE}/dredd-compiler-testing

python3 ${BASE}/dredd-compiler-testing/dredd_test_runners/wgslsmith_runner/webgpu_cts_test.py \
    $MUTATED_PATH \
    $TRACKING_PATH \
    $MUTATION_INFO_FILE \
    $MUTATION_INFO_FILE_FOR_MUTANT_COVERAGE_TRACKING \
    $MUTANT_KILL_PATH \
    file \
    --query_file=$QUERY_FILE \
    --run_timeout 600 \
    --compile_timeout 600 \
    --vk_icd=$LAVAPIPE
