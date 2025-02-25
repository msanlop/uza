# pylint: disable=missing-docstring
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import List, Optional
from dataclasses import dataclass, field

from uzac.utils import Span
from uzac.token import *
from uzac.type import *

DEBUG_PARSE = False


class Node(ABC):
    """
    An uza AST node.
    """

    span: Span

    def visit(self, that):
        """
        The Node passes itself to the apropriate function in the _that_ object.

        Using a visitor lets the compiler step specific logic in that class or
        module and not int the Node objects.

        Args:
            that : A module that defines a that.visit_X(X), where X is self.

        Raises:
            NotImplementedError: The abstract base class Node does not define
            visit.
        """
        raise NotImplementedError(f"visit not implemented for {self}")


@dataclass
class Literal(Node):
    token: Token
    value: bool | str | int | float | Token = field(init=False)
    span: Span = field(compare=False, init=False)

    def __post_init__(self) -> None:
        kind = self.token.kind
        if self.token.kind == token_true:
            self.value = True
        elif self.token.kind == token_false:
            self.value = False
        elif kind in (token_string, token_partial_string):
            self.value = self.token.repr
        elif kind == token_nil:
            self.value = None
        elif kind == token_number:
            try:
                self.value: int | float = int(self.token.repr)
            except ValueError:
                self.value = float(self.token.repr)
        self.span = self.token.span

    def visit(self, that):
        return that.visit_literal(self)

    if DEBUG_PARSE:

        def __repr__(self):
            return f"{self.value}"


@dataclass
class Identifier(Node):
    token: Optional[Token]
    name: str
    span: Span = field(compare=False)

    def __init__(self, identifier: Token | str, span: Span) -> None:
        if isinstance(identifier, Token):
            self.name = identifier.repr
            self.token = identifier
        elif isinstance(identifier, TokenKind):
            self.token = Token(identifier, span)
            self.name = identifier.repr
        else:
            self.name = identifier
        self.span = span

        assert hasattr(self, "token")

    def visit(self, that):
        return that.visit_identifier(self)


@dataclass
class IfElse(Node):
    predicate: Node
    truthy_case: Node
    span: Span = field(compare=False, init=False)
    falsy_case: Optional[Node] = field(default=None)

    def __post_init__(self) -> None:
        if self.falsy_case is not None:
            self.span = self.predicate.span + self.falsy_case.span
        else:
            self.span = self.predicate.span + self.truthy_case.span

    def visit(self, that):
        return that.visit_if_else(self)


@dataclass
class Application(Node):
    func_id: Identifier
    args: list[Node]
    span: Span = field(compare=False)
    generic_arg: Type

    pop_value: bool = field(init=False, default=False)
    "Wether the vm should pop the return value off the stack (if unused)"

    def __init__(self, func_id: Identifier, *args, generic_arg: Type = None) -> None:
        self.func_id = func_id
        self.args = list(args)
        if args:
            self.span = func_id.span + self.args[-1].span
        else:
            self.span = func_id.span
        self.generic_arg = generic_arg

    def visit(self, that):
        return that.visit_application(self)

    if DEBUG_PARSE:

        def __repr__(self):
            return f"({self.func_id.name}[{[repr(a) for a in self.args]}])"


@dataclass
class InfixApplication(Node):
    lhs: Node
    func_id: Identifier
    rhs: Node
    span: Span = field(init=False, compare=False)

    pop_value: bool = field(init=False, default=False)
    "Wether the vm should pop the return value off the stack (if unused)"

    def __post_init__(self) -> None:
        self.span = self.lhs.span + self.rhs.span

    def visit(self, that):
        return that.visit_infix_application(self)

    if DEBUG_PARSE:

        def __repr__(self):
            return f"({self.lhs} {self.func_id.name} {self.rhs})"


@dataclass
class PrefixApplication(Node):
    expr: Node
    func_id: Identifier
    span: Span = field(compare=False, init=False)

    pop_value: bool = field(init=False, default=False)
    "Wether the vm should pop the return value off the stack (if unused)"

    def __post_init__(self) -> None:
        self.span = self.func_id.span + self.expr.span

    def visit(self, that):
        return that.visit_prefix_application(self)

    if DEBUG_PARSE:

        def __repr__(self):
            return f"({self.func_id.name} {self.expr})"


@dataclass
class MethodApplication(Node):
    accessed: Node
    method: Application
    """This field hold the first argument, this Node type is for ease of use and
    clearer ast"""

    span: Span = field(compare=False, init=False)

    pop_value: bool = field(init=False, default=False)
    "Wether the vm should pop the return value off the stack (if unused)"

    def __post_init__(self) -> None:
        self.span = self.accessed.span + self.method.span

    def visit(self, that):
        return that.visit_method_app(self)


App = Application | PrefixApplication | MethodApplication | InfixApplication
"Application AST Nodes"


@dataclass
class VarDef(Node):
    identifier: str
    type_: Optional[Type]
    value: Node
    span: Span = field(compare=False)
    immutable: bool = True

    def visit(self, that):
        return that.visit_var_def(self)


@dataclass
class VarRedef(Node):
    identifier: Identifier
    value: Node
    span: Span = field(compare=False)

    def visit(self, that):
        return that.visit_var_redef(self)


@dataclass
class ExpressionList(Node):
    """
    An ExpressionList is a list of nodes.
    """

    lines: List[Node]
    span: Span = field(compare=False)

    def visit(self, that):
        return that.visit_expression_list(self)


@dataclass
class Function(Node):
    """
    A function declaration.
    """

    identifier: Identifier
    param_names: List[Identifier]
    type_signature: ArrowType
    body: ExpressionList
    span: Span = field(compare=False)

    def visit(self, that):
        return that.visit_function(self)


@dataclass
class Return(Node):
    """
    A return statement.
    """

    value: Node
    span: Span = field(compare=False)
    type_: Type = field(init=False, default_factory=lambda: type_void)

    def visit(self, that):
        return that.visit_return(self)


@dataclass
class Break(Node):
    """
    A break statement. Exits current loop.
    """

    span: Span

    def visit(self, that):
        return that.visit_break(self)


@dataclass
class Continue(Node):
    """
    A continue statement. Skips current loop iteration.
    """

    span: Span

    def visit(self, that):
        return that.visit_continue(self)


@dataclass
class Range(Node):
    """
    A sublist or substring.
    """

    node: Node
    start: Optional[Node]
    end: Optional[Node]
    index_one: bool
    span: Span = field(compare=False)

    def visit(self, that):
        return that.visit_range(self)


@dataclass
class Block(ExpressionList):
    """
    A block is a list of nodes. Creates a new scope.
    """

    type_: Type = field(default_factory=lambda: type_void)

    def visit(self, that):
        return that.visit_block(self)


@dataclass
class WhileLoop(Node):
    cond: Node
    loop: Node
    span: Span = field(compare=False)

    def visit(self, that):
        return that.visit_while_loop(self)


@dataclass
class ForLoop(Node):
    init: Optional[Node]
    cond: Optional[Node]
    incr: Optional[Node]
    interior: Node
    span: Span = field(compare=False)

    def visit(self, that):
        return that.visit_for_loop(self)


# @dataclass
# class Error(Node):
#     error_message: str
#     span: Span = field(compare=False)

#     def visit(self, that):
#         return that.visit_error(self)


@dataclass
class NoOp(Node):
    """
    Do nothing.
    """

    span: Span = field(compare=False)

    def visit(self, that):
        return that.visit_no_op(self)


@dataclass
class Value:
    """
    Defines a value.
    """

    name: str
    value: Literal
    immutable: bool = False


@dataclass
class Program:
    syntax_tree: ExpressionList
    errors: int


class UzaASTVisitor(ABC):
    """
    A `UzaAstVisitor` is a class that implements the necessary methods following
    a visitor pattern. When a class extends the `UzaAstVisitor` and calls `visit`
    on an `Node`, that `Node` calls the appropriate `visit_X` on the class instance.
    The return type depends on the inhereting class. For example, `Interpreter`
    return `Value` while `Typer` return a tuple.

    This pattern allows for implementation to be kept out of the base ast class
    and in the respective module. An exception is made with `BuiltIn`s, which
    defines the implementation for various steps of the compiler pipeline in the
    module.
    """

    @abstractmethod
    def visit_return(self, ret: Return):
        pass

    @abstractmethod
    def visit_break(self, that):
        pass

    @abstractmethod
    def visit_continue(self, that):
        pass

    @abstractmethod
    def visit_function(self, func: Function):
        pass

    @abstractmethod
    def visit_no_op(self, _):
        pass

    @abstractmethod
    def visit_infix_application(self, infix: InfixApplication):
        pass

    @abstractmethod
    def visit_prefix_application(self, prefix: PrefixApplication):
        pass

    @abstractmethod
    def visit_if_else(self, if_else: IfElse):
        pass

    @abstractmethod
    def visit_identifier(self, identifier: Identifier):
        pass

    @abstractmethod
    def visit_application(self, app: Application):
        pass

    @abstractmethod
    def visit_method_app(self, method: MethodApplication):
        pass

    @abstractmethod
    def visit_var_def(self, var_def: VarDef):
        pass

    @abstractmethod
    def visit_var_redef(self, redef: VarRedef):
        pass

    @abstractmethod
    def visit_literal(self, literal: Literal):
        pass

    @abstractmethod
    def visit_expression_list(self, expr_list: ExpressionList):
        pass

    @abstractmethod
    def visit_block(self, scope: Block):
        pass

    @abstractmethod
    def visit_while_loop(self, wl: WhileLoop):
        pass

    @abstractmethod
    def visit_for_loop(self, fl: ForLoop):
        pass

    # optional:
    def visit_builtin(self, bi: "BuiltIn", *arguments: Node, span: Span):
        f"method {self.visit_builtin.__name__} is not implemented by {type(self).__name__}"
