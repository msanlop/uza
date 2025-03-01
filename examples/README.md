# Examples

Since the is no syntax higlighting for `.uza` files, this is the next best thing, with approximative highlighting in markdown code blocks. Click on a header to expand the code.

<details open>
<summary>

## Fizz Buzz - `fizzbuzz.uza`
</summary>

```go
for var i = 0; i <= 100; i += 1 {
    var temp = ""
    if i % 3 == 0 then temp += "Fizz"
    else if i % 5 == 0 then temp += "Buzz"
    else temp += toString(i)
    println(temp)
}
```

</details>
<details>
<summary>

## Fibonacci - `fibonacci_variants.uza`
</summary>

```go
func fib(n : int) => int {
    if n <= 1 then return n
    return fib(n-1) + fib(n-2)
}

func fibTailRec(n : int, prev: int, curr: int) => int {
    if n == 0 then return prev
    if n == 1 then return curr
    return fibTailRec(n-1, curr, prev + curr)
}

func fibLoop(n : int) => int {
    if n < 2 then return n
    var a = 0
    var b = 1
    for var i = 0; i < n - 1; i+= 1 {
        const temp = a + b
        a = b
        b = temp
    }
    return b
}

const n = 35
const start = timeMs()
const res = fib(n)
println(res == 9227465)
const delta = timeMs() - start
println(delta.toString() + "ms")

//const res = fibTailRec(n, 0, 1)
println(f"fib({toString(n)}) = {toString(res)}")
```

</details>

<details>

<summary>

## Conway's Game of Life - `game_of_life.uza`
</summary>

```go
// CONWAY'S GAME OF LIFE //

///////// SETTINGS /////////
const TARGET_FRAME_TIME = 40
const LIMIT_FRAME = true // unset if using -i flag, or big canvas dimension


// if set to true, the output string is built and printed all at once rather than
// printed char by char. This will probably be smoother in general, although costly
// with with 1 allocation per pexel (no StringBuilder...).
// If the platform buffer stdout prints and the terminal emulator is fast enough,
// then setting to false will allow better performance.
const PREFER_SMOOTHER_OUTPUT = true

// STARTING SPAWN ODDS
const SPAWN_ODDS = 20 // (SPAWN_ODDS / 100) %

// DIMENSIONS
const MAX_X = 80
const MAX_Y = 20
////////////////////////////


const TERMINAL_CLEAR = "\033[2J"
const TERMINAL_MOVE_HOME = "\033[H"

func initCells(cells: List<bool>) => void {
    for var c = 0; c < (MAX_X * MAX_Y); c += 1 {
        const v = randInt(SPAWN_ODDS)
        if v <= 3 then cells.append(true)
        else cells.append(false)
    }
}


func isInside(x: int, y: int) => bool {
    return (x >= 0) and (x < MAX_X) and (y >= 0) and (y < MAX_Y)
}

func transformCoords(x: int, y: int) => int {
    return (x % MAX_X) + (y * MAX_X)
}

func tryUpdate(cells: List<bool>, counts: List<int>, x: int, y: int, idx: int) => void {
   if isInside(x, y) and cells.get(transformCoords(x, y)) {
        counts.set(idx, counts.get(idx) + 1)
    }
}

func countNeighbours(cells: List<bool>, counts: List<int>) => void {
    for var y = 0; y < MAX_Y; y += 1 {
        for var x = 0; x < MAX_X; x += 1 {
            const cellIdx = transformCoords(x, y)
            counts.set(cellIdx, 0)

            // TOP
            tryUpdate(cells, counts, x - 1, y - 1, cellIdx)
            tryUpdate(cells, counts, x, y - 1, cellIdx)
            tryUpdate(cells, counts, x + 1, y - 1, cellIdx)

            // LEFT / RIGHT
            tryUpdate(cells, counts, x - 1, y, cellIdx)
            tryUpdate(cells, counts, x + 1, y, cellIdx)

            // BOTTOM
            tryUpdate(cells, counts, x - 1, y + 1, cellIdx)
            tryUpdate(cells, counts, x, y + 1, cellIdx)
            tryUpdate(cells, counts, x + 1, y + 1, cellIdx)
        }
    }
}

func updateCells(cells: List<bool>, counts: List<int>) => void {
    // Any live cell with fewer than two live neighbours dies, as if by underpopulation.
    // Any live cell with two or three live neighbours lives on to the next generation.
    // Any live cell with more than three live neighbours dies, as if by overpopulation.
    // Any dead cell with exactly three live neighbours becomes a live cell, as if by reproduction.

    for var c = 0; c < (MAX_X * MAX_Y); c += 1 {
        if cells.get(c) and counts.get(c) < 2 then {
            cells.set(c, false)
        }
        else if cells.get(c) and counts.get(c) > 3 then {
            cells.set(c, false)
        }
        else if (not cells.get(c)) and (counts.get(c) == 3) then {
            cells.set(c, true)
        }
    }
}

// print cells to stdout
func drawCells(cells: List<bool>) => void {
    print(TERMINAL_CLEAR + TERMINAL_MOVE_HOME)
    var alive = 0
    for var c = 0; c < (MAX_X * MAX_Y); c += 1 {
        if (c % MAX_X) == 0 then print("\n")
        if cells.get(c) then {
            alive += 1
            print("#")
        }
        else print(" ")
    }
    println("\n" + alive.toString() + " cells alive")
}

// build and return output
func getDrawCellsOutput(cells: List<bool>) => string {
    var out = (TERMINAL_CLEAR + TERMINAL_MOVE_HOME)
    var alive = 0
    for var c = 0; c < (MAX_X * MAX_Y); c += 1 {
        if (c % MAX_X) == 0 then out += ("\n")
        if cells.get(c) then {
            alive += 1
            out += ("#")
        }
        else out += (" ")
    }
    out += f"\n{alive.toString()} cells alive\n"
    return out
}


func main() => void {
    var cells = List<bool>()
    initCells(cells)
    const NEIGHBOURS = List<int>()
    for var c = 0; c < (MAX_X * MAX_Y); c += 1 {
        NEIGHBOURS.append(0)
    }
    if PREFER_SMOOTHER_OUTPUT then print(getDrawCellsOutput(cells))
    else drawCells(cells)

    var iter = 0
    const MAX_ITER = 10_000
    var prevFrame = 0
    while iter < MAX_ITER {
        const frameStart = timeMs()

        countNeighbours(cells, NEIGHBOURS)
        updateCells(cells, NEIGHBOURS)

        var out = ""
        if PREFER_SMOOTHER_OUTPUT then out = getDrawCellsOutput(cells)
        else drawCells(cells)
        out += f"frametime: {prevFrame.toString()}ms\n"
        out += f"tick #{iter.toString()}\n"
        print(out)
        flush()

        if (LIMIT_FRAME) then
            while (timeMs() - frameStart) - 1 <= TARGET_FRAME_TIME do sleep(3)

        prevFrame = timeMs() - frameStart
        iter += 1
    }
}

main()

```
</details>
<details>
<summary>

## advent of code 2024, day 1 - `aoc_2024_1.uza`
</summary>

```go

const input_str = "3   4
4   3
2   5
1   3
3   9
3   3"

const list_left = List<int>()
const list_right = List<int>()

func parse_lines(input: string) => List<string> {
    var start: int = 0
    var end: int = 0
    const lines: List<string> = List<string>()
    const input_len = input.len()
    while end < input_len {
        while ((end < input_len) and (input.get(end) != "\n")) {
            end+=1
        }
        lines.append(input.substring(start, end))
        start = end + 1
        end += 1
    }
    return lines
}

func parse_two_ints(line: string, l: List<int>, r: List<int>) => void {
    var start = 0
    var end = 0
    while (end < line.len()) and line.get(end) != " " do end += 1
    l.append(line.substring(start, end).toInt())

    while (end < line.len()) and line.get(end) == " " do end += 1 //clear gap
    start = end
    const line_len = line.len()
    while (end<line_len) and (line.get(end) != "\n") do end += 1
    r.append(line.substring(start, end).toInt())

}

const lines = parse_lines(input_str)
for var i = 0; i < lines.len(); i+=1
    do parse_two_ints(lines.get(i), list_left, list_right)
sort(list_left, false)
sort(list_right, false)

// SUM DIFFERENCES
var sum = 0
for var i = 0; i < list_left.len(); i+=1 {
    const diff = list_left.get(i) - list_right.get(i)
    sum += abs(diff)
}
print("Sum of differences is: ")
println(sum)

//DISGUSTING SIMILARITY SCORE
sum = 0
const pair_count = list_left.len()
var right_start = 0 // don't compare values we know are smaller
for var i = 0; i < pair_count; i+=1 {
    const curr = list_left.get(i)
    for var j = right_start; (j < pair_count); j+=1 {
        const right_num = list_right.get(j)
        if curr == right_num then {
            sum += right_num
        }
        if right_num < curr then right_start = j
    }
}

print("Similarity score is: ")
println(sum)
```
</details>
<details>
<summary>

## Advent of Code 2024, day 2 - `aoc_2024_2.uza`
</summary>

```go
const input_str = "7 6 4 2 1
1 2 7 8 9
9 7 6 2 1
1 3 2 4 5
8 6 4 4 1
1 3 6 7 9"
const levels: List<List<int>> = List<List<int>>()

func parse_lines(input: string) => List<string> {
    var start: int = 0
    var end: int = 0
    const lines: List<string> = List<string>()
    const input_len = input.len()
    while end < input_len {
        while ((end < input_len) and (input.get(end) != "\n")) do end+=1
        lines.append(input.substring(start, end))
        start = end + 1
        end += 1
    }
    return lines
}

func parse_ints(line: string, levels: List<List<int>>) => void {
    var start = 0
    var end = 0
    const line_len = line.len()
    const level: List<int> = List<int>()
    while end < line_len {
        for ;(end < line_len) and (line.get(end) != " "); do end += 1
        level.append(toInt(line.substring(start, end)))
        while (end < line_len) and (line.get(end) == " ") do end += 1
        start = end
    }
    levels.append(level)
}

func checkLevel(level: List<int>) => bool {
    const level_count = level.len()
    var increasing = false
    if (level.get(0) < level.get(1)) then increasing = true
    else increasing = false

    if increasing {
        for var i = 0; i < (level_count - 1); i+=1 {
            const delta = level.get(i + 1) - level.get(i)
            if (delta < 1) or (3 < delta) then return false
        }
        return true
    }
    else
        for var i = 0; i < (level_count - 1); i+=1 {
            const delta = level.get(i) - level.get(i + 1)
            if (delta < 1) or (3 < delta) then return false
        }
        return true
}


// have to reimplement some stuff
//func checkLevelWithDampener(level: List<int>) => bool {
//    const level_count = level.len()
//    if checkLevel(level) then return true
//
//    for var i=0; i < level_count; i+=1 {
//        const cpy = copy(level)
//        removeAt(cpy, i)
//        if checkLevel(cpy) then return true
//    }
//    return false
//}

const lines = parse_lines(input_str)
for var i = 0; i < lines.len(); i+=1 {
    parse_ints(lines.get(i), levels)
}

var sum1 = 0
var sum2 = 0
for var i = 0; i < levels.len(); i+=1 {
    if checkLevel(levels.get(i)) then sum1 += 1
    //if checkLevelWithDampener(levels.get(i)) then sum2 += 1
}

println("PART 1: the number of safe reports is " + toString(sum1))
//print("PART 2: the number of safe reports is: ") // have to reimplement stuff
//println(sum2)
```
</details>
<details>
<summary>

## Sorting algortihms - `sorting_algorithms.uza`
</summary>

```go
const QUICKSORT_INSERTION_BOUND = 12


// UTILS

func printSubArray(list: List<int>, from: int, until: int) => void {
    print("[")
    for ; from < until - 1; from += 1 {
        print(list.get(from))
        print(", ")
    }
    print(list.get(from))
    println("]")
}

func getRandomIntList(maxInt: int, size: int) => List<int> {
    const res = List<int>()
    for var i = 0; i < size; i += 1 {
        res.append(randInt(maxInt))
    }
    return res
}

func copyList(src: List<int>) => List<int> {
    const res = List<int>()
    for var i = 0; i < src.len(); i += 1 {
        res.append(src.get(i))
    }
    return res
}


// SORTING ALGORITHMS

func insertionSortRange(list: List<int>, from: int, until: int) => void {
    const listLen = until - 1
    for var i = from; i < listLen; i += 1 {
        for var j = i + 1; j > from; j = j - 1 {
            const prevIdx = j - 1
            const prev = list.get(prevIdx)
            if list.get(j) < list.get(prevIdx) {
                const temp = list.get(prevIdx)
                list.set(prevIdx, list.get(j))
                list.set(j, temp)
            } else {
                break
            }
        }
    }
}

func insertionSort(list: List<int>) => void {
    const length = list.len()
    insertionSortRange(list, 0, length)
}

func quickSortRange(list: List<int>, from: int, until: int) => void {
    if (until - from) < QUICKSORT_INSERTION_BOUND {
        insertionSortRange(list, from, until)
        return
    }

    const pivot = list.get(from)
    var pivotIdx = from
    for var i = from + 1; i < until; i += 1 {
        var cur = list.get(i)
        if cur < pivot {
            pivotIdx += 1
            list.set(i, list.get(pivotIdx))
            list.set(pivotIdx, cur)
        }
    }

    // put pivot in between sorted lists
    list.set(from, list.get(pivotIdx))
    list.set(pivotIdx, pivot)

    //println(f"WITH PIVOT: {pivot.toString()}: ")
    //printSubArray(list, from, pivotIdx)
    //println("")
    //printSubArray(list, pivotIdx, until)

    quickSortRange(list, from, pivotIdx)
    quickSortRange(list, pivotIdx + 1, until)
}

func quickSort(list: List<int>) => void {
    const length = list.len()
    quickSortRange(list, 0, length)
}

///////////

func main() => void {
    const MAX_INT = 100_000_000
    const LIST_LEN = 10_000
    const REPETITIONS = 5

    const lists: List<List<int>> = List<List<int>>()
    for var i = 0; i < REPETITIONS; i += 1 {
        lists.append(getRandomIntList(MAX_INT, LIST_LEN))
    }

    // INSERTION SORT
    var insertionTime = 0
    for var i = 0; i < REPETITIONS; i += 1 {
        const cpy = copyList(lists.get(i))
        const start = timeMs()
        insertionSort(cpy)
        const delta = timeMs() - start
        println(f"insertionSort took {delta.toString()}ms")
        insertionTime += delta
    }
    insertionTime = insertionTime / REPETITIONS
    println(f"insertionSort average of {REPETITIONS.toString()}: {insertionTime.toString()}ms\n\n")

    // QUICK SORT
    var quickSortTime = 0
    for var i = 0; i < REPETITIONS; i += 1 {
        const cpy = copyList(lists.get(i))
        const start = timeMs()
        quickSort(cpy)
        const delta = timeMs() - start
        println(f"quickSort took {delta.toString()}ms")
        quickSortTime += delta
    }
    quickSortTime = quickSortTime / REPETITIONS
    println(f"quickSort average of {REPETITIONS.toString()}: {quickSortTime.toString()}ms\n\n")

    // QSORT from C runtime
    var qsortTime = 0
    for var i = 0; i < REPETITIONS; i += 1 {
        const cpy = copyList(lists.get(i))
        const start = timeNs()
        sort(cpy, false)
        const delta = timeNs() - start
        println(f"sort took {toString(delta/1_000_000.0)}ms")
        qsortTime += delta
    }
    qsortTime = qsortTime / REPETITIONS
    println(f"sort average of {REPETITIONS.toString()}: {toString(qsortTime/1_000_000.0)}ms\n\n")

    const msg = f"With benchmark config:
        \tint range: [0, {MAX_INT.toString()})
        \tlist size: {LIST_LEN.toString()}"
    println(msg)
}

main()

// Results on Apple M4 CPU:

// insertionSort took 1423ms
// insertionSort took 1423ms
// insertionSort took 1501ms
// insertionSort took 1471ms
// insertionSort took 1436ms
// insertionSort average of 5: 1450ms
//
//
// quickSort took 7ms
// quickSort took 8ms
// quickSort took 7ms
// quickSort took 6ms
// quickSort took 6ms
// quickSort average of 5: 6ms
//
//
// sort took 0.459375ms
// sort took 0.476417ms
// sort took 0.430084ms
// sort took 0.433875ms
// sort took 0.510583ms
// sort average of 5: 0.462066ms
//
//
// With benchmark config:
//                 int range: [0, 100000000)
//                 list size: 10000
```
</details>
<details>
<summary>

## microbenchmark - `fibonacci_bench.uza`
</summary>

```go
const N = 35

func fib(n : int) => int {
    if n <= 1 then return n
    return fib(n-1) + fib(n-2)
}

func fibNTimes(n: int) => float {
    var tot: int = 0
    for var i = 0; i < n; i += 1{
        const start = timeMs()
        const res = fib(N)
        println(res == 9227465)
        const delta = timeMs() - start
        tot += delta
        println(delta.toString() + "ms")
    }
    return tot.toFloat() / n
}

const runs = 10
const mean = fibNTimes(runs)
println(f"average: {mean.toString()}")


// CLOX
//
// fun fib(n) {
//   if (n < 2) return n;
//   return fib(n - 2) + fib(n - 1);
// }
//
// fun fibNTimes(n) {
//   var tot = 0;
//   for (var i = 0; i < n; i = i + 1) {
//     var start = clock();
//     print fib(35) == 9227465;
//     var delta = clock() - start;
//     print delta;
//     tot = tot + delta;
//   }
//   return tot / n;
// }
//
// var mean = fibNTimes(10);
// print "average : ";
// print mean;


// PYTHON
//
// import time
//
// def fib(n):
//     if n < 2:
//         return n
//     return fib(n-2) + fib(n-1)
//
// def fibNTimes(n):
//     tot = 0
//     for i in range(n):
//         start = time.perf_counter()
//         res = fib(35)
//         print(res == 9227465)
//         delta = time.perf_counter() - start
//         print(delta)
//         tot += delta
//     return tot / n
//
// print(f"average: {fibNTimes(10)}")
```

</details>
