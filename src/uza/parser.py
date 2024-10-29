from __future__ import annotations
from collections import deque
import string
from typing import Optional

from .ast import (
    Application,
    Identifier,
    InfixApplication,
    Literal,
    Node,
    PrefixApplication,
    VarDef,
    Error,
    Program,
    VarRedef,
)

from .utils import Span, SymbolTable
from .token import *
from .typing import typer


class Scanner:
    """
    The Scanner class is a iterator over the token of a given source file.
    """

    def __init__(self, source: str, keep_comments=False):
        self._keep_comments = keep_comments
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
        while i < self._source_len and self._source[i] == " ":
            i += 1
        self._start = i

    def _get_next_word(self) -> tuple[str, int]:
        end = self._start + 1
        while not self._overflows(end):
            char = self._char_at(end)
            if not (
                char in string.ascii_letters or char in string.digits or char in "_-"
            ):
                break
            end += 1

        return self._source[self._start : end], end

    def _get_next_string(self) -> tuple[str, int]:
        end = self._start + 1
        while self._char_at(end) != '"':
            end += 1
        return self._source[self._start : end], end

    def _get_next_comment(self) -> int:
        end = self._start + 1
        while not self._overflows(end) and self._char_at(end) != "\n":
            end += 1
        return end

    def _next_token(self) -> Optional[Token]:
        self._consume_white_space()
        if self._overflows():
            return None

        char = self._char_at(self._start)
        if char == "\n":
            end = self._start + 1
            type_ = token_new_line
        elif char == "/":
            idx = self._start + 1
            if self._overflows(idx):
                end = idx
                type_ = token_slash
            else:
                second = self._char_at(idx)
                if second != "/":
                    end = idx
                    type_ = token_slash
                else:
                    end = self._get_next_comment()
                    type_ = token_comment
        elif char in string.digits:
            end = self._next_numeral()
            type_ = token_number
        elif char == ",":
            end = self._start + 1
            type_ = token_comma
        elif char == '"':
            word, end = self._get_next_string()
            end += 1
            type_ = token_string
            str_start = self._start + 1
            str_end = end - 1
            new_string_token = Token(
                type_,
                Span(str_start - 1, str_end + 1, self._source),  # span includes quotes
                self._source[str_start:str_end],
            )
            self._start = end
            return new_string_token
        elif char in string.ascii_letters:
            word, end = self._get_next_word()
            match word:
                case "const":
                    type_ = token_const
                case "var":
                    type_ = token_var
                case "and":
                    type_ = token_and
                case "true":
                    type_ = token_boolean
                case "false":
                    type_ = token_boolean
                case _:
                    type_ = token_identifier
        elif char == "*":
            if (
                not self._overflows(self._start + 1)
                and self._char_at(self._start + 1) == "*"
            ):
                end = self._start + 2
                type_ = token_star_double

            else:
                end = self._start + 1
                type_ = token_star
        else:
            type_maybe = token_types.get(char)
            if type_maybe is None:
                raise RuntimeError(f"could not tokenize {char} at {self._start}")
            type_ = type_maybe
            end = self._start + 1

        assert self._start <= end
        new_token = Token(
            type_, Span(self._start, end, self._source), self._source[self._start : end]
        )
        self._start = end
        return new_token

    def _next_numeral(self):
        end = self._start
        already_has_dot = False
        while self._char_at(end) in string.digits or (
            self._char_at(end) == "." and not already_has_dot
        ):
            if self._char_at(end) == ".":
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
            if not self._keep_comments:
                while token and token.kind == token_comment:
                    token = self._next_token()

            if token is None:
                raise StopIteration
            return token
        raise StopIteration


class Parser:
    """
    A parser parses it source code into a Program, i.e. a list of AST Nodes.
    """

    def __init__(self, source: str):
        self._tokens = deque(Scanner(source))
        self._source = source
        self._errors = 0
        self.failed_nodes = []

        # map of (identifier -> bool) for mutability
        self._symbol_table = SymbolTable()

    def _log_error(self, error: Error):
        self._errors += 1
        self.failed_nodes.append(error)

    def _peek(self):
        if len(self._tokens) == 0:
            return None
        return self._tokens[0]

    def _expect(self, *type_: TokenKind, op=False) -> Token:
        if self._peek() is None:
            raise RuntimeError(f"expected {type_} \n   but no more tokens left")

        if op and not self._peek().kind.is_op():
            raise RuntimeError(f"expected operator\n    but got {self._peek()}")
        elif self._peek().kind not in type_ and not op:
            raise RuntimeError(f"expected {type_}\n    but got {self._peek()}")

        return self._tokens.popleft()

    def _get_top_level(self) -> Node:
        next_ = self._peek()

        if next_.kind in (token_const, token_var):
            res = self._get_var_def()
        elif next_.kind == token_identifier:
            if len(self._tokens) > 1 and self._tokens[1].kind == token_eq:
                res = self._get_var_redef()
            else:
                res = self._get_expr()
        else:
            res = self._get_expr()

        # if len(self._tokens) > 0:
        #     self._expect(token_new_line)
        return res

    def _get_identifier(self) -> Identifier:
        identifier_tok = self._expect(token_identifier)
        return Identifier(identifier_tok, identifier_tok.span)

    def _get_var_redef(self) -> Node:
        identifier = self._get_identifier()
        if self._peek().kind == token_identifier:
            type_tok = self._expect(token_identifier)
            type_ = typer.identifier_to_uza_type(type_tok)
        else:
            type_ = None
        self._expect(token_eq)
        value = self._get_infix(self._get_expr())
        is_immutable = self._symbol_table.get(identifier.name)

        return VarRedef(identifier.name, value, identifier.span + value.span)

    def _get_var_def(self) -> Node:
        decl_token = self._expect(token_var, token_const)
        immutable = decl_token.kind == token_const
        identifier = self._expect(token_identifier)
        if self._peek().kind == token_identifier:
            type_tok = self._expect(token_identifier)
            type_ = typer.identifier_to_uza_type(type_tok)
        else:
            type_ = None
        self._expect(token_eq)
        value = self._get_infix(self._get_expr())
        if not self._symbol_table.define(identifier.repr, immutable):
            err = Error(
                identifier.span.get_underlined(
                    f"'{identifier.repr}' has already been defined in this scope",
                ),
                decl_token.span + identifier.span,
            )
            self._log_error(err)
            return err
        return VarDef(
            identifier.repr,
            type_,
            value,
            decl_token.span + value.span,
            immutable=immutable,
        )

    def _get_function_args(self) -> list[Node]:
        next_ = self._peek()
        args = []
        while next_.kind != token_paren_r:
            arg = self._get_expr()
            next_ = self._peek()
            if next_.kind == token_comma:
                self._expect(token_comma)
            elif next_.kind != token_paren_r:
                raise SyntaxError(f"Expected ',' or ')' but got '{(next_.repr)}'")
            args.append(arg)
            next_ = self._peek()

        return args

    def _get_expr(self) -> Node:
        tok = self._peek()

        if tok.kind == token_paren_l:
            self._expect(token_paren_l)

            node = self._get_infix(self._get_expr())
            self._expect(token_paren_r)
            return self._get_infix(node)

        if tok.kind == token_identifier:
            identifier = self._get_identifier()
            tok = self._peek()
            if not tok:
                return identifier
            if tok.kind != token_paren_l:
                return self._get_infix(identifier)

            self._expect(token_paren_l)
            arguments = self._get_function_args()
            self._expect(token_paren_r)
            func_call = Application(identifier, *arguments)
            return self._get_infix(func_call)

        if tok.kind.is_op():
            prefix_tok = self._expect(tok.kind)
            return PrefixApplication(
                self._get_expr(), Identifier(prefix_tok, prefix_tok.span)
            )
        if tok.kind.is_user_value:
            val = Literal(self._expect(tok.kind))
            return self._get_infix(val)

        source_excerp = self._source[
            max(tok.span.start - 2, 0) : min(tok.span.end + 2, len(self._source))
        ]
        raise RuntimeError(f"did not expect '{tok.repr}' at '{source_excerp}'")

    def _peek_valid_op(self, precedence: int):
        next_tok = self._peek()
        if next_tok is None:
            return False, None
        op_prec = next_tok.kind.precedence
        if next_tok.kind.right_assoc:
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

            lhs = InfixApplication(lhs, Identifier(op, op.span), rhs)
            valid_op, curr_op_precedence = self._peek_valid_op(precedence)

        return lhs

    def parse(self) -> Program:
        if not self._peek():
            return Program([], 0, [])
        expressions = []
        while len(self._tokens) > 0:
            if self._peek().kind == token_new_line:
                self._expect(token_new_line)
                continue

            expr = self._get_top_level()
            expressions.append(expr)
        return Program(expressions, self._errors, self.failed_nodes)
