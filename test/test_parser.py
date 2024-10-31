# pylint: disable=wildcard-import unused-import missing-function-docstring
from uza.uzast import *
from uza.parser import Parser
from uza.interpreter import Interpreter


def test_infix_add():
    source = "123 + 99"
    actual = Parser(source).parse().syntax_tree[0]
    expected = InfixApplication(
        Literal(Token(token_number, Span(0, 4, source), "123")),
        (Identifier(Token(token_plus, Span(5, 7, source)), Span(1, 1, source))),
        Literal(Token(token_number, Span(7, 9, source), "99")),
    )
    assert actual == expected


def test_paren_infix_add():
    source = "(123 + 99)"
    actual = Parser(source).parse().syntax_tree[0]
    expected = InfixApplication(
        Literal(Token(token_number, Span(0, 4, source), "123")),
        (Identifier(Token(token_plus, Span(5, 7, source)), Span(1, 1, source))),
        Literal(Token(token_number, Span(7, 9, source), "99")),
    )
    assert actual == expected


def test_mult_precedence():
    source = "123 + 99 * 2"
    actual = Parser(source).parse().syntax_tree[0]
    # parser = Parser(source)
    # actual = parser._get_infix(parser._get_expr())
    expected = InfixApplication(
        Literal(Token(token_number, Span(0, 4, source), "123")),
        (Identifier(Token(token_plus, Span(5, 7, source)), Span(1, 1, source))),
        InfixApplication(
            Literal(Token(token_number, Span(7, 9, source), "99")),
            Identifier(Token(token_star, Span(1, 1, source)), Span(1, 1, source)),
            Literal(Token(token_number, Span(1, 1, source), "2")),
        ),
    )
    assert actual == expected


def test_mult_precedence_paren():
    source = "(123 + 99) * 2"
    actual = Parser(source).parse().syntax_tree[0]
    expected = InfixApplication(
        InfixApplication(
            Literal(Token(token_number, Span(1, 1, source), "123")),
            (Identifier(Token(token_plus, Span(1, 1, source)), Span(1, 1, source))),
            Literal(Token(token_number, Span(1, 1, source), "99")),
        ),
        Identifier(Token(token_star, Span(1, 1, source)), Span(1, 1, source)),
        Literal(Token(token_number, Span(1, 1, source), "2")),
    )
    assert actual == expected


def test_pow_precedence_right_associative():
    source = "2 ** 3 ** 2"
    actual = Parser(source).parse().syntax_tree[0]
    expected = InfixApplication(
        Literal(Token(token_number, Span(1, 1, source), "2")),
        Identifier(Token(token_star_double, Span(1, 1, source)), Span(1, 1, source)),
        InfixApplication(
            Literal(Token(token_number, Span(1, 1, source), "3")),
            (
                Identifier(
                    Token(token_star_double, Span(1, 1, source)), Span(1, 1, source)
                )
            ),
            Literal(Token(token_number, Span(1, 1, source), "2")),
        ),
    )
    assert actual == expected


def test_declarations():
    source = "const my_val float = 123.53 ** 2"
    actual = Parser(source).parse().syntax_tree[0]
    expected = VarDef(
        "my_val",
        type_float,
        InfixApplication(
            Literal(Token(token_number, Span(1, 1, source), "123.53")),
            Identifier(
                Token(token_star_double, Span(1, 1, source)), Span(1, 1, source)
            ),
            Literal(Token(token_number, Span(1, 1, source), "2")),
        ),
        True,
    )
    print(repr(expected))
    assert actual == expected


def test_math_expressions():
    source = """(5 + 10) * 85.5 / 3
    --(5 + 10) + 85
    (5 + 10) + 85
    2 ** 4 ** 5
    1 and 1
    0 and 1"""

    expressions = Parser(source).parse().syntax_tree
    outputs = [Interpreter(Program([expr], 0, [])).evaluate() for expr in expressions]
    real = [eval(line) for line in source.splitlines()]
    for actual, expected in zip(outputs, real):
        assert actual == expected


def test_builtin_application_parse():
    source = "println(123 + 99)"
    actual = Parser(source).parse().syntax_tree[0]
    expected = Application(
        Identifier("println", Span(1, 1, source)),
        InfixApplication(
            Literal(Token(token_number, Span(0, 4, source), "123")),
            (Identifier(Token(token_plus, Span(5, 7, source)), Span(1, 1, source))),
            Literal(Token(token_number, Span(7, 9, source), "99")),
        ),
    )
    print(repr(expected))
    assert actual == expected
