import pytest

from uza.interpreter import Interpreter
from uza.parser import Parser
from .helper import parse_test_file, TESTS_PATH, MAGENTA, RESET
import os


@pytest.mark.parametrize(
    "description, code, expected_output", parse_test_file(TESTS_PATH)
)
def test_end_to_end(description, code, expected_output, capsys):
    try:
        program = Parser(code).parse()
        Interpreter(program).evaluate()
    except Exception as e:
        pytest.fail(
            f"\nTest: {description}\n"
            f"{MAGENTA}Runtime Error: {e}{RESET}\n"
            f"With code:\n{code}\n",
            pytrace=False,
        )
    captured = capsys.readouterr()
    actual_output = captured.out
    actual_output = actual_output.replace(os.linesep, "")

    assert actual_output == expected_output, (
        f"\nTest: {description}\n"
        f"Expected Output: {expected_output}\n"
        f"Actual Output: {actual_output}\n"
    )
