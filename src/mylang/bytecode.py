from __future__ import annotations
from abc import ABC
from dataclasses import dataclass, field
from io import BufferedReader, BufferedWriter
from pprint import pprint
from typing import Optional
from . import __version_tuple__
from .lang import Literal, Parser, Program, Span
import os
import struct

BYTE_ORDER = "big"
operations = []


class OpCode(ABC):
    def visit(self, that):
        pass
    
    def get_opbyte(self) -> bytes:
        return operations.index(self.name).to_bytes(1, BYTE_ORDER)

@dataclass
class OpReturn(OpCode):
    _op_name = "OP_RETURN"
    name: str = field(init=False, default=_op_name)
    span: Span
    operations.append(_op_name)
    
    def visit(self, that):
        that.visit_return(self)

@dataclass
class OpConstant(OpCode):
    _op_name = "OP_LOAD_CONST"
    name: str = field(init=False, default=_op_name)
    constant: float
    span: Span
    constant_idx: Optional[int] = field(init=False)
    operations.append(_op_name)
    
    def set_constant_index(self, index: int):
        self.constant_idx = index
    
    def visit(self, that):
        that.visit_constant(self)
        
@dataclass
class OpAdd(OpCode):
    _op_name = "OP_ADD"
    name: str = field(init=False, default=_op_name)
    span: Span
    operations.append(_op_name)
    
    def visit(self, that):
        that.visit_add(self)

@dataclass
class OpSub(OpCode):
    _op_name = "OP_SUB"
    name: str = field(init=False, default=_op_name)
    span: Span
    operations.append(_op_name)
    
    def visit(self, that):
        that.visit_sub(self)

@dataclass
class OpMul(OpCode):
    _op_name = "OP_MUL"
    name: str = field(init=False, default=_op_name)
    span: Span
    operations.append(_op_name)
    
    def visit(self, that):
        that.visit_mul(self)
        
@dataclass
class OpDiv(OpCode):
    _op_name = "OP_DIV"
    name: str = field(init=False, default=_op_name)
    span: Span
    operations.append(_op_name)
    
    def visit(self, that):
        that.visit_div(self)


class Chunk:
    code: list[OpCode]
    constants: list[float]

    def __init__(self, code: Optional[list[OpCode]] = None) -> None:
        if code:
            self.code = code
        else:
            self.code = []
        self.constants = []

    def _register_constant(self, opcode: OpConstant):
        try:
            idx = self.constants.index(opcode.constant)
        except ValueError:
            idx = len(self.constants)
            self.constants.append(opcode.constant)
        opcode.set_constant_index(idx)
    
    def add(self, opcode: OpCode):
        self.code.append(opcode)
        if isinstance(opcode, OpConstant):
            self._register_constant(opcode)
        
    def __repr__(self) -> str:
        return f"Chunk({repr(self.code)})"


@dataclass
class ByteCodeProgram: #TODO: change Program and extend it
    version: tuple[int, ...] = field(init=False, default=__version_tuple__)
    chunk: Chunk
    
    
class ByteCodeProgramSerializer:
    def __init__(self, program : ByteCodeProgram, file: BufferedWriter) -> None:
        self.program = program
        self.file = file
        
    def _write_constants(self):
        constants = self.program.chunk.constants
        self.file.write((len(constants)).to_bytes(1, BYTE_ORDER))
        for constant in constants:
            packed = struct.pack('d', constant)
            written = self.file.write(packed)

    def _write_version(self):
        [self.file.write(num.to_bytes(1, BYTE_ORDER)) for num in self.program.version]
        
    def _write_opcode(self, opcode: OpCode):
        self.file.write(opcode.get_opbyte())
        
    def _write_span(self, span: Span):
        self.file.write(span.start.to_bytes(2, BYTE_ORDER))
    
    def visit_return(self, ret: OpReturn):
        self._write_span(ret.span)
        self._write_opcode(ret)
    
    def visit_constant(self, ret: OpConstant):
        self._write_span(ret.span)
        self._write_opcode(ret)
        self.file.write(ret.constant_idx.to_bytes(1, BYTE_ORDER))
        
        
    ###### BINARY OPS ######
    
    def visit_add(self, op_add: OpAdd):
        self._write_span(op_add.span)
        self._write_opcode(op_add)
        
    def visit_sub(self, op_sub: OpSub):
        self._write_span(op_sub.span)
        self._write_opcode(op_sub)
        
    def visit_mul(self, op_mul: OpMul):
        self._write_span(op_mul.span)
        self._write_opcode(op_mul)
        
    def visit_div(self, op_div: OpDiv):
        self._write_span(op_div.span)
        self._write_opcode(op_div)
    
    def _write_chunk(self):
        self._write_constants()
        code = self.program.chunk.code
        for op in code:
            op.visit(self)
    
    def write_to_file(self):
        self._write_version()
        self._write_chunk()
        
    
        
FILENAME = "target/test.uza"
os.makedirs(os.path.dirname(FILENAME), exist_ok=True)

with open(FILENAME, "w+b") as file:
    # source = """
    # 5.12
    # 2.87
    # """
    # program = Parser(source).parse()

    # ByteCodeEmitter.print_program("target/test.zbc")


    test_chunk = Chunk()
    test_chunk.add(OpConstant(25, Span(0,1)))
    test_chunk.add(OpConstant(5, Span(0,1)))
    test_chunk.add(OpConstant(1.5, Span(0,1)))
    test_chunk.add(OpConstant(3, Span(0,1)))
    test_chunk.add(OpAdd(Span(0,1)))
    test_chunk.add(OpSub(Span(0,1)))
    test_chunk.add(OpConstant(5, Span(0,1)))
    test_chunk.add(OpMul(Span(0,1)))
    test_chunk.add(OpDiv(Span(0,1)))
    test_chunk.add(OpReturn(Span(0,1)))
    pprint(test_chunk)
    serializer = ByteCodeProgramSerializer(ByteCodeProgram(test_chunk), file)
    serializer.write_to_file()
    