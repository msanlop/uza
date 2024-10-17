import argparse
from pprint import pprint
import subprocess
import sys
import os
from os.path import dirname

from .typing.typer import Typer
from .bytecode import ByteCodeProgram, ByteCodeProgramSerializer
from .parser import Parser
from .interpreter import Interpreter
import pathlib


def main() -> int:
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
        const="output_file",
        help="Compile the source file with optional output file location and name",
    )
    action_group.add_argument(
        "-o", "--output", type=str, help="Choose bytecode path target and run"
    )

    # If no options are provided, it should default to running the file
    parser.add_argument(
        "-r", "--run", action="store_true", help="Run the source file (default action)"
    )

    action_group.add_argument(
        "-v", "--verbose", action="store_true", help="show verbose output"
    )

    # Parse the arguments
    args = parser.parse_args()

    piped_input = None
    if not sys.stdin.isatty():
        piped_input = sys.stdin.read()

    if piped_input and args.source:
        print("Cannot pipe source and use -i at the same time", file=sys.stderr)
        return 1
    if piped_input and args.file:
        print(
            "Cannot pipe source and pass a source file at the same time",
            file=sys.stderr,
        )
        return 1
    if args.source and args.file:
        print("Cannot use -i and pass a source file at the same time", file=sys.stderr)
        return 1

    source = ""
    if piped_input:
        source = piped_input
    elif args.source:
        source = args.source
    elif args.file:
        with open(args.file, "r", encoding="ascii") as file:
            source = file.read()
    else:
        parser.print_usage()
        print("\nerror: Provide a source file or source code")
        return 1

    program = Parser(source).parse()
    if args.parse:
        for i, node in enumerate(program):
            print(node.span.start, end=": ")  # TODO: use line instead of codepoint
            pprint(node)
            return 0
    elif args.typecheck:
        err, msg = Typer(program).check_types()
        if msg:
            print(msg, file=sys.stderr)
        return err
    elif args.interpret:
        out = Interpreter(program).evaluate()
        if out and isinstance(out, int):
            return out
        else:
            return 0

    path = pathlib.Path("./")
    if args.compile:
        path = pathlib.Path(args.compile)
    elif args.output:
        path = pathlib.Path(args.output)
    else:
        path = pathlib.Path("./target/out.uzo")

    path.parent.mkdir(parents=True, exist_ok=True)
    serializer = ByteCodeProgramSerializer(ByteCodeProgram(program))
    bytes_ = serializer.get_bytes()
    if args.verbose:
        pprint(serializer.program.chunk.code)
    written = 0
    with open(path, "w+b") as file:
        written = file.write(bytes_)

    if args.compile:
        print(f"Wrote {written} bytes to {os.path.join(os.path.curdir, path)}")
        return 0

    src_dir_path = dirname(dirname(os.path.realpath(__file__)))
    try:
        subprocess.run([src_dir_path + "/vm/main", path], check=True)
    except subprocess.CalledProcessError as e:
        err_fmt = f"The VM exited with and error : \n{e.returncode=}\n{e.stdout=}\n{e.stderr=}"
        print(
            err_fmt,
            file=sys.stderr,
        )
    return 0

if __name__ == "__main__":
    sys.exit(main())
