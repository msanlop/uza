from abc import ABC
from dataclasses import dataclass, field
import sys
from typing import Iterator, List
from itertools import count, permutations

from uzac.type import *
from uzac.token import *
from uzac.ast import (
    App,
    Block,
    ExpressionList,
    ForLoop,
    Function,
    IfElse,
    InfixApplication,
    Literal,
    MethodApplication,
    NoOp,
    Program,
    Range,
    Return,
    UzaASTVisitor,
    VarDef,
    VarRedef,
    WhileLoop,
)
from uzac.interpreter import *
from uzac.utils import UzaException, UzaTypeError, in_bold, in_color, ANSIColor
from uzac.builtins import get_builtin


@dataclass
class Substitution:
    """
    A substitution is a map from symbolic types to real types.
    """

    __substitutions: dict["SymbolicType", Type]

    def get_type_of(self, t: "SymbolicType") -> Optional[Type]:
        """
        Returns the substited real type for _t_ in this substitution. None if not
        substitution found.
        """
        return self.__substitutions.get(t)

    def pretty_string(self) -> str:
        if len(self.__substitutions) == 0:
            return ""
        out = ""
        exprs = [expr.span.get_source() for expr in self.__substitutions]
        max_expr_len = max(len(s) for s in exprs)
        for idx, k in enumerate(self.__substitutions):
            yellow_type = in_color(str(k.resolve_type(self)), ANSIColor.YELLOW)
            out += f"{exprs[idx]:<{max_expr_len}} := {yellow_type}\n"
        return out

    def __add__(self, that: object):
        """
        Takes in either a tuple pair or a Substitution and return a new
        Subsitution.
        """
        if isinstance(that, tuple) and len(that) == 2:
            new_dict = {that[0]: that[1], **self.__substitutions}
            return Substitution(new_dict)
        if isinstance(that, Substitution):
            return Substitution(self.__substitutions | that.__substitutions)
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

    def is_symbolic(self):
        return True

    def resolve_type(self, substitution: Substitution) -> Type:
        t = substitution.get_type_of(self)
        if t is None:
            return self
        if t.is_symbolic():
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


@dataclass
class Constraint(ABC):
    span: Span
    substitution: Substitution = field(init=False, default=None)
    _errs: List[UzaException] = field(init=False, default_factory=lambda: list())
    SOLVE_FAIL = (False, None)
    SOLVE_SUCCEED = (True, None)
    SOLVE_OPTIONS = lambda o: (False, o)

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

    def errors(self) -> List[UzaException]:
        """
        Returns the list of errors for previous __solve()_ attempt.
        """
        raise NotImplementedError(
            f"<{self.errors.__name__}> not implemented for {self}"
        )


@dataclass
class IsType(Constraint):
    """
    A constraint for a type to be equal to another.
    """

    a: Type
    b: Type

    def __solve_generic(
        self, a: Type, b: GenericType, sub: Substitution
    ) -> tuple[Type, Optional[Substitution]]:
        match (a, b.param_type):
            case (SymbolicType(), NonInferableType()):
                raise UzaTypeError(self.span, f"Cannot infer type")
            case (_, NonInferableType()):
                return Constraint.SOLVE_SUCCEED

        match a:
            case GenericType(base, param):
                if not Type.matches(base, b.base_type):
                    return Constraint.SOLVE_FAIL
                return IsType(self.span, param, b.param_type).solve(sub)
            case SymbolicType():
                return False, [Substitution({a: b})]
            case _:
                return Constraint.SOLVE_FAIL

    def solve(self, substitution: Substitution) -> tuple[Type, Substitution]:
        self.substitution = substitution
        type_a = self.a.resolve_type(substitution)
        type_b = self.b.resolve_type(substitution)
        if type_b.is_generic_type():
            return self.__solve_generic(type_a, type_b, substitution)
        if type_a == type_b:
            return Constraint.SOLVE_SUCCEED
        if type_a.is_symbolic() or type_b.is_symbolic():
            return False, [substitution + (self.a, self.b)]
        return Constraint.SOLVE_FAIL

    def errors(self) -> List[UzaException]:
        type_b = self.b.resolve_type(self.substitution)
        type_a = self.a.resolve_type(self.substitution)
        self._errs = [
            UzaTypeError(
                self.span,
                f"Expected type '{type_b}' but found '{type_a}'",
            )
        ]
        return self._errs


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

    def solve(self, substitution: Substitution):
        self.substitution = substitution
        type_a = self.a.resolve_type(substitution)
        if isinstance(self.b, UnionType):
            types_b = (t.resolve_type(substitution) for t in self.b.types)
        else:
            types_b = (self.b.resolve_type(substitution),)
        for possible_type in types_b:
            if type_a == possible_type:
                return Constraint.SOLVE_SUCCEED
        return False, (substitution + (self.a, t) for t in types_b)

    def errors(self) -> List[UzaException]:
        type_a = self.a.resolve_type(self.substitution)
        type_b = UnionType(t.resolve_type(self.substitution) for t in self.b.types)
        self._errs = [
            UzaTypeError(
                self.span,
                f"Expected type '{type_b}' but found '{type_a}'",
            )
        ]
        return self._errs


@dataclass
class Applies(Constraint):
    """
    Constraints the list of arguments to match the arrow type of a function.
    """

    args: list[Type]
    ret_type: Type
    args_span: list[Span]
    b: ArrowType
    generic_typevar: Optional[SymbolicType] = field(default=None)
    __args_num_incorrect: Optional[tuple[int]] = field(default=None)

    def __solve_generic_args(
        self, generics_set: dict[Type, bool], sub: Substitution
    ) -> tuple[bool, Optional[Substitution]]:
        """
        This method checks that all the generic arguments match. Returns the same
        as other `solve` methods.
        It fails without substitution if there are more than two types. Or two
        non-Symbolic types (e.g. int and float).
        """
        if len(generics_set) == 0:
            return True, sub

        if len(generics_set) > 2:
            return Constraint.SOLVE_FAIL

        if len(generics_set) == 2:
            # check if symbolic
            a, b = generics_set.keys()
            t1, t2 = a, b

            if a.is_generic_type():
                t1 = a.param_type

            if not Type.matches(t1, t2) and not (t1.is_symbolic() or t2.is_symbolic()):
                self._errs.append(
                    UzaTypeError(
                        self.span,
                        f"Argument type `{b}` does not match for generic function of type `{a}`",
                    )
                )
                return Constraint.SOLVE_FAIL
            if t1.is_symbolic():
                sub += (a, b)

        return True, sub

    def solve(self, substitution: Substitution):
        self.__err_msgs = ""
        num_args = len(self.args)
        num_params = len(self.b.param_types)
        if num_args != num_params:
            self.__args_num_incorrect = (num_args, num_params)
            return False, None

        fatal = False
        solved = True
        option = substitution
        generic_args: dict[Type, bool] = {}

        # check that each argument type matches the parameter type
        for a, b, span in zip(self.args, self.b.param_types, self.args_span):
            type_a = a.resolve_type(substitution)
            type_b = b.resolve_type(substitution)

            # do generics params after loop
            if type_b.is_generic_type() and type_a.is_generic_type():
                generic_args[type_a] = True
            elif type_b.is_generic_arg():
                generic_args[type_a] = True
            elif not Type.matches(type_a, type_b):
                # if does not match, try updating subsitution if possible (type_a
                # is Symbolic) or fail fatally
                solved = False
                if not type_a.is_symbolic():
                    type_str = str(self.b)
                    err = UzaTypeError(
                        span,
                        f"""Expected {type_b} but found {type_a}
                        for function type: {in_color(type_str, ANSIColor.GREEN)}""",
                    )
                    self._errs.append(err)
                    fatal = True
                    continue
                option = option + (a, b)

        if self.b.return_type.is_generic_arg():
            generic_args[self.ret_type] = True
        elif self.ret_type.is_symbolic():
            option += (self.ret_type, self.b.return_type)

        generic_ok, generic_sub = self.__solve_generic_args(generic_args, option)

        if fatal or (not generic_ok and generic_sub is None):
            return Constraint.SOLVE_FAIL

        option = generic_sub

        if solved and generic_ok:
            return True, option
        return False, [option]

    def errors(self) -> List[UzaException]:
        if self.__args_num_incorrect:
            args, params = self.__args_num_incorrect
            self._errs.append(
                UzaTypeError(self.span, f"Expected {params} arguments but found {args}")
            )

        return self._errs


@dataclass
class OneOf(Constraint):
    """
    A list of constraints, one of wich must hold at least.
    """

    choices: List[Constraint]

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
                choices_options.append(*options)
        if len(choices_options) == 0:
            choices_options = None

        if choices_options:
            assert isinstance(choices_options[0], Substitution), (
                f"found {choices_options =}"
            )
        return False, choices_options

    def errors(self) -> List[UzaException]:
        self._errs = []
        for c in self.choices:
            self._errs += c.errors()
        err = UzaTypeError(
            self.span,
            in_bold("No function overload found")
            + "\n (possible function signatures are shown in green)",
        )
        self._errs.append(err)
        return self._errs


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
    errors: List[UzaTypeError]
    warning_msg: str
    substitution: Optional[Substitution]


class Typer(UzaASTVisitor):
    """
    Represents a typer than can typecheck a uza program.
    """

    def __init__(self, program: Program) -> None:
        self.program = program
        self.constaints: List[Constraint] = []

        # map from identifier in frame to tuple[Type, true if const, false if var]
        self.__symbol_table = SymbolTable()
        self.__functions = SymbolTable()

        self.__symbol_gen = count()
        self.substitution = Substitution({})
        self.__errors: list[UzaTypeError] = []
        self.__warnings: list[str] = []

    def __create_new_symbol(self, span: Span):
        """
        Return a new unique SymbolicType.
        """
        return SymbolicType("symbolic_" + str(next(self.__symbol_gen)), span)

    def __get_type_of_identifier(self, identifier: str) -> Type:
        return self.__symbol_table.get(identifier)[0]

    def __var_is_immutable(self, identifier: str) -> Type:
        pair = self.__symbol_table.get(identifier)
        if pair is None:
            return None
        return pair[1]

    def __mark_unused_expression(self, that: Node):
        """
        Mark the Node to be popped in the bytecode if it returns a value. Does
        not affect other Node types.

        For example:
        if true then func()
        The return value of `func` should be popped.

        if true then x += 1
        Reassignement statement does not push to the stack so nothing needs to be
        popped.

        """
        if issubclass(that.__class__, App):
            that.pop_value = True

    def add_constaint(self, constraint: Constraint) -> None:
        """
        Adds a constraint to the typed program.
        """
        self.constaints.append(constraint)

    def visit_return(self, ret: Return) -> tuple[Type, NodeAlwaysReturns]:
        ret_type, _ = ret.value.visit(self)
        self.add_constaint(
            IsReturnType(ret.span, ret_type, self.__functions.get("__func_ret_type"))
        )
        return type_void, True

    def visit_break(self, that):
        return type_void, False

    def visit_continue(self, that):
        return type_void, False

    def visit_function(self, func: Function) -> tuple[Type, NodeAlwaysReturns]:
        f_signature = func.type_signature
        self.__functions.define(func.identifier, func)
        self.__functions.define("__func_ret_type", f_signature.return_type)
        with self.__symbol_table.new_frame():
            for ident, type_ in zip(func.param_names, f_signature.param_types):
                self.__symbol_table.define(ident.name, (type_, False))
            _, body_ret = func.body.visit(self)
            if f_signature.return_type != type_void and not body_ret:
                err = UzaTypeError(
                    func.span,
                    f" Warning: function branches might not always return '{f_signature.return_type}'",
                )
                self.__errors.append(err)

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
            overload_func_ret = self.__create_new_symbol(span)
            constraints = []
            for signature in signatures:
                constraints.append(
                    Applies(
                        Span.from_list(
                            arguments,
                        ),
                        list(arg_types),
                        overload_func_ret,
                        [arg.span for arg in arguments],
                        signature,
                    )
                )
            self.add_constaint(
                OneOf(Span.from_list(arguments, empty_case=span_zero), constraints)
            )
            return overload_func_ret, False
        else:
            func_type = signatures[0]
            self.add_constaint(
                Applies(
                    Span.from_list(arguments, empty_case=span_zero),
                    list(arg_types),
                    func_type.return_type,
                    [arg.span for arg in arguments],
                    func_type,
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

    def visit_method_app(self, method: MethodApplication):
        method.method.pop_value = method.pop_value
        app_type, ret = method.method.visit(self)
        return app_type, ret

    def visit_if_else(self, if_else: IfElse) -> tuple[Type, NodeAlwaysReturns]:
        pred, pred_ret = if_else.predicate.visit(self)
        self.add_constaint(IsType(if_else.predicate.span, pred, type_bool))
        self.__mark_unused_expression(if_else.truthy_case)
        _, truthy_returns = if_else.truthy_case.visit(self)
        if if_else.falsy_case is not None:
            self.__mark_unused_expression(if_else.falsy_case)
            _, falsy_returns = if_else.falsy_case.visit(self)
        else:
            falsy_returns = False

        return type_void, (truthy_returns and falsy_returns)

    def visit_identifier(
        self, identifier: Identifier
    ) -> tuple[Type, NodeAlwaysReturns]:
        return self.__symbol_table.get(identifier.name)[0], False

    def __set_generic_arg(self, bi: BuiltIn, arg: Type) -> BuiltIn:
        arrow_types = bi.type_signatures
        if arg == NonInferableType():
            return bi

        types: List[Type] = []
        for t in arrow_types:
            types.append(t.with_generic_argument(arg))
        return BuiltIn(
            bi.identifier,
            bi.interpret,
            types,
            bi.is_op_code,
            type_not_inferrable=bi.type_not_inferrable,
        )

    def visit_application(self, app: Application) -> tuple[Type, NodeAlwaysReturns]:
        func_id = app.func_id
        builtin = get_builtin(func_id)
        if builtin is not None:
            if builtin.type_not_inferrable:
                if app.generic_arg is not None:
                    builtin = self.__set_generic_arg(builtin, app.generic_arg)
                else:
                    raise UzaTypeError(app.span, "Cannot infer generic type")
            return self.visit_builtin(builtin, *app.args, span=app.span)
        func: Function = self.__functions.get(func_id)
        func_type = func.type_signature
        arg_count = len(app.args)
        param_count = len(func_type.param_types)
        if arg_count != param_count:
            raise UzaTypeError(
                Span.from_list(app.args, empty_case=app.span),
                f"Expected {param_count} arguments but found {arg_count}",
            )
        app_types = (arg.visit(self)[0] for arg in app.args)
        for a, b, spannable in zip(app_types, func_type.param_types, app.args):
            self.add_constaint(IsType(spannable.span, a, b))

        return func_type.return_type, False

    def visit_var_def(self, var_def: VarDef) -> tuple[Type, NodeAlwaysReturns]:
        t = var_def.type_ if var_def.type_ else self.__create_new_symbol(var_def.span)
        self.constaints.append(IsType(var_def.span, t, var_def.value.visit(self)[0]))
        self.__symbol_table.define(var_def.identifier, (t, var_def.immutable))
        return type_void, False

    def visit_var_redef(self, redef: VarRedef) -> tuple[Type, NodeAlwaysReturns]:
        identifier_str = redef.identifier.name
        is_immutable = self.__var_is_immutable(identifier_str)
        if is_immutable is None:
            err = UzaTypeError(
                redef.span,
                f"'{identifier_str}' must be declared before reassignement",
            )
            self.__errors.append(err)
        if is_immutable is True:
            err = UzaTypeError(
                redef.span,
                f"cannot reassign const variable '{identifier_str}'",
            )
            self.__errors.append(err)
        self.add_constaint(
            IsType(
                redef.span,
                redef.value.visit(self)[0],
                self.__get_type_of_identifier(identifier_str),
            )
        )
        return type_void, False

    def visit_literal(self, literal: Literal) -> tuple[Type, NodeAlwaysReturns]:
        if literal.value is None:
            t = type_void
        else:
            t = type(literal.value)
        return python_type_to_uza_type(t), False

    def visit_expression_list(
        self, expr_list: ExpressionList
    ) -> tuple[Type, NodeAlwaysReturns]:
        return self.__check_lines(expr_list.lines)

    def visit_block(self, scope: Block) -> tuple[Type, NodeAlwaysReturns]:
        with self.__symbol_table.new_frame():
            return self.__check_lines(scope.lines)

    def visit_while_loop(self, wl: WhileLoop) -> tuple[Type, NodeAlwaysReturns]:
        self.__mark_unused_expression(wl.cond)
        self.add_constaint(IsType(wl.span, wl.cond.visit(self)[0], type_bool))
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
        with self.__symbol_table.new_frame():
            if fl.init:
                self.__mark_unused_expression(fl.init)
                fl.init.visit(self)
            if not isinstance(fl.cond, NoOp):
                self.add_constaint(IsType(fl.span, fl.cond.visit(self)[0], type_bool))
            if fl.incr:
                self.__mark_unused_expression(fl.incr)
                fl.incr.visit(self)
            fl.interior.visit(self)
            return type_void, False

    def __check_with_sub(
        self, constaints: list[Constraint], substitution: Substitution
    ) -> tuple[int, List[UzaTypeError], Substitution]:
        """
        Recursively try to unify the constraints with the given substitution for
        symbolic types.

        One way to think of this algorithm is that is tries solving constraints
        and inferring types but backtracks (via recursion) when the current
        inferred types are not working, i.e. the substitution does not unify
        the constraints.
        """
        err = 0
        errors = []
        options = []
        idx = 0
        for idx, constraint in enumerate(constaints):
            solved, options = constraint.solve(substitution)
            match solved, options:
                case False, None:
                    return 1, constraint.errors(), substitution
                case False, options_list:
                    for option in options_list:
                        err, errors, new_map = self.__check_with_sub(
                            constaints[idx + 1 :], option
                        )
                        if not err:
                            return 0, [], new_map
                    break
                case True, sub:
                    if sub:
                        assert isinstance(sub, Substitution), (
                            f"is not {Substitution.__name__}: {sub}"
                        )
                        substitution = sub

        return err, errors, substitution

    def __check_lines(self, lines: List[Node]) -> tuple[int, str, str]:
        """
        Type checks a list of nodes.
        """
        node_returns = []
        for node in lines:
            self.__mark_unused_expression(node)
            _, ret = node.visit(self)
            node_returns.append(ret)

        return type_void, any(node_returns)

    def typecheck_program(self) -> TyperDiagnostic:
        """
        Types checks an uza program.

        Args:
            generate_substitution (Substitution): generates and returns the substitution string
                if True

        Returns:
            A TyperDiagnostic
        """
        self.program.syntax_tree.visit(self)
        error_count, errors, substitution = self.__check_with_sub(
            self.constaints, self.substitution
        )

        error_count += len(self.__errors)
        errors += self.__errors
        warn_str = "\n".join(self.__warnings)
        return TyperDiagnostic(error_count, errors, warn_str, substitution)
