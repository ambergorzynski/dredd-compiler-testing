#!/bin/sh

BASE=/data/dev

MUTATION_INFO_FILE="${BASE}/dawn_mutated/dawn_mutated.json"
MUTATION_INFO_FILE_FOR_MUTANT_COVERAGE_TRACKING="${BASE}/dawn_mutant_tracking/dawn_tracking.json"
MUTATED_COMPILER_EXE="${BASE}/wgslsmith_mutated_dawn/target/release/wgslsmith"
MUTATED_TRACKING_COMPILER_EXE="${BASE}/wgslsmith_mutant_coverage_dawn/target/release/wgslsmith"
WGSLSMITH_ROOT="${BASE}/wgslsmith_mutated_dawn/target/release"
MUTANT_KILL_PATH="/data/work/tint_mutation_testing/output/spirv_ast_printer/"
TIMEOUT=60
LAVAPIPE="/data/dev/mesa/build/install/share/vulkan/icd.d/lvp_icd.x86_64.json" 
DAWN="dawn:vk:0"

export PYTHONPATH=${BASE}/dredd-compiler-testing

python3 ${BASE}/dredd-compiler-testing/dredd_test_runners/wgslsmith_runner/main.py \
    $MUTATION_INFO_FILE \
    $MUTATION_INFO_FILE_FOR_MUTANT_COVERAGE_TRACKING \
    $MUTATED_COMPILER_EXE \
    $MUTATED_TRACKING_COMPILER_EXE \
    $WGSLSMITH_ROOT \
    $MUTANT_KILL_PATH \
    --compile_timeout $TIMEOUT \
    --run_timeout $TIMEOUT \
    --vk_icd $LAVAPIPE \
    --dawn_vk $DAWN
