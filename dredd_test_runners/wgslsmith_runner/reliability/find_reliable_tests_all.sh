#!/bin/sh

DAWN_PATH=/data/dev/dawn
CTS_PATH=/data/dev/webgpu_cts
OUTPUT_PATH=/data/work/tint_mutation_testing/lavapipe_driver_reliable_tests
MESA_INSTALL=/data/dev/mesa/build/install

python find_non_flaky_cts_tests.py \
    $DAWN_PATH \
    $CTS_PATH \
    $OUTPUT_PATH \
    --query_base='webgpu:*' \
    --driver='lavapipe' \
    --mesa_install=$MESA_INSTALL
    #--update_queries
