import lang


def test_simple():
    source = "123 + 99"
    actual = lang.Parser(source).parse()[0]
    expected = lang.Op(
        lang.Number(lang.Token(lang.token_NUM, 0, 4, "123")),
        (lang.Token(lang.token_plus, 5, 7)),
        lang.Number(lang.Token(lang.token_NUM, 7, 9, "99")),
    )
    assert actual == expected


def test_paren():
    source = "(123 + 99)"
    actual = lang.Parser(source).parse()[0]
    expected = lang.Op(
        lang.Number(lang.Token(lang.token_NUM, 0, 4, "123")),
        (lang.Token(lang.token_plus, 5, 7)),
        lang.Number(lang.Token(lang.token_NUM, 7, 9, "99")),
    )
    assert actual == expected


def test_mult_precedence():
    source = "123 + 99 * 2"
    actual = lang.Parser(source).parse()[0]
    # parser = lang.Parser(source)
    # actual = parser._get_infix(parser._get_expr())
    expected = lang.Op(
        lang.Number(lang.Token(lang.token_NUM, 0, 4, "123")),
        (lang.Token(lang.token_plus, 5, 7)),
        lang.Op(
            lang.Number(lang.Token(lang.token_NUM, 7, 9, "99")),
            lang.Token(lang.token_star, 1, 1),
            lang.Number(lang.Token(lang.token_NUM, 1, 1, "2")),
        ),
    )
    assert actual == expected


def test_mult_precedence_paren():
    source = "(123 + 99) * 2"
    actual = lang.Parser(source).parse()[0]
    expected = lang.Op(
        lang.Op(
            lang.Number(lang.Token(lang.token_NUM, 1, 1, "123")),
            (lang.Token(lang.token_plus, 1, 1)),
            lang.Number(lang.Token(lang.token_NUM, 1, 1, "99")),
        ),
        lang.Token(lang.token_star, 1, 1),
        lang.Number(lang.Token(lang.token_NUM, 1, 1, "2")),
    )
    assert actual == expected


def test_pow_precedence_right_associative():
    source = "2 ** 3 ** 2"
    actual = lang.Parser(source).parse()[0]
    expected = lang.Op(
        lang.Number(lang.Token(lang.token_NUM, 1, 1, "2")),
        lang.Token(lang.token_star_double, 1, 1),
        lang.Op(
            lang.Number(lang.Token(lang.token_NUM, 1, 1, "3")),
            (lang.Token(lang.token_star_double, 1, 1)),
            lang.Number(lang.Token(lang.token_NUM, 1, 1, "2")),
        ),
    )
    assert actual == expected


def test_declarations():
    source = "val my_val float = 123.53 ** 2"
    actual = lang.Parser(source).parse()[0]
    expected = lang.varDef(
        "my_val",
        "float",
        lang.Op(
            lang.Number(lang.Token(lang.token_NUM, 1, 1, "123.53")),
            lang.Token(lang.token_star_double, 1, 1),
            lang.Number(lang.Token(lang.token_NUM, 1, 1, "2")),
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

    expressions = lang.Parser(source).parse()
    outputs = [lang.Interpreter(expr).evaluate() for expr in expressions]
    real = [eval(line) for line in source.splitlines()]
    for actual, expected in zip(outputs, real):
        assert actual == expected
    # return outputs == real
    # assert has_python_parity(op)
