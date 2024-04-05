#!/bin/sh

i=0

while [ $i -ne 100 ]
do
    DREDD_ENABLED_MUTATION=$i /data/dev/dawn_mutated/tools/run run-cts \
        --verbose \
        --bin=/data/dev/dawn_mutated/out/Debug \
        --cts=/data/dev/webgpu_cts \
        'webgpu:shader'

    result=$?

    [ $result -ne 0 ] && echo "Test failed!" && exit 1

    i=$(($i+1))

    echo "result is ${result}"
    
    sleep 2

done
