import os

TEST_HEADER = "#test "
TEST_EXPECTED = "#expected"
COMMENTED_OUT = "//"

PROJECT_ROOT = os.path.dirname(os.path.dirname(__file__))

TESTS_FILENAME = "test_sources.txt"
TESTS_PATH = os.path.join(os.path.dirname(__file__), TESTS_FILENAME)

TEST_UZA_PATH = os.path.join(PROJECT_ROOT, "uza")

MAGENTA = "\033[0;35m"
RESET = "\033[0m"


def parse_test_file(file_path) -> list[tuple]:
    """returns a list of tuple : (test title, test source, expected output),
    where expected output has no new line character for easier cross platform
    testing.

    Make sure the file has a trailing new line character.
    """

    tests = []
    with open(file_path, "r") as file:
        title, source, expected = ("", "", "")
        content = file.readline()
        while content:
            if content.startswith(COMMENTED_OUT):
                pass
            elif content.startswith(TEST_HEADER):
                title = content[len(TEST_HEADER) :]
            elif content.startswith(TEST_EXPECTED):
                expected = file.readline().replace(os.linesep, "")
                tests.append((title, source, expected))
                source = ""
            else:
                source += content
            content = file.readline()

    return tests
