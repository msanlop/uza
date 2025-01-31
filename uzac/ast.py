# pylint: disable=missing-docstring

from abc import ABC
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
        elif kind == token_string:
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
    name: str
    span: Span = field(compare=False)

    def __init__(self, identifier: Token | str, span: Span) -> None:
        if isinstance(identifier, Token):
            self.name = identifier.repr
        else:
            self.name = identifier
        self.span = span

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

    def __init__(self, func_id: Identifier, *args) -> None:
        self.func_id = func_id
        self.args = list(args)
        if args:
            self.span = func_id.span + self.args[-1].span
        else:
            self.span = func_id.span

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

    def __post_init__(self) -> None:
        self.span = self.func_id.span + self.expr.span

    def visit(self, that):
        return that.visit_prefix_application(self)

    if DEBUG_PARSE:

        def __repr__(self):
            return f"({self.func_id.name} {self.expr})"


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
    identifier: str
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


@dataclass
class Error(Node):
    error_message: str
    span: Span = field(compare=False)

    def visit(self, that):
        return that.visit_error(self)


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
    failed_nodes: List[Error]
