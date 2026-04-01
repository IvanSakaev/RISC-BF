from __future__ import annotations

from contextlib import contextmanager

from concater import _Concater
from config import SCRAP_COUNT, REGISTER_COUNT, MEMORY_SCRAPS_COUNT

_default = object()


class Cell:
    def __init__(self, addr: int):
        self.addr = addr

    def to(self):
        """
        Move pointer to this cell.
        """
        if self.addr > concater.current_pos.addr:
            concater.raw(">" * (self.addr - concater.current_pos.addr))
        elif self.addr < concater.current_pos.addr:
            concater.current_program += "<" * (concater.current_pos.addr - self.addr)
        concater.current_pos = self

    def raw(self, text: str, pos_offset: int = 0):
        self.to()
        concater.raw(text, pos_offset)
    
    def debug(self):
        self.to()
        concater.debug()

    @contextmanager
    def loop(self):
        self.raw("[")
        yield
        self.raw("]")

    @contextmanager
    def ifnot(self):
        """
        Two cells after it must be zero
        """
        self.raw(">+<[>-]>[-", pos_offset=1)
        yield
        self.cell_rel(2).raw("]")

    def change(self, a: int, b: int | None = None):
        """
        Change this register value from "a" to "b".

        Or from 0 to a, if b is None.
        """
        if b is None:
            b = a
            a = 0
        if a > b:
            self.raw("-" * (a - b))
        elif a < b:
            self.raw("+" * (b - a))

    def clear(self):
        """
        Clear register value.
        """
        self.raw("[-]")

    def move(self, *dsts: Cell, multiplier: int | tuple | list = 1):
        """
        Move value from current register to "dsts". Value is multiplied by "multiplier".

        If multiplier is a list, it should be a same length that a count of dsts.
        """
        if isinstance(multiplier, int):
            multiplier = [multiplier] * len(dsts)
        dsts2 = list(dsts)
        assert self not in dsts2
        with self.loop():
            for dst, mult in zip(dsts2, multiplier, strict=True):
                dst.change(mult)
            self.change(-1)

    def copy(
            self,
            *dsts: Cell,
            scrap: Cell | None = None,
            multiplier: int | tuple | list = 1,
    ):
        """
        Copy register value to "dsts". Value is multiplied by "multiplier".

        "scrap" cell is used for copying. Before copying, it should be 0, after it will be 0 too.
        """
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

    def div_imm(
            self,
            base: int,
            mod: Cell | None = None,
            output: Cell | None | object = _default,
            invert_output: bool = False,
    ):
        """
        It divides cell by constant number. Result and reminder are stored. (Result isn't stored if need_output=False)'

        Register will be cleared.

        Reminder is stored in "mod" (scraps[0] by default).

        Two scraps after "mod" are used for calculations (scraps[1] and scraps[2] by default)

        Output value is stored in "output" (scraps[3] by default).
        It won't be stored if "output" = None.
        """
        if mod is None:
            mod = scraps[0]
        if output is _default:
            output = scraps[3]
        assert isinstance(output, Cell) or output is None
        assert base > 0

        mod.change(-base)

        with self.loop():
            mod.change(1)
            with mod.ifnot():
                mod.change(-base)
                if output is not None:
                    output.change(-1 if invert_output else 1)
            self.change(-1)
        mod.change(base)

    def cell_rel(self, n: int):
        """
        Returns cell that is n cells right
        """
        return Cell(self.addr + n)

    def __eq__(self, other):
        if not isinstance(other, Cell):
            return NotImplemented
        return self.addr == other.addr


ROOT = Cell(4)  # Every block starts and ends here
concater = _Concater(ROOT)

next2 = Cell(0)  # next block number
next1 = Cell(1)  # next kiloblock number

current2 = Cell(2)  # current block number
current1 = Cell(3)  # current kiloblock number

# Safe to modify in blocks, equal zero in blocks, after modifying must stay zero
scraps = [Cell(i + 2) for i in range(SCRAP_COUNT)]  # TODO: reduce scrap count
memory_scraps = [Cell(i + REGISTER_COUNT * 8 + SCRAP_COUNT + 2) for i in range(MEMORY_SCRAPS_COUNT)]
scraps.extend(memory_scraps)
