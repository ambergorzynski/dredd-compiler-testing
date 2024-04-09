#!/bin/sh

DREDD_ENABLED_MUTATION=196 /data/dev/dawn_mutated/tools/run run-cts \
    --verbose \
    --bin=/data/dev/dawn_mutated/out/Debug \
    --cts=/data/dev/webgpu_cts \
    'webgpu:shader,validation,expression,call,builtin,abs:*'    


