# import lang
from lang import *


def test_simple():
    source = "123 + 99"
    actual = Parser(source).parse()[0]
    expected = InfixApplication(
        Number(Token(token_NUM, 0, 4, "123")),
        (Token(token_plus, 5, 7)),
        Number(Token(token_NUM, 7, 9, "99")),
    )
    assert actual == expected


def test_paren():
    source = "(123 + 99)"
    actual = Parser(source).parse()[0]
    expected = InfixApplication(
        Number(Token(token_NUM, 0, 4, "123")),
        (Token(token_plus, 5, 7)),
        Number(Token(token_NUM, 7, 9, "99")),
    )
    assert actual == expected


def test_mult_precedence():
    source = "123 + 99 * 2"
    actual = Parser(source).parse()[0]
    # parser = Parser(source)
    # actual = parser._get_infix(parser._get_expr())
    expected = InfixApplication(
        Number(Token(token_NUM, 0, 4, "123")),
        (Token(token_plus, 5, 7)),
        InfixApplication(
            Number(Token(token_NUM, 7, 9, "99")),
            Token(token_star, 1, 1),
            Number(Token(token_NUM, 1, 1, "2")),
        ),
    )
    assert actual == expected


def test_mult_precedence_paren():
    source = "(123 + 99) * 2"
    actual = Parser(source).parse()[0]
    expected = InfixApplication(
        InfixApplication(
            Number(Token(token_NUM, 1, 1, "123")),
            (Token(token_plus, 1, 1)),
            Number(Token(token_NUM, 1, 1, "99")),
        ),
        Token(token_star, 1, 1),
        Number(Token(token_NUM, 1, 1, "2")),
    )
    assert actual == expected


def test_pow_precedence_right_associative():
    source = "2 ** 3 ** 2"
    actual = Parser(source).parse()[0]
    expected = InfixApplication(
        Number(Token(token_NUM, 1, 1, "2")),
        Token(token_star_double, 1, 1),
        InfixApplication(
            Number(Token(token_NUM, 1, 1, "3")),
            (Token(token_star_double, 1, 1)),
            Number(Token(token_NUM, 1, 1, "2")),
        ),
    )
    assert actual == expected


def test_declarations():
    source = "val my_val float = 123.53 ** 2"
    actual = Parser(source).parse()[0]
    expected = varDef(
        "my_val",
        "float",
        InfixApplication(
            Number(Token(token_NUM, 1, 1, "123.53")),
            Token(token_star_double, 1, 1),
            Number(Token(token_NUM, 1, 1, "2")),
        ),
        True,
    )
    print(repr(expected))
    assert actual == expected


def test_math_expressions():
    source = """(5 + 10) * 85 / 3
    --(5 + 10) + 85
    (5 + 10) + 85
    2 ** 4 ** 5"""

    expressions = Parser(source).parse()
    outputs = [Interpreter(expr).evaluate() for expr in expressions]
    real = [eval(line) for line in source.splitlines()]
    for actual, expected in zip(outputs, real):
        assert actual == expected
    # return outputs == real
    # assert has_python_parity(op)


def test_builtin_application_parse():
    source = "println(123 + 99)"
    actual = Parser(source).parse()[0]
    expected = Application(
        Token(token_identifier, 1, 1, "println"),
        InfixApplication(
            Number(Token(token_NUM, 0, 4, "123")),
            (Token(token_plus, 5, 7)),
            Number(Token(token_NUM, 7, 9, "99")),
        ),
    )
    print(repr(expected))
    assert actual == expected


def test_builtin_application_interpret(capsys):
    source = "(123 + 99)"
    source_lang = f"print({source})"
    Interpreter(Parser(source_lang).parse()[0]).evaluate()
    captured = capsys.readouterr()
    assert captured.out == str(eval(source))


def test_builtin_application_interpret_multiple_args():
    source = "min(123, 99)"
    actual = Interpreter(Parser(source).parse()[0]).evaluate()
    assert actual == eval(source)


def test_builtin_application_function_as_arg(capsys):
    source = "min(123, 99)"
    source_lang = f"print({source})"
    Interpreter(Parser(source_lang).parse()[0]).evaluate()
    captured = capsys.readouterr()
    assert captured.out == str(eval(source))
