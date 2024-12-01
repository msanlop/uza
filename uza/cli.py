import argparse
from pprint import pprint
import pathlib
from sys import stderr, stdin
import sys  # sys.exit conflict with exit?
from typing import Sequence

from uza.utils import ANSIColor, in_color

from uza.typer import Typer
from uza.bytecode import ByteCodeProgram, ByteCodeProgramSerializer
from uza.parser import Parser
from uza.interpreter import Interpreter

from vm.main import run_vm


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

    parser.add_argument(
        "-v", "--verbose", action="store_true", help="show verbose output"
    )

    if argv is not None:
        args = parser.parse_args(args=argv)
    else:
        args = parser.parse_args()

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
    if args.verbose:
        print(in_color("\n### ast ###\n", ANSIColor.YELLOW), file=stderr)
        for _, node in enumerate(program.syntax_tree.lines):
            print(
                node.span.start, end=": ", file=stderr
            )  # TODO: use line instead of codepoint
            pprint(node, stream=stderr)

    if program.errors > 0:
        for node in program.failed_nodes:
            print(node.error_message, file=stderr)
        return program.errors

    if args.parse:
        return 0

    if not args.notypechecking:
        type_err, type_msg, warning_msg, substitution_str = Typer(program).check_types(
            output_substitution=args.verbose
        )
        if args.verbose:
            print(in_color("\n### inferred types ###\n", ANSIColor.YELLOW), file=stderr)
            print(substitution_str, file=stderr)
        if warning_msg:
            for msg in warning_msg:
                print(msg, file=stderr)
        if args.typecheck or type_err > 0:
            if type_msg:
                print(type_msg, file=stderr)
            return type_err

    if args.interpret:
        out = Interpreter(program).evaluate()
        if out and isinstance(out, int):
            return out
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
        print("### generated constants ###", file=stderr)
        pprint(serializer.program.chunk.constants, stream=stderr)
        print("### generated bytecode ###", file=stderr)
        pprint(serializer.program.chunk.code, stream=stderr)
    written = 0
    with open(path, "w+b") as file:
        written = file.write(bytes_)

    if args.compile:
        print(f"Wrote {written} bytes to {path}")
        return 0

    return run_vm(serializer)


if __name__ == "__main__":
    sys.exit(main())
