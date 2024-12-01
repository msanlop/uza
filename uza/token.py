from dataclasses import dataclass

from .utils import Span


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


token_types: dict[str, TokenKind] = {}

token_new_line = TokenKind("NL", token_types)
token_plus = TokenKind("+", token_types, 1)
token_plus_plus = TokenKind("++", token_types)
token_plus_eq = TokenKind("+=", token_types)
token_minus = TokenKind("-", token_types, 1)
token_minus_minus = TokenKind("--", token_types)
token_minus_eq = TokenKind("-=", token_types)
token_star = TokenKind("*", token_types, 2)
token_slash = TokenKind("/", token_types, 3)
token_star_double = TokenKind("**", token_types, 9, right_assoc=True)
token_paren_l = TokenKind("(", token_types)
token_paren_r = TokenKind(")", token_types)
token_bracket_l = TokenKind("{", token_types)
token_bracket_r = TokenKind("}", token_types)
token_square_bracket_l = TokenKind("[", token_types, 10)
token_square_bracket_r = TokenKind("]", token_types)
token_const = TokenKind("const", token_types)
token_func = TokenKind("func", token_types)
token_return = TokenKind("return", token_types)
token_arrow = TokenKind("=>", token_types)
token_var = TokenKind("var", token_types)
token_eq = TokenKind("=", token_types)
token_eq_double = TokenKind("==", token_types, 1)
token_angle_bracket_l = TokenKind("<", token_types, 1)
token_angle_bracket_r = TokenKind(">", token_types, 1)
token_identifier = TokenKind("identifier", token_types)
token_comment = TokenKind("comment", token_types)
token_def = TokenKind("def", token_types)
token_if = TokenKind("if", token_types)
token_then = TokenKind("then", token_types)
token_else = TokenKind("else", token_types)
token_comma = TokenKind("comma", token_types)
token_and = TokenKind("and", token_types, 1)
token_or = TokenKind("or", token_types, 1)
token_false = TokenKind("false", token_types, is_user_value=True)
token_true = TokenKind("true", token_types, is_user_value=True)
token_quote = TokenKind('"', token_types)
token_string = TokenKind("STR", token_types, is_user_value=True)
token_number = TokenKind("NUM", token_types, is_user_value=True)
token_boolean = TokenKind("BOOL", token_types, is_user_value=True)
token_while = TokenKind("while", token_types)
token_for = TokenKind("for", token_types)
token_semicolon = TokenKind(";", token_types)
token_colon = TokenKind(":", token_types)
token_pipe = TokenKind("|", token_types)
token_do = TokenKind("do", token_types)
