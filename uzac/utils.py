from __future__ import annotations
from collections import deque
from dataclasses import dataclass
from enum import Enum
import sys
from typing import List, Optional, TypeVar


class ANSIColor(Enum):
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
        return ANSIColor.BOLD.value + string + ANSIColor.END.value
    return string


def in_color(string: str, color: ANSIColor) -> str:
    if _is_terminal:
        return color.value + string + ANSIColor.END.value
    return string


@dataclass(frozen=True)
class Span:
    start: int
    end: int
    source: str

    @staticmethod
    def from_list(spanned_object_list, empty_case: Optional[Span] = None) -> Span:
        """
        Returns the span of the list of spanned objects.

        Args:
            spanned_object_list (List[_ObjectWithSpan_]): list
            empty_case (Optional[Span], optional): A span to default if the list
            is empty. Defaults to None. Example: if list of function arguments
            is empty, sensible default would be the span of the function
            identifier or the '(' token.
        """
        if len(spanned_object_list) == 0:
            return empty_case
        return spanned_object_list[0].span + spanned_object_list[-1].span

    def __get_line(self) -> tuple[str, int, int]:
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
        source, start, _ = self.__get_line()
        lines = source.split("\n")
        source = f"'{source}'"
        source += "\n"
        if _is_terminal:
            source += ANSIColor.RED.value
        if len(lines) > 1:
            source += "^" * (max((len(l) for l in lines)) + padding)
        else:
            source += " " * (padding + 1)  # 1 for '
            source += " " * (self.start - start)
            source += "^" * (self.end - self.start)
        source += f" {error_message}\n"
        if _is_terminal:
            source += ANSIColor.END.value
        return source

    def __add__(self, that: object) -> Span:
        if not isinstance(that, Span):
            raise NotImplementedError(f"Can't add {that} to Span {self}")
        # assert self.source == that.source
        return Span(self.start, that.end, self.source)

    def __repr__(self) -> str:
        return f"Span({self.start, self.end, self.get_source()})"


T = TypeVar("T")


@dataclass
class Symbol:
    """
    An uza program symbol.
    """

    key: str
    val: T


class SymbolTable:
    """
    Symbol table that keeps track of the defined symbols for each stack frame.
    """

    # List of frames, each frame contains list of symbols
    __frames: List[List[Symbol]]

    def __init__(self, frames: List[List[Symbol]] | None = None) -> None:
        if not frames:
            self.__frames: List[List[Symbol]] = [[]]
        else:
            self.__frames = frames

    def __get_locals(self) -> List[Symbol]:
        return self.__frames[-1]

    def new_frame(self) -> SymbolTable:
        self.__frames.append([])
        return self

    def pop_frame(self) -> SymbolTable:
        self.__frames = self.__frames[:-1]

    def define(self, variable_name: str, value: T, false_if_defined=False) -> bool:
        frame_locals = self.__get_locals()
        for symbol in frame_locals:
            if symbol.key == variable_name:
                if false_if_defined:
                    return False
                symbol.val = value
                return True

        frame_locals.append(Symbol(variable_name, value))
        return True

    def get(self, identifier: str) -> Optional[T]:
        idx = len(self.__frames) - 1
        while idx >= 0:
            frame = self.__frames[idx]
            for symbol in frame:
                if symbol.key == identifier:
                    return symbol.val
            idx -= 1

        return None

    def reassign(self, identifier: str, new_value: T) -> None:
        idx = len(self.__frames) - 1
        while idx >= 0:
            frame = self.__frames[idx]
            for j in range(len(frame)):
                if frame[j].key == identifier:
                    frame[j].val = new_value
                    return
            idx -= 1

        raise NameError(f"{identifier} not defined in scope")

    def __enter__(self):
        """
        self.new_frame is called from outside
        """
        pass

    def __exit__(self, type, value, traceback):
        self.pop_frame()


@dataclass
class UzaException(Exception):
    span: Span
    message_underline: str

    def get_error_message(self):
        prefix = in_color(in_bold(self.__class__.__name__), ANSIColor.RED)
        return self.span.get_underlined(
            prefix + in_color(f": {self.message_underline}", ANSIColor.RED)
        )


class UzaSyntaxError(UzaException):
    pass


class UzaNameError(UzaException):
    pass


class UzaTypeError(UzaException):
    pass
