from abc import ABC
from dataclasses import dataclass, field
from enum import Enum
import sys
from typing import List

from .type import UzaType
from ..token import *
from ..ast import InfixApplication, Literal, Program, VarDef
from ..interpreter import *


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

@dataclass
class IsNotVoid(Constraint):
    span : Span
    
    def __init__(self, *types: UzaType):
        self.types = types
    
    def solve(self) -> bool:
        return UzaType.void not in self.types

class Typer:
    def __init__(self, program : Program) -> None:
        self.program = program
        self.constaints : List[Constraint] = []
        self.context = Context()
        
    def add_constaint(self, constraint : Constraint) -> None:
        self.constaints.append(constraint)
        
    def visit_builint(self, func_id: BuiltIn, *params : Node):
        ret = None
        lhs, rhs = params[0], None
        if len(params) == 2:
            rhs = params[1]

        if func_id == bi_print or func_id == bi_println:
            self.add_constaint(IsNotVoid(params))
            return UzaType.void
        elif func_id == bi_div:
            return lhs.visit(self)
        elif func_id in (bi_add, bi_sub, bi_mul):
            lhs_type = lhs.visit(self)
            rhs_type = rhs.visit(self)
            if lhs_type == UzaType.fp or rhs_type == UzaType.fp:
                return UzaType.fp
            else:
                return lhs_type
        
        raise NotImplementedError(f"not implemented for {func_id}")
        
    def visit_infix_application(self, infix: InfixApplication):
        func_id = infix.func_id
        builtin = get_builtin(func_id)
        assert(builtin)
        return self.visit_builint(builtin, infix.lhs, infix.rhs)
    
    def visit_identifier(self, identifier: Identifier):
        return self.context.get(identifier.name)

    def visit_application(self, app: Application):
        func_id = app.func_id
        builtin = get_builtin(func_id)
        assert(builtin)
        return self.visit_builint(builtin, app.args)
        
    
    def visit_var_def(self, varDef : VarDef):
        self.constaints.append(
            IsType(varDef.type_, varDef.value.visit(self), varDef.span)
        )
        self.context.define(varDef.identifier, varDef.type_)
    
    def visit_literal(self, literal : Literal):
        return UzaType.get_python_type[type(literal.value)]
    
    def check_types(self) -> int:
        ret = 0
        for node in self.program:
            node.visit(self)
            
        for constraint in self.constaints:
            if not constraint.solve():
                a = constraint.a
                b = constraint.b
                span = constraint.span
                print(f"Expected type '{a}' but found '{b}' at {span}", file=sys.stderr)
                ret += 1
        
        return ret
