#!/bin/bash

# This script returns 0 if the reduced program is 'interesting'

BASE=/data/work/tint_mutation_testing/reduction/temp
WGSLSMITH=/data/dev/wgslsmith_mutated_dawn/target/release/wgslsmith

# Recondition the program of interest
echo "Reconditioning..."
$WGSLSMITH recondition prog.wgsl recon.wgsl

# Execute the reconditioned program without mutation
echo "Running reconditioned test without mutation..."
$WGSLSMITH run recon.wgsl ${BASE}/inputs.json -c 'dawn:vk:7425' >> stdout_unmutated.txt


# Execute the reconditioned program with mutation
echo "Running reconditioned test with mutation..."
DREDD_ENABLED_MUTATION=10 $WGSLSMITH run recon.wgsl ${BASE}/inputs.json -c 'dawn:vk:7425' >> stdout_mutated.txt

# Check that ouptuts still differ from original outputs (stored somewhere)
# cmp returns 1 if files differ or 0 if they are the same
cmp --silent stdout_unmutated.txt stdout_mutated.txt

RESULT=$?

grep -q 'outputs' stdout_mutated.txt

VALID_RESULT=$?

# If outputs are valid but differ, return 0
if [[ $VALID_RESULT -eq 0 && $RESULT -ne 0 ]]
then
    exit 0
else
    exit 1
fi 

