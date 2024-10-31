from abc import ABC
from typing import List, Optional

from uza.utils import Span
from uza.token import *
from uza.type import *

from dataclasses import dataclass, field


class Node(ABC):
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
    value: bool | str | int | float = field(init=False)
    span: Span = field(compare=False, init=False)

    def __post_init__(self) -> None:
        kind = self.token.kind
        if kind == token_boolean:
            if self.token.repr == "false":
                self.value = False
            elif self.token.repr == "true":
                self.value = True
            else:
                raise ValueError("Invalid boolean token")
        elif kind == token_string:
            self.value = self.token.repr
        elif kind == token_number:
            try:
                self.value: int | float = int(self.token.repr)
            except ValueError:
                self.value = float(self.token.repr)
        self.span = self.token.span

    def visit(self, that):
        return that.visit_literal(self)


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


@dataclass
class PrefixApplication(Node):
    expr: Node
    func_id: Identifier
    span: Span = field(compare=False, init=False)

    def __post_init__(self) -> None:
        self.span = self.func_id.span + self.expr.span

    def visit(self, that):
        return that.visit_prefix_application(self)


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
class Error(Node):
    error_message: str
    span: Span = field(compare=False)

    def visit(self, that):
        return that.visit_error(self)


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
    syntax_tree: list[Node]
    errors: int
    failed_nodes: List[Error]
