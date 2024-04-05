#!/bin/sh

NAME=ast_printer.cc
FILE=src/tint/lang/glsl/writer/ast_printer/${NAME}

#NAME=shader_io.cc
#FILE=src/tint/lang/core/ir/transform/${NAME}

MUTATED='/data/dev/dawn_mutated'
TRACKING='/data/dev/dawn_mutant_tracking'

DREDD='/data/dev/dredd/third_party/clang+llvm/bin/dredd'

# Mutate tint
$DREDD -p ${MUTATED}/out/Debug/compile_commands.json \
    --mutation-info-file ${MUTATED}/dawn_mutated.json \
    ${MUTATED}/${FILE}

cd ${MUTATED}/out/Debug && ninja dawn.node

echo "Tint mutation finished"

# Create mutation tracking tint

$DREDD --only-track-mutant-coverage \
    -p ${TRACKING}/out/Debug/compile_commands.json \
    --mutation-info-file ${TRACKING}/dawn_tracking.json \
    ${TRACKING}/${FILE}

cd ${TRACKING}/out/Debug && make

echo "Mutation tracking finished"

cd '/data/work/tint_mutation_testing'

