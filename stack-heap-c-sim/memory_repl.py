"""
File: memory_repl.py
Description:
    A small C-like memory REPL. See README.md for uses

Student Name: Zane Scott
Course Name: CS 313E
Date Created: 11/8/2026
Date Last Modified: 11/12/2026   
"""

import re
import sys

from stack_heap import Allocator, Heap, Pointer, Stack, StackFrame


class MemoryMachine:
    '''
    Runs a C-like memory commands using a simulated stack and heap.
    Integers in heap memory use four little-endian ordered bytes.
    
    Attributes
    ----------
    stack : Stack
        active function frames and their local variables
    heap : Heap
        byte-addressable memory used for allocations
    allocator : Allocator
        manager for free and allocated regions of the heap
    '''

    def __init__(self, heap_capacity=64, stack_capacity=16):
        self.stack = Stack(stack_capacity)
        self.stack.push_frame(StackFrame('main')) #So you start in main
        self.heap = Heap(heap_capacity)
        self.allocator = Allocator(self.heap)

    def pointer(self, value):
        if not isinstance(value, Pointer):
            raise TypeError('Expected a pointer, not NULL or an integer')
        return value

    def read_integer(self, pointer):
        data = self.heap.read(self.pointer(pointer).address, 4)
        return int.from_bytes(data, 'little', signed=True)

    def destination(self, text):
        '''
        Resolve a dereference/array element into writable pointer.
        
        Parameters
        ----------
        text : str
            assignment target (ex. *p or p[2])
        Returns
        -------
        Pointer : address where the integer should be stored
        '''
        if text.startswith('*'):
            return self.pointer(self.value(text[1:]))
        base, index = text.rsplit('[', 1)
        return self.pointer(self.value(base)).offset(self.value(index[:-1]) * 4)

    def binary(self, op, left, right):
        '''
        Apply arithmetic operator to integers/pointers.
        Pointer offsets count four-byte integers; integer division truncates
        to zero. Rejects unsupported operand combinations.
        
        Parameters
        ----------
        op : str
            operators +, -, *, /, or %
        left : int or Pointer
            value on the left side of the operator
        right : int or Pointer
            value on the right side of the operator
        Returns
        -------
        int or Pointer : result of the arithmetic operation
        '''
        if isinstance(left, Pointer) or isinstance(right, Pointer):
            if op == '+' and isinstance(left, int) and isinstance(right, Pointer):
                return right.offset(left * 4)
            if isinstance(left, Pointer) and isinstance(right, int) and op in ('+', '-'):
                return left.offset(right * 4 * (1 if op == '+' else -1))
            if op == '-' and isinstance(left, Pointer) and isinstance(right, Pointer):
                return (left.address - right.address) // 4
            raise TypeError('Unsupported pointer arithmetic')
        if not isinstance(left, int) or not isinstance(right, int):
            raise TypeError('Arithmetic requires integers or pointers')
        if op == '+':
            return left + right
        if op == '-':
            return left - right
        if op == '*':
            return left * right
        # C int division truncates to zero even for negative numbers.
        quotient = (abs(left) // abs(right)) * (-1 if (left < 0) != (right < 0) else 1)
        return quotient if op == '/' else left - quotient * right

    def value(self, text):
        '''
        Parse and evaluate an expression. Handles local variables, NULL, 
        arithmetic, parentheses, pointer dereferences, and array indexing using
        the regular operator precedence (for what is implemented).
        
        Parameters
        ----------
        text : str
            C-like expression to evaluate
        Returns
        -------
        int, Pointer, or None : evaluated value, with None representing NULL
        '''
        tokens = re.findall(r'\d+|[A-Za-z_]\w*|[^\s]', text) + ['<end>']
        position = 0
        precedence = {'+': 1, '-': 1, '*': 2, '/': 2, '%': 2}

        def take(expected=None):
            nonlocal position   # makes position assignment so much easier
            token = tokens[position]
            if expected is not None and token != expected:
                raise SyntaxError(f'Expected {expected}, got {token}')
            position += 1
            return token

        def unary():
            '''
            Read a value with any leading unary operators or array indexing.
            Resolve variable names in the current frame and read dereferenced
            pointers as four-byte integers.
            
            Returns
            -------
            int, Pointer, or None : value of the parsed operand
            '''
            token = take()
            if token in ('+', '-', '*'):
                result = unary()
                if token == '*':
                    return self.read_integer(result)
                return +result if token == '+' else -result
            if token == '(':
                result = expression()
                take(')')
            elif token.isdigit():
                result = int(token)
            elif token == 'NULL':
                result = None
            elif re.fullmatch(r'[A-Za-z_]\w*', token):
                result = self.stack.curr_frame().get_local(token)
            else:
                raise SyntaxError(f'Unexpected token: {token}')
            while tokens[position] == '[':
                take('[')
                index = expression()
                take(']')
                result = self.read_integer(self.pointer(result).offset(index * 4))
            return result

        def expression(minimum=0):
            '''
            Combine operands while respecting operator precedence.
            
            Parameters
            ----------
            minimum : int
                lowest operator precedence to consume in this call
            Returns
            -------
            int, Pointer, or None : value of the parsed expression
            '''
            left = unary()
            while precedence.get(tokens[position], -1) >= minimum:
                op = take()
                right = expression(precedence[op] + 1)
                left = self.binary(op, left, right)
            return left

        result = expression()
        take('<end>')
        return result

    def execute(self, command):
        '''
        Execute one C-like command/update memory. Handle frame changes, 
        allocations, frees, assignments, and expression output. Empty 
        commands and show leave the machine unchanged.
        
        Parameters
        ----------
        command : str
            command entered by the user, optionally ending with a semicolon
        Returns
        -------
        str, int, Pointer, or None : output to display, or None for no output
        '''
        command = command.strip().rstrip(';').strip()
        if not command or command == 'show':
            return
        if command.startswith('enter '):
            self.stack.push_frame(StackFrame(command[6:].strip()))
        elif command == 'leave':
            self.stack.pop_frame()
        elif command.startswith('free('):
            pointer = self.value(command[5:-1])
            if pointer is not None:  # Like C, free(NULL) is a no-op.
                self.allocator.free(pointer)
        elif '=' in command:
            target, expression = command.split('=', 1)
            target = target.strip()
            # Declarations and assignments both store a local value.
            if target.startswith(('int ', 'ptr ')):
                target = target.split()[1]
            # Resolve the destination before doing anything that allocates.
            frame = self.stack.curr_frame()
            expression = expression.strip()
            if target.startswith('*') or '[' in target:
                pointer = self.destination(target)
                value = self.value(expression)
                self.heap.write(pointer.address, value.to_bytes(4, 'little', signed=True))
            else:
                allocation = re.fullmatch(r'(malloc|calloc)\s*\((.*)\)', expression)
                if allocation:
                    kind, arguments = allocation.groups()
                    sizes = [self.value(arg) for arg in arguments.split(',')]
                    if len(sizes) != (1 if kind == 'malloc' else 2):
                        raise SyntaxError('malloc needs 1 argument; calloc needs 2')
                    if any(not isinstance(n, int) or n <= 0 for n in sizes):
                        raise ValueError('Allocation arguments must be positive integers')
                    size = sizes[0] if kind == 'malloc' else sizes[0] * sizes[1]
                    value = self.allocator.allocate(size)
                    if kind == 'calloc':
                        self.heap.write(value.address, bytes(size))
                else:
                    value = self.value(expression)
                frame.set_local(target, value)
                if allocation:
                    return (f'{kind} → {target} → '
                            f'heap[{value.address}:{value.address + size}]')
        else:
            value = self.value(command.removeprefix('print '))
            return 'NULL' if value is None else value

    def render(self):
        '''
        Builds a text view of the stack, heap blocks, and raw memory.
        Shows local values, allocation ranges, complete four-byte integers
        within allocated blocks, and the heap bytes in hexadecimal.
        Returns
        -------
        str : formatted view of the current memory state
        '''
        lines = ['STACK']
        for frame in reversed(self.stack.frames):
            lines.append(f'  {frame.function_name}')
            for name, value in frame.locals.items():
                if isinstance(value, Pointer):
                    lines.append(f'    {name} → heap[{value.address}] ({value})')
                else:
                    lines.append(f'    {name} = {"NULL" if value is None else value}')
        if self.stack.is_empty():
            lines.append('  (empty)')
        lines.append('HEAP (byte ranges; end address excluded)')
        for block in self.allocator.blocks:
            state = 'free' if block.is_free else 'allocated'
            end = block.start + block.size
            lines.append(f'  heap[{block.start}:{end}] — {block.size} bytes {state}')
            if not block.is_free:
                for address in range(block.start, end - 3, 4):
                    data = self.heap.read(address, 4)
                    number = int.from_bytes(data, 'little', signed=True)
                    lines.append(f'    heap[{address}] = {number}')
                if block.size % 4:
                    lines.append(f'    ({block.size % 4} trailing bytes; no full integer)')
        lines.append('RAW BYTES (hex addresses and values)')
        for address in range(0, self.heap.capacity, 16):
            data = self.heap.memory[address:address + 16]
            lines.append(f'  {address:04x}: {data.hex(" ")}')
        return '\n'.join(lines)


def main():
    machine = MemoryMachine()
    result = None
    while True:
        if sys.stdin.isatty() and sys.stdout.isatty():
            print('\033[2J\033[H', end='')
        print(machine.render())
        if result is not None:
            print(result)
        command = input('memory> ')
        if command.strip() in ('quit', 'exit'):
            break
        result = machine.execute(command)


if __name__ == '__main__':
    main()
