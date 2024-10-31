"""
This bytecode module handles bytecode generation to be interpreted by the VM.

"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Optional
import struct
from uza import __version_tuple__
from uza.uzast import (
    Application,
    Identifier,
    InfixApplication,
    Literal,
    VarDef,
    Program,
)
from uza.utils import Span
from uza.interpreter import (
    bi_add,
    bi_div,
    bi_mul,
    bi_sub,
    get_builtin,
)

BYTE_ORDER = "little"
operations = []

OP_CODES = [
    "OP_RETURN",
    "OP_LCONST",
    "OP_DCONST",
    "OP_STRCONST",
    "OP_ADD",
    "OP_SUB",
    "OP_MUL",
    "OP_DIV",
    "OP_NEG",
]


def opcode_int(opcode: str):
    return OP_CODES.index(opcode)


Const = float | int | bool
VALUE_TYPES = {
    int: 0,
    bool: 1,
    float: 2,
    dict: 3,  # TODO: revisit, then change _write_constant for string
    # also just use arrays, dict of len 4 or 1 is dumb
}

OBJECT_TYPES = {
    str: 0,
}


@dataclass
class OpCode:
    op_name: str
    span: Span
    constant: Optional[int | float | str | bool] = field(default=None)
    code: int = field(init=False)
    constant_index: Optional[int] = field(init=False, default=None)

    def __post_init__(self):
        self.code = opcode_int(self.op_name)


class Chunk:
    """
    A bytecode chunk.

    A bytechunk constainst a constant pool, and a list of bytecodes.
    """

    code: list[OpCode]
    constants: list[Const]

    def __init__(self, code: Optional[list[OpCode]] = None) -> None:
        if code:
            self.code = code
        else:
            self.code = []
        self.constants = []

    def _register_constant(self, constant: str | int | float | str) -> int:
        """
        Registers a constant and return its index in the constant pool.
        """
        idx = 0
        try:
            idx = self.constants.index(constant)
        except ValueError:
            idx = len(self.constants)
            self.constants.append(constant)
        return idx

    def add_op(self, op: OpCode):
        """
        Adds the bytecode to the chunk and the constant if necessary.
        """
        if op.constant:
            idx = self._register_constant(op.constant)
            op.constant_index = idx
            self.code.append(op)
        else:
            self.code.append(op)

    def __repr__(self) -> str:
        return f"Chunk({repr(self.code)})"


class ByteCodeProgram:
    """
    This class emits the bytecode and build the Chunks.

    This bytecode program can then be serialized and written to disk or passed
    along to the VM.
    """

    program: Program
    chunk: Chunk

    def __init__(self, program: Program) -> None:
        self.program = program
        self.chunk = Chunk()
        self._build_chunk()

    def visit_literal(self, literal: Literal):
        type_ = type(literal.value)
        code_name = ""
        if type_ == int:
            code_name = "OP_LCONST"
        elif type_ == float:
            code_name = "OP_DCONST"
        elif type_ == str:
            code_name = "OP_STRCONST"
        else:
            raise NotImplementedError(f"can't do opcode for literal '{literal}'")
        self.chunk.add_op(OpCode(code_name, literal.span, constant=literal.value))

    def visit_identifier(self, identifier: Identifier):
        pass

    def visit_var_def(self, var_def: VarDef):
        pass

    def visit_application(self, application: Application):
        func_id = application.func_id
        # the println function is emitted as RETURN for now
        if func_id.name == "println":
            application.args[0].visit(self)
            self.chunk.add_op(OpCode("OP_RETURN", application.span))
            return

    def visit_infix_application(self, application: InfixApplication):
        function = get_builtin(application.func_id)
        code_str = ""
        if function == bi_add:
            code_str = "OP_ADD"
        elif function == bi_sub:
            code_str = "OP_SUB"
        elif function == bi_mul:
            code_str = "OP_MUL"
        elif function == bi_div:
            code_str = "OP_DIV"
        else:
            raise NotImplementedError(f"vm can't do {function} yet")

        application.lhs.visit(self)
        application.rhs.visit(self)
        self.chunk.add_op(OpCode(code_str, application.span))

    def _build_chunk(self):
        for line in self.program.syntax_tree:
            line.visit(self)


class ByteCodeProgramSerializer:
    """
    This class emits the bytecode in _bytes_ that is run by the VM.

    This class does _not_ write to a file.
    The bytes can then be written on disk or piped to the VM. One downside with
    this approach is that the program is stored in memory in full instead of
    writing it as the codegen emits the opcodes. But it also simplifies the file
    handling and the piping of byte code without passing through disk.
    """

    bytes_: bytes
    written: int
    program: ByteCodeProgram

    def __init__(self, program: ByteCodeProgram) -> None:
        self.program = program
        self.written = 0
        self.bytes_ = b""
        self._serialize()

    def _write(self, buff):
        """
        Appends to the bytes buffer for the program.
        """
        self.written += len(buff)
        self.bytes_ += buff

    def _write_constants(self):
        """
        Write the constant pool to self.file.
        """
        # TODO: pack 8 const type flags into 1 byte
        constants = self.program.chunk.constants
        self._write((len(constants)).to_bytes(1, BYTE_ORDER))
        for constant in constants:
            const_type = type(constant)
            if const_type == str:
                self._write(struct.pack("<B", VALUE_TYPES.get(dict)))
                self._write(OBJECT_TYPES.get(str).to_bytes(1, BYTE_ORDER))
                length_pack = struct.pack("<q", len(constant))
                self._write(length_pack)
                packed = struct.pack(f"{len(constant)}s", bytes(constant, "ascii"))
                self._write(packed)
                continue

            fmt = ""

            self._write(struct.pack("<B", VALUE_TYPES.get(const_type)))
            if const_type == int:
                fmt = "<q"
            elif const_type == float:
                fmt = "<d"
            packed = struct.pack(fmt, constant)
            self._write(packed)

    def _write_version(self):
        for num in __version_tuple__:
            self._write(num.to_bytes(1, BYTE_ORDER))

    def _write_span(self, span: Span):
        span_pack = struct.pack("<H", span.start)
        self._write(span_pack)

    def _write_chunk(self):
        self._write_constants()
        code = self.program.chunk.code
        for opcode in code:
            self._write_span(opcode.span)
            self._write(opcode.code.to_bytes(1, BYTE_ORDER))
            if opcode.constant_index is not None:
                self._write(opcode.constant_index.to_bytes(1, BYTE_ORDER))

    def _serialize(self):
        self._write_version()
        self._write_chunk()

    def get_bytes(self):
        return self.bytes_
