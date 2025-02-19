import argparse
from pprint import pprint
import pathlib
from sys import stderr, stdin
import sys  # sys.exit conflict with exit?
from typing import Sequence

from uzac.driver import Driver
from uzac.utils import ANSIColor, in_color

from uzac.typer import Typer, TyperDiagnostic
from uzac.bytecode import ByteCodeProgram, ByteCodeProgramSerializer
from uzac.parser import Parser
from uzac.interpreter import Interpreter

from vm.main import run_vm

FILE_SUFFIX = ".uzb"


def main(argv: Sequence[str] = None) -> int:
    """
    Run the uza CLI.

    Returns:
        int: return code, 0 if no errors were encountered.
    """
    parser = argparse.ArgumentParser(
        prog="uza",
        description="one of the programming language of all time",
        epilog=":^)",
    )

    # input_group = parser.add_mutually_exclusive_group(required=True)
    parser.add_argument("file", nargs="?", type=str, help="The input source file")
    parser.add_argument("-s", "--source", type=str, help="The source code string")
    parser.add_argument(
        "--notypechecking", action="store_true", help="Disable typechecking"
    )

    action_group = parser.add_mutually_exclusive_group()
    action_group.add_argument(
        "-p", "--parse", action="store_true", help="Parse the source file"
    )
    action_group.add_argument(
        "-i",
        "--interpret",
        action="store_true",
        help="Interpret the source file (can also be piped with -i)",
    )
    action_group.add_argument(
        "-t",
        "--typecheck",
        action="store_true",
        help="Typecheck the program",
    )
    action_group.add_argument(
        "-c",
        "--compile",
        type=str,
        metavar="OUTPUT",
        nargs="?",
        const="",
        help="Compile the source file with optional output file location and name",
    )
    action_group.add_argument(
        "-o", "--output", type=str, help="Choose bytecode path target and run"
    )

    # If no options are provided, it should default to running the file
    parser.add_argument(
        "-r", "--run", action="store_true", help="Run the source file (default action)"
    )

    parser.add_argument(
        "-v", "--verbose", action="store_true", help="show verbose output"
    )

    if argv is not None:
        args = parser.parse_args(args=argv)
    else:
        args = parser.parse_args()

    verbose = args.verbose

    piped_input = None
    # argv is used for testing, do not read stdin then
    if not stdin.isatty() and argv is None:
        piped_input = stdin.read()

    if piped_input and args.source:
        print("Cannot pipe source and use -i at the same time", file=stderr)
        return 1
    if piped_input and args.file:
        print(
            "Cannot pipe source and pass a source file at the same time",
            file=stderr,
        )
        return 1
    if args.source and args.file:
        print("Cannot use -i and pass a source file at the same time", file=stderr)
        return 1

    source: str = ""
    code: bytes | None = None
    if piped_input:
        source = piped_input
    elif args.source:
        source = args.source
    elif args.file:
        mode = "r"
        try:
            if args.file.endswith(".uzb"):
                with open(args.file, "rb") as file:
                    code = file.read()
            else:
                with open(args.file, "r", encoding="ascii") as file:
                    source = file.read()
        except UnicodeDecodeError as e:
            print(e, file=sys.stderr)
            if "range(128)" in e.reason:
                print(
                    in_color(
                        "Error: uza currently only supports ascii encoding",
                        ANSIColor.RED,
                    )
                )
            return 1
        except FileNotFoundError as e:
            print(
                in_color(f"Error: {e.strerror} : '{args.file}'", ANSIColor.RED),
                file=sys.stderr,
            )
    else:
        parser.print_usage()
        print("\nerror: Provide a source file or source code")
        return 1

    out = None
    if args.parse:
        config = Driver.Configuration.PARSE
    elif args.typecheck:
        config = Driver.Configuration.TYPECHECK
    elif args.interpret:
        config = Driver.Configuration.INTERPRET
    elif args.compile is not None:
        config = Driver.Configuration.COMPILE
        out = args.compile
        if out == "":
            f = args.file
            out = pathlib.Path(f).stem + FILE_SUFFIX
        else:
            if pathlib.Path(out).suffix == "":
                out += FILE_SUFFIX
            else:
                out = pathlib.Path(out).stem + FILE_SUFFIX
                print(in_color(f"using {out}", ANSIColor.PURPLE))
    else:
        config = Driver.Configuration.INTERPRET_BYTECODE

    skip_tc = True if args.notypechecking else False

    return Driver.run_with_config(
        config,
        source,
        code,
        output_file=out,
        verbose=verbose,
        omit_typechecking=skip_tc,
    )


if __name__ == "__main__":
    sys.exit(main())
