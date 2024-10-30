from uza.typer import Typer
from uza.parser import Parser


def test_add_int_float():
    source = """
    const foo float = 123.5
    const bar int = 123
    foo + bar
    """
    typer = Typer(Parser(source).parse())
    err, _, _ = typer.check_types()
    assert not err


def test_add_int_string():
    source = """
    const foo float = 123.5
    const bar string = "123"
    foo + bar
    """
    typer = Typer(Parser(source).parse())
    err, _, _ = typer.check_types()
    assert err > 0


def test_inference():
    source = """
    const foo = 1
    const bar = 1
    foo + bar
    """
    typer = Typer(Parser(source).parse())
    err, _, _ = typer.check_types()
    assert not err


def test_inference_fail():
    source = """
    const foo = 1
    const bar = "hello"
    foo + bar
    """
    typer = Typer(Parser(source).parse())
    err, _, _ = typer.check_types()
    assert err > 0


def test_inference_fail_nested():
    source = """
    const foo = 1
    const bar = 123.54 + 4532
    foo + bar + "hi"
    """
    typer = Typer(Parser(source).parse())
    err, _, _ = typer.check_types()
    assert err > 0


def test_inference_var_defs():
    source = """
    const foo float = 1.
    const bar = 123.54 + 4532
    const test = foo + bar
    println(test)
    """
    typer = Typer(Parser(source).parse())
    err, _, _ = typer.check_types()
    assert not err


def test_const_redef_fails():
    source = """
    const foo float = 1.
    foo = 2.
    """
    typer = Typer(Parser(source).parse())
    err, _, _ = typer.check_types()
    assert err == 1


def test_var_redef_works():
    source = """
    var foo float = 1.
    foo = 2.
    """
    typer = Typer(Parser(source).parse())
    err, _, _ = typer.check_types()
    assert not err


def test_var_type_redef_fails():
    source = """
    var foo float = 1.
    foo = 123
    """
    typer = Typer(Parser(source).parse())
    err, _, _ = typer.check_types()
    assert err > 0
