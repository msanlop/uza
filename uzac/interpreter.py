# pylint: disable=missing-docstring

from __future__ import annotations
from dataclasses import dataclass
from typing import List, Optional, TypeVar

from uzac.type import ArrowType
from uzac.ast import (
    Application,
    ExpressionList,
    ForLoop,
    Function,
    Identifier,
    IfElse,
    InfixApplication,
    Literal,
    Node,
    PrefixApplication,
    Block,
    Range,
    Return,
    Value,
    VarDef,
    Program,
    VarRedef,
    WhileLoop,
)
from uzac.utils import SymbolTable
from uzac.builtins import *


@dataclass
class FunctionReturn(Exception):
    """
    Exception to bubble up function returns to the application.
    """

    value: Optional[Return]


@dataclass
class Exit(Exception):
    """
    Uza exit with status code.
    """

    value: int


class Interpreter:
    """
    A class that takes in a program and interprets it by walking the AST.

    Uses the visitor pattern by calling node.visit(self). Performance is not a
    concern in this implementation. It's main use is to ensure parity with the
    VM interpretation and to more easily test ideas.
    """

    def __init__(self, program: Program):
        # either [variable_name, Value] or [function_name, Function instance]
        self._context = SymbolTable()
        self._program = program

    T = TypeVar("T")
    R = TypeVar("R")

    def visit_no_op(self, _):
        pass

    def visit_built_in_application(self, func_id: BuiltIn, *params) -> Optional[Value]:
        return func_id.interpret(*params)

    def visit_function(self, func: Function):
        self._context.define(func.identifier, func)

    def visit_return(self, ret: Return):
        val = ret.value.visit(self)
        raise FunctionReturn(val)

    def visit_var_def(self, definition: VarDef):
        value = definition.value.visit(self)
        self._context.define(definition.identifier, value)

    def visit_var_redef(self, redef: VarRedef):
        value = redef.value.visit(self)
        self._context.reassign(redef.identifier, value)

    def visit_identifier(self, identifier: Identifier) -> Value | Function:
        return self._context.get(identifier.name)

    def visit_literal(self, literal: Literal):
        if type(literal.value) is str:
            return str(literal.value)
        return literal.value

    def _short_circuit_and(self, *args):
        for arg in args:
            if not arg.visit(self):
                return False
        return True

    def visit_application(self, application: Application):
        evaluated = [param.visit(self) for param in application.args]
        build_in_id = get_builtin(application.func_id)
        if build_in_id:
            return self.visit_built_in_application(build_in_id, *evaluated)
        with self._context.new_frame():
            func: Function = self._context.get(application.func_id)
            for arg, param in zip(evaluated, func.param_names):
                self._context.define(param.name, arg)
            try:
                func.body.visit(self)
            except FunctionReturn as fr:
                return fr.value

    def visit_prefix_application(self, prefix_app: PrefixApplication):
        evaluated = prefix_app.expr.visit(self)
        build_in_id = get_builtin(prefix_app.func_id)
        if build_in_id:
            return self.visit_built_in_application(build_in_id, evaluated)
        raise NotImplementedError("no user functions yet, something went wrong")

    def visit_infix_application(self, infix_app: InfixApplication):
        if infix_app.func_id.name == "and":
            return self._short_circuit_and(infix_app.lhs, infix_app.rhs)
        left = infix_app.lhs.visit(self)
        right = infix_app.rhs.visit(self)
        identifier = infix_app.func_id
        built_in_id = get_builtin(identifier)
        if built_in_id:
            return self.visit_built_in_application(built_in_id, left, right)
        raise NotImplementedError(f"not implemented for {infix_app}")

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
        return None

    def visit_expression_list(self, expr_list: ExpressionList):
        self._visit_lines(expr_list.lines)

    def visit_block(self, block: Block):
        with self._context.new_frame():
            return self._visit_lines(block.lines)

    def visit_range(self, range: Range):
        node = range.node.visit(self)
        if range.start:
            start = range.start.visit(self)
        else:
            start = 0

        if range.index_one:
            return node[start]

        if range.end:
            end = range.end.visit(self)
        else:
            end = len(node)

        return node[start:end]

    def visit_while_loop(self, wl: WhileLoop):
        cond = wl.cond.visit(self)
        while cond:
            wl.loop.visit(self)
            cond = wl.cond.visit(self)

    def visit_for_loop(self, fl: ForLoop):
        with self._context.new_frame():
            fl.init.visit(self)
            while fl.cond.visit(self):
                fl.interior.visit(self)
                fl.incr.visit(self)

    def evaluate(self) -> Optional[Value]:
        """
        The main _Interpreter_ function that evaluates the top level nodes.

        Returns:
            Optional[int | float]: exit value
        """
        try:
            self._program.syntax_tree.visit(self)
        except Exit as e:
            return e.value
