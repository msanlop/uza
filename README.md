Table of contents
---

<!--ts-->
   * [Introduction](#uza)
   * [Language Tour](#language-tour)
   * [Usage](#usage)
   * [Installation-and-build](#installation-and-build)
      * [Venv install](#venv-install)
      * [Global install](#global-pip-install)
      * [Build from source](#build-from-source)
          * [Testing](#testing)
   * [Benchmark](#benchmark)
   * [TODO](#todo)
<!--te-->


# Uza
Uza is a small statically typed programming language.
This repo features an uza compiler/interpreter written in Python in the `uzac` directory. It also features a garbage collected virtual machine, based on the second part of Bob Nystrom's [Crafting Interpreters](https://craftinginterpreters.com/), in the `vm` directory.


Here is an example of an uza program:
```go
func fib(n : int) => int {
    if n <= 1 then return n
    return fib(n-1) + fib(n-2)
}

const n = 30
println("The 30th fibonacci number is " + fib(30).toString())
```

# Language Tour

## Variables

Variables use the `var` keyword and take an optional type:
```go
var count: int = 42
var str = "hello world" // 'string' type inferred
```

Constants are declared using `const` and cannot be reassigned:
```go
const G = 10.0

G = 9.81 // FAILS: UzaTypeError: cannot reassign const variable 'G'
```

## Blocks
Blocks statements allow for creation of a new scope.
```go
var i = 0
{
  var i = 42
  const foo = "unused"
  println(i) // 42
}
println(i) // 0
println(foo) // UzaNameError: variable `foo` not defined in this scope
```

## Functions
Functions are defined using `func` and must be typed:

```go
func add(a: int, b: int) => int {
    return a + b
}
```

Functions that have a void return type always return `nil`:

```go
func printMessage() => void {
    print("Hello, World!")
}

print(printMessage)//Hello, World!nil
```

## Lists
Lists are dynamic arrays and can take a generic type. A List instead can be
constructed with `List<type>()`.

```go
var numbers: List<int> = List<int>()
numbers.append(1)
numbers.append(42)

println(numbers.len()) // 2
println(numbers) // [1, 42]

numbers.set(0, 97)
println(numbers) // [97, 42]

const DESCENDING = false
numbers.sort(DESCENDING)
println(numbers) // [42, 97]
```

---

## Control Flow

### Conditionals

```go
const x = 15
if x > 10 {
  println("Large") // Large
}
else {
  println("Small")
}

println(2 > 1 and true) // true

println(not (false or true)) // false
```

`If` statements can also take a single expression/statement instead of a
block by using the `then` keyword:
```go
const x = 7

if x > 10 then println("Large")
else if x > 5 then println("Medium") // Medium
else println("Small")

// identical to:
if x > 10 then
  println("Large")
else if x > 5 then
  println("Medium") // Medium
else
  println("Small")
```

### Loops

For loops are take in three optional statements:
- A initializer, that is run before the first iteration.
- A conditional, that is checked every iteration.
- And a statement that is run after each iteration.

```go
for var i = 0; i < 3; i += 1 {
    println(i)
}
```

While loops only take a conditional that evaluates to a `boolean`:
```scala
var count = 0
while count < 10 {
  count += 1
}
```

Like `if` statments, `while` and `for` loops can take in a block, or a single
expression or statment using the `do` keyword:

```go
println("pair numbers in [0, 10]: ")
for var i = 0; i <= 10; i += 2 do println(i)
```
---

## Unit Conversions

### `toInt` and `toFloat`
```go
const i: int = 1
const f: float = i + 0.5 // implicit conversion of i to float
println(f) // 1.5


const str = "1.6"
const bigger = str.toFloat()
println(bigger > f) // true

//truncate int
println(bigger.toInt() < f) // true
```
### `toString`
```go
const number = 42
println(number.toString() + "24") // 4224
```

### Scientific notation
```go
const str = "1.5E9"
const scientific = str.toFloat()
println(scientific)                          // 1500000000.000
println(scientific.toInt() == 1_500_000_000) // true
```

## String Handling

### String Concatenation

```go
var message = "Hello, " + "World!"
```

### Substrings
```go
const str = "aldskfjldjaflj Hello, world!"

var i = 0
while str.get(i) != " " do i += 1

println(str.substring(i + 1, str.len())) // Hello world!
```

### f-strings
String interpolations, with a syntax similar to Python:
```go
const name = "Jane"
const age = 33
println(f"{name} is {age.toString()} years old.")
```

## Utils
Other useful functions:
```go
const foo: float = abs(3.14)

print("hi")
flush() // flush stdout

const t: int = timeNs() // nanoseconds counter

const ms: int = timeMs() // milliseconds counter

const n: int = randInt(1000) // random value between 0 and N (excluded)

sleep(1000) // sleep thread for N ms
```
---
https://github.com/user-attachments/assets/88df8be4-6310-4c58-9edf-4bcea188dad4

Output of `examples/game_of_life.uza`, an implementation of [Conway's Game of Life](https://en.wikipedia.org/wiki/Conway's_Game_of_Life).
More examples are available in the `examples` directory.

# Usage
Compile and execute.
```bash
uza source.uza
```

Compile and execute from stdin.
```bash
echo 'println("hello world!")' | uza
```

Compile to bytecode. Execute bytecode without compilation step.
```bash
uza source.uza -c // Wrote X bytes to code.uzb
uza code.uzb
```

Interpret without VM installed (slow execution)
```bash
uza source.uza -i
```

For more options:
```bash
uza --help
```


# Installation and Build
> [!NOTE]
> Uza is a personal learning project and not meant for production use.
> Unless you like a challenge :^)

> [!WARNING]
> There are no official prebuilt binaries for Linux and Windows on ARM64 or ARMv7. You will need to build from source for these architectures.



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

# Benchmark

This microbenchmark should be taken with a grain of salt. It's not a good representation of the overall speed of each language and interpreter. The only reason I include this is because I like comparing performance and looking at charts :).

This benchmark runs a recursive fibonacci function to compute the 35th fibonacci number. The benchmark code can be found in `examples/fibonacci_bench.uza`.
The following interpreters were tested:
- **uza (pypy)**: A tree-walk uza interpreter running on PyPy, a JIT implementation of Python. (Running `uza` with the `-i` flag)
- **uza**: `Uza` running the bytecode VM in the `vm` directory
- **clox**: [A `Lox` bytecode interpreter](https://github.com/munificent/craftinginterpreters). The VM implementation is similar to the VM in this repo
- **python3.12**: The reference Python implementation
- **pypy3.10**: JIT implementation of Python

![A chart showing different languages speeds on a fibonacci benchark, including very slow uza with pypy](./res/fib_bench_0.png)

The chart above shows just how slow the tree-walk approach is. Running a tree-walk interpreter of uza, inside pypy is orders of magnitude slower than running a C bytecode interpreter, or running a JIT with pypy. Running the same benchmark with a tree-walk interpreter inside of CPython instead of PyPy would probably take minutes!

![A chart showing different languages speeds on a fibonacci benchark](./res/fib_bench_1.png)

Taking a closer look at other values, we notice similar performance for the bytecode interpreters.
We might the uza would perform better than Lox and Python, since it is staically typed, but the current VM implementation is still very close to the `clox` one. There are still quite a few runtime type checks, which could be avoided by emiting more specialized opcodes. For example, instead of having a single `OP_ADD` for additions, the compiler could emit `OP_IADD`, `OP_FADD`, and `OP_STRCONCAT` to separately handle integer, float and string additions respectively. Implicit integer conversions when adding integers to floats would also have to be handled at compile-time instead of runtime by emitting `OP_ITOF` for example — analogous to the JVM's `i2f` instruction — as the current `OP_TOINT` does runtime checks for the base type.
The compiler also does zero optimisations on the AST, so that's anothing thing to explore.

PyPy's JIT shows an incredible, almost 10x improvement over CPython in this benchmark. Note that in real-world cases, the [average speedup is closer to 2.9x](https://speed.pypy.org/). It'll be interesting to see how the new CPython JIT will fare in comparaison to PyPy in the coming versions.


# TODO
- Structs
- Closures, lambda functions
- Generics and overloading for user functions
- Iterators
- Maps
- Modules, stdlib
- JIT, add jitting to the VM or try using RPython
- it never ends...
