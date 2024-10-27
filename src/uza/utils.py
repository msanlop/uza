from __future__ import annotations
from collections import deque
from dataclasses import dataclass
import sys
from typing import TypeVar


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


def in_color(string: str, color: ANSIColor) -> str:
    if _is_terminal:
        return color + string + ANSIColor.END
    return string


@dataclass(frozen=True)
class Span:
    start: int
    end: int
    source: str

    def _get_line(self) -> tuple[str, int, int]:
        """
        Return the entire line for this span.
        """
        start = self.start
        while start > 0 and self.source[start - 1] != "\n":
            start -= 1
        end = self.end
        while end < len(self.source) and self.source[end] != "\n":
            end += 1

        return (self.source[start:end], start, end)

    def get_source(self) -> str:
        """
        Return the source code for this span.
        """
        return self.source[self.start : self.end]

    def get_underlined(self, error_message="", padding=0) -> str:
        """
        Return the source code line and underline the span with _error_message_.

        Args:
            error_message (str, optional): The error message. Defaults to "".
            padding (int, optional): To align with any indenting. Defaults to 0.

        Returns:
            str: _description_
        """
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

    def __add__(self, that: object) -> Span:
        if not isinstance(that, Span):
            return NotImplemented
        assert self.source == that.source
        return Span(self.start, that.end, self.source)


T = TypeVar("T")


class SymbolTable:
    """
    Symbol table that keeps track of the defined symbols for each stack frame.
    This class is used in in different contexts so the typevar T can take
    different types, e.g. type 'Value' for the interpret, or type 'bool' for
    the parser to keep track of symbols and const variables.

    _frames_ is queue of locals, a tuple with the context name and a dict with
    the (variable name and it's associated value) pairs.
    """

    frames: deque[tuple[str, dict[str, T]]]

    def __init__(self, frames: deque[tuple[str, dict[str, T]]] | None = None) -> None:
        if not frames:
            self.frames: deque[tuple[str, dict[str, T]]] = deque()
            self.frames.appendleft(("", {}))
        else:
            self.frames = frames

    def _get_locals(self) -> dict[str, T]:
        top_frame = self.frames[0]
        return top_frame[1]

    def with_new_frame(self, context_name: str, frame: dict[str, T]) -> SymbolTable:
        new_frames = deque((*self.frames, (context_name, frame)))
        return SymbolTable(new_frames)

    def define(self, variable_name: str, value: T) -> bool:
        """
        Tries to define the identifier with the value. Return true if succeeds,
        false if the given variable name is already been defined in this scope.
        """
        frame_locals = self._get_locals()
        already_defined_in_scope = frame_locals.get(variable_name)
        if already_defined_in_scope:
            return False

        frame_locals[variable_name] = value
        return True

    def get(self, identifier: str) -> T:
        for frame in self.frames:
            frame_locals = frame[1]
            value = frame_locals.get(identifier)
            if value is not None:
                return value
        raise NameError(f'"{identifier}" has not been defined')

    def reassign(self, identifier: str, new_value: T) -> None:
        frame_locals = self._get_locals()
        frame_locals[identifier] = new_value
