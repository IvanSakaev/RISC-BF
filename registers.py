from __future__ import annotations

from cell import Cell, scraps
from config import SCRAP_COUNT


class Register:
    def __init__(self, addr: int | Cell | Register):
        if isinstance(addr, Register):
            addr = addr.addr
        if isinstance(addr, Cell):
            addr = addr.addr
        self.addr: int = addr

    def get_cell(self, number):
        assert 0 <= number < 8
        return Cell(self.addr + number)

    def get_cells(self):
        return [Cell(self.addr + i) for i in range(8)]

    def move_big(self, *dsts: Cell | Register, multiplier: int | tuple | list = 1):
        dsts2 = [Register(dst) for dst in dsts]
        assert self not in dsts2
        for i in range(8):
            small_src = self.get_cell(i)
            small_dsts = [d.get_cell(i) for d in dsts2]
            small_src.move(*small_dsts, multiplier=multiplier)

    def copy_big(
        self,
        *dsts: Register,
        scrap: Cell | None = None,
        multiplier: int | tuple | list = 1,
    ):
        if scrap is None:
            scrap = scraps[0]
        assert self not in dsts
        for dst in dsts:
            assert scrap not in dst.get_cells()
        if isinstance(multiplier, int):
            multiplier = [multiplier] * len(dsts)
        multiplier = list(multiplier) + [1]
        for i in range(8):
            small_src = self.get_cell(i)
            small_dsts = [d.get_cell(i) for d in dsts]
            small_dsts.append(scrap)
            small_src.move(small_dsts, multiplier)
            scrap.move(small_src)

    def clear_big(self):
        for cell in self.get_cells():
            cell.clear()

    def change_big(self, a: int, b: int | None = None, clear=False):
        assert 0 <= a < 2**32
        if b is None:
            b = a
            a = 0
        val = b - a
        if val < 0:
            val = 2**32 - val
        for cell in self.get_cells():
            if clear:
                cell.clear()
            cell.change(val % 16)
            val //= 16

    def normalize_big(self):
        """
        Normalize big register (8 cells).
        Before normalization every cell SHOULD BE <= 0xf0.
        After every cell store only one hex number (value <= 0xf).

        It uses scraps 0, 1, 2, 3
        """
        mod = scraps[0]  # 2 scraps after MOD are used too in div_imm()
        output = scraps[3]

        for i in range(8):
            small = self.get_cell(i)
            need_output = i < 7
            if need_output:
                small.div_imm(16, mod, output)
            else:
                small.div_imm(16, mod, output=None)
            mod.move(small)
            if need_output:
                small2 = small.cell_rel(1)
                output.move(small2)

    def normalize_big_fast(self):
        """
        Normalize big register (8 cells).
        Before normalization every cell except one SHOULD BE normalized. This one cell SHOULD BE <= 0x10. For other cases use normalize_big().
        After every cell store only one hex number (value <= 0xf).

        It uses scraps 0, 1
        """
        transfer = scraps[0]
        mod = scraps[1]
        for i in range(8):
            small = self.get_cell(i)

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
                    small.cell_rel(1).change(1)
                transfer.change(-1)

    def __eq__(self, other):
        if not isinstance(other, Register):
            return NotImplemented
        return self.addr == other.addr

    def __repr__(self):
        for key, value in regs.items():
            if self is value:
                return key
        return f"REG{self.addr}"


class Immediate(int):
    def move(self, *dsts: Cell, multiplier: int | list = 1):
        if isinstance(multiplier, int):
            multiplier = [multiplier] * len(dsts)
        for dst, mult in zip(dsts, multiplier):
            dst.change(self * mult)

    def copy(self, *dsts: Cell, multiplier: int | list = 1):
        self.move(*dsts, multiplier=multiplier)


RegisterOrImmediate = Register | Immediate

ZERO = Register(
    -7
)  # IMPORTANT! It isn't a physical register, it mustn't be used for data storage

# Variable is only the first cell of register. 7 cells after that are register too.
# Register cells SHOULD BE only 4 bits (values between 0 and 15)
# Operations with registers should be little-endian
regs = {
    "x0": ZERO,
    "zero": ZERO,
} | {f"x{i + 1}": Register(i * 8 + SCRAP_COUNT - 4) for i in range(8)}
