from __future__ import annotations
from collections import deque
from functools import reduce
import string
from typing import Callable, List, Optional, TypeVar

from uzac.interpreter import get_builtin
from uzac.ast import (
    Application,
    Block,
    ExpressionList,
    ForLoop,
    Function,
    Identifier,
    IfElse,
    InfixApplication,
    Literal,
    NoOp,
    Node,
    PrefixApplication,
    Range,
    Return,
    VarDef,
    Error,
    Program,
    VarRedef,
    WhileLoop,
)

from uzac.type import ArrowType, Type, identifier_to_uza_type
from uzac.utils import Span, SymbolTable
from uzac.token import *
from uzac import typer


class Scanner:
    """
    The Scanner class is a iterator over the token of a given source file.
    """

    def __init__(self, source: str, discard_style=True):
        self._discard_style = discard_style
        self._source = source
        self._source_len = len(source)
        self._start = 0
        self._line = 0

    def _char_at(self, i):
        return self._source[i]

    def _overflows(self, i: Optional[int] = None) -> bool:
        if i:
            return i >= self._source_len
        return self._start >= self._source_len

    def _get_next_word(self) -> int:
        end = self._start + 1
        while not self._overflows(end):
            char = self._char_at(end)
            if not (
                char in string.ascii_letters or char in string.digits or char in "_"
            ):
                break
            end += 1

        return end

    def _get_next_string(self) -> int:
        end = self._start + 1
        while self._char_at(end) != '"':
            # TODO: multiline strings
            # if self._char_at(end) == "\n":
            #     raise SyntaxError(
            #         rf"found \n in string literal at {self._source[self._start : end]}"
            #     )
            end += 1
        return end

    def _get_next_comment(self) -> int:
        end = self._start + 1
        while not self._overflows(end) and self._char_at(end) != "\n":
            end += 1
        return end

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

    def _next_token(self) -> Optional[Token]:
        """
        Scans the next token, at self._start in Scanner source.
        Return None if there are no more tokens.
        """
        if self._overflows():
            return None

        char = self._char_at(self._start)
        if char in string.digits:
            end = self._next_numeral()
            type_ = token_number
        elif char == '"':
            end = self._get_next_string()
            end += 1
            type_ = token_string
            str_start = self._start + 1
            str_end = end - 1
            new_string_token = Token(
                type_,
                Span(str_start - 1, str_end + 1, self._source),  # span includes quotes
                self._source[str_start:str_end].replace("\\n", "\n"),  # horrible hack
            )
            self._start = end
            return new_string_token
        elif char in string.ascii_letters:
            end = self._get_next_word()
            word = self._source[self._start : end]
            if word in token_types:
                type_ = token_types[word]
            else:
                type_ = token_identifier
        else:
            end = self._start + 2
            maybe_double_token = None
            if not self._overflows(end):
                maybe_double_token = token_types.get(self._source[self._start : end])

            if maybe_double_token:
                type_ = maybe_double_token
                if type_ == token_slash_slash:
                    type_ = token_comment
                    end = self._get_next_comment()
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

    def __iter__(self):
        return self

    def __next__(self):
        while self._start < self._source_len:
            token = self._next_token()
            if token.kind == token_new_line:
                self._line += 1
            if self._discard_style:
                while token and token.kind in (token_comment, token_space, token_tab):
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
        self._tokens = deque(Scanner(source))  # TODO: use the iter directly
        self._source = source
        self._errors = 0
        self.failed_nodes = []

        # map of (Identifier -> bool) for mutability
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

    def _get_type(self) -> Type:
        types = []
        tok = self._expect(token_identifier)
        type_ = identifier_to_uza_type(tok)
        types.append(type_)
        tok = self._peek()
        while tok.kind == token_pipe:
            self._expect(token_pipe)
            tok = self._expect(token_identifier)
            type_ = identifier_to_uza_type(tok)
            types.append(type_)
            tok = self._peek()

        if len(types) > 1:
            return reduce(lambda x, y: x | y, types)
        return types[0]

    def _get_function(self) -> Function:
        func_tok = self._expect(token_func)
        id_tok = self._expect(token_identifier)
        func_name = Identifier(id_tok, id_tok.span)

        # define soon to allow recursion
        self._symbol_table.define(func_name, True)
        with self._symbol_table.new_frame():
            self._expect(token_paren_l)
            tok = self._peek()
            params = []
            types = []
            while tok.kind != token_paren_r:
                tok = self._expect(token_identifier)
                param = Identifier(tok, tok.span)
                params.append(param)
                self._symbol_table.define(param.name, False)
                self._expect(token_colon)
                types.append(self._get_type())
                tok = self._peek()
                if tok.kind == token_comma:
                    self._expect(token_comma)

            self._expect(token_paren_r)
            self._expect(token_arrow)
            ret_type = self._get_type()
            self._consume_white_space_and_peek()
            bracket_tok = self._expect(token_bracket_l)
            lines = self._parse_lines(end_token=token_bracket_r)
            tok_r = self._expect(token_bracket_r)
            body = ExpressionList(
                lines, Span.from_list(lines, bracket_tok.span) + tok_r.span
            )

        return Function(
            func_name,
            params,
            ArrowType(types, ret_type),
            body,
            span=func_name.span + body.span,
        )

    def _get_top_level(self) -> Node:
        next_ = self._peek()
        while next_.kind == token_new_line:
            self._expect(token_new_line)
            next_ = self._peek()

        if next_.kind == token_func:
            return self._get_function()
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
            if (
                get_builtin(identifier) == None
                and self._symbol_table.get(identifier) is None
            ):
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

    def _get_var_redef(self, identifier: Identifier) -> Node:
        if self._peek().kind == token_identifier:
            type_tok = self._expect(token_identifier)
            type_ = typer.identifier_to_uza_type(type_tok)
        else:
            type_ = None

        tok = self._expect(token_eq, token_plus_eq, token_minus_eq)
        if tok.kind == token_eq:
            value = self._get_expr()
        else:
            # syntactic sugar for +=, -= #TODO: different node for optimized VM op
            rhs = None
            if tok.kind == token_plus_eq:
                op = "+"
            else:
                op = "-"
            if tok.kind in (token_plus_eq, token_minus_eq):
                rhs = self._get_expr()
            else:
                rhs = Literal(Token(token_number, tok.span, "1"))

            value = InfixApplication(identifier, Identifier(op, tok.span), rhs)

        return VarRedef(identifier.name, value, identifier.span + value.span)

    def _get_type(self, recurse=True) -> Type:
        type_tok = self._expect(token_identifier)
        tok = self._peek()
        generic = None
        if tok.kind == token_angle_bracket_l:
            self._expect(token_angle_bracket_l)
            generic = self._get_type(recurse=False)
            tok = self._peek()
            if tok.kind == token_angle_bracket_r:
                r_brack = self._expect(token_angle_bracket_r)
                span = type_tok.span + r_brack.span
                type_tok = Token(token_identifier, span, repr=span.get_source())

        type_ = typer.identifier_to_uza_type(type_tok)

        return type_

    def _get_var_def(self) -> Node:
        decl_token = self._expect(token_var, token_const)
        immutable = decl_token.kind == token_const
        identifier = self._expect(token_identifier)
        if self._peek().kind == token_colon:
            self._expect(token_colon)
            type_ = self._get_type()
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
        with self._symbol_table.new_frame():
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
                interior = ExpressionList(
                    interior_lines, Span.from_list(interior_lines)
                )
                return ForLoop(init, cond, incr, interior, for_tok.span + interior.span)
            self._consume_white_space_and_peek()
            self._expect(token_do)
            interior = self._get_expr()
        return ForLoop(init, cond, incr, interior, for_tok.span + interior.span)

    def _get_range(self, node: Node) -> Range:
        self._expect(token_square_bracket_l)
        tok = self._peek()
        if tok.kind == token_colon:
            start = 0
        else:
            start = self._get_expr()

        tok = self._peek()
        single_item = True
        end = None

        if tok.kind == token_colon:
            single_item = False
            self._expect(token_colon)
            tok = self._peek()
            if tok.kind != token_square_bracket_r:
                end = self._get_expr()
        bracket_tok = self._expect(token_square_bracket_r)

        return Range(node, start, end, single_item, node.span + bracket_tok.span)

    def _get_expr(self, parsing_infix=False) -> Node:
        tok = self._consume_white_space_and_peek()

        if tok.kind in (token_const, token_var):
            return self._get_var_def()
        elif tok.kind == token_nil:
            tok = self._expect(token_nil)
            if parsing_infix:
                return Literal(tok)
            else:
                return self._get_infix(Literal(tok))

        elif tok.kind == token_paren_l:
            self._expect(token_paren_l)
            node = self._get_infix(self._get_expr())
            self._expect(token_paren_r)
            if parsing_infix:
                return node
            return self._get_infix(node)
        elif tok.kind == token_while:
            return self._get_while_loop()
        elif tok.kind == token_return:
            ret_tok = self._expect(token_return)
            if self._peek().kind == token_new_line:
                val = NoOp(ret_tok.span)
            else:
                val = self._get_expr()
            return Return(val, val.span)
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
            elif tok.kind in (token_eq, token_plus_eq):
                return self._get_var_redef(identifier)
            elif tok.kind == token_paren_l:
                self._expect(token_paren_l)
                arguments = self._get_function_args()
                paren_l_span = self._expect(token_paren_r).span
                if len(arguments) > 0:
                    arguments[-1].span += paren_l_span
                func_call = Application(identifier, *arguments)
                return self._get_infix(func_call)

            return self._get_infix(identifier)

        elif tok.kind.is_op():
            prefix_tok = self._expect(tok.kind)
            lhs = self._get_expr(parsing_infix=True)
            expr = self._get_infix(lhs, prefix_tok.kind.precedence)
            prefix_app = PrefixApplication(
                expr, Identifier(prefix_tok, prefix_tok.span + expr.span)
            )
            if not parsing_infix:
                return self._get_infix(prefix_app)
            else:
                return prefix_app

        elif tok.kind.is_user_value:
            val = Literal(self._expect(tok.kind))
            if parsing_infix:
                return val
            else:
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
        while valid_op and curr_op_precedence >= precedence:
            op = self._expect(op=True)
            rhs = self._get_expr(parsing_infix=True)

            higher_op, next_op_precedence = self._peek_valid_op(curr_op_precedence + 1)
            while higher_op:
                rhs = self._get_infix(rhs, next_op_precedence)
                higher_op, next_op_precedence = self._peek_valid_op(
                    curr_op_precedence + 1
                )
            if op.kind.is_prefix_operator:
                rhs = PrefixApplication(rhs, Identifier(op, op.span))
            lhs = InfixApplication(lhs, Identifier(op, op.span), rhs)
            valid_op, curr_op_precedence = self._peek_valid_op(precedence)

        return lhs

    def parse(self) -> Program:
        top_level_lines = self._parse_lines()
        span = Span(0, 0, "")
        span = Span.from_list(top_level_lines, span)

        top_level = ExpressionList(top_level_lines, span)
        return Program(top_level, self._errors, self.failed_nodes)
