from __future__ import annotations
from dataclasses import dataclass, field
from operator import (
    add,
    and_,
    eq,
    ge,
    gt,
    le,
    lt,
    mod,
    mul,
    ne,
    not_,
    or_,
    pow,
    truediv,
)
import random
import sys
import time
from typing import Callable, List, Optional
from uzac.type import (
    ArrowType,
    GenericType,
    NonInferableType,
    type_bool,
    type_int,
    type_list,
    type_list_class,
    type_generic_meta,
    type_float,
    type_string,
    type_list_int,
    type_list_float,
    type_void,
)

from uzac.ast import Identifier, Value

_builtins: dict[str, BuiltIn] = {}


def get_builtin(identifier: Identifier) -> Optional[BuiltIn]:
    """
    Returns a _BuiltIn_ with the given who's name matches the _identifier_
    if it exists.
    """
    return _builtins.get(identifier.name)


@dataclass(frozen=True)
class BuiltIn:
    """
    A BuiltIn is a function that is part of the standard library.
    """

    identifier: str
    interpret: Callable[..., Value]  # tree walk interpretation in python
    type_signatures: List[ArrowType]  # len == 1 if no overloads
    arity: int = field(init=False)
    is_op_code: bool = field(
        default=False
    )  # if true, emits specific opcode instead of CALL_NATIVE
    type_not_inferrable: bool = field(default=False)

    def __post_init__(self):
        # adds itself to the dict that holds all the builtins
        _builtins[self.identifier] = self
        object.__setattr__(self, "arity", len(self.type_signatures[0].param_types))

    def __str__(self) -> str:
        return f"BuiltIn({self.identifier}, {self.type_signatures})"


# ARITHMETIC FUNCTIONS

__bi_arith_types = [
    ArrowType([type_int, type_int], type_int),
    ArrowType([type_float, type_float], type_float),
    ArrowType([type_int, type_float], type_float),
    ArrowType([type_float, type_int], type_float),
]
__bi_string_concat = ArrowType([type_string, type_string], type_string)

bi_add = BuiltIn("+", add, [*__bi_arith_types, __bi_string_concat])


def __sub_or_neg(*args):
    if len(args) == 1:
        return -args[0]
    return args[0] - args[1]


__identity_int_float_types = [
    ArrowType([type_int], type_int),
    ArrowType([type_float], type_float),
]

bi_sub = BuiltIn(
    "-",
    __sub_or_neg,
    __bi_arith_types + __identity_int_float_types,
)
bi_mul = BuiltIn("*", mul, __bi_arith_types)
bi_div = BuiltIn("/", truediv, __bi_arith_types)
bi_mod = BuiltIn("%", mod, [ArrowType([type_int, type_int], type_int)])
bi_pow = BuiltIn("**", pow, __bi_arith_types)
bi_max = BuiltIn("max", max, __bi_arith_types)
bi_min = BuiltIn("min", min, __bi_arith_types)
bi_abs = BuiltIn("abs", abs, __identity_int_float_types)


# IO FUNCTIONS


def __lower_str_bool(func, **kwargs):
    """
    Hack to turn boolean strings into lower case
    """

    def decorated(*args):
        new_args = map(lambda a: str(a).lower() if isinstance(a, bool) else a, args)
        new_args = map(lambda a: "nil" if a is None else a, new_args)
        return func(*new_args, **kwargs)

    return decorated


__bi_print_types = [
    ArrowType([type_string], type_void),
    ArrowType([type_int], type_void),
    ArrowType([type_float], type_void),
    ArrowType([type_list], type_void),
    ArrowType([type_bool], type_void),
    ArrowType([type_void], type_void),
]

bi_print = BuiltIn("print", __lower_str_bool(print, end=""), __bi_print_types)
bi_println = BuiltIn("println", __lower_str_bool(print), __bi_print_types)
bi_flush = BuiltIn("flush", lambda: sys.stdout.flush(), [ArrowType([], type_void)])


def __read_file(file_name):
    with open(file_name) as file:
        return file.read()


bi_readAll = BuiltIn("readAll", __read_file, [ArrowType([type_string], type_string)])

# BOOLEAN STUFF

__bool_func_types = [
    ArrowType([type_bool, type_bool], type_bool),
    ArrowType([type_int, type_int], type_bool),
    ArrowType([type_string, type_string], type_bool),
    ArrowType([type_float, type_float], type_bool),
]
__bool_cmp_overloads = [
    ArrowType([type_int, type_int], type_bool),
    ArrowType([type_float, type_float], type_bool),
    ArrowType([type_int, type_float], type_bool),
    ArrowType([type_float, type_int], type_bool),
]

bi_and = BuiltIn("and", and_, __bool_func_types)
bi_or = BuiltIn("or", or_, __bool_func_types)
bi_eq = BuiltIn("==", eq, __bool_func_types)
bi_ne = BuiltIn("!=", ne, __bool_func_types)
bi_lt = BuiltIn("<", lt, __bool_cmp_overloads)
bi_le = BuiltIn("<=", le, __bool_cmp_overloads)
bi_gt = BuiltIn(">", gt, __bool_cmp_overloads)
bi_ge = BuiltIn(">=", ge, __bool_cmp_overloads)

bi_not = BuiltIn("not", not_, [ArrowType([type_bool], type_bool)])

# TYPE CONVERSION FUNCTIONS


def __uza_to_int(arg):
    """
    toInt is supposed to parse an truncate ints from strings
    """
    try:
        return int(arg)
    except ValueError:
        return int(float(arg))


bi_to_int = BuiltIn(
    "toInt",
    __uza_to_int,
    [
        ArrowType([type_float], type_int),
        ArrowType([type_string], type_int),
        ArrowType([type_int], type_int),
    ],
    is_op_code=True,
)

bi_to_float = BuiltIn(
    "toFloat",
    float,
    [
        ArrowType([type_float], type_float),
        ArrowType([type_int], type_float),
        ArrowType([type_string], type_float),
    ],
    is_op_code=True,
)

bi_to_string = BuiltIn(
    "toString",
    str,
    [
        ArrowType([type_int], type_string),
        ArrowType([type_float], type_string),
        ArrowType([type_string], type_string),
    ],
    is_op_code=True,
)


bi_new_list = BuiltIn(
    "List",
    list,
    [
        ArrowType([], GenericType(type_list_class, NonInferableType())),
    ],
    type_not_inferrable=True,
)
bi_len = BuiltIn(
    "len",
    len,
    [
        ArrowType([type_string], type_int),
        ArrowType([type_list], type_int),
    ],
)
bi_append = BuiltIn(
    "append",
    list.append,
    [
        ArrowType([type_list, type_generic_meta], type_void),
    ],
)
bi_get = BuiltIn(
    "get",
    lambda l, i: l[i],
    [
        ArrowType([type_list, type_int], type_generic_meta),
        ArrowType([type_string, type_int], type_string),
    ],
)


def __interpreter_set(value, idx, val):
    value[idx] = val


bi_get = BuiltIn(
    "set",
    __interpreter_set,
    [
        ArrowType([type_list, type_int, type_generic_meta], type_void),
    ],
)

bi_substring = BuiltIn(
    "substring",
    lambda l, start, end: l[start:end],
    [
        ArrowType([type_string, type_int, type_int], type_string),
    ],
)

bi_sort = BuiltIn(
    "sort",
    lambda l, rev: l.sort(reverse=rev),
    [
        ArrowType([type_list_int, type_bool], type_void),
        ArrowType([type_list_float, type_bool], type_void),
    ],
)


# def __del_item(array, idx):
#     del array[idx]


# bi_append = BuiltIn(
#     "removeAt", __del_item, [ArrowType([type_list, type_int], type_void)]
# )
# bi_append = BuiltIn("copy", list.copy, [ArrowType([type_list], type_list)])

bi_time_ns = BuiltIn(
    "timeNs",
    time.perf_counter_ns,
    [
        ArrowType([], type_int),
    ],
)

bi_time_ms = BuiltIn(
    "timeMs",
    lambda: time.perf_counter_ns() // 1_000_000,
    [
        ArrowType([], type_int),
    ],
)

bi_rand_int = BuiltIn(
    "randInt",
    lambda n: random.randint(0, n),
    [
        ArrowType([type_int], type_int),
    ],
)

bi_sleep = BuiltIn(
    "sleep",
    lambda m: time.sleep(m),
    [
        ArrowType([type_int], type_void),
    ],
)
