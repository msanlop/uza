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
if x > 10 {
  println("Large")
}
else {
  println("Small")
}
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
String interpolations with a syntax similar to Python:
```go
const name = "Jane"
const age = 33
println(f"{name} is {age.toString()} years old.")
```

While the `print` and `println` functions have overload for primitive types, string interpolation values
must first be converted to a string.

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
- Structs
- Closures, lambda functions
- Generics and overloading for user functions
- Iterators
- Maps
- Modules, stdlib
- JIT, add jitting to the VM or try using RPython
- it never ends...
