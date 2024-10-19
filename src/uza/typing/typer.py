from abc import ABC
from dataclasses import dataclass, field
from typing import List
from itertools import count

from .type import *
from ..token import *
from ..ast import InfixApplication, Literal, Program, VarDef
from ..interpreter import *
from ..utils import in_bold


@dataclass(eq=True, frozen=True)
class SymbolicType(Type):
    """
    A SymbolicType is a type that is yet to be infered.

    Args:
        Type (str): identifier MUST be unique, as dataclass __eq__ will use it
    """

    identifier: str


@dataclass
class Mapping:
    """
    A mapping is a map from symbolic types to real types.
    """

    _substitutions: dict[SymbolicType, Type]

    def get_type_of(self, t: SymbolicType) -> Optional[Type]:
        """
        Returns the substited real type for _t_ in this mapping. None if not
        substitution found.
        """
        return self._substitutions.get(t)

    def __add__(self, that: object):
        if isinstance(that, tuple) and len(that) == 2:
            new_dict = {that[0]: that[1], **self._substitutions}
            return Mapping(new_dict)
        if isinstance(that, Mapping):
            return Mapping(self._substitutions | that._substitutions)
        return NotImplementedError


class Constraint(ABC):
    span: Span
    mapping: Mapping

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
    """
    A constraint for a type to be equal to another.
    """

    a: Type
    b: Type
    span: Span
    mapping: Mapping = field(default=None)

    def solve(self, mapping: Mapping):
        self.mapping = mapping
        if isinstance(self.a, SymbolicType):
            val = mapping.get_type_of(self.a)
            if val:
                return val == self.b, None
            return True, (self.a, self.b)
        return self.a == self.b, None

    def fail_message(self) -> str:
        if isinstance(self.b, SymbolicType):
            b_type = self.mapping.get_type_of(self.b)
        else:
            b_type = self.b
        if isinstance(self.a, SymbolicType):
            a_type = self.mapping.get_type_of(self.a)
        else:
            a_type = self.a
        source = self.span.get_underlined(
            error_message=f" Expected type '{b_type}' but found '{a_type}'",
            padding=len("at "),
        )
        return f"at {source}\n"


@dataclass
class IsSubType(Constraint):
    """
    A constraint for a type to be a subtype of another or equal to it.
    """

    a: Type
    b: UnionType
    span: Span
    mapping: Mapping = field(default=None)

    def solve(self, mapping: Mapping):
        self.mapping = mapping
        if isinstance(self.a, SymbolicType):
            val = mapping.get_type_of(self.a)
            if val:
                return val in self.b.types, None
            return True, (self.a, self.b)
        return self.a in self.b.types, None

    def fail_message(self) -> str:
        if isinstance(self.b, SymbolicType):
            b_type = self.mapping.get_type_of(self.b)
        else:
            b_type = self.b
        if isinstance(self.a, SymbolicType):
            a_type = self.mapping.get_type_of(self.a)
        else:
            a_type = self.a
        source = self.span.get_underlined(
            error_message=f" Expected type '{b_type}' but found '{a_type}'",
            padding=len("at "),
        )
        return f"at {source}\n"


@dataclass
class EitherOr(Constraint):  # TODO: arbitrary number of possibilities?
    a: List[Constraint]
    b: List[Constraint]
    span: Span
    mapping: Mapping = field(default=None)
    _a_solved: list[bool] = field(default=None)
    _b_solved: list[bool] = field(default=None)

    def solve(self, mapping: Mapping) -> bool:
        self.mapping = mapping
        self._a_solved = [constraint.solve(mapping)[0] for constraint in self.a]
        self._b_solved = [constraint.solve(mapping)[0] for constraint in self.b]
        a_true = all(self._a_solved)
        b_true = all(self._b_solved)
        return a_true or b_true, None

    def fail_message(self) -> str:
        # location_str = f"at {self.span.get_underlined(len('at '))}"
        a_messages = "\n".join(
            c.fail_message() for (c, res) in zip(self.a, self._a_solved) if not res
        )
        b_messages = "\n".join(
            c.fail_message() for (c, res) in zip(self.b, self._b_solved) if not res
        )
        msg = f"\n{in_bold('Expected one of the following:')}\n"
        msg += f"{a_messages}{in_bold('or')}:\n{b_messages}"
        return msg


@dataclass
class IsNotVoid(Constraint):
    """probably useless TODO: update"""

    span: Span

    def __init__(self, *types: Type):
        self.types = types

    def solve(self, mapping: Mapping) -> bool:
        return type_void not in self.types


class Typer:
    def __init__(self, program: Program) -> None:
        self.program = program
        self.constaints: List[Constraint] = []
        self.context = Context()
        self.symbol_gen = count()
        self.mapping = Mapping({})

    def _create_new_symbol(self):
        """
        Return a new unique SymbolicType.
        """
        return SymbolicType("symbolic_" + str(next(self.symbol_gen)))

    def add_constaint(self, constraint: Constraint) -> None:
        """
        Adds a constraint to the typed program.
        """
        self.constaints.append(constraint)

    def visit_builtin(self, func_id: BuiltIn, *arguments: Node):
        lhs, rhs = arguments[0], None
        if len(arguments) == 2:
            rhs = arguments[1]

        if func_id in (bi_print, bi_println):
            for arg in arguments:
                arg.visit(self)

            return type_void

        arithmetic_type = UnionType(type_int, type_float)
        if func_id == bi_div:
            return lhs.visit(self)
        if func_id == bi_add:
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
                lhs.span + rhs.span,
            )
            self.add_constaint(add_func_constraint)
            # TODO: cleaner overloading handling
            if lhs_type == arithmetic_type == rhs_type:
                return arithmetic_type
            if lhs_type == type_string == rhs_type:
                return type_string
            return None  # TODO: return what?
        if func_id in (bi_sub, bi_mul, bi_div):
            lhs_type = lhs.visit(self)
            rhs_type = rhs.visit(self)
            self.add_constaint(IsSubType(lhs_type, arithmetic_type, lhs.span))
            self.add_constaint(IsSubType(rhs_type, arithmetic_type, rhs.span))
            if type_float in (lhs_type, rhs_type):
                return type_float
            return lhs_type

        raise NotImplementedError(f"not implemented for {func_id}")

    def visit_infix_application(self, infix: InfixApplication):
        func_id = infix.func_id
        builtin = get_builtin(func_id)
        assert builtin
        return self.visit_builtin(builtin, infix.lhs, infix.rhs)

    def visit_identifier(self, identifier: Identifier):
        return self.context.get(identifier.name)

    def visit_application(self, app: Application):
        func_id = app.func_id
        builtin = get_builtin(func_id)
        assert builtin
        return self.visit_builtin(builtin, *app.args)

    def visit_var_def(self, var_def: VarDef):
        t = var_def.type_ if var_def.type_ else self._create_new_symbol()
        self.constaints.append(IsType(t, var_def.value.visit(self), var_def.span))
        self.context.define(var_def.identifier, t)

    def visit_literal(self, literal: Literal):
        return python_type_to_uza_type(type(literal.value))

    def _check_with_mapping(
        self, constaints: list[Constraint], mapping: Mapping
    ) -> tuple[int, str]:
        """
        Try to solve the contraints with the given mapping for symbolic types.
        """
        err = 0
        err_string = ""
        for idx, constraint in enumerate(constaints):
            solved, option = constraint.solve(mapping)
            # if constraint fails return TODO: check the rest of types
            if not option:
                if not solved:
                    err += 1
                    err_string += constraint.fail_message()
                    # return 1, constraint.fail_message()
                continue

            # if mapping, iterate recursively over mappings
            new_mapping = mapping + option
            res, _ = self._check_with_mapping(constaints[idx + 1 :], new_mapping)
            if res != 0:
                err += 1
                # err_string += c_err_string
            else:
                self.mapping = new_mapping

        return err, err_string

    def check_types(self) -> tuple[int, str]:
        """
        Types checks the proram and returns the returns a tuple with the number
        of errors found and any error messages.

        Returns:
            tuple[int, str]: errors found, error message
        """
        for node in self.program:
            node.visit(self)

        res, err = self._check_with_mapping(self.constaints, self.mapping)
        return res, err
