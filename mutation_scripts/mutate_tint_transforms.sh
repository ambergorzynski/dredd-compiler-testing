#!/bin/sh

MUTATED='/data/dev/dawn_mutated'
TRACKING='/data/dev/dawn_mutant_tracking'

#FILES=$(find /data/dev/dawn_mutated/src/tint/lang/core/ir/transform/ ! -type d -name '*.cc' \
#    | xargs grep -L "test")

TRANSFORM=${MUTATED}/src/tint/lang/core/ir/transform
MUTATED_FILES="$TRANSFORM/value_to_let.cc $TRANSFORM/direct_variable_access.cc $TRANSFORM/add_empty_entry_point.cc"

TRACK_TRANSFORM=${TRACKING}/src/tint/lang/core/ir/transform
TRACKED_FILES="$TRACK_TRANSFORM/value_to_let.cc $TRACK_TRANSFORM/direct_variable_access.cc $TRACK_TRANSFORM/add_empty_entry_point.cc"

DREDD='/data/dev/dredd/third_party/clang+llvm/bin/dredd'

echo "Mutating..."

# Mutate tint
$DREDD -p ${MUTATED}/out/Debug/compile_commands.json \
    --mutation-info-file ${MUTATED}/dawn_mutated.json \
    ${MUTATED_FILES}

cd ${MUTATED}/out/Debug && ninja dawn.node

echo "Tint mutation finished"

# Create mutation tracking 
$DREDD --only-track-mutant-coverage \
    -p ${TRACKING}/out/Debug/compile_commands.json \
    --mutation-info-file ${TRACKING}/dawn_tracking.json \
    ${TRACKED_FILES}

cd ${TRACKING}/out/Debug && ninja dawn.node

echo "Mutation tracking finished"

cd '/data/work/tint_mutation_testing'


