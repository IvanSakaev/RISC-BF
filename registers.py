from __future__ import annotations

from concater import _Concater


class Register:
    def __init__(self, addr):
        self.addr = addr

    def to(self):
        if self.addr > concater.current_pos.addr:
            concater.raw(">" * (self.addr - concater.current_pos.addr))
        elif self.addr < concater.current_pos.addr:
            concater.current_program += "<" * (concater.current_pos.addr - self.addr)
        concater.current_pos = self

    def change(self, a: int, b: int):
        """
        Change this register value from "a" to "b"
        """
        self.to()
        if a > b:
            concater.raw("-" * (a - b))
        elif a < b:
            concater.raw("+" * (b - a))
    
    def clear(self):
        self.to()
        concater.raw("[-]")

    def move(self, *dsts: Register, multiplier: int | tuple | list = 1):
        if isinstance(multiplier, int):
            multiplier = [multiplier] * len(dsts)
        self.to()
        concater.raw("[")
        for dst, mult in zip(dsts, multiplier):
            dst.change(0, mult)
        self.change(0, -1)
        self.to()
        concater.raw("]")

    def __repr__(self):
        if self.addr == -2:
            return "J"
        elif self.addr == -1:
            return "S"
        elif self.addr == 8:
            return "SP"
        return f"R{self.addr}"


class Immediate(int):
    def move(self, *dsts: Register, multiplier: int | list = 1):
        if isinstance(multiplier, int):
            multiplier = [multiplier] * len(dsts)
        for dst, mult in zip(dsts, multiplier):
            dst.change(0, self * mult)



RegisterOrImmediate = Register | Immediate


ROOT = Register(0)
concater = _Concater(ROOT)

regs = {
    "R1": Register(1),
    "R2": Register(2),
    "R3": Register(3),
    "R4": Register(4),
    "R5": Register(5),
    "R6": Register(6),
    "R7": Register(7),
    "SP": Register(8),
}

next2 = Register(-5)  # next block number
next1 = Register(-4)  # next kiloblock number

current2 = Register(-3)  # current block number
current1 = Register(-2)  # current kiloblock number

# Safe to modiefy in blocks, but after modiefying must equal zero
scraps = [
    Register(-3),
    Register(-2),
    Register(-1),
    Register(0),
]

# Use only for memory addressing
addressing = [
    Register(9),
    Register(10),
    Register(11),
    Register(12),
]
