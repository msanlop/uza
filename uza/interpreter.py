from __future__ import annotations
from dataclasses import dataclass
from typing import List, Optional, TypeVar

from uza.type import ArrowType
from uza.uzast import (
    Application,
    Identifier,
    IfElse,
    InfixApplication,
    Literal,
    Node,
    PrefixApplication,
    Block,
    Scope,
    Value,
    VarDef,
    Program,
    VarRedef,
)
from uza.utils import SymbolTable


@dataclass(frozen=True)
class BuiltIn:
    """
    A BuiltIn is a function that is part of the standard library.
    """

    identifier: str
    # TODO define type
    _builtins_dict: dict[str, BuiltIn]

    def __post_init__(self):
        """adds itself to the dict that holds all the builtins"""
        self._builtins_dict[self.identifier] = self

    def __repr__(self) -> str:
        return f"BuiltIn({self.identifier})"


_builtins: dict[str, BuiltIn] = {}
bi_add = BuiltIn("+", _builtins)
bi_sub = BuiltIn("-", _builtins)
bi_mul = BuiltIn("*", _builtins)
bi_div = BuiltIn("/", _builtins)
bi_pow = BuiltIn("**", _builtins)
bi_and = BuiltIn("and", _builtins)
bi_or = BuiltIn("or", _builtins)
bi_print = BuiltIn("print", _builtins)
bi_println = BuiltIn("println", _builtins)
bi_max = BuiltIn("max", _builtins)
bi_min = BuiltIn("min", _builtins)


def get_builtin(identifier: Identifier) -> Optional[BuiltIn]:
    """
    Returns a _BuiltIn_ with the given who's name matches the _identifier_
    if it exists.
    """
    return _builtins.get(identifier.name)


class Interpreter:
    """
    A class that takes in a program and interprets it by walking the AST.

    Uses the visitor pattern by calling node.visit(self). Performance is not a
    concern in this implementation. It's main use is to ensure parity with the
    VM interpretation and to more easily test ideas.
    """

    def __init__(self, program: Program | Node):
        self._context = SymbolTable()
        self._program = program

    T = TypeVar("T")
    R = TypeVar("R")

    def visit_built_in_application(self, func_id, *params) -> Optional[Value]:
        ret = None
        lhs, rhs = params[0], None
        if len(params) > 1:
            rhs = params[1]

        if func_id == bi_add:
            ret = lhs + rhs
        elif func_id == bi_sub:
            if len(params) == 1:
                ret = -lhs
            else:
                ret = lhs - rhs
        elif func_id == bi_mul:
            ret = lhs * rhs
        elif func_id == bi_div:
            # C division casts the rhs to the lhs's type TODO: false
            casted = type(lhs)(rhs)
            if isinstance(lhs, int):
                ret = lhs // casted
            else:
                ret = lhs / casted
        elif func_id == bi_and:
            ret = lhs and rhs
        elif func_id == bi_or:
            ret = lhs or rhs
        elif func_id == bi_pow:
            ret = lhs**rhs
        elif func_id == bi_print:
            params = map(
                lambda p: str(p).lower() if isinstance(p, bool) else p, params
            )  # hack to fix bools prints
            print(*params, end="")
            ret = None
        elif func_id == bi_println:
            params = map(
                lambda p: str(p).lower() if isinstance(p, bool) else p, params
            )  # hack to fix bools prints
            print(*params)
            ret = None
        elif func_id == bi_max:
            ret = max(lhs, rhs)
        elif func_id == bi_min:
            ret = min(lhs, rhs)
        else:
            raise NotImplementedError(f"for : {func_id}")

        return ret

    def visit_var_def(self, definition: VarDef):
        value = definition.value.visit(self)
        self._context.define(definition.identifier, value)

    def visit_var_redef(self, redef: VarRedef):
        value = redef.value.visit(self)
        self._context.reassign(redef.identifier, value)

    def visit_identifier(self, identifier: Identifier):
        return self._context.get(identifier.name)

    def visit_literal(self, literal: Literal):
        return literal.value

    def visit_application(self, application: Application):
        evaluated = [param.visit(self) for param in application.args]
        build_in_id = get_builtin(application.func_id)
        if build_in_id:
            return self.visit_built_in_application(build_in_id, *evaluated)
        raise NotImplementedError("no user functions yet, something went wrong")

    def visit_prefix_application(self, prefix_app: PrefixApplication):
        evaluated = prefix_app.expr.visit(self)
        build_in_id = get_builtin(prefix_app.func_id)
        if build_in_id:
            return self.visit_built_in_application(build_in_id, evaluated)
        raise NotImplementedError("no user functions yet, something went wrong")

    def visit_infix_application(self, infix_app: InfixApplication):
        left = infix_app.lhs.visit(self)
        right = infix_app.rhs.visit(self)
        identifier = infix_app.func_id
        built_in_id = get_builtin(identifier)
        if built_in_id:
            return self.visit_built_in_application(built_in_id, left, right)
        raise NotImplementedError("no user functions yet, something went wrong")

    def visit_if_else(self, if_else: IfElse):
        pred = if_else.predicate.visit(self)
        assert type(pred) == bool
        if pred:
            return if_else.truthy_case.visit(self)
        if if_else.falsy_case is not None:
            return if_else.falsy_case.visit(self)
        return None

    def _visit_lines(self, lines: List[Node]):
        for node in lines:
            last = node.visit(self)
        return last

    def visit_block(self, block: Block):
        with self._context.new_frame():
            return self._visit_lines(block.lines)

    def visit_scope(self, scope: Scope):
        return self._visit_lines(scope.lines)

    def evaluate(self) -> Optional[Value]:
        """
        The main _Interpreter_ function that evaluates the top level nodes.

        Returns:
            Optional[int | float]: return the evaluated result of the last line
        """
        res = self._program.syntax_tree.visit(self)
        return res
