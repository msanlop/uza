import ctypes
import importlib.resources
from os.path import dirname, join
import sys
import importlib

from uza.bytecode import ByteCodeProgramSerializer

LIB_NAME = "vm"


def load_shared_library(directory, lib_name):
    folder = "lib"
    if sys.platform.startswith("win"):
        filenames = [f"{lib_name}.dll", f"{lib_name}.dll"]
        folder = "bin"
    elif sys.platform == "darwin":
        filenames = [f"lib{lib_name}.dylib"]
    else:
        filenames = [f"lib{lib_name}.so"]

    for fn in filenames:
        lib_path = join(dirname(__file__), folder, fn)
        try:
            return ctypes.CDLL(lib_path)
        except OSError as e:
            pass
    print(f"Could not load lib{lib_name}", file=sys.stderr)
    exit(1)


vm_ = load_shared_library("", LIB_NAME)
vm_.run_vm.argtypes = (ctypes.c_int, ctypes.c_char_p)


def run_vm(program: ByteCodeProgramSerializer):
    """
    Runs the vm with the given bytecode.

    Args:
        num_bytes (int): size of bytes
        code (bytes): _description_

    Returns:
        _type_: _description_
    """
    code = program.get_bytes()
    byte_buff = ctypes.create_string_buffer(code)
    return vm_.run_vm(ctypes.c_int(len(code)), byte_buff)
