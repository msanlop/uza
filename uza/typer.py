from abc import ABC
from dataclasses import dataclass, field
from typing import List
from itertools import count, permutations

from uza.type import *
from uza.token import *
from uza.uzast import InfixApplication, Literal, Program, VarDef, Error, VarRedef
from uza.interpreter import *
from uza.utils import in_bold, in_color, ANSIColor


@dataclass
class Substitution:
    """
    A substitution is a map from symbolic types to real types.
    """

    _substitutions: dict["SymbolicType", Type]

    def get_type_of(self, t: "SymbolicType") -> Optional[Type]:
        """
        Returns the substited real type for _t_ in this substitution. None if not
        substitution found.
        """
        return self._substitutions.get(t)

    def pretty_string(self) -> str:
        if len(self._substitutions) == 0:
            return ""
        out = ""
        exprs = [expr.span.get_source() for expr in self._substitutions]
        colored = [in_color(s, ANSIColor.GREEN) for s in exprs]
        max_expr_len = max(len(s) for s in colored)
        for idx, k in enumerate(self._substitutions):
            yellow_type = in_color(str(k.resolve_type(self)), ANSIColor.YELLOW)
            out += f"{colored[idx]:<{max_expr_len}} := {yellow_type}\n"
        return out

    def __add__(self, that: object):
        if isinstance(that, tuple) and len(that) == 2:
            new_dict = {that[0]: that[1], **self._substitutions}
            return Substitution(new_dict)
        if isinstance(that, Substitution):
            return Substitution(self._substitutions | that._substitutions)
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

    def resolve_type(self, substitution: Substitution) -> Type:
        t = substitution.get_type_of(self)
        if t is None:
            return self
        if isinstance(t, SymbolicType):
            return t.resolve_type(substitution)
        return t

    def __str__(self) -> str:
        return f"{self.__class__}({self.identifier})"


class Constraint(ABC):
    span: Span
    substitution: Substitution

    def solve(
        self, substitution: Substitution
    ) -> tuple[bool, Optional[list[Substitution]]]:
        """
        Tries to solve the constraint. Three outcomes are possible:
        - The contraint holds
        - The constraint 'fails' but returns a list of substitution for symbolic types
        - The constraint fails

        Args:
            substitution (Substitution): the current substitution of symbolic types

        Raises:
            NotImplementedError: if the contraint doesn't implement <solve>

        Returns:
            tuple[bool, Optional[list[tuple]]]:
                (true, None) if holds
                (false, None) if not solvable
                (false, list) for a list of possible substitutions
        """
        raise NotImplementedError(f"<solve> not implemented for {self}")

    def fail_message(self) -> str:
        """
        Returns the failed message for previous _solve()_ try. This method is
        stateful!
        If called before _solve()_ it might have self.substitution = None. And some
        implementations generate the message while solving.
        """
        raise NotImplementedError(f"<fail_message> not implemented for {self}")


@dataclass
class IsType(Constraint):
    """
    A constraint for a type to be equal to another.
    """

    a: Type
    b: Type
    span: Span
    substitution: Substitution = field(default=None)

    def solve(self, substitution: Substitution):
        self.substitution = substitution
        type_a = self.a.resolve_type(substitution)
        type_b = self.b.resolve_type(substitution)
        if type_a == type_b:
            return True, None
        if isinstance(type_a, SymbolicType) or isinstance(type_b, SymbolicType):
            return False, [substitution + (self.a, self.b)]
        return False, None

    def fail_message(self) -> str:
        type_b = self.b.resolve_type(self.substitution)
        type_a = self.a.resolve_type(self.substitution)
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
    substitution: Substitution = field(default=None)

    def solve(self, substitution: Substitution):
        self.substitution = substitution
        type_a = self.a.resolve_type(substitution)
        types_b = (t.resolve_type(substitution) for t in self.b.types)
        for possible_type in types_b:
            if type_a == possible_type:
                return True, None
        return False, (substitution + (self.a, t) for t in types_b)

    def fail_message(self) -> str:
        type_a = self.a.resolve_type(self.substitution)
        type_b = UnionType(t.resolve_type(self.substitution) for t in self.b.types)
        source = self.span.get_underlined(
            error_message=f" Expected type '{type_b}' but found '{type_a}'",
            padding=len("at "),
        )
        return f"at {source}\n"


@dataclass
class Applies(Constraint):
    """
    Constraints the list of arguments to match the arrow type of a function.
    """

    args: list[Type]
    args_span: list[Span]
    b: ArrowType
    span: Span  # TODO: change args to have more precise span to the argument
    substitution: Substitution = field(default=None)
    _args_num_incorrect: Optional[tuple[int]] = field(default=None)
    _err_msgs: Optional[str] = field(default=None)

    def solve(self, substitution: Substitution):
        self._err_msgs = ""
        num_args = len(self.args)
        num_params = len(self.b.parameters)
        if num_args != num_params:
            self._args_num_incorrect = (num_args, num_params)
            return False, None

        fatal = False
        solved = True
        option = substitution
        for a, b, span in zip(self.args, self.b.parameters, self.args_span):
            type_a = a.resolve_type(substitution)
            type_b = b.resolve_type(substitution)
            if type_a != type_b:
                solved = False
                if not isinstance(a, SymbolicType):
                    type_str = str(self.b)
                    self._err_msgs += (
                        f"for function type: {in_color(type_str, ANSIColor.GREEN)}\nat "
                    )
                    self._err_msgs += span.get_underlined(
                        f"Expected {type_b} but found {type_a}", len("at ")
                    )
                    fatal = True
                    continue
                if substitution.get_type_of(a) is not None:
                    type_str = str(self.b)
                    self._err_msgs += (
                        f"for function type: {in_color(type_str, ANSIColor.GREEN)}\nat "
                    )
                    self._err_msgs += span.get_underlined(
                        f"Expected {type_b} but found {type_a}", len("at ")
                    )
                    fatal = True
                    continue
                option = option + (a, b)

        if fatal:
            return False, None
        return solved, [option]

    def fail_message(self) -> str:
        if self._args_num_incorrect:
            args, params = self._args_num_incorrect
            return f"Expected {params} arguments but found {args}"

        return self._err_msgs


@dataclass
class OneOf(Constraint):
    """
    A list of constraints, one of wich must hold at least.
    """

    choices: List[Constraint]
    span: Span
    substitution: Substitution = field(default=None)
    _a_solved: list[bool] = field(default=None)

    def solve(self, substitution: Substitution) -> bool:
        self.substitution = substitution
        choices_options = []
        for choice in self.choices:
            works, options = choice.solve(substitution)
            if works:
                return works, None
            if options:
                choices_options.append(options)
        if len(choices_options) == 0:
            choices_options = None
        return False, choices_options

    def fail_message(self) -> str:
        fails_msgs = (c.fail_message() for c in self.choices)
        msg = f"\n{in_bold('or:')} \n".join(fails_msgs)
        return f"{in_bold('None of the following hold:')} \n{msg}"


@dataclass
class IsNotVoid(Constraint):
    """probably useless TODO: update"""

    span: Span

    def __init__(self, *types: Type):
        self.types = types

    def solve(self, substitution: Substitution) -> bool:
        return type_void not in self.types


class Typer:
    """
    Represents a typer than can typecheck a uza program.
    """

    def __init__(self, program: Program) -> None:
        self.program = program
        self.constaints: List[Constraint] = []

        # map from identifier in frame to tuple[Type, true if const, false if var]
        self.symbols = SymbolTable()

        self.symbol_gen = count()
        self.substitution = Substitution({})
        self._error_strings: list[str] = []

    def _create_new_symbol(self, node: Node):
        """
        Return a new unique SymbolicType.
        """
        return SymbolicType("symbolic_" + str(next(self.symbol_gen)), node.span)

    def _get_type_of_identifier(self, identifier: str) -> Type:
        return self.symbols.get(identifier)[0]

    def _var_is_immutable(self, identifier: str) -> Type:
        pair = self.symbols.get(identifier)
        if pair is None:
            return None
        return pair[1]

    def add_constaint(self, constraint: Constraint) -> None:
        """
        Adds a constraint to the typed program.
        """
        self.constaints.append(constraint)

    def visit_builtin(self, func_id: BuiltIn, *arguments: Node):
        lhs, rhs = arguments[0], None
        if len(arguments) == 2:
            rhs = arguments[1]

        ### PRINT FUNCTIONS ###

        if func_id in (bi_print, bi_println):
            for arg in arguments:
                arg.visit(self)
            return type_void

        ### INFIX ARITHMETIC ###

        lhs_type = lhs.visit(self)
        rhs_type = rhs.visit(self)
        arithmetic_type = UnionType(type_int, type_float)
        arith_constaint = Applies(
            [lhs_type, rhs_type],
            [rhs.span, rhs.span],
            ArrowType([arithmetic_type, arithmetic_type], arithmetic_type),
            lhs.span + rhs.span,
        )
        if func_id == bi_add:
            string_add_constaint = Applies(
                [lhs_type, rhs_type],
                [lhs.span, rhs.span],
                ArrowType([type_string, type_string], arithmetic_type),
                lhs.span + rhs.span,
            )

            polymorphic = OneOf(
                [arith_constaint, string_add_constaint],
                arguments[0].span + arguments[-1].span,
            )
            self.add_constaint(polymorphic)
            return lhs_type

        if func_id in (bi_sub, bi_mul, bi_div):
            self.add_constaint(arith_constaint)
            return arithmetic_type

        raise NotImplementedError(f"not implemented for {func_id}")

    def visit_infix_application(self, infix: InfixApplication):
        func_id = infix.func_id
        builtin = get_builtin(func_id)
        assert builtin
        return self.visit_builtin(builtin, infix.lhs, infix.rhs)

    def visit_identifier(self, identifier: Identifier):
        return self.symbols.get(identifier.name)[0]

    def visit_application(self, app: Application):
        func_id = app.func_id
        builtin = get_builtin(func_id)
        assert builtin
        return self.visit_builtin(builtin, *app.args)

    def visit_var_def(self, var_def: VarDef):
        t = var_def.type_ if var_def.type_ else self._create_new_symbol(var_def)
        self.constaints.append(IsType(t, var_def.value.visit(self), var_def.span))
        self.symbols.define(var_def.identifier, (t, var_def.immutable))

    def visit_var_redef(self, redef: VarRedef):
        identifier = redef.identifier
        is_immutable = self._var_is_immutable(identifier)
        if is_immutable is None:
            err = redef.span.get_underlined(
                f"'{identifier}' must be declared before reassignement",
            )
            self._error_strings.append(err)
        if is_immutable is True:
            err = redef.span.get_underlined(
                f"cannot reassign const variable '{identifier}'",
            )
            self._error_strings.append(err)
        self.add_constaint(
            IsType(
                redef.value.visit(self),
                self._get_type_of_identifier(redef.identifier),
                redef.span,
            )
        )

    def visit_literal(self, literal: Literal):
        return python_type_to_uza_type(type(literal.value))

    def visit_error(self, error: Error):
        raise RuntimeError(f"Unexpected visit to error node :{error} in typer")

    def _check_with_sub(
        self, constaints: list[Constraint], substitution: Substitution
    ) -> tuple[int, str, Substitution]:
        """
        Recursively try to unify the constraints with the given substitution for
        symbolic types.

        One way to think of this algorithm is that is tries solving constraints
        and inferring types but backtracks (via recursion) when the current
        inferred types are not working, i.e. the substitution does not unify
        the constraints.
        """
        err = 0
        err_string = ""
        options = []
        idx = 0
        for idx, constraint in enumerate(constaints):
            solved, options = constraint.solve(substitution)
            match solved, options:
                case False, None:
                    return 1, constraint.fail_message(), substitution
                case False, options_list:
                    for option in options_list:
                        err, err_string, new_map = self._check_with_sub(
                            constaints[idx + 1 :], option
                        )
                        if not err:
                            return 0, "", new_map
                    break

        return err, err_string, substitution

    def check_types(self, output_substitution=False) -> tuple[int, str, str]:
        """
        Types checks the proram and returns the returns a tuple with the number
        of errors found and any error messages.

        Args:
            generate_substitution (Substitution): generates and returns the substitution string
                if True

        Returns:
            tuple[int, str, str]: (errors found, error message, substitution string or none)
        """
        for node in self.program.syntax_tree:
            node.visit(self)

        errors = len(self._error_strings)
        if errors > 0:
            return errors, "\n".join(self._error_strings), None

        errors, err_str, substitution = self._check_with_sub(
            self.constaints, self.substitution
        )
        if output_substitution:
            verbose_map = substitution.pretty_string()
        else:
            verbose_map = ""

        return errors, err_str, verbose_map
