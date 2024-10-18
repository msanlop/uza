from __future__ import annotations
from typing import List

from ..token import *


@dataclass(frozen=True)
class Type:
    identifier: str

@dataclass(frozen=True, eq=True)
class UnionType(Type):
    types: List[Type]
    
    def __init__(self, *types: List[Type]) -> None:
        super().__init__("union")
        object.__setattr__(self, 'types', types)
    
    def __str__(self) -> str:
        union = " | ".join(str(t) for t in self.types)
        return f"{union}"
    
    def __repr__(self) -> str:
        union = "|".join(str(t) for t in self.types)
        return f"{UnionType.__name__}({union})"

    def __eq__(self, that: object) -> bool:
        if not isinstance(that, UnionType):
            return NotImplemented
        return all(a == b for (a,b) in zip(self.types, that.types))
    
    def __add__(self, that: object) -> bool:
        if isinstance(that, BuiltInType):
            return UnionType(*self.types, that)
        if isinstance(that, UnionType):
            return UnionType(self.types, that.types)
        if not isinstance(that, Type):
            return NotImplemented

@dataclass(frozen=True)
class BuiltInType:
    """
    A BuiltInType is a type that is part of the standard library.
    """

    identifier: str
    _builtins_dict: dict[str, Type]

    def __post_init__(self):
        """adds itself to the dict that holds all the builtin types"""
        self._builtins_dict[self.identifier] = self

    def __str__(self) -> str:
        return self.identifier

    def __repr__(self) -> str:
        return f"{BuiltInType.__name__}({self.identifier})"

_builtin_types: dict[str, BuiltInType] = {}
type_int = BuiltInType("int", _builtin_types)
type_float = BuiltInType("float", _builtin_types)
type_string = BuiltInType("string", _builtin_types)
type_bool = BuiltInType("bool", _builtin_types)
type_void = BuiltInType("void", _builtin_types)


_python_to_uza = {
    int: type_int,
    float: type_float,
    str: type_string,
    bool: type_bool,
    None: type_void
}

_id_to_uza = {
    "int" : type_int,
    "float": type_float,
    "string": type_string,
    "bool": type_bool,
    "void": type_void,
}

def python_type_to_uza_type(type_) -> BuiltInType:
    return _python_to_uza[type_]

def identifier_to_uza_type(identifier : Token) -> BuiltInType:
    assert identifier.kind == token_identifier
    return _id_to_uza[identifier.repr]
    
# class UzaType:
    
#     def to_type(type_ : Token) -> int :
#         assert type_.kind == token_identifier
#         return UzaType._uza_to_enum.get(type_.repr)
