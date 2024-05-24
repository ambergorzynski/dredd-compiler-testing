#!/bin/sh

DAWN=/data/dev/dawn_mutated

$DAWN/tools/run \
    run-cts --verbose \
    --bin=$DAWN/out/Debug \
    --cts=/data/dev/webgpu_cts \
    "webgpu:shader,execution,expression,call,builtin,textureDimensions:*"
    #'webgpu:api,operation,storage_texture,read_only:basic:format="bgra8unorm";shaderStage="vertex";dimension="3d";depthOrArrayLayers=1'
    #'webgpu:api,operation,storage_texture,read_only:*'
