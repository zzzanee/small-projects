# C-like memory REPL

This is a simulator for stack and heap memory allocation, with a c-like 
implementation of some commands you can do on the memory


## Run it

```sh
python3 memory_repl.py
```
You start inside `main`, with a 64-byte heap and 16 available frames. Enter one command per line. Trailing semicolons are optional except for `quit`/`exit`

## Example usage script

[`example.txt`](example.txt) is an example of all available operations which
you can run line by line, or if you want you can pipe it with:

```sh
python3 memory_repl.py < c_repl/example.txt
```

## Command reference

### Variables/expressions

| Command | Meaning |
| --- | --- |
| `int x = 10` | Create a local integer. |
| `ptr p = NULL` | Create a pointer with no target. |
| `x = (x + 2) * 3` | Update a local using an expression. |
| `print x` | Print a value below the memory display. |
| `x + 1` | Evaluate and print without storing. |

Expressions support decimal integers, local names, `NULL`, unary `+` and `-`,
and binary `+`, `-`, `*`, `/`, `%`. Arithmetic follows PEMD%AS and division 
truncates to zero (`-7 / 3` = `-2`).

`int` and `ptr` are declaration labels and not enforced types. Plain assignment
can also create a local. Ordinary local arithmetic uses Python integers.

### Heap allocation and pointers

| Command | Meaning |
| --- | --- |
| `ptr p = malloc(8)` | Reserve 8 heap bytes; report their location. |
| `ptr q = calloc(2, 4)` | Reserve 2 × 4 bytes and fill them with zeros. |
| `ptr alias = p` | Copy a pointer, not the bytes it points to. |
| `*p = 42` | Write a signed 4-byte integer through a pointer. |
| `print *p` | Read through a pointer. |
| `p[1] = -7` | Write using an index (which may be an expression). |
| `print p[1]` | Read an indexed integer. |
| `q = p + 1` | Advance one integer: 4 bytes. |
| `q = 1 + p` | Integer + pointer also works. |
| `q = p - 1` | Move backward one integer. |
| `q - p` | Distance between pointers in 4-byte integer elements. |
| `*(p + 1) = 20` | Write through a calculated pointer. |
| `print *(p + 1)` | Read through a calculated pointer. |
| `free(p)` | Release an allocation using its starting pointer. |
| `free(NULL)` | Do nothing. |

`malloc`/`calloc` must be the entire right-hand side of a local assignment.
Their arguments may be integer expressions and must be positive. Heap integers
are signed 32-bit and stored little-endian (least significant byte first).

Heap address zero is valid and is **not** `NULL`. Freeing memory does not erase
its bytes or clear pointer variables. `malloc` will reuse old bytes without 
clearing but `calloc` will zero its allocation.

### Frames and display

| Command | Meaning |
| --- | --- |
| `enter helper` | Push a new frame |
| `leave` | Remove the current frame/its locals. |
| `show` | Redraw the memory display. |
| `quit` or `exit` | Stop the REPL. |

Only the current frame's locals are accessible. Leaving a frame does **not**
free its heap allocation. If you leave `main`, enter another frame before 
assigning locals again.

The display shows every frame, pointer arrows, allocated/free byte ranges,
decimal integers in allocated blocks, and raw hexadecimal bytes. A range like
`heap[0:8]` is end exclusive. A partial integer at the end of an allocation is
shown only in the raw bytes.
