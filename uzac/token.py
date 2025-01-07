from __future__ import annotations
from dataclasses import dataclass, field

from .utils import Span

token_types: dict[str, TokenKind] = {}


@dataclass(frozen=True)
class TokenKind:
    """
    An uza TokenKind.
    Tokens are added to a global dict with all TokenKind.
    """

    repr: str
    _token_dict: dict = field(init=False, default_factory=lambda: token_types)
    precedence: int = -1
    right_assoc: bool = False
    is_user_value: bool = False

    def __post_init__(self):
        self._token_dict[self.repr] = self

    def is_op(self):
        return self.precedence >= 0

    def __eq__(self, value: object) -> bool:
        if not isinstance(value, TokenKind):
            raise NotImplementedError(f"for {value}")
        return self.repr == value.repr

    def __repr__(self) -> str:
        return f"TokenKind('{self.repr}')"


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
            raise NotImplementedError(f"for {value}")
        if self.kind != value.kind:
            return False
        if self.kind.is_user_value:
            return self.repr == value.repr

        return True


token_new_line = TokenKind("\n")
token_space = TokenKind(" ")
token_plus = TokenKind("+", 1)
token_plus_eq = TokenKind("+=")
token_minus = TokenKind("-", 1)
token_minus_eq = TokenKind("-=")
token_star = TokenKind("*", 2)
token_slash = TokenKind("/", 3)
token_slash_slash = TokenKind("//")
token_star_double = TokenKind("**", 9, right_assoc=True)
token_paren_l = TokenKind("(")
token_paren_r = TokenKind(")")
token_bracket_l = TokenKind("{")
token_bracket_r = TokenKind("}")
token_square_bracket_l = TokenKind("[", 10)
token_square_bracket_r = TokenKind("]")
token_const = TokenKind("const")
token_func = TokenKind("func")
token_return = TokenKind("return")
token_arrow = TokenKind("=>")
token_var = TokenKind("var")
token_eq = TokenKind("=")
token_eq_double = TokenKind("==", 1)
token_bang = TokenKind("!", 1)
token_bang_eq = TokenKind("!=", 1)
token_angle_bracket_l = TokenKind("<", 1)
token_angle_bracket_r = TokenKind(">", 1)
token_identifier = TokenKind("identifier")
token_comment = TokenKind("comment")
token_def = TokenKind("def")
token_if = TokenKind("if")
token_then = TokenKind("then")
token_else = TokenKind("else")
token_comma = TokenKind(",")
token_and = TokenKind("and", 1)
token_or = TokenKind("or", 1)
token_false = TokenKind("false", is_user_value=True)
token_true = TokenKind("true", is_user_value=True)
token_quote = TokenKind('"')
token_string = TokenKind("STR", is_user_value=True)
token_number = TokenKind("NUM", is_user_value=True)
token_boolean = TokenKind("BOOL", is_user_value=True)
token_while = TokenKind("while")
token_for = TokenKind("for")
token_semicolon = TokenKind(";")
token_colon = TokenKind(":")
token_pipe = TokenKind("|")
token_do = TokenKind("do")
