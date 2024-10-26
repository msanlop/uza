from abc import ABC
from dataclasses import dataclass, field
from typing import List
from itertools import count

from .type import *
from ..token import *
from ..ast import InfixApplication, Literal, Program, VarDef
from ..interpreter import *
from ..utils import in_bold, in_color, ANSIColor





@dataclass
class Mapping:
    """
    A mapping is a map from symbolic types to real types.
    """

    _substitutions: dict["SymbolicType", Type]

    def get_type_of(self, t: "SymbolicType") -> Optional[Type]:
        """
        Returns the substited real type for _t_ in this mapping. None if not
        substitution found.
        """
        return self._substitutions.get(t)
    
    def pretty_print_mapping(self):
        for k in self._substitutions:
            green_expr = in_color(k.span.get_source(), ANSIColor.GREEN)
            yellow_type = in_color(str(self.get_type_of(k)), ANSIColor.YELLOW)
            print(f"{green_expr: <40} := {yellow_type}")

    def __add__(self, that: object):
        if isinstance(that, tuple) and len(that) == 2:
            new_dict = {that[0]: that[1], **self._substitutions}
            return Mapping(new_dict)
        if isinstance(that, Mapping):
            return Mapping(self._substitutions | that._substitutions)
        raise NotImplementedError(f"Can't add {self.__class__} and {that.__class__}")


@dataclass(eq=True, frozen=True)
class SymbolicType(Type):
    """
    A SymbolicType is a type that is yet to be infered.

    Args:
        Type (str): identifier MUST be unique, as dataclass __eq__ will use it
    """

    identifier: str
    span: Span
    
    def resolve_type(self, mapping: Mapping) -> Type:
        t = mapping.get_type_of(self)
        if t is None:
            return self
        if isinstance(t, SymbolicType):
            return t.resolve_type(mapping)
        return t
    
    def __str__(self) -> str:
        return f"{self.__class__}({self.identifier})"
        

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
        type_a = self.a.resolve_type(mapping)
        type_b = self.b.resolve_type(mapping)
        if type_a == type_b:
            return True, None
        if isinstance(type_a, SymbolicType) or isinstance(type_b, SymbolicType):
            return False, [mapping + (self.a, self.b)]
        return False, None

    def fail_message(self) -> str:
        type_b = self.b.resolve_type(self.mapping)
        type_a = self.a.resolve_type(self.mapping)
        source = self.span.get_underlined(
            error_message=f" Expected type '{type_b}' but found '{type_a}'",
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
        type_a = self.a.resolve_type(mapping)
        types_b = (t.resolve_type(mapping) for t in self.b.types)
        for possible_type in types_b:
            if type_a == possible_type:
                return True, None
        return False, (mapping + (self.a, t) for t in self.b.types)

    def fail_message(self) -> str:
        type_a = self.a.resolve_type(self.mapping)
        type_b = UnionType(t.resolve_type(self.mapping) for t in self.b.types)
        source = self.span.get_underlined(
            error_message=f" Expected type '{type_b}' but found '{type_a}'",
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

    def _create_new_symbol(self, node: Node):
        """
        Return a new unique SymbolicType.
        """
        return SymbolicType("symbolic_" + str(next(self.symbol_gen)), node.span)

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
            polymorphic_constraint = EitherOr(
                [
                    IsSubType(lhs_type, type_string, lhs.span),
                    IsType(rhs_type, lhs_type, rhs.span)
                ],
                [
                    IsSubType(lhs_type, arithmetic_type, lhs.span),
                    IsSubType(rhs_type, arithmetic_type, lhs.span)
                ],
                lhs.span + rhs.span
            )
            # self.add_constaint(IsType(rhs_type, lhs_type, rhs.span))
            # self.add_constaint(IsSubType(lhs_type, arithmetic_type + type_string, lhs.span))
            return lhs_type
        if func_id in (bi_sub, bi_mul, bi_div):
            lhs_type = lhs.visit(self)
            rhs_type = rhs.visit(self)
            self.add_constaint(IsType(rhs_type, lhs_type, rhs.span))
            self.add_constaint(IsSubType(lhs_type, arithmetic_type + type_string, lhs.span))
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
        t = var_def.type_ if var_def.type_ else self._create_new_symbol(var_def)
        self.constaints.append(IsType(t, var_def.value.visit(self), var_def.span))
        self.context.define(var_def.identifier, t)

    def visit_literal(self, literal: Literal):
        return python_type_to_uza_type(type(literal.value))

    def _check_with_mapping(
        self, constaints: list[Constraint], mapping: Mapping
    ) -> tuple[int, str, Mapping]:
        """
        Try to solve the contraints with the given mapping for symbolic types.
        """
        err = 0
        err_string = ""
        options = []
        for idx, constraint in enumerate(constaints):
            solved, options = constraint.solve(mapping)
            # if constraint fails return TODO: check the rest of types
            if options:
                break
            if not solved:
                return 1, constraint.fail_message(), mapping
        
        if not options:
            return 0, "", mapping
        
        for option in options:
            err, err_string, new_map = self._check_with_mapping(constaints[idx + 1 :], option)
            if not err:
                return 0, "", new_map

        return err, err_string, mapping

    def check_types(self) -> tuple[int, str]:
        """
        Types checks the proram and returns the returns a tuple with the number
        of errors found and any error messages.

        Returns:
            tuple[int, str]: errors found, error message
        """
        for node in self.program:
            node.visit(self)

        res, err, map_ = self._check_with_mapping(self.constaints, self.mapping)
        map_.pretty_print_mapping()
        return res, err
