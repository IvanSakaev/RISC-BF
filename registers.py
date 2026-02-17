from __future__ import annotations

from concater import _Concater


class Register:
    def __init__(self, addr: int):
        self.addr = addr

    def to(self):
        if self.addr > concater.current_pos.addr:
            concater.raw(">" * (self.addr - concater.current_pos.addr))
        elif self.addr < concater.current_pos.addr:
            concater.current_program += "<" * (concater.current_pos.addr - self.addr)
        concater.current_pos = self

    def change(self, a: int, b: int | None = None):
        """
        Change this register value from "a" to "b"
        Or from 0 to a, if b is None
        """
        if b is None:
            b = a
            a = 0
        if a > b:
            self.to()
            concater.raw("-" * (a - b))
        elif a < b:
            self.to()
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
            dst.change(mult)
        self.change(-1)
        self.to()
        concater.raw("]")

    def reg_rel(self, n: int):
        """
        Returns register that is n cells right
        """
        return Register(self.addr + n)

    def __repr__(self):
        for key, value in regs.items():
            if self is value:
                return key
        return f"ADDR{self.addr}"


class Immediate(int):
    def move(self, *dsts: Register, multiplier: int | list = 1):
        if isinstance(multiplier, int):
            multiplier = [multiplier] * len(dsts)
        for dst, mult in zip(dsts, multiplier):
            dst.change(self * mult)


RegisterOrImmediate = Register | Immediate


ZERO = Register(-7)  # it isn't a physical register, it mustn't be used for data storage

next2 = Register(-6)  # next block number
next1 = Register(-5)  # next kiloblock number

current2 = Register(-4)  # current block number
current1 = Register(-3)  # current kiloblock number

ROOT = Register(-2)  # Every block starts and ends here
concater = _Concater(ROOT)

# Safe to modiefy in blocks, equal zero in blocks, after modiefying must stay zero
scraps = [
    Register(-4),  # current block number
    Register(-3),  # current kiloblock number
    Register(-2),  # ROOT, it is used in ifnot checks
    Register(-1),  # it is used in ifnot checks
]

# Variable is only the first cell of register. 7 cells after that are register too.
# Register cells SHOULD BE only 4 bits (values between 0 and 15)
# Operations with registers should be little-endian
regs = {
    "x0": ZERO,
    "x1": Register(0),
    "x2": Register(8),
    "x3": Register(16),
    "x4": Register(24),
    "x5": Register(32),
    "x6": Register(40),
    "x7": Register(48),
    "x8": Register(56),
    "sp": Register(64),  # TODO
}

# Use only for memory addressing
addressing = [
    Register(65),  # address we need to go
    Register(66),  # address we need to return (must equal previous register at start)
    Register(67),  # value to write/read
    Register(68),  # always equal zero
]
