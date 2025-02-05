# Uza
Uza is a simple statically typed programming language, that takes inspiration from Scala and Python.
This repo features an uza compiler/interpreter written in Python in the `uzac` directory, as well as a custom Virtual Machine written in C in the `vm` directory.

Here is fibonacci in uza:
```go
func fib(n : int) => int {
    if n <= 1 then return n
    return fib(n-1) + fib(n-2)
}

const n = 30
println(f"fib({toString(n)}) = {toString(fib(n))}")
```

# Overview
Uza has 5 primitive types:
```go
nil      // null/None type
42       // int, 64 bit
3.14     // float, double precision
true     // bool
"hello"  // string
```

There is also a `List` type and `func[_func_name_]` function type.

The typechecker has partial type inference.
Functions signatures must be type annotated and generic type variable declarations must be annotated too — for example `const foo = List()` => `const foo: List<int> = List()`.
```go
const foo = "hello world"
println(foo * 2)

// at 'println(foo * 2)'
//             ^^^Expected int but found string
```

There are no implicit conversions in uza.

```go
func halve(n: float) => float {
    return n / 2
}
const foo = 1

println(halve(foo))
// at 'println(halve(foo))'
//                   ^^^^ Error: Expected type 'float' but found 'int'

println(halve(toFloat(foo))) // 0.5
```


More examples are available in the `examples` directory.

# Installation and Build
> [!NOTE]
> Uza is a personal learning project and not meant for production use.
> Unless you like a challenge :^)


The main way to install uza is through `pip`, Python's package manager.
Installing in a `venv` removes the need to edit the PATH but requires the `venv` to be active to use uza.

## `venv` install
The `venv` environement has to be active to run uza.
#### UNIX shell
```bash
python3 -m venv venv
source ./venv/bin/activate
pip install uza
uza --help
```

#### Powershell
```powershell
python3 -m venv venv
venv\Scripts\activate
pip install uza
uza --help
```

## global `pip` install
#### UNIX
```bash
pip install uza
uza --help
```

#### Windows
```powershell
pip install uza --force-reinstall --user
uza --help
```

You might get one of the following warnings when installing uza globally:

```bash
WARNING: The script uza is installed in '/opt/homebrew/Cellar/pypy3.10/7.3.17_1/libexec/bin' which is not on PATH.
Consider adding this directory to PATH or, if you prefer to suppress this warning, use --no-warn-script-location.
NOTE: The current PATH contains path(s) starting with `~`, which may not be expanded by all applications.

------------------

WARNING: The script uza is installed in '/home/smith/.local/bin' which is not on PATH.
Consider adding this directory to PATH or, if you prefer to suppress this warning, use --no-warn-script-location.

------------------

But still not in path so you have to   WARNING: The script uza.exe is installed in 'C:\Users\doe\AppData\Local\Packages\PythonSoftwareFoundation.Python.3.13_qbz5n2kfra8p0\LocalCache\local-packages\Python313\Scripts' which is not on PATH.
  Consider adding this directory to PATH or, if you prefer to suppress this warning, use --no-warn-script-location.
```

To use without adding to path:
```bash
python3 -m uzac --help
```

## Build from source
> [!NOTE]
> The python compiler also has a tree-walk interpret, using the `-i` flag, for which there is no need to compile the VM. To interpret uza in python, prefer using a python interpreter with a JIT such as `pypy3` for much better performance.

```bash
git clone git@github.com:msanlop/uza.git
cd uza
mkdir build && cd build
cmake ..
make
```

You can now run uza by executing `python uza` from root dir of the repo.
### Add local installation to path (UNIX)
```bash
printf "#!$(which python3)\n$(cat uza)" > uza
export PATH=$(pwd):$PATH
./uza --help
```
Export in shell config file, e.g. `~/.bashrc`, to persist across sessions.

### Testing
```bash
pip install -r requirements.txt
pytest
```

## TODO
- Generics
- Closures, lambda functions
- Structs, methods
- Iterators
- Maps
- Modules, stdlib
- JIT, convert the interpreter to RPython and see how well it performs
- it never ends...
