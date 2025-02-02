import pytest
from uzac.typer import Typer
from uzac.parser import Parser


def test_add_int_float():
    source = """
    const foo : float = 123.5
    const bar :int = 123
    foo + bar
    """
    typer = Typer(Parser(source).parse())
    err, _, _, _ = typer.check_types()
    assert not err


def test_add_int_string():
    source = """
    const foo : float = 123.5
    const bar : string = "123"
    foo + bar
    """
    typer = Typer(Parser(source).parse())
    err, _, _, _ = typer.check_types()
    assert err > 0


def test_inference():
    source = """
    const foo = 1
    const bar = 1
    foo + bar
    """
    typer = Typer(Parser(source).parse())
    err, _, _, _ = typer.check_types()
    assert not err


def test_inference_fail():
    source = """
    const foo = 1
    const bar = "hello"
    foo + bar
    """
    typer = Typer(Parser(source).parse())
    err, _, _, _ = typer.check_types()
    assert err > 0


def test_inference_fail_nested():
    source = """
    const foo = 1
    const bar = 123.54 + 4532
    foo + bar + "hi"
    """
    typer = Typer(Parser(source).parse())
    err, _, _, _ = typer.check_types()
    assert err > 0


def test_inference_var_defs():
    source = """
    const foo : float = 1.
    const bar = 123.54 + 4532
    const test = foo + bar
    println(test)
    """
    typer = Typer(Parser(source).parse())
    err, _, _, _ = typer.check_types()
    assert not err


def test_const_redef_fails():
    source = """
    const foo : float = 1.
    foo = 2.
    """
    typer = Typer(Parser(source).parse())
    err, _, _, _ = typer.check_types()
    assert err == 1


def test_var_redef_works():
    source = """
    var foo : float = 1.
    foo = 2.
    """
    typer = Typer(Parser(source).parse())
    err, _, _, _ = typer.check_types()
    assert not err


def test_var_type_redef_fails():
    source = """
    var foo : float = 1.
    foo = 123
    """
    typer = Typer(Parser(source).parse())
    err, _, _, _ = typer.check_types()
    assert err > 0


def test_fail_on_generic_decl_without_type():
    source = """
    const foo = List()
    println(foo)
    """
    with pytest.raises(TypeError):
        typer = Typer(Parser(source).parse())
        typer.check_types()


def test_fail_functions_that_do_not_always_return():
    source = """
    func voidFunc(n: int) => int {
        if n > 50 {
            return n * 2
        }
        else {
            if n < 0 {
                return 0
            }
        }
    }

    println(voidFunc(15))
    """
    typer = Typer(Parser(source).parse())
    errc, _, _, _ = typer.check_types()
    assert errc > 0

    source = """
    func voidFunc(n: int) => void {
        if n > 50 {
            return
        }
        else if n < 0 then return
    }

    println(voidFunc(15))
    """
    typer = Typer(Parser(source).parse())
    errc, _, _, _ = typer.check_types()
    assert not errc
