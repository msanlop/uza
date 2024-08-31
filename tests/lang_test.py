# pylint: disable=wildcard-import
from src.mylang.lang import *  # TODO: split tests by compiling step


def test_infix_add():
    source = "123 + 99"
    actual = Parser(source).parse()[0]
    expected = InfixApplication(
        Literal(Token(token_number, Span(0, 4), "123")),
        (Identifier(Token(token_plus, Span(5, 7)), Span(5, 7))),
        Literal(Token(token_number, Span(7, 9), "99")),
    )
    assert actual == expected


def test_paren_infix_add():
    source = "(123 + 99)"
    actual = Parser(source).parse()[0]
    expected = InfixApplication(
        Literal(Token(token_number, Span(0, 4), "123")),
        (Identifier(Token(token_plus, Span(5, 7)), Span(5, 7))),
        Literal(Token(token_number, Span(7, 9), "99")),
    )
    assert actual == expected


def test_mult_precedence():
    source = "123 + 99 * 2"
    actual = Parser(source).parse()[0]
    # parser = Parser(source)
    # actual = parser._get_infix(parser._get_expr())
    expected = InfixApplication(
        Literal(Token(token_number, Span(0, 4), "123")),
        (Identifier(Token(token_plus, Span(5, 7)), Span(5, 7))),
        InfixApplication(
            Literal(Token(token_number, Span(7, 9), "99")),
            Identifier(Token(token_star, Span(1, 1)), Span(1, 1)),
            Literal(Token(token_number, Span(1, 1), "2")),
        ),
    )
    assert actual == expected


def test_mult_precedence_paren():
    source = "(123 + 99) * 2"
    actual = Parser(source).parse()[0]
    expected = InfixApplication(
        InfixApplication(
            Literal(Token(token_number, Span(1, 1), "123")),
            (Identifier(Token(token_plus, Span(1, 1)), Span(1, 1))),
            Literal(Token(token_number, Span(1, 1), "99")),
        ),
        Identifier(Token(token_star, Span(1, 1)), Span(1, 1)),
        Literal(Token(token_number, Span(1, 1), "2")),
    )
    assert actual == expected


def test_pow_precedence_right_associative():
    source = "2 ** 3 ** 2"
    actual = Parser(source).parse()[0]
    expected = InfixApplication(
        Literal(Token(token_number, Span(1, 1), "2")),
        Identifier(Token(token_star_double, Span(1, 1)), Span(1, 1)),
        InfixApplication(
            Literal(Token(token_number, Span(1, 1), "3")),
            (Identifier(Token(token_star_double, Span(1, 1)), Span(1, 1))),
            Literal(Token(token_number, Span(1, 1), "2")),
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
            Literal(Token(token_number, Span(1, 1), "123.53")),
            Identifier(Token(token_star_double, Span(1, 1)), Span(1, 1)),
            Literal(Token(token_number, Span(1, 1), "2")),
        ),
        True,
    )
    print(repr(expected))
    assert actual == expected


def test_math_expressions():
    source = """(5 + 10) * 85 / 3
    --(5 + 10) + 85
    (5 + 10) + 85
    2 ** 4 ** 5
    1 and 1
    0 and 1"""

    expressions = Parser(source).parse()
    outputs = [Interpreter(expr).evaluate() for expr in expressions]
    real = [eval(line) for line in source.splitlines()]
    for actual, expected in zip(outputs, real):
        assert actual == expected


def test_builtin_application_parse():
    source = "println(123 + 99)"
    actual = Parser(source).parse()[0]
    expected = Application(
        Identifier("println", Span(1,2)),
        InfixApplication(
            Literal(Token(token_number, Span(0, 4), "123")),
            (Identifier(Token(token_plus, Span(5, 7)),  Span(5, 7))),
            Literal(Token(token_number, Span(7, 9), "99")),
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


def test_print_string(capsys):
    source = "Hello world!"
    source_lang = f'print("{source}")'
    Interpreter(Parser(source_lang).parse()[0]).evaluate()
    captured = capsys.readouterr()
    assert captured.out == source


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


def test_print_val(capsys):
    expr = "123.43 * 2.0"
    source = f"""val foo float = {expr}
    print(foo)
    """
    actual = Interpreter(Parser(source).parse()).evaluate()
    captured = capsys.readouterr()
    assert captured.out == str(eval(expr))


def test_print_infix_val_application(capsys):
    source = f"""
    val foo float = 1.5
    val bar float = 1.5
    print(foo + bar)
    """
    actual = Interpreter(Parser(source).parse()).evaluate()
    captured = capsys.readouterr()
    assert captured.out == "3.0"
