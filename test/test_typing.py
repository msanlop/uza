from src.uza.typing.typer import Typer
from src.uza.parser import Parser


def test_add_int_float():
    source = """
    val foo float = 123.5
    val bar int = 123
    foo + bar
    """
    typer = Typer(Parser(source).parse())
    err, _ = typer.check_types()
    assert not err


def test_add_int_string():
    source = """
    val foo float = 123.5
    val bar string = "123"
    foo + bar
    """
    typer = Typer(Parser(source).parse())
    err, _ = typer.check_types()
    assert err > 0


def test_inference():
    source = """
    val foo = 1
    val bar = 1
    foo + bar
    """
    typer = Typer(Parser(source).parse())
    err, _ = typer.check_types()
    assert not err


def test_inference_fail():
    source = """
    val foo = 1
    val bar = "hello"
    foo + bar
    """
    typer = Typer(Parser(source).parse())
    err, _ = typer.check_types()
    assert err > 0
