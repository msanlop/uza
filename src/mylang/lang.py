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
class Token:
    kind: TokenKind
    start: int
    end: int
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
            if not (char in string.ascii_letters or char in "_-" or char in string.digits):
                break
            end += 1

        return self._source[self._start : end], end

    def _get_next_string(self, delimiter="") -> tuple[str, int]:
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
            type = token_new_line
        elif char in string.digits:
            end = self._next_numeral()
            type = token_number
        elif char == ",":
            end = self._start + 1
            type = token_comma
        elif char == '"':
            word, end = self._get_next_string()
            end += 1
            type = token_string
            str_start = self._start + 1
            str_end = end - 1
            new_string_token = Token(
                type, str_start, str_end, self._source[str_start:str_end]
            )
            self._start = end
            return new_string_token
        elif char in string.ascii_letters:
            word, end = self._get_next_word()
            match word:
                case "val":
                    type = token_val  # TODO: test type()
                case "var":
                    type = token_var
                case "and":
                    type = token_and
                case "true":
                    type = token_boolean
                case "false":
                    type = token_boolean
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
class Literal(Node):
    token: Token
    value: bool | str | int | float = field(init=False)

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

    def visit(self, that):
        return that.visit_literal(self)


@dataclass
class Identifier(Node):
    name: str

    def __init__(self, identifier: Token | str) -> None:
        if isinstance(identifier, Token):
            self.name = identifier.repr
        else:
            self.name = identifier

    def visit(self, that):
        return that.visit_identifier(self)


@dataclass
class Application(Node):
    func_id: Identifier
    params: list[Node]

    def __init__(self, func_id: Identifier, *args) -> None:
        self.func_id = func_id
        self.params = list(args)

    def visit(self, that):
        return that.visit_application(self)


@dataclass
class InfixApplication(Node):
    lhs: Node
    func_id: Identifier
    rhs: Node

    def visit(self, that):
        return that.visit_infix_application(self)


@dataclass
class PrefixApplication(Node):
    expr: Node
    func_id: Identifier

    def visit(self, that):
        return that.visit_prefix_application(self)


@dataclass
class varDef(Node):
    identifier: str
    tpe: str
    value: Node
    immutable: bool = True

    def visit(self, that):
        return that.visit_var_def(self)


Program = List[Node]


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

    def _get_function_args(self) -> list[Node]:
        next = self._peek()
        args = []
        while next.kind != token_paren_r:
            arg = self._get_expr()
            next = self._peek()
            if next.kind == token_comma:
                self._expect(token_comma)
            elif next.kind != token_paren_r:
                raise SyntaxError(f"Expected ',' or ')' but got {next}")
            args.append(arg)
            next = self._peek()

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
            identifier = Identifier(identifier_tok)
            tok = self._peek()
            if tok.kind != token_paren_l:
                return self._get_infix(identifier)

            self._expect(token_paren_l)
            arguments = self._get_function_args()
            self._expect(token_paren_r)
            return Application(identifier, *arguments)

        if tok.kind.is_op():
            prefix_tok = self._expect(tok.kind)
            return PrefixApplication(self._get_expr(), Identifier(prefix_tok))
        if tok.kind.is_user_value:
            val = Literal(self._expect(tok.kind))
            return self._get_infix(val)

        raise RuntimeError(
            f"did not expect '{tok.repr}' at '{self._source[max(tok.start - 2, 0): min(tok.end + 2, len(self._source))]}'"
        )

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

            lhs = InfixApplication(lhs, Identifier(op), rhs)
            valid_op, curr_op_precedence = self._peek_valid_op(precedence)

        return lhs

    def parse(self) -> Program:
        if not self._peek():
            return []
        expressions = []
        while len(self._tokens) > 0:
            expr = self._get_top_level()
            expressions.append(expr)

        return expressions


@dataclass(frozen=True)
class BuiltIn:
    identifier: str
    _builtins_dict: dict[str, BuiltIn]

    def __post_init__(self):
        self._builtins_dict[self.identifier] = self

    def __repr__(self) -> str:
        return f"BuiltIn({self.identifier})"


_builtins: dict[str, BuiltIn] = {}
bi_add = BuiltIn("+", _builtins)
bi_minus = BuiltIn("-", _builtins)
bi_mult = BuiltIn("*", _builtins)
bi_div = BuiltIn("/", _builtins)
bi_pow = BuiltIn("**", _builtins)
bi_land = BuiltIn("and", _builtins)
bi_print = BuiltIn("print", _builtins)
bi_println = BuiltIn("println", _builtins)
bi_max = BuiltIn("max", _builtins)
bi_min = BuiltIn("min", _builtins)


def get_builtin(identifier: Identifier) -> Optional[BuiltIn]:
    return _builtins.get(identifier.name)


@dataclass
class Value:
    name: str
    value: Literal
    immutable: bool = False


class Context:  # TODO change to allow functions
    def __init__(
        self, frames: deque[tuple[str, dict[str, Value]]] | None = None
    ) -> None:
        """Excetution context that containts the stack frames. Each frame has a context name and the local definitions.

        Args:
            frames (deque[tuple[str, dict[str, Value]]], optional): TODO: redo this whole docstr
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
            if value:
                return value
        raise NameError(f'"{identifier}" has not been defined')

    def reassign(self, identifier: str, new_value: Value) -> None:
        pass  # immutable check in the parser


class Interpreter:
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
        if func_id == bi_add:
            ret = params[0] + params[1]
        elif func_id == bi_minus:
            if len(params) == 1:
                ret = -params[0]
            else:
                ret = params[0] + params[1]
        elif func_id == bi_mult:
            ret = params[0] * params[1]
        elif func_id == bi_div:
            ret = params[0] / params[1]
        elif func_id == bi_land:
            ret = params[0] and params[1]
        elif func_id == bi_pow:
            ret = params[0] ** params[1]
        elif func_id == bi_print:
            print(*params, end="")
            ret = None
        elif func_id == bi_println:
            print(*params)
            ret = None
        elif func_id == bi_max:
            ret = max(params[0], params[1])
        elif func_id == bi_min:
            ret = min(params[0], params[1])

        return ret

    def visit_var_def(self, definition: varDef):
        value = definition.value.visit(self)
        self._context.define(definition.identifier, value)

    def visit_identifier(self, identifier: Identifier):
        return self._context.get(identifier.name)

    def visit_literal(self, literal: Literal):
        return literal.value

    def visit_application(self, application: Application):
        evaluated = [param.visit(self) for param in application.params]
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

    def evaluate(self) -> Optional[int | float]:
        lines = [node.visit(self) for node in self._program]
        return lines[-1]


source = """
val foo float = 1.5
val bar float = 1.5
val something string = "LETTTSSSS GOOOOOO "
val ttwoo string = "I THINK"
print(something)
println(ttwoo)
println(foo + bar)
println(foo ** bar)
println(foo ** bar)
println(foo ** bar)
println(foo ** bar)
println(foo ** bar)
println(foo ** bar)
println(foo * bar * foo * bar / 2)
val t3 bool = true
"""
actual = Interpreter(Parser(source).parse()).evaluate()