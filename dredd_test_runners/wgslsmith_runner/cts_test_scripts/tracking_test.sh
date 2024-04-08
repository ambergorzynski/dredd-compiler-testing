#!/bin/sh

DREDD_MUTANT_TRACKING_FILE=/data/dev/dredd-compiler-testing/dredd_test_runners/wgslsmith_runner/cts_test_scripts/here.txt \
    /data/dev/dawn_mutant_tracking/tools/run run-cts \
    --verbose \
    --bin=/data/dev/dawn_mutant_tracking/out/Debug \
    --cts=/data/dev/webgpu_cts \
    'webgpu:shader,execution,flow_control,loop:*'    



