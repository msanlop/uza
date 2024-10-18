from __future__ import annotations
from dataclasses import dataclass


@dataclass(frozen=True)
class Span:
    start: int
    end: int
    source: str

    def __add__(self, that: object) -> Span:
        if not isinstance(that, Span):
            return NotImplemented
        assert(self.source == that.source)
        return Span(self.start, that.end, self.source)
    
    def get_source(self) -> str:
        return self.source[self.start: self.end]

