import contextlib
import io
from pathlib import Path
import subprocess
import pytest
import sys
import os

from .helper import (
    parse_test_file,
    TESTS_PATH,
    TEST_UZA_PATH,
    RESET,
    MAGENTA,
    PROJECT_ROOT,
    remove_new_lines,
)


@pytest.mark.parametrize(
    "description, code, expected_output", parse_test_file(TESTS_PATH)
)
def test_end_to_end(description, code, expected_output, capfd):
    bytecode_out = os.path.join(PROJECT_ROOT, "out.uzo")

    try:
        subprocess.run(
            [
                "python",
                os.path.join(os.path.dirname(os.path.dirname(__file__)), "uza"),
                "--output",
                bytecode_out,
                "-s",
                code,
            ],
            check=True,
        )
    except Exception as e:
        pytest.fail(
            f"\nTest: {description}\n"
            f"{MAGENTA}Runtime Error: {e}{RESET}\n"
            f"With code:\n{code}\n",
            pytrace=False,
        )
    captured_out = capfd.readouterr()
    actual_output = captured_out.out
    actual_output = remove_new_lines(actual_output)

    try:
        expected_output = pytest.approx(float(expected_output))
        actual_output = pytest.approx(float(actual_output))
    except ValueError:
        pass

    assert actual_output == expected_output, (
        f"\nTest: {description}\n"
        f"Expected Output: {expected_output}\n"
        f"Actual Output: {actual_output}\n"
    )
