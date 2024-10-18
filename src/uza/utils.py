from __future__ import annotations
from dataclasses import dataclass
import sys


class ANSIColor:
    """ANSI color codes"""

    BLACK = "\033[0;30m"
    RED = "\033[0;31m"
    GREEN = "\033[0;32m"
    BROWN = "\033[0;33m"
    BLUE = "\033[0;34m"
    PURPLE = "\033[0;35m"
    CYAN = "\033[0;36m"
    LIGHT_GRAY = "\033[0;37m"
    DARK_GRAY = "\033[1;30m"
    LIGHT_RED = "\033[1;31m"
    LIGHT_GREEN = "\033[1;32m"
    YELLOW = "\033[1;33m"
    LIGHT_BLUE = "\033[1;34m"
    LIGHT_PURPLE = "\033[1;35m"
    LIGHT_CYAN = "\033[1;36m"
    LIGHT_WHITE = "\033[1;37m"
    BOLD = "\033[1m"
    FAINT = "\033[2m"
    ITALIC = "\033[3m"
    UNDERLINE = "\033[4m"
    BLINK = "\033[5m"
    NEGATIVE = "\033[7m"
    CROSSED = "\033[9m"
    END = "\033[0m"


_is_terminal = sys.stderr.isatty()


def in_bold(string: str) -> str:
    if _is_terminal:
        return ANSIColor.BOLD + string + ANSIColor.END
    return string


@dataclass(frozen=True)
class Span:
    start: int
    end: int
    source: str

    def __add__(self, that: object) -> Span:
        if not isinstance(that, Span):
            return NotImplemented
        assert self.source == that.source
        return Span(self.start, that.end, self.source)

    def get_source(self) -> str:
        return self.source[self.start : self.end]

    def _get_line(self) -> tuple[str, int, int]:
        start = self.start
        while start > 0 and self.source[start - 1] != "\n":
            start -= 1
        end = self.end
        while end < len(self.source) and self.source[end] != "\n":
            end += 1

        return (self.source[start:end], start, end)

    def get_underlined(self, error_message="", padding=0) -> str:
        line, start, _ = self._get_line()
        line = f"'{line}'"
        line += "\n"
        line += " " * (padding + 1)  # 1 for '
        line += " " * (self.start - start)
        if _is_terminal:
            line += ANSIColor.RED
        line += "^" * (self.end - self.start)
        line += error_message
        if _is_terminal:
            line += ANSIColor.END
        return line
