from __future__ import annotations

from contextlib import contextmanager

from concater import _Concater
from config import SCRAP_COUNT


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
        dsts2 = list(dsts)
        assert self not in dsts2
        self.to()
        concater.raw("[")
        for dst, mult in zip(dsts2, multiplier):
            dst.change(mult)
        self.change(-1)
        self.to()
        concater.raw("]")

    def copy(
        self,
        *dsts: Register,
        scrap: Register | None = None,
        multiplier: int | tuple | list = 1,
    ):
        if scrap is None:
            scrap = scraps[0]
        assert self not in dsts
        assert scrap not in dsts
        if isinstance(multiplier, int):
            multiplier = [multiplier] * len(dsts)
        dsts2 = list(dsts) + [scrap]
        multiplier = list(multiplier) + [1]
        self.move(*dsts2, multiplier=multiplier)
        scrap.move(self)

    def move_big(self, *dsts: Register, multiplier: int | tuple | list = 1):
        assert self not in dsts
        small_src = self
        small_dsts = list(dsts)
        for i in range(8):
            small_src.move(*small_dsts, multiplier=multiplier)
            small_src = small_src.reg_rel(1)
            small_dsts = list(map(lambda r: r.reg_rel(1), small_dsts))

    def copy_big(
        self,
        *dsts: Register,
        scrap: Register | None = None,
        multiplier: int | tuple | list = 1,
    ):
        if scrap is None:
            scrap = scraps[0]
        assert self not in dsts
        assert scrap not in dsts
        if isinstance(multiplier, int):
            multiplier = [multiplier] * len(dsts)
        dsts2 = list(dsts) + [scrap]
        multiplier = list(multiplier) + [1]
        self.move_big(*dsts2, multiplier=multiplier)
        scrap.move_big(self)

    def clear_big(self):
        reg = self
        for i in range(8):
            reg.clear()
            reg = reg.reg_rel(1)

    def change_big(self, a: int, b: int | None = None, clear=False):
        if b is None:
            b = a
            a = 0
        val = b - a
        assert val > 0
        reg = self
        for i in range(8):
            if clear:
                reg.clear()
            reg.change(val % 16)
            val //= 16
            reg = reg.reg_rel(1)

    def div_imm(self, base: int, need_output: bool = True):
        """
        It divides register by constant number. Result and reminder are stored. (Result isn't stored if need_output=False)'


        Register will be cleared.

        Reminder is stored in scraps[0]

        Output value is stored in scraps[3]  (only if need_output = True)

        scraps[1] and scraps[2] are used for calculations
        """
        assert base > 0
        mod = scraps[0]  # 2 scraps after MOD are used too
        if need_output:
            output = scraps[3]

        mod.change(-base)

        with self.loop():
            mod.change(1)
            with mod.ifnot():
                mod.change(-base)
                if need_output:
                    output.change(1)
            self.change(-1)
        mod.change(base)

    def normalize_big(self):
        """
        Normalize big register (8 cells).
        Before normalization every cell should be <= 0xf0.
        After every cell store only one hex number (value <= 0xf).

        It uses scraps 0, 1, 2, 3
        """
        mod = scraps[0]  # 2 scraps after MOD are used too in div_imm()
        output = scraps[3]

        for i in range(8):
            small = self.reg_rel(i)
            small.div_imm(16, need_output=(i < 7))
            mod.move(small)
            if i < 7:
                small2 = self.reg_rel(i + 1)
                output.move(small2)

    def normalize_big_fast(self):  # TODO: check on bugs
        """
        Normalize big register (8 cells).
        Before normalization every cell SHOULD BE <= 0x10. For other cases use normalize_big().
        After every cell store only one hex number (value <= 0xf).

        It uses scraps 0, 1
        """
        transfer = scraps[0]
        mod = scraps[1]
        for i in range(8):
            small = self.reg_rel(i)

            transfer.change(1)
            small.change(-16)

            with small.loop():
                small.move(mod)
                transfer.change(-1)

            small.change(16)
            mod.move(small)

            with transfer.loop():
                small.change(-16)
                if i < 7:
                    self.reg_rel(i + 1).change(1)

    @contextmanager
    def loop(self):
        self.to()
        concater.raw("[")
        yield
        self.to()
        concater.raw("]")

    @contextmanager
    def ifnot(self):
        """
        Two cells after it must be zero
        """
        self.to()
        concater.raw(">+<[>-]>[>]<", pos_offset=1)
        with self.reg_rel(1).loop():
            self.reg_rel(1).change(-1)
            yield

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

    def copy(self, *dsts: Register, multiplier: int | list = 1):
        self.move(*dsts, multiplier=multiplier)


RegisterOrImmediate = Register | Immediate


ZERO = Register(-7)  # it isn't a physical register, it mustn't be used for data storage

next2 = Register(-6)  # next block number
next1 = Register(-5)  # next kiloblock number

current2 = Register(-4)  # current block number
current1 = Register(-3)  # current kiloblock number

ROOT = Register(-2)  # Every block starts and ends here
concater = _Concater(ROOT)

# Safe to modiefy in blocks, equal zero in blocks, after modiefying must stay zero
scraps = [Register(i - 4) for i in range(SCRAP_COUNT)]

# Variable is only the first cell of register. 7 cells after that are register too.
# Register cells SHOULD BE only 4 bits (values between 0 and 15)
# Operations with registers should be little-endian
regs = {
    "x0": ZERO,
    "zero": ZERO,
} | {f"x{i + 1}": Register(i * 8 + SCRAP_COUNT - 4) for i in range(8)}

# # Use only for memory addressing
# addressing = [  # TODO
#     Register(65),  # address we need to go
#     Register(66),  # address we need to return (must equal previous register at start)
#     Register(67),  # value to write/read
#     Register(68),  # always equal zero
# ]
