from __future__ import annotations
import string
from typing import Callable, Optional, TypeVar, List
from collections import deque
from abc import ABC
from dataclasses import dataclass, field


@dataclass(frozen=True)
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


@dataclass(frozen=True)
class Span:
    start: int
    end: int

    def __add__(self, that: object) -> Span:
        if not isinstance(that, Span):
            return NotImplemented
        return Span(self.start, that.end)


@dataclass(frozen=True)
class Token:
    kind: TokenKind
    span: Span
    repr: str = ""

    def __post_init__(self):
        if self.repr == "":
            object.__setattr__(self, "repr", self.kind.repr)  # bypass frozen=True

    def __eq__(self, value: object) -> bool:
        if not isinstance(value, Token):
            return NotImplemented
        if self.kind != value.kind:
            return False
        if self.kind.is_user_value:
            return self.repr == value.repr

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
token_val = TokenKind("val", token_types)
token_var = TokenKind("var", token_types)
token_eq = TokenKind("=", token_types)
token_eq_double = TokenKind("==", token_types)
token_identifier = TokenKind("identifier", token_types)
token_def = TokenKind("def", token_types)
token_comma = TokenKind("comma", token_types)
token_and = TokenKind("and", token_types, 1)
token_false = TokenKind("false", token_types)
token_quote = TokenKind('"', token_types)
token_string = TokenKind("STR", token_types, is_user_value=True)
token_number = TokenKind("NUM", token_types, is_user_value=True)
token_boolean = TokenKind("BOOL", token_types, is_user_value=True)


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

    def _next_token(self) -> Optional[Token]:
        self._consume_white_space()
        if self._overflows():
            return None

        char = self._char_at(self._start)
        if char == "\n":
            end = self._start + 1
            type_ = token_new_line
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
                type_, Span(str_start, str_end), self._source[str_start:str_end]
            )
            self._start = end
            return new_string_token
        elif char in string.ascii_letters:
            word, end = self._get_next_word()
            match word:
                case "val":
                    type_ = token_val  # TODO: test type()
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
            type_, Span(self._start, end), self._source[self._start : end]
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
            if token is None:
                raise StopIteration
            return token
        raise StopIteration


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
        self.span = func_id.span + self.args[-1].span

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
    tpe: str
    value: Node
    span: Span = field(compare=False)
    immutable: bool = True

    def visit(self, that):
        return that.visit_var_def(self)


Program = List[Node]


class Parser:
    """
    A parser parses it source code into a Program, i.e. a list of AST Nodes.
    """

    def __init__(self, source: str):
        self._tokens = deque(Lexer(source))
        self._source = source

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

        if next_.kind in (token_val, token_var):
            res = self._get_var_def()
        else:
            res = self._get_expr()

        if len(self._tokens) > 0:
            self._expect(token_new_line)
        return res

    def _get_var_def(self) -> Node:
        decl_token = self._expect(token_var, token_val)
        immutable = decl_token.kind == token_val
        identifier = self._expect(token_identifier)
        tpe = self._expect(token_identifier)
        self._expect(token_eq)
        value = self._get_infix(self._get_expr())

        return VarDef(identifier.repr, tpe.repr, value, Span(1, 1), immutable=immutable)

    def _get_function_args(self) -> list[Node]:
        next_ = self._peek()
        args = []
        while next_.kind != token_paren_r:
            arg = self._get_expr()
            next_ = self._peek()
            if next_.kind == token_comma:
                self._expect(token_comma)
            elif next_.kind != token_paren_r:
                raise SyntaxError(f"Expected ',' or ')' but got {next_}")
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
            identifier_tok = self._expect(token_identifier)
            identifier = Identifier(identifier_tok, identifier_tok.span)
            tok = self._peek()
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
                self._get_expr(), Identifier(prefix_tok, Span(1, 1))
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
            return []
        expressions = []
        while len(self._tokens) > 0:
            if self._peek().kind == token_new_line:
                self._expect(token_new_line)
                continue
            
            expr = self._get_top_level()
            expressions.append(expr)

        return expressions


@dataclass(frozen=True)
class BuiltIn:
    """
    A BuiltIn is a function that is part of the standard library.
    """

    identifier: str
    _builtins_dict: dict[str, BuiltIn]

    def __post_init__(self):
        """adds itself to the dict that holds all the builtins"""
        self._builtins_dict[self.identifier] = self

    def __repr__(self) -> str:
        return f"BuiltIn({self.identifier})"


_builtins: dict[str, BuiltIn] = {}
bi_add = BuiltIn("+", _builtins)
bi_sub = BuiltIn("-", _builtins)
bi_mul = BuiltIn("*", _builtins)
bi_div = BuiltIn("/", _builtins)
bi_pow = BuiltIn("**", _builtins)
bi_land = BuiltIn("and", _builtins)
bi_print = BuiltIn("print", _builtins)
bi_println = BuiltIn("println", _builtins)
bi_max = BuiltIn("max", _builtins)
bi_min = BuiltIn("min", _builtins)


def get_builtin(identifier: Identifier) -> Optional[BuiltIn]:
    """
    Returns a _BuiltIn_ with the given who's name matches the _identifier_
    if it exists.
    """
    return _builtins.get(identifier.name)


@dataclass
class Value:
    """
    Defines a value.
    """

    name: str
    value: Literal
    immutable: bool = False


class Context:
    """Excetution context that containts the stack frames.

    _frames_ is queue of locals, a tuple with the context name and a dict with
    the (variable name, value) pairs.
    """

    frames: deque[tuple[str, dict[str, Value]]]

    def __init__(
        self, frames: deque[tuple[str, dict[str, Value]]] | None = None
    ) -> None:
        """Excetution context that containts the stack frames. Each frame has a
        context name and the local definitions.

        Args:
            frames (deque[tuple[str, dict[str, Value]]], optional):
                Defaults to deque().
        """
        if not frames:
            self.frames: deque[tuple[str, dict[str, Value]]] = deque()
            self.frames.appendleft(("", {}))
        else:
            self.frames = frames

    def with_new_frame(self, context_name: str, frame: dict[str, Value]) -> Context:
        new_frames = deque((*self.frames, (context_name, frame)))
        return Context(new_frames)

    def define(self, variable_name: str, value: Value) -> None:
        top_frame = self.frames[0]
        frame_locals = top_frame[1]
        frame_locals[variable_name] = value

    def get(self, identifier: str) -> Value:
        for frame in self.frames:
            frame_locals = frame[1]
            value = frame_locals.get(identifier)
            if value is not None:
                return value
        raise NameError(f'"{identifier}" has not been defined')

    def reassign(self, identifier: str, new_value: Value) -> None:
        pass  # immutable check in the parser


class Interpreter:
    """
    A class that takes in a program and interprets it by walking the AST.

    Uses the visitor pattern by calling node.visit(self). Performance is not a
    concern in this implementation. It's main use is to ensure parity with the
    VM interpretation and to more easily test ideas.
    """

    def __init__(self, ast: Program | Node):
        self._context = Context()
        if isinstance(ast, Node):
            self._program = [ast]
        else:
            self._program = ast

    T = TypeVar("T")
    R = TypeVar("R")

    def _in_scope(
        self, scope_name: str, locals_vals: dict[str, Value], func: Callable[[], R]
    ) -> R:
        saved = self._context
        self._context = saved.with_new_frame(scope_name, locals_vals)
        res = func()
        self._context = saved
        return res

    def visit_built_in_application(self, func_id, *params) -> Optional[Value]:
        ret = None
        lhs, rhs = params[0], None
        if len(params) > 1:
            rhs = params[1]

        if func_id == bi_add:
            ret = lhs + rhs
        elif func_id == bi_sub:
            if len(params) == 1:
                ret = -lhs
            else:
                ret = lhs - rhs
        elif func_id == bi_mul:
            ret = lhs * rhs
        elif func_id == bi_div:
            # C division casts the rhs to the lhs's type
            casted = type(lhs)(rhs)
            if isinstance(lhs, int):
                ret = lhs // casted
            else:
                ret = lhs / casted
        elif func_id == bi_land:
            ret = lhs and rhs
        elif func_id == bi_pow:
            ret = lhs**rhs
        elif func_id == bi_print:
            print(*params, end="")
            ret = None
        elif func_id == bi_println:
            print(*params)
            ret = None
        elif func_id == bi_max:
            ret = max(lhs, rhs)
        elif func_id == bi_min:
            ret = min(lhs, rhs)

        return ret

    def visit_var_def(self, definition: VarDef):
        value = definition.value.visit(self)
        self._context.define(definition.identifier, value)

    def visit_identifier(self, identifier: Identifier):
        return self._context.get(identifier.name)

    def visit_literal(self, literal: Literal):
        return literal.value

    def visit_application(self, application: Application):
        evaluated = [param.visit(self) for param in application.args]
        build_in_id = get_builtin(application.func_id)
        if build_in_id:
            return self.visit_built_in_application(build_in_id, *evaluated)
        raise NotImplementedError("no user functions yet, something went wrong")

    def visit_prefix_application(self, prefix_app: PrefixApplication):
        evaluated = prefix_app.expr.visit(self)
        build_in_id = get_builtin(prefix_app.func_id)
        if build_in_id:
            return self.visit_built_in_application(build_in_id, evaluated)
        raise NotImplementedError("no user functions yet, something went wrong")

    def visit_infix_application(self, infix_app: InfixApplication):
        left = infix_app.lhs.visit(self)
        right = infix_app.rhs.visit(self)
        identifier = infix_app.func_id
        built_in_id = get_builtin(identifier)
        if built_in_id:
            return self.visit_built_in_application(built_in_id, left, right)
        raise NotImplementedError("no user functions yet, something went wrong")

    def evaluate(self) -> Optional[Value]:
        """
        The main _Interpreter_ function that evaluates the top level nodes.

        Returns:
            Optional[int | float]: return the evaluated result of the last line
        """
        lines = [node.visit(self) for node in self._program]
        return lines[-1]
