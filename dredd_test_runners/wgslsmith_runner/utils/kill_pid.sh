#!/bin/sh

nvidia-smi | grep 'node' | awk '{ print $5 }' | xargs -n1 kill -9
                
