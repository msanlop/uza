from __future__ import annotations
from collections import deque
from functools import reduce
import string
import sys
from typing import Callable, List, Optional, TypeVar
import typing

from uzac.builtins import get_builtin
from uzac.ast import (
    Application,
    Block,
    Break,
    Continue,
    ExpressionList,
    ForLoop,
    Function,
    Identifier,
    IfElse,
    InfixApplication,
    Literal,
    MethodApplication,
    NoOp,
    Node,
    PrefixApplication,
    Range,
    Return,
    UzaASTVisitor,
    VarDef,
    Program,
    VarRedef,
    WhileLoop,
)

from uzac.type import ArrowType, GenericType, Type, identifier_to_uza_type
from uzac.utils import (
    ANSIColor,
    Span,
    SymbolTable,
    UzaNameError,
    UzaSyntaxError,
    in_color,
)
from uzac.token import *
from uzac import typer


class Scanner:
    """
    The Scanner class is a iterator over the token of a given source file.
    """

    def __init__(self, source: str, discard_style=True):
        self.__discard_style = discard_style
        self.__source = source
        self.__source_len = len(source)
        self.__start = 0
        self.__line = 0
        self.__token_buffer = []

    def __char_at(self, i) -> Optional[str]:
        if self.__overflows(i):
            return None
        return self.__source[i]

    def __overflows(self, i: Optional[int] = None) -> bool:
        if i:
            return i >= self.__source_len
        return self.__start >= self.__source_len

    def __get_next_word(self) -> int:
        end = self.__start + 1
        while not self.__overflows(end):
            char = self.__char_at(end)
            if not (
                char in string.ascii_letters or char in string.digits or char in "_"
            ):
                break
            end += 1

        return end

    def __get_next_string(self) -> int:
        end = self.__start + 1
        while not self.__overflows(end) and self.__char_at(end) != '"':
            # TODO: multiline strings
            # if self.__char_at(end) == "\n":
            #     raise SyntaxError(
            #         rf"found \n in string literal at {self.__source[self.__start : end]}"
            #     )
            end += 1
        if self.__overflows(end):
            span = Span(self.__start, end, self.__source)
            raise UzaSyntaxError(span, "Could not find closing '\"'")
        return end

    def __get_next_f_string_tokens(self) -> list[Token]:
        def create_string_token(end):
            res = Token(token_partial_string, Span(self.__start, end, self.__source))
            self.__start = end
            return res

        tokens = []

        f_quote_tok = Token(
            token_f_quote, Span(self.__start, self.__start + 2, self.__source)
        )
        tokens.append(f_quote_tok)
        self.__start += 2
        end = self.__start

        char = self.__char_at(end)
        while char != '"':
            # continue parsing string
            if char != "{":
                end += 1
            # get expression
            else:
                if end - self.__start > 0:  # commit string
                    tokens.append(create_string_token(end))

                tok = self.__next_token()
                while tok.kind != token_bracket_r:
                    tokens.append(tok)
                    tok = self.__next_token()

                tokens.append(tok)
                end = self.__start

            char = self.__char_at(end)
            if char is None:
                span = f_quote_tok.span + Span(None, end - 1, self.__source)
                raise UzaSyntaxError(span, "Could not find closing '\"'")

        if end - self.__start > 0:  # string at the end
            tokens.append(create_string_token(end))

        tokens.append(Token(token_quote, Span(self.__start, end, self.__source)))
        self.__start += 1
        return tokens

    def __get_next_comment(self) -> int:
        end = self.__start + 1
        while not self.__overflows(end) and self.__char_at(end) != "\n":
            end += 1
        return end

    def __next_numeral(self):
        end = self.__start
        already_has_dot = False
        char = self.__char_at(end)
        while char in string.digits or (
            char == "." and not already_has_dot or char == "_"
        ):
            if char == ".":
                already_has_dot = True
            if end + 1 == self.__source_len:
                return end + 1
            end += 1
            char = self.__char_at(end)
        return end

    def __next_token(self) -> Optional[Token | list[Token]]:
        """
        Scans the next token, at self.__start in Scanner source.
        Return None if there are no more tokens.
        """
        if self.__overflows():
            return None

        char = self.__char_at(self.__start)
        if char in string.digits:
            end = self.__next_numeral()
            type_ = token_number
        elif (
            char == "f"
            and not self.__overflows(self.__start + 1)
            and self.__char_at(self.__start + 1) == '"'
        ):
            return self.__get_next_f_string_tokens()
        elif char == '"':
            end = self.__get_next_string()
            end += 1
            type_ = token_string
            str_start = self.__start + 1
            str_end = end - 1
            new_string_token = Token(
                type_,
                Span(str_start - 1, str_end + 1, self.__source),  # span includes quotes
            )
            self.__start = end
            return new_string_token
        elif char in string.ascii_letters:
            end = self.__get_next_word()
            word = self.__source[self.__start : end]
            if word in token_types:
                type_ = token_types[word]
            else:
                type_ = token_identifier
        else:
            end = self.__start + 2
            maybe_double_token = None
            if not self.__overflows(end):
                maybe_double_token = token_types.get(self.__source[self.__start : end])

            if maybe_double_token:
                # TokenKind with 2 chars
                type_ = maybe_double_token
                if type_ == token_slash_slash:
                    type_ = token_comment
                    end = self.__get_next_comment()
            else:
                # single char TokenKind
                type_maybe = token_types.get(char)
                if type_maybe is None:
                    raise UzaSyntaxError(
                        Span(self.__start, self.__start + 1, self.__source),
                        f"Invalid syntax '{char}'",
                    )
                type_ = type_maybe
                end = self.__start + 1

        assert self.__start <= end
        new_token = Token(type_, Span(self.__start, end, self.__source))
        self.__start = end
        return new_token

    def next_token(self):
        """
        Returns the next token and buffers any extra tokens in the instance __token_buffer
        """
        if len(self.__token_buffer) > 0:
            token = self.__token_buffer[0]
            self.__token_buffer = self.__token_buffer[1:]
        else:
            token = self.__next_token()

        if isinstance(token, list):
            self.__token_buffer.extend(token[1:])
            token = token[0]
        return token

    def __iter__(self):
        return self

    def __next__(self):
        while self.__start < self.__source_len:
            token = self.next_token()
            if token.kind == token_new_line:
                self.__line += 1
            if self.__discard_style:
                while token and token.kind in (token_comment, token_space, token_tab):
                    token = self.next_token()

            if token is None:
                raise StopIteration
            return token
        raise StopIteration


class Parser:
    """
    A parser parses it source code into a uza `Program`.
    """

    def __init__(self, source: str):
        self.__tokens = deque(Scanner(source))  # TODO: use the iter directly
        self.__source = source
        self.__errors = 0

        # map of (Identifier -> bool) for mutability
        self.__symbol_table = SymbolTable()

    def __snapshot(self):
        """
        Does NOT SAVE symbol table state. Add if necessary.
        """
        p = Parser(self.__source)
        p.__tokens = self.__tokens.copy()
        return p

    def __restore(self, snapshot: Parser):
        self.__tokens = snapshot.__tokens

    def __log_error(self, error: Error):
        self.__errors += 1

    def __peek(self, error_on_none=False):
        if len(self.__tokens) == 0:
            if error_on_none:
                raise UzaSyntaxError(
                    Span(len(self.__source) - 1, len(self.__source), self.__source),
                    "unexpected end of file",
                )
            return None

        assert self.__tokens[0] is not None
        return self.__tokens[0]

    def __expect(self, *type_: TokenKind, op=False) -> Token:
        tok = self.__peek(error_on_none=True)
        if op and not tok.kind.is_op():
            raise UzaSyntaxError(
                tok.span, f"Expected operator but found {tok.span.get_source()}"
            )
        elif tok.kind not in type_ and not op:
            tkinds = " ".join(f"`{k.repr}`" for k in type_)
            raise UzaSyntaxError(
                tok.span,
                f"Found `{tok.span.get_source()}` but expected one of: {tkinds}",
            )

        return self.__tokens.popleft()

    def __consume_white_space_and_peek(self) -> Token:
        temp = self.__peek()
        while temp and temp.kind == token_new_line:
            self.__expect(temp.kind)
            temp = self.__peek()
        return temp

    def __get_type(self) -> Type:
        types = []
        tok = self.__expect(token_identifier)
        type_ = identifier_to_uza_type(tok)
        types.append(type_)
        tok = self.__peek()
        while tok.kind == token_pipe:
            self.__expect(token_pipe)
            tok = self.__expect(token_identifier)
            type_ = identifier_to_uza_type(tok)
            types.append(type_)
            tok = self.__peek()

        if len(types) > 1:
            return reduce(lambda x, y: x | y, types)
        return types[0]

    def __get_function(self) -> Function:
        func_tok = self.__expect(token_func)
        id_tok = self.__expect(token_identifier)
        func_name = Identifier(id_tok, id_tok.span)

        # define soon to allow recursion
        self.__symbol_table.define(func_name, True)
        with self.__symbol_table.new_frame():
            self.__expect(token_paren_l)
            tok = self.__peek()
            params = []
            types = []
            while tok.kind != token_paren_r:
                tok = self.__expect(token_identifier)
                param = Identifier(tok, tok.span)
                params.append(param)
                self.__symbol_table.define(param.name, False)
                self.__expect(token_colon)
                types.append(self.__get_type())
                tok = self.__peek()
                if tok.kind == token_comma:
                    self.__expect(token_comma)

            self.__expect(token_paren_r)
            self.__expect(token_arrow)
            ret_type = self.__get_type()
            self.__consume_white_space_and_peek()
            bracket_tok = self.__expect(token_bracket_l)
            lines = self.__parse_lines(end_token=token_bracket_r)
            tok_r = self.__expect(token_bracket_r)
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

    def __get_top_level(self) -> Node:
        next_ = self.__peek()
        while next_.kind == token_new_line:
            self.__expect(token_new_line)
            next_ = self.__peek()

        if next_.kind == token_func:
            return self.__get_function()
        return self.__get_expr()

    def __get_if_else(self) -> Node:
        self.__expect(token_if)
        pred = self.__get_expr()
        tok = self.__peek()
        if tok and tok.kind == token_bracket_l:
            t_case = self.__parse_block(end_token=token_bracket_r)
        else:
            self.__expect(token_then)
            t_case = self.__get_expr()
        self.__consume_white_space_and_peek()
        f_case = None
        tok = self.__consume_white_space_and_peek()
        if tok and tok.kind == token_else:
            self.__expect(token_else)
            f_case = self.__get_expr()
        return IfElse(pred, t_case, f_case)

    def __check_for_identifier_func(self, identifier: Identifier) -> None:
        identifier_tok = identifier.token
        if (
            get_builtin(identifier) == None
            and self.__symbol_table.get(identifier) is None
        ):
            raise UzaNameError(
                identifier_tok.span, f"function `{identifier_tok.repr}` is undefined"
            )

    def __check_for_identifier_var(self, identifier: Identifier) -> None:
        identifier_tok = identifier.token
        if self.__symbol_table.get(identifier_tok.repr) is None:
            raise UzaNameError(
                identifier_tok.span,
                f"variable `{identifier_tok.repr}` not defined in this scope",
            )

    def __get_identifier(self) -> Identifier:
        identifier_tok = self.__expect(token_identifier)
        identifier = Identifier(identifier_tok, identifier_tok.span)
        return identifier

    def __get_var_redef(self, identifier: Identifier) -> Node:
        if self.__peek().kind == token_identifier:
            type_tok = self.__expect(token_identifier)
            type_ = typer.identifier_to_uza_type(type_tok)
        else:
            type_ = None

        tok = self.__expect(token_eq, token_plus_eq, token_minus_eq)
        if tok.kind == token_eq:
            value = self.__get_expr()
        else:
            # syntactic sugar for +=, -= #TODO: different node for optimized VM op
            rhs = None
            if tok.kind == token_plus_eq:
                op = token_plus
            else:
                op = token_minus
            if tok.kind in (token_plus_eq, token_minus_eq):
                rhs = self.__get_expr()

            tok_span = tok.span
            op_tok_span = Span(tok_span.start, tok_span.start + 1, tok_span.source)
            op_tok = Token(op, op_tok_span)
            op_ident = Identifier(op_tok, op_tok_span)
            value = InfixApplication(identifier, op_ident, rhs)

        return VarRedef(identifier, value, identifier.span + value.span)

    def __get_generic_param(self) -> Type:
        self.__expect(token_angle_bracket_l)
        type_ = self.__get_type()
        self.__expect(token_angle_bracket_r)
        return type_

    def __get_type(self) -> Type:
        type_tok = self.__expect(token_identifier)
        type_ = typer.identifier_to_uza_type(type_tok)
        tok = self.__peek()
        if tok.kind == token_angle_bracket_l:
            self.__expect(token_angle_bracket_l)
            generic = typer.identifier_to_uza_type(type_tok)
            type_ = generic.with_argument(self.__get_type())
            tok = self.__peek()
            if tok.kind == token_angle_bracket_r:
                r_brack = self.__expect(token_angle_bracket_r)
                span = type_tok.span + r_brack.span
                type_tok = Token(token_identifier, span)
        else:
            type_ = typer.identifier_to_uza_type(type_tok)

        return type_

    def __get_var_def(self) -> Node:
        decl_token = self.__expect(token_var, token_const)
        immutable = decl_token.kind == token_const
        identifier = self.__expect(token_identifier)
        if self.__peek().kind == token_colon:
            self.__expect(token_colon)
            type_ = self.__get_type()
        else:
            type_ = None
        self.__expect(token_eq)
        value = self.__get_expr()
        if not self.__symbol_table.define(
            identifier.repr, immutable, false_if_defined=True
        ):
            # FIXME: no Error node
            raise UzaSyntaxError(
                identifier.span,
                f"'{identifier.repr}' has already been defined in this scope",
            )
        return VarDef(
            identifier.repr,
            type_,
            value,
            decl_token.span + value.span,
            immutable=immutable,
        )

    def __get_function_args(self) -> list[Node]:
        next_ = self.__peek()
        args: list[Node] = []
        while next_ is not None and next_.kind != token_paren_r:
            arg = self.__get_expr()
            next_ = self.__peek(error_on_none=True)
            if next_.kind == token_comma:
                self.__expect(token_comma)
            elif next_.kind != token_paren_r:
                raise UzaSyntaxError(
                    next_.span, f"Unexpected token while parsing function args"
                )
            args.append(arg)
            next_ = self.__peek(error_on_none=True)

        return args

    def __parse_lines(self, end_token: Optional[TokenKind] = None) -> List[Node]:
        expressions: list[Node] = []
        while len(self.__tokens) > 0:
            tok = self.__peek()
            if tok.kind == token_new_line:
                self.__expect(token_new_line)
                continue
            if end_token and tok.kind == end_token:
                break
            expr = self.__get_top_level()
            expressions.append(expr)

        return expressions

    def __parse_block(self, end_token: Optional[TokenKind] = None) -> Block:
        self.__expect(token_bracket_l)

        with self.__symbol_table.new_frame():
            lines = self.__parse_lines(end_token)
            if len(lines) > 0:
                span = lines[0].span + lines[-1].span
            else:
                span = Span(0, 0, "empty block")

        self.__expect(token_bracket_r)
        return Block(lines, span)

    def __get_while_loop(self) -> WhileLoop:
        self.__expect(token_while)
        cond = self.__get_expr()
        tok = self.__peek()
        if tok and tok.kind == token_bracket_l:
            interior = self.__parse_block(end_token=token_bracket_r)
            return WhileLoop(cond, interior, cond.span + interior.span)
        self.__consume_white_space_and_peek()
        self.__expect(token_do)
        interior = self.__get_expr()
        return WhileLoop(cond, interior, cond.span + interior.span)

    def __get_for_loop(self) -> ForLoop:
        with self.__symbol_table.new_frame():
            for_tok = self.__expect(token_for)
            tok = self.__peek()
            if tok and tok.kind == token_semicolon:
                init = NoOp(for_tok.span)
            else:
                init = self.__get_expr()
            self.__expect(token_semicolon)
            tok = self.__peek()
            if tok and tok.kind == token_semicolon:
                cond = Literal(Token(token_true, for_tok.span))
            else:
                cond = self.__get_expr()
            self.__expect(token_semicolon)
            tok = self.__peek()
            if tok and tok.kind in (token_bracket_l, token_do):
                incr = NoOp(for_tok.span)
            else:
                incr = self.__get_expr()
            tok = self.__peek()
            if tok and tok.kind == token_bracket_l:
                tok_bl = self.__expect(token_bracket_l)
                interior_lines = self.__parse_lines(end_token=token_bracket_r)
                self.__expect(token_bracket_r)
                interior = ExpressionList(
                    interior_lines, Span.from_list(interior_lines, tok_bl.span)
                )
                return ForLoop(init, cond, incr, interior, for_tok.span + interior.span)
            self.__consume_white_space_and_peek()
            self.__expect(token_do)
            interior = self.__get_expr()
        return ForLoop(init, cond, incr, interior, for_tok.span + interior.span)

    def __get_range(self, node: Node) -> Range:
        self.__expect(token_square_bracket_l)
        tok = self.__peek()
        if tok.kind == token_colon:
            start = 0
        else:
            start = self.__get_expr()

        tok = self.__peek()
        single_item = True
        end = None

        if tok.kind == token_colon:
            single_item = False
            self.__expect(token_colon)
            tok = self.__peek()
            if tok.kind != token_square_bracket_r:
                end = self.__get_expr()
        bracket_tok = self.__expect(token_square_bracket_r)

        return Range(node, start, end, single_item, node.span + bracket_tok.span)

    def __get_f_string(self) -> Node:
        def get_either_string_or_expr(tok_kind: TokenKind):
            if tok_kind == token_partial_string:
                res = Literal(self.__expect(token_partial_string))
            elif tok_kind == token_bracket_l:
                self.__expect(token_bracket_l)
                value = self.__parse_lines(end_token=token_bracket_r)
                assert len(value) == 1
                value = value[0]
                self.__expect(token_bracket_r)
                res = value
            return res

        ftok = self.__expect(token_f_quote)
        fstring = None

        tok = self.__peek()
        while tok and tok.kind in (token_partial_string, token_bracket_l):
            value = get_either_string_or_expr(tok.kind)
            if fstring is None:
                fstring = value
            else:
                fstring = InfixApplication(
                    fstring, Identifier(token_plus, value.span), value
                )
            tok = self.__peek()

        if tok.kind == token_quote:
            self.__expect(token_quote)
        return fstring

    def __get_expr(self, parsing_infix=False) -> typing.Subclass[Type]:
        tok = self.__consume_white_space_and_peek()
        if tok is None:
            return None

        if tok.kind in (token_const, token_var):
            return self.__get_var_def()
        elif tok.kind == token_break:
            return Break(self.__expect(token_break).span)
        elif tok.kind == token_continue:
            return Continue(self.__expect(token_continue).span)
        elif tok.kind == token_paren_l:
            self.__expect(token_paren_l)
            node = self.__get_infix(self.__get_expr())
            self.__expect(token_paren_r)
            if parsing_infix:
                return node
            return self.__get_infix(node)
        elif tok.kind == token_f_quote:
            fstring = self.__get_f_string()
            if parsing_infix:
                return fstring
            return self.__get_infix(fstring)
        elif tok.kind == token_while:
            return self.__get_while_loop()
        elif tok.kind == token_return:
            ret_tok = self.__expect(token_return)
            if self.__peek().kind == token_new_line:
                val = NoOp(ret_tok.span)
            else:
                val = self.__get_expr()
            return Return(val, val.span)
        elif tok.kind == token_for:
            return self.__get_for_loop()
        elif tok.kind == token_if:
            return self.__get_if_else()
        elif tok.kind == token_bracket_l:
            node = self.__parse_block(end_token=token_bracket_r)
            return self.__get_infix(node)
        elif tok.kind == token_identifier:
            identifier = self.__get_identifier()
            tok = self.__peek()
            generic_param = None
            if not tok:
                self.__check_for_identifier_var(identifier)
                return identifier
            elif tok.kind in (token_eq, token_plus_eq):
                return self.__get_var_redef(identifier)
            elif tok.kind == token_angle_bracket_l:
                # try to parse generic function call
                # identifier :: < :: type :: > :: ( :: expr :: )
                snapshot = self.__snapshot()
                try:
                    generic_param = self.__get_generic_param()
                    tok = self.__peek()
                    assert tok.kind == token_paren_l
                except Exception:  # TODO: change to UzaParserException
                    self.__restore(snapshot)

            if tok.kind == token_paren_l:
                self.__check_for_identifier_func(identifier)
                self.__expect(token_paren_l)
                arguments = self.__get_function_args()
                paren_r_span = self.__expect(token_paren_r).span
                if len(arguments) > 0:
                    arguments[-1].span += paren_r_span
                func_call = Application(
                    identifier, *arguments, generic_arg=generic_param
                )
                if parsing_infix:
                    return func_call
                return self.__get_infix(func_call)

            self.__check_for_identifier_var(identifier)
            return self.__get_infix(identifier)

        elif tok.kind.is_op():
            prefix_tok = self.__expect(tok.kind)
            lhs = self.__get_expr(parsing_infix=True)
            expr = self.__get_infix(lhs, prefix_tok.kind.precedence)
            prefix_app = PrefixApplication(
                expr, Identifier(prefix_tok, prefix_tok.span + expr.span)
            )
            if not parsing_infix:
                return self.__get_infix(prefix_app)
            else:
                return prefix_app

        elif tok.kind.is_user_value:
            val = Literal(self.__expect(tok.kind))
            if parsing_infix:
                return val
            else:
                return self.__get_infix(val)
        else:
            raise UzaSyntaxError(
                tok.span, f"Unexpected token: `{tok.span.get_source()}`"
            )

    def __peek_valid_op(self, precedence: int):
        next_tok = self.__peek()
        if next_tok is None:
            return False, None
        op_prec = next_tok.kind.precedence
        if next_tok.kind.right_assoc:
            return (
                op_prec + 1 >= precedence,
                op_prec,
            )  # TODO: might break for future operations
        return op_prec >= precedence, op_prec

    def __get_infix(self, lhs: Node, precedence=1) -> Node:
        """
        evaluates operations with in the appropriate order of precedence
        """
        valid_op, curr_op_precedence = self.__peek_valid_op(precedence)
        while valid_op and curr_op_precedence >= precedence:
            op = self.__expect(op=True)
            rhs = self.__get_expr(parsing_infix=True)

            higher_op, next_op_precedence = self.__peek_valid_op(curr_op_precedence + 1)
            while higher_op:
                rhs = self.__get_infix(rhs, next_op_precedence)
                higher_op, next_op_precedence = self.__peek_valid_op(
                    curr_op_precedence + 1
                )
            if op.kind.is_prefix_operator:
                rhs = PrefixApplication(rhs, Identifier(op, op.span))
            elif op.kind == token_dot:
                assert issubclass(rhs.__class__, Application)
                rhs.args.insert(0, lhs)
                lhs = MethodApplication(lhs, rhs)
            else:
                lhs = InfixApplication(lhs, Identifier(op, op.span), rhs)
            valid_op, curr_op_precedence = self.__peek_valid_op(precedence)

        return lhs

    def parse(self) -> Program:
        top_level_lines = self.__parse_lines()
        span = Span(0, 0, "")
        span = Span.from_list(top_level_lines, span)

        top_level = ExpressionList(top_level_lines, span)
        return Program(top_level, self.__errors)
