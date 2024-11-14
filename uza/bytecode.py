"""
This bytecode module handles bytecode generation to be interpreted by the VM.

"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Optional, TypeVar
import struct
from uza import __version_tuple__
from uza.uzast import (
    Application,
    Block,
    Identifier,
    InfixApplication,
    Literal,
    Node,
    VarDef,
    Program,
    VarRedef,
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
    "OP_DEFGLOBAL",
    "OP_GETGLOBAL",
    "OP_SETGLOBAL",
    "OP_BLOCK",
    "OP_EXITBLOCK",
    "OP_DEFLOCAL",
    "OP_GETLOCAL",
    "OP_SETLOCAL",
    "OP_EXITVM",
]


def opcode_int(opcode: str):
    return OP_CODES.index(opcode)


Const = float | int | bool
VALUE_TYPES = {
    None: 0,
    int: 1,
    bool: 2,
    float: 3,
    dict: 4,  # TODO: revisit, then change _write_constant for string
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
    constant_index: Optional[int] = field(default=None)
    local_index: Optional[int] = field(default=None)
    outer_local_index: Optional[int] = field(default=None)
    code: int = field(init=False)

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


T = TypeVar("T")


class ByteCodeLocals:
    """
    This class keeps track of local variables and allow the emiter to generate
    indexes when accesing variables on the stack. The top level frame is always
    empty as globals operations use a hash table and chunk constants.

    TODO: exntend SymbolTable, make it generic?
    """

    frames: List[List[str]]
    depth: int  # global scope is depth 0

    def __init__(self, frames: List[List[str]] | None = None) -> None:
        if frames is None:
            self.frames = []
        else:
            self.frames = frames
        self.depth = len(self.frames)

    def _get_current_frame(self) -> List[str]:
        if self.depth == 0:
            return None
        return self.frames[0]

    def get_num_locals(self) -> int:
        return len(self._get_current_frame())

    def define(self, variable_name: str) -> int:
        """
        Returns the index in the current stack frame.
        """
        frame_locals = self._get_current_frame()
        already_defined_in_scope = variable_name in frame_locals
        if already_defined_in_scope:
            raise NameError(f"Unexpected redefinition of {variable_name}")

        idx = len(frame_locals)
        frame_locals.append(variable_name)
        return idx

    def new_frame(self) -> ByteCodeLocals:
        self.frames.insert(0, [])
        self.depth += 1
        return self

    def pop_frame(self) -> None:
        self.frames = self.frames[1:]
        self.depth -= 1

    def get(self, identifier: str) -> Optional[tuple[int, int]]:
        """
        Returns a tuple with the stack frame depth and local variale index.
        Returns None if the variable is in global (top-level frame -> use GLOBAL).
        """
        for idx, frame in enumerate(self.frames):
            try:
                res = frame.index(identifier)
                return idx, res
            except ValueError:
                pass

        return None

    def __enter__(self):
        """
        self.new_frame MUST be called from outside
        """
        pass

    def __exit__(self, type, value, traceback):
        self.pop_frame()


class ByteCodeProgram:
    """
    This class emits the bytecode and build the Chunks.

    This bytecode program can then be serialized and written to disk or passed
    along to the VM.
    """

    program: Program
    chunk: Chunk
    _local_vars: ByteCodeLocals

    def __init__(self, program: Program) -> None:
        self.program = program
        self.chunk = Chunk()
        self._local_vars = ByteCodeLocals()
        self._build_chunk()

    def depth(self) -> int:
        return self._local_vars.depth

    def visit_literal(self, literal: Literal) -> List[OpCode]:
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
        return [OpCode(code_name, literal.span, constant=literal.value)]

    def visit_identifier(self, identifier: Identifier) -> List[OpCode]:
        name = identifier.name
        if self.depth() == 0:
            return [OpCode("OP_GETGLOBAL", identifier.span, constant=name)]
        res = self._local_vars.get(name)
        if res is None:
            return [OpCode("OP_GETGLOBAL", identifier.span, constant=name)]

        frame_idx, idx = res
        if frame_idx != 0:
            raise NotImplementedError("variables from outer frames not yet implemented")
        return [OpCode("OP_GETLOCAL", identifier.span, local_index=idx)]

    def visit_var_def(self, var_def: VarDef) -> List[OpCode]:
        value = var_def.value.visit(self)
        name = var_def.identifier
        if self.depth() == 0:
            return [
                *value,
                OpCode("OP_DEFGLOBAL", var_def.span, constant=var_def.identifier),
            ]

        idx = self._local_vars.define(name)
        return [*value, OpCode("OP_DEFLOCAL", var_def.span, local_index=idx)]

    def visit_var_redef(self, var_redef: VarRedef) -> List[OpCode]:
        value = var_redef.value.visit(self)
        name = var_redef.identifier
        if self.depth() == 0:
            return [
                *value,
                OpCode("OP_SETGLOBAL", var_redef.span, constant=var_redef.identifier),
            ]

        idx = self._local_vars.define(name)
        return [*value, OpCode("OP_SETLOCAL", var_redef.span, local_index=idx)]

    def visit_application(self, application: Application) -> List[OpCode]:
        func_id = application.func_id
        # the println function is emitted as RETURN for now
        if func_id.name == "println":
            return [
                *application.args[0].visit(self),
                OpCode("OP_RETURN", application.span),
            ]
        raise NotImplementedError("only println implemented currently")

    def visit_infix_application(self, application: InfixApplication) -> List[OpCode]:
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

        return [
            *application.lhs.visit(self),
            *application.rhs.visit(self),
            OpCode(code_str, application.span),
        ]

    def _build_lines(self, lines: list[Node]) -> List[OpCode]:
        """
        Generates the bytecode for a sequence of nodes (lines of uza code).
        """
        res = []
        for node in lines:
            res.extend(node.visit(self))
        return res

    def visit_block(self, block: Block) -> List[OpCode]:
        with self._local_vars.new_frame():
            block_ops = self._build_lines(block.lines)
            return [
                OpCode(
                    "OP_BLOCK",
                    block.span,
                    local_index=self._local_vars.get_num_locals(),
                ),
                *block_ops,
                OpCode("OP_EXITBLOCK", block.span),
            ]

    def _build_chunk(self):
        top_level = self._build_lines(self.program.syntax_tree.lines)
        for op in top_level:
            self.chunk.add_op(op)
        self.chunk.add_op(OpCode("OP_EXITVM", Span(0, 0, "META")))


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
            elif opcode.local_index is not None:
                self._write(opcode.local_index.to_bytes(1, BYTE_ORDER))

    def _serialize(self):
        self._write_version()
        self._write_chunk()

    def get_bytes(self):
        return self.bytes_
