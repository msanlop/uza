import subprocess
import pytest
from .helper import parse_test_file


TEST_FILENAME = "./test/test_sources.txt"
MAGENTA = "\033[0;35m"
RESET = "\033[0m"


@pytest.mark.parametrize(
    "description, code, expected_output", parse_test_file(TEST_FILENAME)
)
def test_end_to_end(description, code, expected_output, capfd):
    try:
        subprocess.run(
            ["pypy3", "./src/main.py", "--output", f"./target/out.uzo", "-s", code],
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
