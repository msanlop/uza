from __future__ import annotations
from collections import deque
from dataclasses import dataclass
from typing import Callable, Optional, TypeVar

from .ast import (
    Application,
    Identifier,
    InfixApplication,
    Literal,
    Node,
    PrefixApplication,
    Value,
    VarDef,
    Program,
)


@dataclass(frozen=True)
class BuiltIn:
    """
    A BuiltIn is a function that is part of the standard library.
    """

    identifier: str
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
bi_land = BuiltIn("and", _builtins)
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


class Context:
    """Excetution context that containts the stack frames.

    _frames_ is queue of locals, a tuple with the context name and a dict with
    the (variable name, value) pairs.
    """

    frames: deque[tuple[str, dict[str, Value]]]

    def __init__(
        self, frames: deque[tuple[str, dict[str, Value]]] | None = None
    ) -> None:
        """Excetution context that containts the stack frames. Each frame has a
        context name and the local definitions.

        Args:
            frames (deque[tuple[str, dict[str, Value]]], optional):
                Defaults to deque().
        """
        if not frames:
            self.frames: deque[tuple[str, dict[str, Value]]] = deque()
            self.frames.appendleft(("", {}))
        else:
            self.frames = frames

    def with_new_frame(self, context_name: str, frame: dict[str, Value]) -> Context:
        new_frames = deque((*self.frames, (context_name, frame)))
        return Context(new_frames)

    def define(self, variable_name: str, value: Value) -> None:
        top_frame = self.frames[0]
        frame_locals = top_frame[1]
        frame_locals[variable_name] = value

    def get(self, identifier: str) -> Value:
        for frame in self.frames:
            frame_locals = frame[1]
            value = frame_locals.get(identifier)
            if value is not None:
                return value
        raise NameError(f'"{identifier}" has not been defined')

    def reassign(self, identifier: str, new_value: Value) -> None:
        pass  # immutable check in the parser


class Interpreter:
    """
    A class that takes in a program and interprets it by walking the AST.

    Uses the visitor pattern by calling node.visit(self). Performance is not a
    concern in this implementation. It's main use is to ensure parity with the
    VM interpretation and to more easily test ideas.
    """

    def __init__(self, ast: Program | Node):
        self._context = Context()
        if isinstance(ast, Node):
            self._program = [ast]
        else:
            self._program = ast

    T = TypeVar("T")
    R = TypeVar("R")

    def _in_scope(
        self, scope_name: str, locals_vals: dict[str, Value], func: Callable[[], R]
    ) -> R:
        saved = self._context
        self._context = saved.with_new_frame(scope_name, locals_vals)
        res = func()
        self._context = saved
        return res

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
            # C division casts the rhs to the lhs's type
            casted = type(lhs)(rhs)
            if isinstance(lhs, int):
                ret = lhs // casted
            else:
                ret = lhs / casted
        elif func_id == bi_land:
            ret = lhs and rhs
        elif func_id == bi_pow:
            ret = lhs**rhs
        elif func_id == bi_print:
            print(*params, end="")
            ret = None
        elif func_id == bi_println:
            print(*params)
            ret = None
        elif func_id == bi_max:
            ret = max(lhs, rhs)
        elif func_id == bi_min:
            ret = min(lhs, rhs)

        return ret

    def visit_var_def(self, definition: VarDef):
        value = definition.value.visit(self)
        self._context.define(definition.identifier, value)

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

    def evaluate(self) -> Optional[Value]:
        """
        The main _Interpreter_ function that evaluates the top level nodes.

        Returns:
            Optional[int | float]: return the evaluated result of the last line
        """
        lines = [node.visit(self) for node in self._program]
        return lines[-1]
