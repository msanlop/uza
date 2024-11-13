import os
import re

TEST_HEADER = "#test "
TEST_EXPECTED = "#expected"
COMMENTED_OUT = "//"

PROJECT_ROOT = os.path.dirname(os.path.dirname(__file__))

TESTS_FILENAME = "test_sources.txt"
TESTS_PATH = os.path.join(os.path.dirname(__file__), TESTS_FILENAME)

TEST_UZA_PATH = os.path.join(PROJECT_ROOT, "uza")

MAGENTA = "\033[0;35m"
RESET = "\033[0m"


def remove_new_lines(string: str) -> str:
    return re.sub(r"\n|\r", "", string)


def parse_test_file(file_path) -> list[tuple]:
    """returns a list of tuple : (test title, test source, expected output),
    where expected output has no new line character for easier cross platform
    testing.

    Make sure the file has a trailing new line character.
    """

    tests = []
    with open(file_path, "r") as file:
        title, source, expected = ("", "", "")
        line = file.readline()
        while line:
            print(line)
            if line.startswith(COMMENTED_OUT):
                pass
            elif line.startswith(TEST_HEADER):
                title = line[len(TEST_HEADER) :]
            elif line.startswith(TEST_EXPECTED):
                expected = ""
                temp = remove_new_lines(file.readline())
                while True:
                    expected += temp
                    print(expected)
                    temp = remove_new_lines(file.readline())
                    if len(temp) == 0:
                        line = temp
                        break
                tests.append((title, source, expected))
                source = ""
            else:
                source += line
            line = file.readline()

    return tests
