from abc import ABC
from dataclasses import dataclass, field
from enum import Enum
import sys
from typing import Dict, List
from itertools import count

from .type import *
from ..token import *
from ..ast import InfixApplication, Literal, Program, VarDef
from ..interpreter import *

@dataclass(eq=True, frozen=True)
class SymbolicType(Type):
    identifier: str

@dataclass
class Mapping:
    substitutions: dict[SymbolicType, Type]

    def __add__(self, that: object):
        if isinstance(that, tuple) and len(that) == 2:
            new_dict = {that[0]:that[1], **self.substitutions}
            return Mapping(new_dict)
        if isinstance(that, Mapping):
            return Mapping(self.substitutions | that.substitutions)
        return NotImplementedError

class Constraint(ABC):
    span : Span
    mapping : Mapping
    
    
    def solve(self, mapping: Mapping) -> tuple[bool, Optional[list[tuple]]]:
        """
        If the constraint can be check, returns a bool, otherwise returns a tuple
        with the SymbolicType mapped to the type.
        """
        raise NotImplementedError(f"visit not implemented for {self}")

    def fail_message(self) -> str:
        """
        Returns the failed message for previous _solve()_ try. This method is
        stateful! If called before _solve()_ it might have self.mapping = None.
        """
        raise NotImplementedError(f"visit not implemented for {self}")

@dataclass
class IsType(Constraint):
    a : Type
    b : Type
    span : Span
    mapping : Mapping = field(default=None)
    
    def solve(self, mapping: Mapping):
        self.mapping = mapping
        if isinstance(self.a, SymbolicType):
            val = mapping.substitutions.get(self.a)
            if val:
                return val == self.b, None
            return True, (self.a, self.b)
        return self.a == self.b, None
    
    def fail_message(self) -> str:
        if isinstance(self.b, SymbolicType):
            b_type = self.mapping.substitutions.get(self.b)
        else:
            b_type = self.b
        if isinstance(self.a, SymbolicType):
            a_type = self.mapping.substitutions.get(self.a)
        else:
            a_type = self.a
        return f"Expected type '{b_type}' but found '{a_type}' at {self.span}"
        
    
@dataclass
class IsSubType(Constraint):
    a : Type
    b : UnionType
    span : Span
    mapping : Mapping = field(default=None)
    
    def solve(self, mapping: Mapping):
        self.mapping = mapping
        if isinstance(self.a, SymbolicType):
            val = mapping.substitutions.get(self.a)
            if val:
                return val in self.b.types, None
            return True, (self.a, self.b)
        return self.a in self.b.types, None
    
    def fail_message(self) -> str:
        if isinstance(self.b, SymbolicType):
            b_type = self.mapping.substitutions.get(self.b)
        else:
            b_type = self.b
        if isinstance(self.a, SymbolicType):
            a_type = self.mapping.substitutions.get(self.a)
        else:
            a_type = self.a
        return f"Expected type '{b_type}' but found '{a_type}' at {self.span}"

@dataclass
class EitherOr(Constraint): #TODO: arbitrary number of possibilities?
    a : List[Constraint]
    b : List[Constraint]
    span : Span
    mapping : Mapping = field(default=None)
    _a_solved : list[bool] = field(default=None)
    _b_solved : list[bool] = field(default=None)
    
    def solve(self, mapping: Mapping) -> bool:
        self.mapping = mapping
        self._a_solved = [constraint.solve(mapping)[0] for constraint in self.a]
        self._b_solved = [constraint.solve(mapping)[0] for constraint in self.b]
        a_true = all(self._a_solved)
        b_true = all(self._b_solved)
        return a_true or b_true, None
    
    def fail_message(self) -> str:
        a_messages = "\n ".join(c.fail_message() for (c, res) in zip(self.a, self._a_solved) if not res)
        b_messages = "\n ".join(c.fail_message() for (c, res) in zip(self.b, self._b_solved) if not res)
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
        self.symbol_gen = count()
        self.mapping = Mapping({})
        
    def _create_new_symbol(self):
        return SymbolicType("symbolic_" + str(next(self.symbol_gen)))
        
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
        t = varDef.type_ if varDef.type_ else self._create_new_symbol()
        self.constaints.append(
            IsType(t, varDef.value.visit(self), varDef.span)
        )
        self.context.define(varDef.identifier, t)
    
    def visit_literal(self, literal : Literal):
        return python_type_to_uza_type(type(literal.value))
    
    def _check_with_mapping(self, constaints: list[Constraint], mapping : Mapping) -> tuple[int, str]:
        for idx, constraint in enumerate(constaints):
            solved, option = constraint.solve(mapping)
            # if constraint fails return TODO: check the rest of types
            if not option:
                if not solved:
                    return 1, constraint.fail_message()
                else:
                    continue

            # if mapping, iterate recursively over mappings
            new_mapping = mapping + option
            res, err_string = self._check_with_mapping(constaints[idx + 1:], new_mapping)
            if res != 0:
                return res, err_string
            else:
                self.mapping = new_mapping
        
        return 0, ""
            
    
    def check_types(self) -> tuple[int, str]:
        for node in self.program:
            node.visit(self)
            
        res, err = self._check_with_mapping(self.constaints, self.mapping)
        print(self.mapping)
        return res, err
