TEST_HEADER = "#test "
TEST_EXPECTED = "#expected"


def parse_test_file(file_path) -> list[tuple]:
    """returns a list of tuple : (test title, test source, expected output)

    Make sure the file has a trailing new line character.
    """

    tests = []
    with open(file_path, "r") as file:
        title, source, expected = ("", "", "")
        content = file.readline()
        while content:
            if content.startswith(TEST_HEADER):
                title = content[len(TEST_HEADER) :]
            elif content.startswith(TEST_EXPECTED):
                expected = file.readline()
                tests.append((title, source, expected))
                title, source, expected = ("", "", "")
            else:
                source += content
            content = file.readline()

    return tests
