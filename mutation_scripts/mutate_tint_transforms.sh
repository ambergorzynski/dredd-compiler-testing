#!/bin/sh

NAME="robustness.cc"

MUTATED='/data/dev/dawn_mutated_transform'
TRACKING='/data/dev/dawn_mutant_tracking_transform'

#FILES=$(find /data/dev/dawn_mutated/src/tint/lang/core/ir/transform/ ! -type d -name '*.cc' \
#    | xargs grep -L "test")

TRANSFORM=${MUTATED}/src/tint/lang/core/ir/transform
#MUTATED_FILES="$TRANSFORM/value_to_let.cc $TRANSFORM/direct_variable_access.cc $TRANSFORM/add_empty_entry_point.cc $TRANSFORM/bgra8unorm_polyfill.cc $TRANSFORM/binding_remapper.cc $TRANSFORM/combine_access_instructions.cc $TRANSFORM/conversion_polyfill.cc $TRANSFORM/demote_to_helper.cc $TRANSFORM/vectorize_scalar_matrix_constructors.cc"

MUTATED_FILES="$TRANSFORM/$NAME"

TRACK_TRANSFORM=${TRACKING}/src/tint/lang/core/ir/transform
#TRACKED_FILES="$TRACK_TRANSFORM/value_to_let.cc $TRACK_TRANSFORM/direct_variable_access.cc $TRACK_TRANSFORM/add_empty_entry_point.cc $TRACK_TRANSFORM/bgra8unorm_polyfill.cc $TRACK_TRANSFORM/binding_remapper.cc $TRACK_TRANSFORM/combine_access_instructions.cc $TRACK_TRANSFORM/conversion_polyfill.cc $TRACK_TRANSFORM/demote_to_helper.cc $TRACK_TRANSFORM/vectorize_scalar_matrix_constructors.cc"

TRACKED_FILES="${TRACK_TRANSFORM}/$NAME"

DREDD='/data/dev/dredd/third_party/clang+llvm/bin/dredd'

echo "Saving copies of unmutated files..."
cp $MUTATED_FILES /data/work/tint_mutation_testing/unmutated/
cp $TRACKED_FILES /data/work/tint_mutation_testing/unmutated/

echo "Mutating..."

# Mutate tint
$DREDD -p ${MUTATED}/out/Debug/compile_commands.json \
    --mutation-info-file ${MUTATED}/dawn_mutated.json \
    ${MUTATED_FILES}

cd ${MUTATED}/out/Debug && ninja dawn.node

echo "Tint mutation finished"
: <<'END'
# Create mutation tracking 
$DREDD --only-track-mutant-coverage \
    -p ${TRACKING}/out/Debug/compile_commands.json \
    --mutation-info-file ${TRACKING}/dawn_tracking.json \
    ${TRACKED_FILES}

cd ${TRACKING}/out/Debug && ninja dawn.node

echo "Mutation tracking finished"

cd /data/dev/dredd-compiler-testing/mutation_scripts/
END
