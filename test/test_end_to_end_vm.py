from pathlib import Path
import subprocess
import pytest
from .helper import (
    parse_test_file,
    TESTS_PATH,
    TEST_UZA_PATH,
    RESET,
    MAGENTA,
    PROJECT_ROOT,
)
import os


@pytest.mark.parametrize(
    "description, code, expected_output", parse_test_file(TESTS_PATH)
)
def test_end_to_end(description, code, expected_output, capfd):
    bytecode_out = os.path.join(PROJECT_ROOT, "out.uzo")
    try:
        subprocess.run(
            [TEST_UZA_PATH, "--output", bytecode_out, "-s", code],
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
    actual_output = actual_output.replace(os.linesep, "")

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
