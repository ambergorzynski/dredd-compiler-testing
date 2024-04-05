#!/bin/sh

/data/dev/dawn_mutant_tracking/tools/run run-cts \
    --verbose \
    --bin=/data/dev/dawn_mutant_tracking/out/Debug \
    --cts=/data/dev/webgpu_cts \
    'webgpu:shader,execution,flow_control,loop:*'    
#'webgpu:examples:gpu,buffers:*'



