from abc import ABC
from dataclasses import dataclass, field
import sys
from typing import Iterator, List
from itertools import count, permutations

from uzac.type import *
from uzac.token import *
from uzac.ast import (
    Block,
    ExpressionList,
    ForLoop,
    Function,
    IfElse,
    InfixApplication,
    Literal,
    NoOp,
    Program,
    Range,
    Return,
    VarDef,
    Error,
    VarRedef,
    WhileLoop,
)
from uzac.interpreter import *
from uzac.utils import in_bold, in_color, ANSIColor


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
    span: Span  # used for printing typer substitution

    def resolve_type(self, substitution: Substitution) -> Type:
        t = substitution.get_type_of(self)
        if t is None:
            return self
        if isinstance(t, SymbolicType):
            return t.resolve_type(substitution)
        return t

    def __str__(self) -> str:
        return f"{self.__class__}({self.identifier})"

    def __hash__(self):
        return self.identifier.__hash__()


@dataclass(frozen=True)
class IncompleteBranchType(Type):
    """
    A type to represent a branch that returns only one path.
    """

    path_type: Type
    span: Span

    def complete(self, that: Type):
        return self.path_type | that

    def __or__(self, that: object) -> bool:
        if isinstance(that, self.__class__):
            return self.path_type | that.path_type
        return self.complete(that)


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
        if isinstance(type_a, NonInferableType) or isinstance(type_b, NonInferableType):
            if isinstance(type_a, SymbolicType) or isinstance(type_b, SymbolicType):
                raise TypeError("\n" + self.span.get_underlined(f"Cannot infer type"))
            return True, None
        if type_a == type_b:
            return True, None
        elif isinstance(type_a, SymbolicType) or isinstance(type_b, SymbolicType):
            return False, [substitution + (self.a, self.b)]
        return False, None

    def fail_message(self) -> str:
        type_b = self.b.resolve_type(self.substitution)
        type_a = self.a.resolve_type(self.substitution)
        source = self.span.get_underlined(
            error_message=f" Error: Expected type '{type_b}' but found '{type_a}'",
            padding=len("at "),
        )
        return f"at {source}\n"


@dataclass
class IsReturnType(IsType):
    def fail_message(self):
        msg = super().fail_message()
        idx = msg.index("type")
        return msg[:idx] + "return " + msg[idx:]


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
        if isinstance(self.b, UnionType):
            types_b = (t.resolve_type(substitution) for t in self.b.types)
        else:
            types_b = (self.b.resolve_type(substitution),)
        for possible_type in types_b:
            if type_a == possible_type:
                return True, None
        return False, (substitution + (self.a, t) for t in types_b)

    def fail_message(self) -> str:
        type_a = self.a.resolve_type(self.substitution)
        type_b = UnionType(t.resolve_type(self.substitution) for t in self.b.types)
        source = self.span.get_underlined(
            error_message=f" Error: Expected type '{type_b}' but found '{type_a}'",
            padding=len("at "),
        )
        return f"at {source}\n"


@dataclass
class Applies(Constraint):
    """
    Constraints the list of arguments to match the arrow type of a function.
    """

    args: list[Type]
    ret_type: Type
    args_span: list[Span]
    b: ArrowType
    span: Span  # TODO: change args to have more precise span to the argument
    substitution: Substitution = field(default=None)
    _args_num_incorrect: Optional[tuple[int]] = field(default=None)
    _err_msgs: Optional[str] = field(default=None)

    def solve(self, substitution: Substitution):
        self._err_msgs = ""
        num_args = len(self.args)
        num_params = len(self.b.param_types)
        if num_args != num_params:
            self._args_num_incorrect = (num_args, num_params)
            return False, None

        fatal = False
        solved = True
        option = substitution
        for a, b, span in zip(self.args, self.b.param_types, self.args_span):
            type_a = a.resolve_type(substitution)
            type_b = b.resolve_type(substitution)
            if not Type.matches(type_a, type_b):
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
                sub_type = substitution.get_type_of(a)
                if sub_type is not None and (not isinstance(sub_type, SymbolicType)):
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

        if isinstance(self.ret_type, SymbolicType):
            return solved, option + (self.ret_type, self.b.return_type)

        return solved, []

    def fail_message(self) -> str:
        if self._args_num_incorrect:
            args, params = self._args_num_incorrect
            return self.span.get_underlined(
                f"Expected {params} arguments but found {args}"
            )

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

    def solve(
        self, substitution: Substitution
    ) -> tuple[bool, Optional[list[Substitution]]]:
        self.substitution = substitution
        choices_options = []
        for choice in self.choices:
            works, options = choice.solve(substitution)
            if works:
                return works, options
            if options:
                choices_options.append(options)
        if len(choices_options) == 0:
            choices_options = None

        if choices_options:
            assert isinstance(choices_options[0], Substitution), (
                f"found {choices_options =}"
            )
        return False, choices_options

    def fail_message(self) -> str:
        fails_msgs = (c.fail_message() for c in self.choices)
        line = "-" * 50
        msg = f"\n{line}\n{in_bold('or:')} \n".join(fails_msgs)
        return f"{in_bold('None of the following hold:')} \n{msg}"


@dataclass
class IsNotVoid(Constraint):
    """probably useless TODO: update"""

    span: Span

    def __init__(self, *types: Type):
        self.types = types

    def solve(self, substitution: Substitution) -> bool:
        return type_void not in self.types


# the return type of a tree node. If equal to type_node then either no Return nodes
# are inside the tree, or some node returns type_void
NodeAlwaysReturns = bool


@dataclass(frozen=True)
class TyperDiagnostic:
    """
    A TyperDiagnostic record that contains the number of errors, error and
    warning messages and the substitution that unifies the program if it exists.
    """

    error_count: int
    error_msg: str
    warning_msg: str
    substitution: Optional[Substitution]


class Typer:
    """
    Represents a typer than can typecheck a uza program.
    """

    def __init__(self, program: Program) -> None:
        self.program = program
        self.constaints: List[Constraint] = []

        # map from identifier in frame to tuple[Type, true if const, false if var]
        self._symbol_table = SymbolTable()
        self._functions = SymbolTable()

        self._symbol_gen = count()
        self.substitution = Substitution({})
        self._error_strings: list[str] = []
        self._warnings: list[str] = []

    def _create_new_symbol(self, span: Span):
        """
        Return a new unique SymbolicType.
        """
        return SymbolicType("symbolic_" + str(next(self._symbol_gen)), span)

    def _get_type_of_identifier(self, identifier: str) -> Type:
        return self._symbol_table.get(identifier)[0]

    def _var_is_immutable(self, identifier: str) -> Type:
        pair = self._symbol_table.get(identifier)
        if pair is None:
            return None
        return pair[1]

    def add_constaint(self, constraint: Constraint) -> None:
        """
        Adds a constraint to the typed program.
        """
        self.constaints.append(constraint)

    def visit_return(self, ret: Return) -> tuple[Type, NodeAlwaysReturns]:
        ret_type, _ = ret.value.visit(self)
        self.add_constaint(
            IsReturnType(ret_type, self._functions.get("__func_ret_type"), ret.span)
        )
        return type_void, True

    def visit_function(self, func: Function) -> tuple[Type, NodeAlwaysReturns]:
        f_signature = func.type_signature
        self._functions.define(func.identifier, func)
        self._functions.define("__func_ret_type", f_signature.return_type)
        with self._symbol_table.new_frame():
            for ident, type_ in zip(func.param_names, f_signature.param_types):
                self._symbol_table.define(ident.name, (type_, False))
            _, body_ret = func.body.visit(self)
            if f_signature.return_type != type_void and not body_ret:
                err = func.span.get_underlined(
                    in_color(
                        f" Warning: function branches might not always return '{f_signature.return_type}'",
                        ANSIColor.RED,
                    )
                )
                self._error_strings.append(err)

        return f_signature.return_type, False

    def visit_builtin(
        self, bi: BuiltIn, *arguments: Node, span: Span
    ) -> tuple[Type, NodeAlwaysReturns]:
        arg_types = [arg.visit(self)[0] for arg in arguments]
        signatures = bi.type_signatures

        span_zero = None
        if len(arguments) == 0:
            span_zero = Span(
                len(bi.identifier), len(bi.identifier + "()"), bi.identifier + "()"
            )

        if len(signatures) > 1:  # overloads
            overload_func_ret = self._create_new_symbol(span)
            constraints = []
            for signature in signatures:
                constraints.append(
                    Applies(
                        list(arg_types),
                        overload_func_ret,
                        [arg.span for arg in arguments],
                        signature,
                        Span.from_list(
                            arguments,
                        ),
                    )
                )
            self.add_constaint(
                OneOf(constraints, Span.from_list(arguments, empty_case=span_zero))
            )
            return overload_func_ret, False
        else:
            func_type = signatures[0]
            self.add_constaint(
                Applies(
                    list(arg_types),
                    func_type.return_type,
                    [arg.span for arg in arguments],
                    func_type,
                    Span.from_list(arguments, empty_case=span_zero),
                )
            )
            return func_type.return_type, False

    def visit_no_op(self, _) -> tuple[Type, NodeAlwaysReturns]:
        return type_void, False

    def visit_infix_application(self, infix: InfixApplication) -> Type:
        func_id = infix.func_id
        builtin = get_builtin(func_id)
        assert builtin
        return self.visit_builtin(builtin, infix.lhs, infix.rhs, span=infix.span)

    def visit_prefix_application(self, prefix: PrefixApplication) -> Type:
        func_id = prefix.func_id
        builtin = get_builtin(func_id)
        assert builtin
        return self.visit_builtin(builtin, prefix.expr, span=prefix.span)

    def visit_if_else(self, if_else: IfElse) -> tuple[Type, NodeAlwaysReturns]:
        pred, pred_ret = if_else.predicate.visit(self)
        self.add_constaint(IsType(pred, type_bool, if_else.predicate.span))
        truthy_type, truthy_returns = if_else.truthy_case.visit(self)
        if if_else.falsy_case is not None:
            falsy_type, falsy_returns = if_else.falsy_case.visit(self)
        else:
            falsy_returns = False

        return type_void, truthy_returns and falsy_returns

    def visit_identifier(
        self, identifier: Identifier
    ) -> tuple[Type, NodeAlwaysReturns]:
        return self._symbol_table.get(identifier.name)[0], False

    def visit_application(self, app: Application) -> tuple[Type, NodeAlwaysReturns]:
        func_id = app.func_id
        builtin = get_builtin(func_id)
        if builtin:
            return self.visit_builtin(builtin, *app.args, span=app.span)
        func: Function = self._functions.get(func_id)
        func_type = func.type_signature
        arg_count = len(app.args)
        param_count = len(func_type.param_types)
        if arg_count != param_count:
            raise TypeError(
                in_color(
                    "\n"
                    + Span.from_list(app.args).get_underlined(
                        f"Expected {param_count} arguments but found {arg_count}"
                    ),
                    ANSIColor.RED,
                )
            )
        app_types = (arg.visit(self)[0] for arg in app.args)
        for a, b, spannable in zip(app_types, func_type.param_types, app.args):
            self.add_constaint(IsType(a, b, spannable.span))

        return func_type.return_type, False

    def visit_var_def(self, var_def: VarDef) -> tuple[Type, NodeAlwaysReturns]:
        t = var_def.type_ if var_def.type_ else self._create_new_symbol(var_def.span)
        self.constaints.append(IsType(t, var_def.value.visit(self)[0], var_def.span))
        self._symbol_table.define(var_def.identifier, (t, var_def.immutable))
        return type_void, False

    def visit_var_redef(self, redef: VarRedef) -> tuple[Type, NodeAlwaysReturns]:
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
                redef.value.visit(self)[0],
                self._get_type_of_identifier(redef.identifier),
                redef.span,
            )
        )
        return type_void, False

    def visit_literal(self, literal: Literal) -> tuple[Type, NodeAlwaysReturns]:
        if literal.value is None:
            t = type_void
        else:
            t = type(literal.value)
        return python_type_to_uza_type(t), False

    def visit_error(self, error: Error) -> tuple[Type, NodeAlwaysReturns]:
        raise RuntimeError(f"Unexpected visit to error node :{error} in typer")

    def visit_expression_list(
        self, expr_list: ExpressionList
    ) -> tuple[Type, NodeAlwaysReturns]:
        return self._check_lines(expr_list.lines)

    def visit_block(self, scope: Block) -> tuple[Type, NodeAlwaysReturns]:
        with self._symbol_table.new_frame():
            return self._check_lines(scope.lines)

    def visit_while_loop(self, wl: WhileLoop) -> tuple[Type, NodeAlwaysReturns]:
        self.add_constaint(IsType(wl.cond.visit(self)[0], type_bool, wl.span))
        _, loop_ret = wl.loop.visit(self)
        return type_void, loop_ret

    # def visit_range(self, range: Range) -> tuple[Type, ReturnType]:
    #     indexee_type, _ = range.node.visit(self)
    #     index_constraint = OneOf(
    #         [
    #             IsSubType(indexee_type, type_string, range.node.span),
    #             IsSubType(indexee_type, type_list, range.node.span),
    #         ],
    #         range.span,
    #     )
    #     self.add_constaint(index_constraint)
    #     if range.start is not None:
    #         start_type, _ = range.start.visit(self)
    #         self.add_constaint(IsType(start_type, type_int, range.start.span))
    #     if range.end is not None:
    #         start_type, _ = range.end.visit(self)
    #         self.add_constaint(IsType(start_type, type_int, range.end.span))

    #     if indexee_type == type_string:
    #         return type_string, type_void
    #     return type_int | type_string, type_void

    def visit_for_loop(self, fl: ForLoop) -> tuple[Type, NodeAlwaysReturns]:
        with self._symbol_table.new_frame():
            if fl.init:
                fl.init.visit(self)
            if not isinstance(fl.cond, NoOp):
                self.add_constaint(IsType(fl.cond.visit(self)[0], type_bool, fl.span))
            if fl.incr:
                fl.incr.visit(self)
            fl.interior.visit(self)
            return type_void, False

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
        err_string = ""  # TODO: pass lambda function instead of creating string
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
                case True, sub:
                    if sub:
                        assert isinstance(sub, Substitution)
                        substitution = sub

        return err, err_string, substitution

    def _check_lines(self, lines: List[Node]) -> tuple[int, str, str]:
        """
        Type checks a list of nodes.
        """
        node_returns = []
        for node in lines:
            _, ret = node.visit(self)
            node_returns.append(ret)

        return type_void, any(node_returns)

        # errors = len(self._error_strings)
        # if errors > 0:
        #     return errors, "\n".join(self._error_strings), None

        # errors, err_str, substitution = self._check_with_sub(
        #     self.constaints, self.substitution
        # )

        # return errors, err_str, substitution

    def check_types(self) -> TyperDiagnostic:
        """
        Types checks an uza program.

        Args:
            generate_substitution (Substitution): generates and returns the substitution string
                if True

        Returns:
            A TyperDiagnostic
        """
        self.program.syntax_tree.visit(self)
        errors, err_str, substitution = self._check_with_sub(
            self.constaints, self.substitution
        )

        errors += len(self._error_strings)
        err_str = "\n".join(self._error_strings) + err_str
        warn_str = "\n".join(self._warnings)
        return TyperDiagnostic(errors, err_str, warn_str, substitution)
