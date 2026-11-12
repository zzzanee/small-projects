"""
File: stack_heap.py
Description:
    This file creates objects meant to represent how a computer allocates
    its memory at a lower level

Student Name: Zane Scott
Course Name: CS313E
Date Created: 11/9/2026
Date Last Modified: 11/12/2026   
"""

class Stack:
    '''Hold active function frames; capacity is measured in frames.'''

    def __init__(self, capacity):
        self.capacity = capacity
        self.frames = []

    def push_frame(self, frame):
        '''Push a StackFrame, rejecting pushes when the stack is full.'''
        if self.is_full():
            raise OverflowError('Stack is full')
        self.frames.append(frame)

    def pop_frame(self):
        '''Remove and return the top frame; reject an empty stack.'''
        if self.is_empty():
            raise IndexError('Stack is empty')
        return self.frames.pop()

    def curr_frame(self):
        '''Return the top frame without removing it.'''
        if self.is_empty():
            raise IndexError('Stack is empty')
        return self.frames[-1]

    def is_empty(self):
        return len(self.frames) == 0

    def is_full(self):
        return len(self.frames) >= self.capacity


class StackFrame:
    '''Represent one function call and its local variables.'''

    def __init__(self, function_name, return_address=None):
        self.function_name = function_name
        self.return_address = return_address
        self.locals = {}

    def get_local(self, name):
        '''Return a local value; reject an undefined name.'''
        return self.locals[name]

    def set_local(self, name, value):
        '''Create or update a local variable.'''
        self.locals[name] = value


class Heap:
    '''
    Holds simulated byte-addressable memory within a fixed capacity.
    Notably not a binary heap but a memory heap
    '''

    def __init__(self, capacity):
        self.capacity = capacity
        self.memory = bytearray(capacity)

    def read(self, address, size=1):
        '''Read size bytes starting at an integer address after bounds checks.'''
        self._check_bounds(address, size)
        return bytes(self.memory[address:address + size])

    def write(self, address, data):
        '''Write bytes-like data at an integer address after bounds checks.'''
        data = memoryview(data).tobytes()
        self._check_bounds(address, len(data))
        self.memory[address:address + len(data)] = data

    def _check_bounds(self, address, size):
        '''Reject negative addresses/sizes and ranges outside the heap.'''
        if not isinstance(address, int) or not isinstance(size, int):
            raise TypeError('Address and size must be integers')
        if address < 0 or size < 0 or address + size > self.capacity:
            raise IndexError('Memory access is outside the heap')


class Pointer:
    '''Represent an integer byte address within a particular heap.'''

    def __init__(self, heap, address):
        self.heap = heap
        self.address = address

    def offset(self, amount):
        '''Return a new pointer offset by amount bytes.'''
        return Pointer(self.heap, self.address + amount)

    def __repr__(self):
        return f'0x{self.address:04x}'


class MemoryBlock:
    '''Describe a heap region by its start, byte size, and free status.'''

    def __init__(self, start, size, is_free=True):
        self.start = start
        self.size = size
        self.is_free = is_free


class Allocator:
    '''Manage blocks in address order, splitting and coalescing as needed.'''

    def __init__(self, heap):
        self.heap = heap
        self.blocks = [MemoryBlock(0, heap.capacity)]

    def allocate(self, size):
        '''Allocate a positive byte count and return a Pointer; reject exhaustion.'''
        if not isinstance(size, int) or size <= 0:
            raise ValueError('Allocation size must be a positive integer')
        block = self._find_free_block(size)
        if block is None:
            raise MemoryError('Not enough contiguous heap memory')
        self._split_block(block, size)
        block.is_free = False
        return Pointer(self.heap, block.start)

    def free(self, pointer):
        '''Free an allocation; reject foreign, invalid, or already-freed pointers.'''
        if pointer.heap is not self.heap:
            raise ValueError('Pointer belongs to another heap')
        for block in self.blocks:
            if block.start == pointer.address and not block.is_free:
                block.is_free = True
                self._merge_free_blocks()
                return
        raise ValueError('Invalid or already-freed pointer')

    def _find_free_block(self, size):
        '''Find a free block large enough for the requested byte count.'''
        return next((block for block in self.blocks
                     if block.is_free and block.size >= size), None)

    def _split_block(self, block, size):
        '''Separate an allocation from any unused remainder of a block.'''
        if block.size > size:
            remainder = MemoryBlock(block.start + size, block.size - size)
            self.blocks.insert(self.blocks.index(block) + 1, remainder)
            block.size = size

    def _merge_free_blocks(self):
        '''Coalesce adjacent free blocks.'''
        index = 0
        while index + 1 < len(self.blocks):
            left, right = self.blocks[index:index + 2]
            if left.is_free and right.is_free and left.start + left.size == right.start:
                left.size += right.size
                self.blocks.pop(index + 1)
            else:
                index += 1



    
