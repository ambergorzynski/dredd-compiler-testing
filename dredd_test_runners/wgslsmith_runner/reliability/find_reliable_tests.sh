#!/bin/sh

DAWN_PATH=/data/dev/dawn
CTS_PATH=/data/dev/webgpu_cts
OUTPUT_PATH=/data/dev/dredd-compiler-testing/output
QUERY_FILE=/data/dev/dredd-compiler-testing/output/query_file.txt

python find_non_flaky_cts_tests.py \
    $DAWN_PATH \
    $CTS_PATH \
    $OUTPUT_PATH \
    $QUERY_FILE \
    --update_queries
