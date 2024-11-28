from __future__ import annotations
from collections import deque
import string
from typing import Callable, List, Optional, TypeVar

from uza.interpreter import get_builtin
from uza.ast import (
    Application,
    Block,
    ExpressionList,
    ForLoop,
    Identifier,
    IfElse,
    InfixApplication,
    Literal,
    NoOp,
    Node,
    PrefixApplication,
    VarDef,
    Error,
    Program,
    VarRedef,
    WhileLoop,
)

from uza.utils import Span, SymbolTable
from uza.token import *
from uza import typer


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
        elif char == "=":
            end = self._start + 1
            type_ = token_eq
            if not self._overflows(end) and self._char_at(end) == "=":
                end += 1
                type_ = token_eq_double
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
            if word in token_types:
                type_ = token_types[word]
            else:
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
            raise RuntimeError(
                f"expected {type_}\n    but got {self._peek()}: {self._peek().span.get_source()}"
            )

        return self._tokens.popleft()

    def _consume_white_space_and_peek(self) -> TokenKind:
        temp = self._peek()
        while temp and temp.kind == token_new_line:
            self._expect(temp.kind)
            temp = self._peek()
        return temp

    def _get_top_level(self) -> Node:
        next_ = self._peek()
        while next_.kind == token_new_line:
            self._expect(token_new_line)
            next_ = self._peek()

        return self._get_expr()

    def _get_if_else(self) -> Node:
        self._expect(token_if)
        pred = self._get_expr()
        tok = self._peek()
        if tok and tok.kind == token_bracket_l:
            t_case = self._parse_block(end_token=token_bracket_r)
        else:
            self._expect(token_then)
            t_case = self._get_expr()
        self._consume_white_space_and_peek()
        f_case = None
        tok = self._consume_white_space_and_peek()
        if tok and tok.kind == token_else:
            self._expect(token_else)
            f_case = self._get_expr()
        return IfElse(pred, t_case, f_case)

    def _get_identifier(self) -> Identifier:
        identifier_tok = self._expect(token_identifier)
        identifier = Identifier(identifier_tok, identifier_tok.span)
        if self._peek().kind == token_paren_l:
            if get_builtin(identifier) == None:
                raise NameError(
                    "\n" + identifier_tok.span.get_underlined("function is undefined")
                )
        else:
            if self._symbol_table.get(identifier_tok.repr) is None:
                raise NameError(
                    "\n"
                    + identifier_tok.span.get_underlined(
                        "variable not defined in this scope"
                    )
                )
        return identifier

    def _get_var_redef(self, identifier) -> Node:
        if self._peek().kind == token_identifier:
            type_tok = self._expect(token_identifier)
            type_ = typer.identifier_to_uza_type(type_tok)
        else:
            type_ = None
        self._expect(token_eq)
        value = self._get_expr()
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
        value = self._get_expr()
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

    def _parse_lines(self, end_token: Optional[TokenKind] = None) -> List[Node]:
        expressions: list[Node] = []
        while len(self._tokens) > 0:
            tok = self._peek()
            if tok.kind == token_new_line:
                self._expect(token_new_line)
                continue
            if end_token and tok.kind == end_token:
                break
            expr = self._get_top_level()
            expressions.append(expr)

        return expressions

    def _parse_block(self, end_token: Optional[TokenKind] = None) -> Block:
        self._expect(token_bracket_l)

        with self._symbol_table.new_frame():
            lines = self._parse_lines(end_token)
            if len(lines) > 0:
                span = lines[0].span + lines[-1].span
            else:
                span = Span(0, 0, "empty block")

        self._expect(token_bracket_r)
        return Block(lines, span)

    def _get_while_loop(self) -> WhileLoop:
        self._expect(token_while)
        cond = self._get_expr()
        tok = self._peek()
        if tok and tok.kind == token_bracket_l:
            interior = self._parse_block(end_token=token_bracket_r)
            return WhileLoop(cond, interior, cond.span + interior.span)
        self._consume_white_space_and_peek()
        self._expect(token_do)
        interior = self._get_expr()
        return WhileLoop(cond, interior, cond.span + interior.span)

    def _get_for_loop(self) -> ForLoop:
        for_tok = self._expect(token_for)
        tok = self._peek()
        if tok and tok.kind == token_semicolon:
            init = NoOp(for_tok.span)
        else:
            init = self._get_expr()
        self._expect(token_semicolon)
        tok = self._peek()
        if tok and tok.kind == token_semicolon:
            cond = Literal(Token(token_true, for_tok.span))
        else:
            cond = self._get_expr()
        self._expect(token_semicolon)
        tok = self._peek()
        if tok and tok.kind in (token_bracket_l, token_do):
            incr = NoOp(for_tok.span)
        else:
            incr = self._get_expr()
        tok = self._peek()
        if tok and tok.kind == token_bracket_l:
            self._expect(token_bracket_l)
            interior_lines = self._parse_lines(end_token=token_bracket_r)
            self._expect(token_bracket_r)
            interior = ExpressionList(interior_lines, Span.from_list(interior_lines))
            return ForLoop(init, cond, incr, interior, for_tok.span + interior.span)
        self._consume_white_space_and_peek()
        self._expect(token_do)
        interior = self._get_expr()
        return ForLoop(init, cond, incr, interior, for_tok.span + interior.span)

    def _get_expr(self) -> Node:
        tok = self._consume_white_space_and_peek()

        if tok.kind in (token_const, token_var):
            return self._get_var_def()
        elif tok.kind == token_paren_l:
            self._expect(token_paren_l)
            node = self._get_infix(self._get_expr())
            self._expect(token_paren_r)
            return self._get_infix(node)
        elif tok.kind == token_while:
            return self._get_while_loop()
        elif tok.kind == token_for:
            return self._get_for_loop()
        elif tok.kind == token_if:
            return self._get_if_else()
        elif tok.kind == token_bracket_l:
            node = self._parse_block(end_token=token_bracket_r)
            return self._get_infix(node)
        elif tok.kind == token_identifier:
            identifier = self._get_identifier()
            tok = self._peek()
            if not tok:
                return identifier
            elif tok.kind == token_eq:
                return self._get_var_redef(identifier)
            elif tok.kind == token_paren_l:
                self._expect(token_paren_l)
                arguments = self._get_function_args()
                self._expect(token_paren_r)
                func_call = Application(identifier, *arguments)
                return self._get_infix(func_call)

            return self._get_infix(identifier)

        elif tok.kind.is_op():
            prefix_tok = self._expect(tok.kind)
            return PrefixApplication(
                self._get_expr(), Identifier(prefix_tok, prefix_tok.span)
            )
        elif tok.kind.is_user_value:
            val = Literal(self._expect(tok.kind))
            return self._get_infix(val)
        else:
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
        top_level_lines = self._parse_lines()
        span = Span(0, 0, "")
        span = Span.from_list(top_level_lines, span)

        top_level = Block(top_level_lines, span)
        return Program(top_level, self._errors, self.failed_nodes)
