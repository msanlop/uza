from abc import ABC
from dataclasses import dataclass
from enum import Enum
import sys
from typing import List
from .token import *
from .ast import Literal, Program, VarDef

class UzaType():
    integer = 1
    fp = 2
    string = 3
    boolean = 4
    object = 5
    
    get_python_type = {
        int: integer,
        float: fp,
        str: string,
        bool: boolean,
    }
    
    _uza_to_enum = {
        "int" : integer,
        "float": fp,
        "string": string,
        "bool": boolean,
    }
    
    def to_type(type_ : Token) -> int :
        assert type_.kind == token_identifier
        return UzaType._uza_to_enum.get(type_.repr)


class Constraint(ABC):
    span : Span
    
    def solve(self) -> bool:
        raise NotImplementedError(f"visit not implemented for {self}")

@dataclass
class IsType(Constraint):
    a : UzaType
    b : UzaType
    span : Span
    
    def solve(self) -> bool:
        return self.a == self.b

class Typer:
    def __init__(self, program : Program) -> None:
        self.program = program
        self.constaints : List[Constraint] = []
    
    def visit_var_def(self, varDef : VarDef):
        self.constaints.append(
            IsType(varDef.tpe, varDef.value.visit(), varDef.span)
        )
    
    def visit_literal(self, literal : Literal):
        return UzaType.get_python_type[type(literal.value)]
    
    def check_types(self) -> int:
        ret = 0
        for node in self.program:
            node.visit()
            
        for constraint in self.constaints:
            if not constraint.solve():
                a = constraint.a
                b = constraint.b
                span = constraint.span
                print(f"Expected type {a} but found {b} at {span}", file=sys.stderr)
                ret += 1
        
        return ret
