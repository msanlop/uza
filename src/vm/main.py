import ctypes
from os.path import dirname, join
import sys
from importlib import resources

from uza.bytecode import ByteCodeProgramSerializer

LIB_NAME = "vm"
# LIB_DIR = join(dirname(dirname(dirname(__file__))), "build", "lib")


def load_shared_library(directory, lib_name):
    if sys.platform.startswith("win"):
        filename = f"{lib_name}.dll"
    elif sys.platform == "darwin":
        directory = join("/", "usr", "local", "lib")
        filename = f"lib{lib_name}.dylib"
    else:
        filename = f"lib{lib_name}.so"

    lib_path = join("lib", filename)
    try:
        return ctypes.CDLL(lib_path)
    except OSError as e:
        print(f"Could not load {lib_path}: {e}")
        sys.exit(1)


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
