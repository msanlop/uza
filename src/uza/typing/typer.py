from abc import ABC
from dataclasses import dataclass, field
from enum import Enum
import sys
from typing import List

from .type import *
from ..token import *
from ..ast import InfixApplication, Literal, Program, VarDef
from ..interpreter import *


class Constraint(ABC):
    span : Span
    
    def solve(self) -> bool:
        raise NotImplementedError(f"visit not implemented for {self}")

    def fail_message(self) -> str:
        raise NotImplementedError(f"visit not implemented for {self}")

@dataclass
class IsType(Constraint):
    a : Type
    b : Type
    span : Span
    
    def solve(self) -> bool:
        return self.a == self.b
    
    def fail_message(self) -> str:
        return f"Expected type '{self.b}' but found '{self.a}' at {self.span}"
        
    
@dataclass
class IsSubType(Constraint):
    a : Type
    b : UnionType
    span : Span
    
    def solve(self) -> bool:
        return self.a in self.b.types
    
    def fail_message(self) -> str:
        return f"Expected type '{self.b}' but found '{self.a}' at {self.span}"

@dataclass
class EitherOr(Constraint): #TODO: arbitrary number of possibilities?
    a : List[Constraint]
    b : List[Constraint]
    span : Span
    
    def solve(self) -> bool:
        a_true = all(constraint.solve() for constraint in self.a)
        b_true = all(constraint.solve() for constraint in self.b)
        return a_true or b_true
    
    def fail_message(self) -> str:
        a_messages = "\n ".join(c.fail_message() for c in self.a if not c.solve())
        b_messages = "\n ".join(c.fail_message() for c in self.b if not c.solve())
        return f"Expected one of the following at {self.span}:\n {a_messages}\nor:\n {b_messages}"

@dataclass
class IsNotVoid(Constraint):
    span : Span
    
    def __init__(self, *types: Type):
        self.types = types
    
    def solve(self) -> bool:
        return type_void not in self.types

class Typer:
    def __init__(self, program : Program) -> None:
        self.program = program
        self.constaints : List[Constraint] = []
        self.context = Context()
        
    def add_constaint(self, constraint : Constraint) -> None:
        self.constaints.append(constraint)
        
    def visit_builint(self, func_id: BuiltIn, *arguments : Node):
        ret = None
        lhs, rhs = arguments[0], None
        if len(arguments) == 2:
            rhs = arguments[1]

        if func_id == bi_print or func_id == bi_println:
            arg_types = [arg.visit(self) for arg in arguments]
            return type_void
        
        arithmetic_type = UnionType(type_int, type_float)
        if func_id == bi_div:
            return lhs.visit(self)
        elif func_id == bi_add:
            lhs_type = lhs.visit(self)
            rhs_type = rhs.visit(self)
            add_func_constraint = EitherOr(
                [
                    IsSubType(lhs_type, arithmetic_type, lhs.span),
                    IsSubType(rhs_type, arithmetic_type, rhs.span),
                ],
                [
                    IsType(lhs_type, type_string, lhs.span),
                    IsType(rhs_type, type_string, rhs.span),
                ],
                lhs.span + rhs.span
            )
            self.add_constaint(add_func_constraint)
            return arithmetic_type + type_string
        elif func_id in (bi_add, bi_sub, bi_mul):
            lhs_type = lhs.visit(self)
            rhs_type = rhs.visit(self)
            self.add_constaint(IsSubType(lhs_type, arithmetic_type, lhs.span))
            self.add_constaint(IsSubType(rhs_type, arithmetic_type, rhs.span))
            if lhs_type == type_float or rhs_type == type_float:
                return type_float
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
        return self.visit_builint(builtin, *app.args)
        
    
    def visit_var_def(self, varDef : VarDef):
        self.constaints.append(
            IsType(varDef.type_, varDef.value.visit(self), varDef.span)
        )
        self.context.define(varDef.identifier, varDef.type_)
    
    def visit_literal(self, literal : Literal):
        return python_type_to_uza_type(type(literal.value))
    
    def check_types(self) -> tuple[int, str]:
        ret = 0
        err_string = ""
        for node in self.program:
            node.visit(self)
            
        for constraint in self.constaints:
            if not constraint.solve():
                ret += 1
                err_string += constraint.fail_message()
        
        return (ret, err_string)
