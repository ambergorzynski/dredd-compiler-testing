#!/bin/sh

FILE_NAME=$1

MUTATED='/data/dev/dawn_mutated_transform'
TRACKING='/data/dev/dawn_mutant_tracking_transform'

TRANSFORM=${MUTATED}/src/tint/lang/core/ir/transform/
TRACK_TRANSFORM=${TRACKING}/src/tint/lang/core/ir/transform/

cp /data/work/tint_mutation_testing/unmutated/$FILE_NAME $TRANSFORM
cp /data/work/tint_mutation_testing/unmutated/$FILE_NAME $TRACK_TRANSFORM
