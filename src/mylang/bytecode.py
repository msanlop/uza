from io import BufferedReader, BufferedWriter
from pprint import pprint
from typing import Optional
from mylang import __version_tuple__
import os

BYTE_ORDER = "big"
operations = {
    "OP_RETURN",
    "READ_CONSTANT",
}


opcodes = {t[0]: t[1] for t in zip(operations, range(len(operations)))}
code_to_str = {t[1]: t[0] for t in zip(operations, range(len(operations)))}

pprint(opcodes)

class Chunk:
    code: list[bytes]
    
    def __init__(self, opcodes: list[int]) -> None:
        self.code = [op.to_bytes(1, BYTE_ORDER) for op in opcodes]
        
    def __str__(self) -> str:
        code_str = str.join('\n', [code_to_str[int.from_bytes(op, BYTE_ORDER)] for op in self.code])
        return f"Chunk(\n{code_str}\n)"
        
    
test_chunk = Chunk([opcodes['READ_CONSTANT'], opcodes['OP_RETURN']])

class ByteCodeEmitter:
    def write_version(file: BufferedWriter):
        for num in __version_tuple__:
            file.write(int(num).to_bytes(1, BYTE_ORDER))
            
    def read_version(file: BufferedReader):
        version = []
        for i in range(3):
            b = file.read(1)
            version.append(int.from_bytes(b, BYTE_ORDER))

        return version
    
            
    def write_opcodes(file: BufferedWriter, chunk: Chunk):
        for op in chunk.code:
            file.write(op)
            
    def read_opcodes(file: BufferedReader) -> Chunk:
        ops = []
        b = file.read(1)
        while b:
            ops.append(int.from_bytes(b, BYTE_ORDER))
            b = file.read(1)
        return Chunk(ops)
        
    def output_bc(filename: str):
        os.makedirs(os.path.dirname(filename), exist_ok=True)
        with open(filename, "wb") as file:
            ByteCodeEmitter.write_version(file)
            ByteCodeEmitter.write_opcodes(file, test_chunk)
            
    def print_program(filename: str):
        with open(filename, "rb") as file:
            version = ByteCodeEmitter.read_version(file)
            version = [str(i) for i in version]
            chunk = ByteCodeEmitter.read_opcodes(file)
            print(str.join('.', version))
            print(chunk)
            
            
            
            
ByteCodeEmitter.output_bc('target/test.zbc')
ByteCodeEmitter.print_program('target/test.zbc')