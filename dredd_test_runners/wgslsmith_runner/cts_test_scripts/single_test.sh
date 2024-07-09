#!/bin/sh

/data/dev/dawn_mutated/tools/run run-cts \
    --verbose \
    --bin=/data/dev/dawn_mutated/out/Debug \
    --cts=/data/dev/webgpu_cts \
    'unittests:*'
    #'webgpu:shader,*'
    #'webgpu:api,operation,command_buffer,copyTextureToTexture:*'
    #'webgpu:api,operation,buffers,map_oom:*'
    #'webgpu:examples:gpu,buffers:*'

    #'webgpu:shader,execution,flow_control,loop:*'    


