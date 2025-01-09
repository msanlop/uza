"""
This bytecode module handles bytecode generation to be interpreted by the VM.

"""

from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum, IntEnum, auto
from typing import List, Optional, TypeVar
import struct
from uzac import __version_tuple__
from uzac.ast import (
    Application,
    Block,
    ExpressionList,
    ForLoop,
    Function,
    Identifier,
    IfElse,
    InfixApplication,
    Literal,
    Node,
    Return,
    VarDef,
    Program,
    VarRedef,
    WhileLoop,
)
from uzac.token import token_true
from uzac.utils import Span
from uzac.interpreter import (
    bi_add,
    bi_div,
    bi_mul,
    bi_sub,
    bi_and,
    bi_or,
    get_builtin,
    bi_eq,
    bi_lt,
)

BYTE_ORDER = "little"
operations = []


class OPCODE(Enum):
    RETURN = 0
    CALL = auto()
    CALL_NATIVE = auto()
    JUMP = auto()
    LOOP = auto()
    POP = auto()
    LFUNC = auto()
    LCONST = auto()
    DCONST = auto()
    STRCONST = auto()
    BOOLTRUE = auto()
    BOOLFALSE = auto()
    JUMP_IF_FALSE = auto()
    JUMP_IF_TRUE = auto()
    ADD = auto()
    SUB = auto()
    MUL = auto()
    DIV = auto()
    NEG = auto()
    EQ = auto()
    LT = auto()
    DEFGLOBAL = auto()
    GETGLOBAL = auto()
    SETGLOBAL = auto()
    BLOCK = auto()
    EXITBLOCK = auto()
    DEFLOCAL = auto()
    GETLOCAL = auto()
    SETLOCAL = auto()
    EXITVM = auto()


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
class Op:
    code: OPCODE
    span: Span
    constant: Optional[int | float | str | bool] = field(default=None)
    constant_index: Optional[int] = field(default=None)
    local_index: Optional[int] = field(default=None)
    outer_local_index: Optional[int] = field(default=None)
    jump_offset: Optional[int] = field(default=None)
    size: int = field(init=False)

    def size_in_bytes(self) -> int:
        """
        Returns the size of the opcode in bytes when turned into binary. It
        does not count the bytes writen for the lines (as these stores aside
        from the bytecode array).
        !MODIFY serializer.h too when this is changed.
        """
        size = 1  # code
        if self.constant is not None:
            size += 1
        if self.local_index is not None:
            size += 1
        if self.outer_local_index is not None:
            size += 1
        if self.jump_offset is not None:
            size += 2
        return size

    def __post_init__(self):
        self.size = self.size_in_bytes()


class Chunk:
    """
    A bytecode chunk.

    A bytechunk constainst a constant pool, and a list of bytecodes.
    """

    name: str
    code: list[Op]
    constants: list[Const]

    def __init__(self, name: str, code: Optional[list[Op]] = None) -> None:
        self.name = name
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

    def add_op(self, op: Op) -> int:
        """
        Adds the bytecode to the chunk and the constant if necessary.

        Returns the size in bytes of the opcode.
        """
        if op.constant is not None:
            idx = self._register_constant(op.constant)
            op.constant_index = idx
            self.code.append(op)
        else:
            self.code.append(op)

        return op.size

    def __repr__(self) -> str:
        return f"Chunk({self.name}, {repr(self.code)})"


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
            return frame_locals.index(variable_name)

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

        return None, None

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
    chunks: List[Chunk]
    _chunk: Chunk
    _local_vars: ByteCodeLocals
    _written: int

    def __init__(self, program: Program) -> None:
        self.program = program
        self._written = 0
        self._chunk = Chunk("<main>")
        self.chunks = list()
        self.chunks.append(self._chunk)
        self._local_vars = ByteCodeLocals()
        self._build_chunk()

    def _get_chunk_offset(self, name: str) -> Optional[int]:
        try:
            list(map(lambda chunk: chunk.name, self.chunks)).index(name)
        except ValueError:
            return None

    def emit_op(self, op: Op) -> int:
        self._chunk.add_op(op)
        self._written += op.size
        return self._written

    def depth(self) -> int:
        return self._local_vars.depth

    def visit_no_op(self, _):
        pass

    def visit_literal(self, literal: Literal) -> int:
        type_ = type(literal.value)
        opc = None
        if type_ == bool:
            if literal.token.kind == token_true:
                opc = OPCODE.BOOLTRUE
            else:
                opc = OPCODE.BOOLFALSE
            return self.emit_op(Op(opc, literal.span))
        if type_ == int:
            opc = OPCODE.LCONST
        elif type_ == float:
            opc = OPCODE.DCONST
        elif type_ == str:
            opc = OPCODE.STRCONST
        else:
            raise NotImplementedError(f"can't do opcode for literal '{literal}'")
        return self.emit_op(Op(opc, literal.span, constant=literal.value))

    def visit_if_else(self, if_else: IfElse) -> int:
        if_else.predicate.visit(self)
        skip_truthy = Op(OPCODE.JUMP_IF_FALSE, if_else.predicate.span, jump_offset=0)
        self.emit_op(skip_truthy)
        skip_truthy_point = self._written

        pop_pred = Op(OPCODE.POP, if_else.predicate.span)
        self.emit_op(pop_pred)
        if_else.truthy_case.visit(self)
        skip_truthy.jump_offset = (
            self._written - skip_truthy_point
        )  # jump over the uint16 offset too
        falsy = if_else.falsy_case
        if falsy is not None:
            jump_false_op = Op(
                OPCODE.JUMP, falsy.span, jump_offset=0
            )  # truthy case, skip else clause
            self.emit_op(jump_false_op)
            skip_falsy_point = self._written
            # skip over the new jump at the end of truthy case if pred == false
            skip_truthy.jump_offset = self._written - skip_truthy_point

            falsy.visit(self)
            self.emit_op(pop_pred)
            jump_false_op.jump_offset = self._written - skip_falsy_point

        return self._written

    def visit_identifier(self, identifier: Identifier) -> int:
        name = identifier.name
        if self.depth() == 0:
            return self.emit_op(Op(OPCODE.GETGLOBAL, identifier.span, constant=name))
        frame_idx, idx = self._local_vars.get(name)
        if frame_idx is None:
            return self.emit_op(Op(OPCODE.GETGLOBAL, identifier.span, constant=name))

        if frame_idx != 0:
            raise NotImplementedError("variables from outer frames not yet implemented")
        return self.emit_op(Op(OPCODE.GETLOCAL, identifier.span, local_index=idx))

    def visit_function(self, func: Function) -> int:
        with self._local_vars.new_frame():
            chunk_save = self._chunk
            chunk_new = Chunk(func.identifier.name)

            self.chunks.append(chunk_new)
            self._chunk = chunk_new
            for idx, param in enumerate(func.param_names):
                self._local_vars.define(param.name)

            func.body.visit(self)

            self._chunk = chunk_save
            self.emit_op(
                Op(
                    OPCODE.LCONST,
                    constant=func.identifier.name,
                    span=func.identifier.span,
                )
            )
            chunk_idx = len(self.chunks) - 1
            self.emit_op(Op(OPCODE.LFUNC, constant=chunk_idx, span=func.span))

    def visit_var_def(self, var_def: VarDef) -> int:
        var_def.value.visit(self)
        name = var_def.identifier
        if self.depth() == 0:
            return self.emit_op(
                Op(OPCODE.DEFGLOBAL, var_def.span, constant=var_def.identifier)
            )

        idx = self._local_vars.define(name)
        return self.emit_op(Op(OPCODE.DEFLOCAL, var_def.span, local_index=idx))

    def visit_var_redef(self, var_redef: VarRedef) -> int:
        var_redef.value.visit(self)
        name = var_redef.identifier
        frame_idx, idx = self._local_vars.get(name)

        if self.depth() == 0 or frame_idx is None:
            return self.emit_op(
                Op(OPCODE.SETGLOBAL, var_redef.span, constant=var_redef.identifier),
            )
        if frame_idx != 0:
            raise NotImplementedError("only current frame locals are implemented")
        return self.emit_op(Op(OPCODE.SETLOCAL, var_redef.span, local_index=idx))

    def visit_application(self, application: Application) -> int:
        for arg in application.args[::-1]:
            arg.visit(self)

        if get_builtin(application.func_id):
            return self.emit_op(
                Op(
                    OPCODE.CALL_NATIVE,
                    constant=application.func_id.name,
                    span=application.span,
                )
            )
        self.emit_op(
            Op(OPCODE.LCONST, constant=application.func_id.name, span=application.span)
        )
        return self.emit_op(
            Op(OPCODE.CALL, local_index=len(application.args), span=application.span)
        )

    def visit_return(self, ret: Return) -> int:
        ret.value.visit(self)
        return self.emit_op(Op(OPCODE.RETURN, span=ret.span))

    def _and(self, and_app: InfixApplication) -> int:
        and_app.lhs.visit(self)
        short_circuit_op = Op(OPCODE.JUMP_IF_FALSE, and_app.span, jump_offset=0)
        self.emit_op(short_circuit_op)
        jump_point = self._written
        self.emit_op(Op(OPCODE.POP, and_app.span))
        and_app.rhs.visit(self)
        short_circuit_op.jump_offset = self._written - jump_point
        return -1

    def _or(self, or_app: InfixApplication) -> int:
        or_app.lhs.visit(self)
        short_circuit_op = Op(OPCODE.JUMP_IF_TRUE, or_app.span, jump_offset=0)
        self.emit_op(short_circuit_op)
        jump_point = self._written
        self.emit_op(Op(OPCODE.POP, or_app.span))
        or_app.rhs.visit(self)
        short_circuit_op.jump_offset = self._written - jump_point
        return -1

    def visit_infix_application(self, application: InfixApplication) -> int:
        function = get_builtin(application.func_id)
        opc = ""
        if function == bi_add:
            opc = OPCODE.ADD
        elif function == bi_sub:
            opc = OPCODE.SUB
        elif function == bi_mul:
            opc = OPCODE.MUL
        elif function == bi_div:
            opc = OPCODE.DIV
        elif function == bi_and:
            return self._and(application)
        elif function == bi_or:
            return self._or(application)
        elif function == bi_eq:
            opc = OPCODE.EQ
        elif function == bi_lt:
            opc = OPCODE.LT
        else:
            raise NotImplementedError(f"vm can't do {function} yet")

        application.lhs.visit(self)
        application.rhs.visit(self)
        return self.emit_op(Op(opc, application.span))

    def _build_lines(self, lines: list[Node]) -> int:
        """
        Generates the bytecode for a sequence of nodes (lines of uza code).
        """
        for node in lines:
            node.visit(self)
        return self._written

    def visit_expression_list(self, expr_list: ExpressionList):
        return self._build_lines(expr_list.lines)

    def visit_block(self, block: Block) -> int:
        with self._local_vars.new_frame():
            block_op = Op(
                OPCODE.BLOCK,
                block.span,
                local_index=-1,
            )
            self.emit_op(block_op)
            self._build_lines(block.lines)
            block_op.local_index = self._local_vars.get_num_locals()
        return self.emit_op(Op(OPCODE.EXITBLOCK, block.span))

    def visit_for_loop(self, fl: ForLoop) -> int:
        with self._local_vars.new_frame():
            block_op = Op(
                OPCODE.BLOCK,
                fl.span,
                local_index=-1,
            )
            self.emit_op(block_op)

            fl.init.visit(self)
            jump_first_increment = Op(OPCODE.JUMP, fl.span, jump_offset=0)
            self.emit_op(jump_first_increment)
            jump_first_incr_point = self._written

            fl.incr.visit(self)
            jump_first_increment.jump_offset = self._written - jump_first_incr_point

            fl.cond.visit(self)
            end_loop = Op(OPCODE.JUMP_IF_FALSE, fl.cond.span, jump_offset=0)
            self.emit_op(end_loop)
            end_loop_point = self._written
            pop = Op(OPCODE.POP, fl.cond.span)
            self.emit_op(pop)

            fl.interior.visit(self)
            loop = Op(
                OPCODE.LOOP,
                fl.interior.span,
                jump_offset=self._written - jump_first_incr_point,
            )
            self.emit_op(loop)
            end_loop.jump_offset = self._written - end_loop_point
            self.emit_op(pop)

            block_op.local_index = self._local_vars.get_num_locals()

        return self.emit_op(Op(OPCODE.EXITBLOCK, fl.span))

    def visit_while_loop(self, wl: WhileLoop) -> int:
        cond_point = self._written
        wl.cond.visit(self)
        end_loop = Op(OPCODE.JUMP_IF_FALSE, wl.cond.span, jump_offset=0)
        self.emit_op(end_loop)
        end_loop_point = self._written
        pop = Op(OPCODE.POP, wl.cond.span)
        self.emit_op(pop)

        wl.loop.visit(self)
        loop = Op(
            OPCODE.LOOP,
            wl.loop.span,
            jump_offset=self._written - cond_point,
        )
        self.emit_op(loop)
        self.emit_op(pop)

        end_loop.jump_offset = self._written - end_loop_point
        return self._written

    def _build_chunk(self):
        self._build_lines(self.program.syntax_tree.lines)
        return self.emit_op(Op(OPCODE.EXITVM, Span(0, 0, "META")))


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
        wrote = len(buff)
        self.written += wrote
        self.bytes_ += buff
        return wrote

    def _write_constants(self, chunk: Chunk):
        """
        Write the constant pool to self.file.
        """
        constants = chunk.constants
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
        return self._write(span_pack)

    def _write_chunk(self, chunk: Chunk):
        self._write_constants(chunk)
        code = chunk.code
        written = 0
        for opcode in code:
            self._write_span(
                opcode.span
            )  # line information is stored in different array from bytecode
            written += self._write(opcode.code.value.to_bytes(1, BYTE_ORDER))
            if opcode.constant_index is not None:
                written += self._write(opcode.constant_index.to_bytes(1, BYTE_ORDER))
            elif opcode.local_index is not None:
                written += self._write(opcode.local_index.to_bytes(1, BYTE_ORDER))
            elif opcode.jump_offset is not None:
                offset_bytes = struct.pack("<H", opcode.jump_offset)
                written += self._write(offset_bytes)
            if written != opcode.size:
                raise AssertionError(
                    f"AssertionError for {opcode=}\n exepected it to be {opcode.size} in size but wrote {written} instead"
                )
            written = 0

    def _serialize(self):
        self._write_version()
        chunks = self.program.chunks
        chunk_count = struct.pack("<I", len(chunks))
        self._write(chunk_count)
        for chunk in chunks:
            op_count = struct.pack("<I", len(chunk.code))
            self._write(op_count)
            self._write_chunk(chunk)

    def get_bytes(self):
        return self.bytes_
