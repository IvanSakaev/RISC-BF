from __future__ import annotations


class Instruction: ...


class Register:
    def __init__(self, addr):
        self.addr = addr

    def is_immediate(self):
        return isinstance(self, Immediate)

    def to(self, reg: Register | None = None):
        if reg is None:
            reg = ROOT
        if self.addr > reg.addr:
            return ">" * (self.addr - reg.addr)
        else:
            return "<" * (reg.addr - self.addr)

    def back(self, reg: Register | None = None):
        if reg is None:
            reg = ROOT
        if self.addr > reg.addr:
            return "<" * (self.addr - reg.addr)
        else:
            return ">" * (reg.addr - self.addr)

    def __repr__(self):
        if self.addr == -2:
            return "J"
        elif self.addr == -1:
            return "S"
        elif self.addr == 8:
            return "SP"
        return f"R{self.addr}"


class Immediate(int):
    def is_immediate(self):
        return isinstance(self, Immediate)


RegisterOrImmediate = Register | Immediate


ROOT = Register(0)

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
