import pytest

from uzac.driver import Driver
from uzac.interpreter import Interpreter
from uzac.parser import Parser
from uzac.typer import Typer
from .helper import parse_test_file, TESTS_PATH, MAGENTA, RESET, remove_new_lines
import os


@pytest.mark.parametrize(
    "description, code, expected_output", parse_test_file(TESTS_PATH)
)
def test_end_to_end(description, code, expected_output, capsys):
    try:
        res = Driver.run_with_config(Driver.Configuration.INTERPRET, source=code)
        assert res == 0
    except Exception as e:
        pytest.fail(
            f"\nTest: {description}\n"
            f"{MAGENTA}Runtime Error: {e}{RESET}\n"
            f"With code:\n{code}\n",
            pytrace=False,
        )
    captured = capsys.readouterr()
    actual_output = captured.out
    actual_output = remove_new_lines(actual_output)

    try:
        expected_output = pytest.approx(float(expected_output))
        actual_output = pytest.approx(float(actual_output))
    except ValueError:
        pass

    assert actual_output == expected_output, (
        f"\nTest: {description}\n"
        f"With code:\n----------------------------\n{code}\n----------------------------\n"
        f"Expected Output: {expected_output}\n"
        f"Actual Output: {actual_output}\n"
    )
