from __future__ import annotations
import string
from collections import namedtuple
import sys
from typing import Callable, Optional
from collections import deque
from collections.abc import Sequence
from abc import ABC
from dataclasses import dataclass

OP_PREFIX = {"MINUS"}

NUM_TOK = "NUM"


@dataclass
class TokenKind:
    repr: str
    _token_dict: dict
    precedence: int = -1
    right_assoc: bool = False
    is_user_value: bool = False

    def __post_init__(self):
        self._token_dict[self.repr] = self

    def is_op(self):
        return self.precedence >= 0

    def __eq__(self, value: object) -> bool:
        if not isinstance(value, TokenKind):
            return NotImplemented
        return self.repr == value.repr

    def __repr__(self) -> str:
        return f"TokenKind('{self.repr}')"


@dataclass
class Token:
    kind: TokenKind
    start: int
    end: int
    repr: str = ""

    def __post_init__(self):
        if self.repr == "":
            self.repr = self.kind.repr

    def __eq__(self, value: object) -> bool:
        if not isinstance(value, Token):
            return NotImplemented
        if self.kind != value.kind:
            return False

        if self.kind.is_user_value:
            return self.repr == value.repr
        else:
            return True


token_types: dict[str, TokenKind] = {}

token_new_line = TokenKind("NL", token_types)
token_plus = TokenKind("+", token_types, 1)
token_minus = TokenKind("-", token_types, 1)
token_star = TokenKind("*", token_types, 2)
token_slash = TokenKind("/", token_types, 3)
token_star_double = TokenKind("**", token_types, 9, right_assoc=True)
token_paren_l = TokenKind("(", token_types)
token_paren_r = TokenKind(")", token_types)
token_NUM = TokenKind("NUM", token_types, is_user_value=True)
token_val = TokenKind("val", token_types)
token_var = TokenKind("var", token_types)
token_eq = TokenKind("=", token_types)
token_eq_double = TokenKind("==", token_types)
token_identifier = TokenKind("identifier", token_types)


class Lexer:
    def __init__(self, source: str):
        self._source = source
        self._source_len = len(source)
        self._start = 0

    def _char_at(self, i):
        return self._source[i]

    def _overflows(self, i: Optional[int] = None) -> bool:
        if i:
            return i >= self._source_len
        return self._start >= self._source_len

    def _consume_white_space(self):
        i = self._start
        # while i < self._source_len and self._source[i] in string.whitespace:
        while i < self._source_len and self._source[i] is " ":
            i += 1
        self._start = i

    def _get_next_word(self) -> tuple[str, int]:
        end = self._start + 1
        while not self._overflows(end):
            char = self._char_at(end)
            if char not in string.ascii_letters and char not in "_-":
                break
            end += 1

        return self._source[self._start : end], end

    def _next_token(self) -> Optional[Token]:
        self._consume_white_space()
        if self._overflows():
            return None

        char = self._char_at(self._start)
        if char is "\n":
            end = self._start + 1
            type = token_new_line
        elif char in string.digits:
            end = self._next_numeral()
            type = token_NUM
        elif char in string.ascii_letters:
            word, end = self._get_next_word()
            match word:
                case "val":
                    type = token_val  # TODO: test type()
                case "var":
                    type = token_var
                case _:
                    type = token_identifier
        elif char == "*":
            if (
                not self._overflows(self._start + 1)
                and self._char_at(self._start + 1) == "*"
            ):
                end = self._start + 2
                type = token_star_double

            else:
                end = self._start + 1
                type = token_star
        else:
            type_maybe = token_types.get(char)
            if type_maybe is None:
                raise RuntimeError(f"could not tokenize {char} at {self._start}")
            type = type_maybe
            end = self._start + 1

        assert self._start <= end
        new_token = Token(type, self._start, end, self._source[self._start : end])
        self._start = end
        return new_token

    def _next_numeral(self):
        end = self._start
        already_has_dot = False
        while self._char_at(end) in string.digits or (
            self._char_at(end) == "." and not already_has_dot
        ):
            if self._char_at(end) == ".":
                end + 2
                already_has_dot = True
            if end + 1 == self._source_len:
                return end + 1
            end += 1
        return end

    def __iter__(self):
        return self

    def __next__(self):
        while self._start < self._source_len:
            token = self._next_token()
            if token is None:
                raise StopIteration
            return token
        raise StopIteration


class Node(ABC):
    pass

    def visit(self, that):
        """The Node passes it self to the appropriately named function in the _that_ class.
        Using a visitor pattern to move the step-specific logic to a different class.

        Args:
            that : A function that defined a _visit_X where X is self

        Raises:
            NotImplementedError: The abstract base class Node does not define visit.
            If the subclass Node does not define it's visit function, it defaults to this one via inheritance.
        """
        raise NotImplementedError(f"visit not implemented for {self.__repr__()}")


@dataclass
class Number(Node):
    token: Token

    def __post_init__(self) -> None:
        try:
            self.number: int | float = int(self.token.repr)
        except ValueError:
            self.number = float(self.token.repr)

    def visit(self, that):
        return that.visit_number(self)


@dataclass
class Op(Node):
    lhs: Node
    op: Token
    rhs: Node

    def visit(self, that):
        return that.visit_op(self)


@dataclass
class PrefixOp(Node):
    expr: Node
    op: Token

    def visit(self, that):
        return that.visit_prefix_op(self)


@dataclass
class varDef(Node):
    identifier: str
    tpe: str
    value: Node
    immutable: bool = True

    def visit(self, that):
        return that.visit_var_def(self)


class Parser:
    def __init__(self, source: str):
        self._tokens = deque(Lexer(source))
        self._source = source

    def _peek(self):
        if len(self._tokens) == 0:
            return None
        return self._tokens[0]

    def _expect(self, *type: TokenKind, op=False) -> Token:
        if self._peek() is None:
            raise RuntimeError(f"expected {type} \n   but no more tokens left")
        elif op and not self._peek().kind.is_op():
            raise RuntimeError(f"expected operator\n    but got {self._peek()}")
        elif self._peek().kind not in type and not op:
            raise RuntimeError(f"expected {type}\n    but got {self._peek()}")
        else:
            return self._tokens.popleft()

    def _get_top_level(self) -> Node:
        next = self._peek()
        while next.kind == token_new_line:
            next = self._expect(token_new_line)
            next = self._peek()

        if next.kind == token_val or next.kind == token_var:
            res = self._get_var_def()
        else:
            res = self._get_expr()

        if len(self._tokens) > 0:
            self._expect(token_new_line)
        return res

    def _get_var_def(self) -> Node:
        decl_token = self._expect(token_var, token_val)
        if decl_token.kind == token_val:
            immutable = True
        else:
            immutable = True
        identifier = self._expect(token_identifier)
        tpe = self._expect(token_identifier)
        self._expect(token_eq)
        value = self._get_infix(self._get_expr())

        return varDef(identifier.repr, tpe.repr, value, immutable=immutable)

    def _get_expr(self) -> Node:
        tok = self._peek()

        if tok.kind == token_paren_l:
            self._expect(token_paren_l)

            node = self._get_infix(self._get_expr())
            self._expect(token_paren_r)
            return self._get_infix(node)

        if tok.kind.is_op():
            operation_token = self._expect(tok.kind)
            return PrefixOp(self._get_expr(), operation_token)
        if tok.kind == token_NUM:
            return self._get_infix(Number(self._expect(token_NUM)))

        raise RuntimeError(
            f"did not expect '{tok.repr}' at '{self._source[max(tok.start - 2, 0): min(tok.end + 2, len(self._source))]}'"
        )

    def _peek_valid_op(self, precedence: int):
        next = self._peek()
        if next is None:
            return False, None
        op_prec = next.kind.precedence
        if next.kind.right_assoc:
            return (
                op_prec + 1 >= precedence,
                op_prec,
            )  # TODO: might break for future operations
        return op_prec >= precedence, op_prec

    def _get_infix(self, lhs: Node, precedence=1) -> Node:
        """
        evaluates operations with in the appropriate order of precedence
        """
        valid_op, curr_op_precedence = self._peek_valid_op(precedence)
        while valid_op:
            op = self._expect(op=True)
            rhs = self._get_expr()

            higher_op, next_op_precedence = self._peek_valid_op(curr_op_precedence + 1)
            while higher_op:
                rhs = self._get_infix(rhs, next_op_precedence)
                higher_op, next_op_precedence = self._peek_valid_op(
                    curr_op_precedence + 1
                )

            lhs = Op(lhs, op, rhs)
            valid_op, curr_op_precedence = self._peek_valid_op(precedence)

        return lhs

    def parse(self) -> list[Node]:
        if not self._peek():
            return []
        expressions = []
        while len(self._tokens) > 0:
            expr = self._get_top_level()
            expressions.append(expr)

        return expressions
        # node = self._get_expr()
        # if not node:
        #     return None
        # head = self._get_infix(node)
        # if self._peek() is not None:
        #     tok: Token = self._peek()
        #     raise SyntaxError(f"Did not expect character {tok} at {tok.start}")
        # return head


class Interpreter:
    def __init__(self, ast: Node):
        self._ast = ast

    def visit_number(self, number: Number):
        return number.number

    def visit_prefix_op(self, prefix_op: PrefixOp):
        evaluated = prefix_op.expr.visit(self)
        assert prefix_op.op.kind == token_minus  # add more
        return -evaluated

    def visit_op(self, operation: Op):
        left = operation.lhs.visit(self)
        right = operation.rhs.visit(self)
        op = operation.op
        if op.kind == token_star_double:
            return left**right
        elif op.kind == token_plus:
            return left + right
        elif op.kind == token_star:
            return left * right
        elif op.kind == token_slash:
            return left / right
        elif op.kind == token_minus:
            return left - right

    def evaluate(self) -> int | float:
        return self._ast.visit(self)
