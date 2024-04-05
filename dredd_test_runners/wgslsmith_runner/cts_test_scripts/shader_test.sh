#!/bin/sh

/data/dev/dawn_mutated/tools/run run-cts \
    --verbose \
    --bin=/data/dev/dawn_mutated/out/Debug \
    --cts=/data/dev/webgpu_cts \
    'webgpu,shader,execution:padding:struct_implicit:*'



