import argparse
import re

from pathlib import Path
from typing import List


def prepare_csmith_program(original_program: Path, prepared_program: Path, csmith_root: Path) -> None:
    # This expands many #includes inline, so that a Csmith program only depends on standard include files, rather than
    # Csmith include files. This avoids needing to fully pre-process before test case reduction (which can lead to the
    # reduced program being too target-specific), but means that the reducer does not leave in high level Csmith
    # features such as safe math wrapper calls.

    # We do two separate header inlining passes, because things have been designed to work with a build of Csmith rather
    # than an installation of Csmith.

    # First, expand inline any of the #includes that refer to header files in the Csmith runtime source directory.
    include_files_to_follow: List[str] = ["csmith", "csmith_minimal", "random_inc", "platform_avr", "platform_generic", "platform_msp430"]
    content: str = open(original_program, 'r').read()
    for include_file in include_files_to_follow:
        pattern: str = f'(.*)(#include "{include_file}\\.h")(.*)'
        match = re.search(pattern, content, re.DOTALL)
        assert match is not None
        assert len(match.groups()) == 3
        content = match.group(1) + open(csmith_root / "runtime" / (include_file + ".h"), 'r').read() + match.group(3)

    # Now inline safe math header files from the Csmith build runtime directory. We do this twice because they are each
    # included twice. (The inlining of includes could be more judicious, since the includes are mutually exclusive
    # depending on preprocessor defines, but it's simplest just to inline them all.)
    build_include_files_to_follow: List[str] = ["safe_math_macros_notmp", "safe_math_macros", "safe_math"]
    for _ in range(0, 2):
        for include_file in build_include_files_to_follow:
            pattern: str = f'(.*)(#include "{include_file}\\.h")(.*)'
            match = re.search(pattern, content, re.DOTALL)
            assert match is not None
            assert len(match.groups()) == 3
            content = match.group(1) + open(csmith_root / "build" / "runtime" / (include_file + ".h"), 'r').read() + match.group(3)

    with open(prepared_program, 'w') as outfile:
        outfile.write(content)


# Press the green button in the gutter to run the script.
if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument("original_program", help="Program to be prepared.", type=Path)
    parser.add_argument("prepared_program", help="File that prepared program will be written to.", type=Path)
    parser.add_argument("csmith_root", help="Path to a checkout of Csmith, assuming that it has been built under "
                                            "'build' beneath this directory.", type=Path)
    args = parser.parse_args()
    prepare_csmith_program(original_program=args.original_program,
                           prepared_program=args.prepared_program,
                           csmith_root=args.csmith_root)
