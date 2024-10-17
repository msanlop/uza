from __future__ import annotations
from dataclasses import dataclass


@dataclass(frozen=True)
class Span:
    start: int
    end: int

    def __add__(self, that: object) -> Span:
        if not isinstance(that, Span):
            return NotImplemented
        return Span(self.start, that.end)
