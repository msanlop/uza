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
    MethodApplication,
    Node,
    PrefixApplication,
    Block,
    Range,
    Return,
    UzaASTVisitor,
    Value,
    VarDef,
    Program,
    VarRedef,
    WhileLoop,
)
from uzac.utils import SymbolTable
from uzac.builtins import *


@dataclass
class UzaPythonInterpreterControlFlow(BaseException):
    """
    Simple (yet unoptimized) way to handle control flow in the tree-walk interpreter
    """


@dataclass
class FunctionReturn(UzaPythonInterpreterControlFlow):
    """
    Exception to bubble up function returns to the application.
    """

    value: Optional[Return]


@dataclass
class LoopBreak(UzaPythonInterpreterControlFlow):
    """
    Break out of current loop
    """


@dataclass
class LoopContinue(UzaPythonInterpreterControlFlow):
    """
    Skip current loop iteration
    """


@dataclass
class Exit(Exception):
    """
    Uza exit with status code.
    """

    value: int


class Interpreter(UzaASTVisitor):
    """
    A class that takes in a program and interprets it by walking the AST.

    Uses the visitor pattern by calling node.visit(self). Performance is not a
    concern in this implementation. It's main use is to ensure parity with the
    VM interpretation and to more easily test ideas.
    """

    def __init__(self, program: Program):
        # either [variable_name, Value] or [function_name, Function instance]
        self.__context = SymbolTable()
        self.__program = program

    T = TypeVar("T")
    R = TypeVar("R")

    def visit_no_op(self, _):
        pass

    def visit_built_in_application(self, func_id: BuiltIn, *params) -> Optional[Value]:
        return func_id.interpret(*params)

    def visit_function(self, func: Function):
        self.__context.define(func.identifier, func)

    def visit_return(self, ret: Return):
        val = ret.value.visit(self)
        raise FunctionReturn(val)

    def visit_break(self, that):
        raise LoopBreak()

    def visit_continue(self, that):
        raise LoopContinue()

    def visit_var_def(self, definition: VarDef):
        value = definition.value.visit(self)
        self.__context.define(definition.identifier, value)

    def visit_var_redef(self, redef: VarRedef):
        value = redef.value.visit(self)
        self.__context.reassign(redef.identifier.name, value)

    def visit_identifier(self, identifier: Identifier) -> Value | Function:
        return self.__context.get(identifier.name)

    def visit_literal(self, literal: Literal):
        if type(literal.value) is str:
            return str(literal.value)
        return literal.value

    def __short_circuit_and(self, *args):
        for arg in args:
            if not arg.visit(self):
                return False
        return True

    def visit_application(self, application: Application):
        evaluated = [param.visit(self) for param in application.args]
        build_in_id = get_builtin(application.func_id)
        if build_in_id:
            return self.visit_built_in_application(build_in_id, *evaluated)
        with self.__context.new_frame():
            func: Function = self.__context.get(application.func_id)
            for arg, param in zip(evaluated, func.param_names):
                self.__context.define(param.name, arg)
            try:
                func.body.visit(self)
            except FunctionReturn as fr:
                return fr.value

    def visit_method_app(self, method: MethodApplication):
        return method.method.visit(self)

    def visit_prefix_application(self, prefix_app: PrefixApplication):
        evaluated = prefix_app.expr.visit(self)
        build_in_id = get_builtin(prefix_app.func_id)
        if build_in_id:
            return self.visit_built_in_application(build_in_id, evaluated)
        raise NotImplementedError("no user functions yet, something went wrong")

    def visit_infix_application(self, infix_app: InfixApplication):
        if infix_app.func_id.name == "and":
            return self.__short_circuit_and(infix_app.lhs, infix_app.rhs)
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

    def __visit_lines(self, lines: List[Node]):
        for node in lines:
            last = node.visit(self)
        return None

    def visit_expression_list(self, expr_list: ExpressionList):
        self.__visit_lines(expr_list.lines)

    def visit_block(self, block: Block):
        with self.__context.new_frame():
            return self.__visit_lines(block.lines)

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
            try:
                wl.loop.visit(self)
                cond = wl.cond.visit(self)
            except LoopBreak:
                break
            except LoopContinue:
                continue

    def visit_for_loop(self, fl: ForLoop):
        with self.__context.new_frame():
            fl.init.visit(self)
            while fl.cond.visit(self):
                try:
                    fl.interior.visit(self)
                    fl.incr.visit(self)
                except LoopBreak:
                    break
                except LoopContinue:
                    continue

    def evaluate(self) -> Optional[Value]:
        """
        The main __Interpreter_ function that evaluates the top level nodes.

        Returns:
            Optional[int | float]: exit value
        """
        try:
            self.__program.syntax_tree.visit(self)
        except Exit as e:
            return e.value
