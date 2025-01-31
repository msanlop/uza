from __future__ import annotations
from dataclasses import field
from typing import List
from functools import reduce
from uzac.token import *


@dataclass(frozen=True)
class Type:
    """
    A uza Type.
    """

    def resolve_type(self, substitution) -> Type:
        """
        If type is SymbolicType, flatten the map to find the final type. Otherwise
        returns self for any other concrete type.
        For example with substitution {a: b, b: int}: a.resolve_type = int

        This allows for easy flattening of symbolic types without having to check
        and if/else every time for SymbolicTypes.
        TODO: see if avoiding useless function calls by checking has significant better perf

        Args:
            substitution Substitution:

        Returns:
            Type: Type
        """
        return self

    def __or__(self, that: object) -> bool:
        if Type.matches(self, that):
            return self
        if isinstance(that, UnionType):
            return UnionType(self, that.types)
        if issubclass(Type, that.__class__):
            return that | self
        if isinstance(that, Type):
            return UnionType(self, that)
        raise NotImplementedError(f"for {self} | {that}")

    def __contains__(self, that: object):
        if issubclass(that.__class__, Type):
            return False
        raise NotImplementedError

    @staticmethod
    def matches(a: Type, b: Type):
        if isinstance(b, UnionType):
            if isinstance(a, UnionType):
                return a in b
            return a in b
        return a == b


@dataclass(frozen=True, eq=True)
class UnionType(Type):
    """
    Represents a union type.
    """

    types: List[Type] = field(init=False)

    def __init__(self, *types: List[Type]) -> None:
        object.__setattr__(self, "types", types)

    def __str__(self) -> str:
        union = " | ".join(str(t) for t in self.types)
        return union

    def __eq__(self, that: object) -> bool:
        if isinstance(that, UnionType):
            for own, their in zip(self.types, that.types):
                if own not in that.types:
                    return False
                if their not in self.types:
                    return False
            return True
        if issubclass(that.__class__, Type):
            return False
        raise NotImplementedError

    def __contains__(self, that: object):
        if isinstance(that, self.__class__):
            return all(map(lambda t: t in self.types, that.types))
        if issubclass(that.__class__, Type):
            return that in self.types
        raise NotImplementedError

    def __or__(self, that: object) -> bool:
        if isinstance(that, Type):
            return UnionType(*self.types, that)
        if isinstance(that, UnionType):
            return UnionType(self.types, that.types)
        raise NotImplementedError


@dataclass(frozen=True, eq=True)
class ArrowType(Type):
    """
    An arrow type takes in a type and returns another type.
    """

    param_types: list[Type]
    return_type: Type

    def __str__(self) -> str:
        return f"({', '.join((str(p) for p in self.param_types))}) -> {str(self.return_type)}"


@dataclass(frozen=True, eq=True)
class BuiltInType(Type):
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


@dataclass(frozen=True)
class NonInferableType(Type):
    """
    Type cannot be inferred.
    """


_builtin_types: dict[str, BuiltInType] = {}
type_int = BuiltInType("int", _builtin_types)
type_float = BuiltInType("float", _builtin_types)
type_string = BuiltInType("string", _builtin_types)
type_bool = BuiltInType("bool", _builtin_types)
type_void = BuiltInType("nil", _builtin_types)
type_list_int = BuiltInType("List<int>", _builtin_types)
type_list_list_int = BuiltInType("List<List<int>>", _builtin_types)
type_list_string = BuiltInType("List<string>", _builtin_types)
type_list_float = BuiltInType("List<float>", _builtin_types)
type_list_bool = BuiltInType("List<bool>", _builtin_types)


_python_to_uza = {
    int: type_int,
    float: type_float,
    str: type_string,
    bool: type_bool,
    None: type_void,
    "nil": type_void,
}

_id_to_uza = {
    "int": type_int,
    "float": type_float,
    "string": type_string,
    "bool": type_bool,
    "void": type_void,
    "nil": type_void,
    "List<int>": type_list_int,
    "List<List<int>>": type_list_list_int,
    "List<bool>": type_list_bool,
    "List<string>": type_list_string,
    "List<float>": type_list_float,
}


def python_type_to_uza_type(type_) -> BuiltInType:
    if type_ == type_void:
        return type_
    return _python_to_uza.get(type_)


def identifier_to_uza_type(identifier: Token) -> BuiltInType:
    assert identifier.kind == token_identifier
    return _id_to_uza[identifier.repr]


# class UzaType:

#     def to_type(type_ : Token) -> int :
#         assert type_.kind == token_identifier
#         return UzaType._uza_to_enum.get(type_.repr)
