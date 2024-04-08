#!/bin/sh

DREDD_ENABLED_MUTATION=11 /data/dev/dawn_mutated/tools/run run-cts \
    --verbose \
    --bin=/data/dev/dawn_mutant_tracking/out/Debug \
    --cts=/data/dev/webgpu_cts \
    'webgpu:shader,execution,flow_control,loop:*'    
#'webgpu:examples:gpu,buffers:*'

#    'webgpu:api,operation,buffers,map_oom:*'


