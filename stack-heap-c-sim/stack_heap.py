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
    '''
    Hold active function frames with capacity measured in frames.
    
    Attributes
    ----------
    capacity : int
        how many stack frames you have available
    frames : list of StackFrame
        stack of the active function frames
    '''

    def __init__(self, capacity):
        self.capacity = capacity
        self.frames = []

    def push_frame(self, frame):
        '''
        Push a StackFrame, rejects when the stack is full.
       
        Parameters
        ----------
        frame : StackFrame
            The stackframe being added
        '''
        if self.is_full():
            raise OverflowError('Stack is full')
        self.frames.append(frame)

    def pop_frame(self):
        '''
        Remove and return the top frame; reject an empty stack.
        
        Returns
        -------
        StackFrame : the popped stackframe
        '''
        if self.is_empty():
            raise IndexError('Stack is empty')
        return self.frames.pop()
    def curr_frame(self):
        '''Return the top frame without removing it.
        
        Returns
        -------
        StackFrame : the next up stackframe
        '''
        if self.is_empty():
            raise IndexError('Stack is empty')
        return self.frames[-1]

    def is_empty(self):
        return len(self.frames) == 0
    def is_full(self):
        return len(self.frames) >= self.capacity


class StackFrame:
    '''
    Represent one function call and its local variables.
    
    Attributes
    ----------
    function_name : str
        name of the function being called
    return_address : object or None
        optional location to return to after the function finishes
    locals : dict
        local variable names mapped to their values
    '''

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
    Note: Not a binary heap but a memory heap
    
    Attributes
    ----------
    capacity : int
        total number of bytes available
    memory : bytearray
        bytes stored in the simulated heap
    '''

    def __init__(self, capacity):
        self.capacity = capacity
        self.memory = bytearray(capacity)

    def read(self, address, size=1):
        '''
        Read bytes from the heap after checking the requested range.
        
        Parameters
        ----------
        address : int
            starting byte address to read from
        size : int
            number of bytes to read, defaults to 1
        Returns
        -------
        bytes : a copy of the requested heap bytes
        '''
        self._check_bounds(address, size)
        return bytes(self.memory[address:address + size])

    def write(self, address, data):
        '''
        Copy bytes into the heap after checking the destination range.
        
        Parameters
        ----------
        address : int
            starting byte address to write to
        data : bytes-like object
            data to copy into the heap
        '''
        data = memoryview(data).tobytes()
        self._check_bounds(address, len(data))
        self.memory[address:address + len(data)] = data

    def _check_bounds(self, address, size):
        '''
        Reject non-integer addresses/sizes and ranges outside the heap.
        
        Parameters
        ----------
        address : int
            starting byte address of the memory access
        size : int
            number of bytes being accessed
        '''
        if not isinstance(address, int) or not isinstance(size, int):
            raise TypeError('Address and size must be integers')
        if address < 0 or size < 0 or address + size > self.capacity:
            raise IndexError('Memory access is outside the heap')


class Pointer:
    '''
    Represent a byte address within a heap.
    
    Attributes
    ----------
    heap : Heap
        heap that the ponter belongs to
    address : int
        byte address within that heap
    '''

    def __init__(self, heap, address):
        self.heap = heap
        self.address = address

    def offset(self, amount):
        '''Return a new pointer offset by amount bytes.'''
        return Pointer(self.heap, self.address + amount)

    def __repr__(self):     #For debugging
        return f'0x{self.address:04x}'


class MemoryBlock:
    '''
    Define heap region via start, byte size, and free status.
    
    Attributes
    ----------
    start : int
        starting byte address
    size : int
        number of bytes
    is_free : bool
        whether the block is available for allocation
    '''
    def __init__(self, start, size, is_free=True):
        self.start = start
        self.size = size
        self.is_free = is_free


class Allocator:
    '''
    Manage blocks in address order, splitting and merging as needed.
    
    Attributes
    ----------
    heap : Heap
        The heap being managed
    blocks : list of MemoryBlock
        free and allocated regions ordered by starting address
    '''

    def __init__(self, heap):
        self.heap = heap
        self.blocks = [MemoryBlock(0, heap.capacity)]

    def allocate(self, size):
        '''
        Allocate bytes from the first free block large enough to hold them.
        Split off any unused space; reject invalid sizes or insufficient space.
        
        Parameters
        ----------
        size : int
            positive number of bytes to allocate
        Returns
        -------
        Pointer : pointer to the start of the allocated block
        '''
        if not isinstance(size, int) or size <= 0:
            raise ValueError('Allocation size must be a positive integer')
        block = self._find_free_block(size)
        if block is None:
            raise MemoryError('Not enough free memory for a block this size')
        self._split_block(block, size)
        block.is_free = False
        return Pointer(self.heap, block.start)

    def free(self, pointer):
        '''
        Free an allocation and merge neighboring free blocks.
        Rejects foreign, invalid, or already-freed pointers.
        
        Parameters
        ----------
        pointer : Pointer
            pointer to the start of the allocation
        '''
        if pointer.heap is not self.heap:
            raise ValueError('Pointer belongs to another heap')
        for block in self.blocks:
            if block.start == pointer.address and not block.is_free:
                block.is_free = True
                self._merge_free_blocks()
                return
        raise ValueError('Invalid or already-freed pointer')

    def _find_free_block(self, size):
        '''First-fit allocation.'''
        return next((block for block in self.blocks
                     if block.is_free and block.size >= size), None)

    def _split_block(self, block, size):
        '''
        Separate an allocation from any unused remainder of a block.
        Insert the remainder directly after the original block.
        
        Parameters
        ----------
        block : MemoryBlock
            block to split if it is larger than the requested size
        size : int
            number of bytes to keep in the original block
        '''
        if block.size > size:
            remainder = MemoryBlock(block.start + size, block.size - size)
            self.blocks.insert(self.blocks.index(block) + 1, remainder)
            block.size = size

    def _merge_free_blocks(self):
        '''
        Combine consecutive free blocks that touch in memory.
        Keeps checking the current block after a merge so that runs of
        multiple free blocks become one larger block.
        '''
        index = 0
        while index + 1 < len(self.blocks):
            left, right = self.blocks[index:index + 2]
            if left.is_free and right.is_free and left.start + left.size == right.start:
                left.size += right.size
                self.blocks.pop(index + 1)
            else:
                index += 1



    
