import argparse
from pprint import pprint
import subprocess
import sys
import os
from mylang.bytecode import ByteCodeProgram, ByteCodeProgramSerializer
from mylang.lang import Interpreter, Parser


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        prog="uza",
        description="one of the programming language of all time",
        epilog=":)",
    )

    input_group = parser.add_mutually_exclusive_group(required=True)
    input_group.add_argument("-f", "--file", type=str, help="The input source file")
    input_group.add_argument("-s", "--source", type=str, help="The source code string")

    action_group = parser.add_mutually_exclusive_group()
    action_group.add_argument(
        "-p", "--parse", action="store_true", help="Parse the source file"
    )
    action_group.add_argument(
        "-i", "--interpret", action="store_true", help="Interpret the source file"
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
    source = ""
    if args.source:
        source = args.source
    else:
        with open(args.file, "r", encoding="ascii") as file:
            source = file.read()

    program = Parser(source).parse()
    if args.parse:
        for i, node in enumerate(program):
            print(node.span.start, end=": ")  # TODO: use line instead of codepoint
            pprint(node)
            sys.exit(0)
    elif args.interpret:
        out = Interpreter(program).evaluate()
        if out and isinstance(out, int):
            sys.exit(out)
        else:
            sys.exit(0)

    filename = ""
    if args.compile:
        filename = args.compile
    elif args.output:
        filename = args.output
    elif os.path.exists("./target"):
        filename = os.path.join("./target", "out.uzabc")

    serializer = ByteCodeProgramSerializer(ByteCodeProgram(program))
    bytes_ = serializer.get_bytes()
    if args.verbose:
        pprint(serializer.program.chunk.code)
    written = 0
    with open(filename, "w+b") as file:
        written = file.write(bytes_)

    if args.compile:
        print(f"Wrote {written} bytes to {os.path.join(os.path.curdir, filename)}")
        sys.exit(0)

    try:
        subprocess.run(["./src/vm/main", filename], check=True)
    except subprocess.CalledProcessError as e:
        err_fmt = f"The VM exited with and error : \n{e.returncode=}\n{e.stdout=}\n{e.stderr=}"
        print(
            err_fmt,
            file=sys.stderr,
        )
