from config import MEMORY_ADDRESS_HALFBYTES
from instructions.arithmeticInstructions import AddI
from instructions.baseInstructions import *
from dataclasses import dataclass


@dataclass
class StoreWord(Instruction):
    src: Register
    addr: OffsetRegister

    def evaluate(self, program: Program, cur_block: Block, comments: bool = False, byte_count: int = 4):
        concater.rem(f"sw {self.src} {self.addr.offset}({self.addr.register})", comments)

        if self.addr.register == ZERO:
            assert self.addr.offset >= 0
            dst = memory_scraps[-1].cell_rel(1 + self.addr.offset)
            for i in range(byte_count):
                small_dst = dst.cell_rel(i)
                small_dst.clear()
            if self.src != ZERO:
                for i in range(byte_count * 2):
                    small_src = self.src.get_cell(i)
                    small_dst = dst.cell_rel(i // 2)
                    small_src.copy(small_dst, scrap=memory_scraps[0], multiplier=(16 if i % 2 == 0 else 1))
            return

        zero_scrap = memory_scraps[0]
        addr_cells = memory_scraps[1: MEMORY_ADDRESS_HALFBYTES + 1]
        addr_scrap = memory_scraps[MEMORY_ADDRESS_HALFBYTES + 1]
        data_cell = memory_scraps[MEMORY_ADDRESS_HALFBYTES + 2:]
        first_mem_cell = data_cell[-1].cell_rel(1)
        if self.addr.offset >= 0:
            need_mem_cell = first_mem_cell.cell_rel(self.addr.offset)
        else:
            need_mem_cell = first_mem_cell
            AddI(self.addr.register, self.addr.register, self.addr.offset).evaluate(program, cur_block)

        if self.src != ZERO:
            for i in range(byte_count * 2):  # Move src to data
                small_src = self.src.get_cell(i)
                small_src.copy(data_cell[i // 2], scrap=zero_scrap, multiplier=(1 if i % 2 == 0 else 16))
        for i in range(MEMORY_ADDRESS_HALFBYTES):
            self.addr.register.get_cell(i).copy(addr_cells[i], scrap=zero_scrap)

        if self.addr.offset < 0:
            AddI(self.addr.register, self.addr.register, -self.addr.offset).evaluate(program, cur_block)

        _go_to_addr(memory_scraps, zero_scrap, addr_cells, addr_scrap)

        # WARNING: You don't know your actual position now. It's impossible to use cells before zero_scrap
        for i in range(byte_count):
            need_mem_cell.cell_rel(i).clear()
        if self.src != ZERO:
            for i in range(byte_count):
                data_cell[i].move(need_mem_cell.cell_rel(i))

        # Moving back
        _go_from_addr(memory_scraps, zero_scrap, addr_cells)


@dataclass
class StoreHalfword(Instruction):
    src: Register
    addr: OffsetRegister

    def evaluate(self, program: Program, cur_block: Block, comments: bool = False):
        concater.rem(f"sh {self.src} {self.addr.offset}({self.addr.register})", comments)
        StoreWord(self.src, self.addr).evaluate(program, cur_block, byte_count=2)


@dataclass
class StoreByte(Instruction):
    src: Register
    addr: OffsetRegister

    def evaluate(self, program: Program, cur_block: Block, comments: bool = False):
        concater.rem(f"sb {self.src} {self.addr.offset}({self.addr.register})", comments)
        StoreWord(self.src, self.addr).evaluate(program, cur_block, byte_count=1)


@dataclass
class LoadWord(Instruction):
    src: Register
    addr: OffsetRegister

    def evaluate(self, program: Program, cur_block: Block, comments: bool = False, byte_count: int = 4):
        concater.rem(f"lw {self.src} {self.addr.offset}({self.addr.register})", comments)

        if self.src == ZERO:
            return

        if self.addr.register == ZERO:
            assert self.addr.offset >= 0
            dst = memory_scraps[-1].cell_rel(1 + self.addr.offset)
            self.src.clear_big()
            for i in range(byte_count):
                small_src1 = self.src.get_cell(i * 2)
                small_src2 = self.src.get_cell(i * 2 + 1)
                small_dst = dst.cell_rel(i)
                small_dst.div_imm(16, memory_scraps[0], small_src2)
                small_src2.move(small_src1, small_dst, multiplier=[1, 16])
                memory_scraps[0].move(small_src2, small_dst)
            return

        zero_scrap = memory_scraps[0]
        addr_cells = memory_scraps[1: MEMORY_ADDRESS_HALFBYTES + 1]
        addr_scrap = memory_scraps[MEMORY_ADDRESS_HALFBYTES + 1]
        data_cell = memory_scraps[MEMORY_ADDRESS_HALFBYTES + 2:]
        first_mem_cell = data_cell[-1].cell_rel(1)

        if self.addr.offset >= 0:
            need_mem_cell = first_mem_cell.cell_rel(self.addr.offset)
        else:
            need_mem_cell = first_mem_cell
            AddI(self.addr.register, self.addr.register, self.addr.offset).evaluate(program, cur_block)

        for i in range(MEMORY_ADDRESS_HALFBYTES):
            self.addr.register.get_cell(i).copy(addr_cells[i], scrap=zero_scrap)

        if self.addr.offset < 0:
            AddI(self.addr.register, self.addr.register, -self.addr.offset).evaluate(program, cur_block)

        _go_to_addr(memory_scraps, zero_scrap, addr_cells, addr_scrap)

        # WARNING: You don't know your actual position now. It's impossible to use cells before zero_scrap
        for i in range(byte_count):
            need_mem_cell.cell_rel(i).copy(data_cell[i], scrap=zero_scrap)

        # Moving back
        _go_from_addr(memory_scraps, zero_scrap, addr_cells)

        self.src.clear_big()
        for i in range(byte_count):  # Move data to src
            small_src1 = self.src.get_cell(i * 2)
            small_src2 = self.src.get_cell(i * 2 + 1)
            small_dst = data_cell[i]
            small_dst.div_imm(16, memory_scraps[0], small_src2)
            memory_scraps[0].move(small_src1)


@dataclass
class LoadHalfword(Instruction):
    src: Register
    addr: OffsetRegister

    def evaluate(self, program: Program, cur_block: Block, comments: bool = False):
        concater.rem(f"lh {self.src} {self.addr.offset}({self.addr.register})", comments)
        LoadWord(self.src, self.addr).evaluate(program, cur_block, byte_count=2)
        mod = scraps[0]
        out = scraps[3]
        self.src.get_cell(3).div_imm(8, mod, out)
        mod.move(self.src.get_cell(3))
        out.debug()
        out.move(*[self.src.get_cell(i) for i in range(3, 8)], multiplier=[(8 if i == 3 else 15) for i in range(3, 8)])


@dataclass
class LoadHalfwordUnsigned(Instruction):
    src: Register
    addr: OffsetRegister

    def evaluate(self, program: Program, cur_block: Block, comments: bool = False):
        concater.rem(f"lhu {self.src} {self.addr.offset}({self.addr.register})", comments)
        LoadWord(self.src, self.addr).evaluate(program, cur_block, byte_count=2)


@dataclass
class LoadByte(Instruction):
    src: Register
    addr: OffsetRegister

    def evaluate(self, program: Program, cur_block: Block, comments: bool = False):
        concater.rem(f"lb {self.src} {self.addr.offset}({self.addr.register})", comments)
        LoadWord(self.src, self.addr).evaluate(program, cur_block, byte_count=1)
        mod = scraps[0]
        out = scraps[3]
        self.src.get_cell(1).div_imm(8, mod, out)
        mod.move(self.src.get_cell(1))
        out.debug()
        out.move(*[self.src.get_cell(i) for i in range(1, 8)], multiplier=[(8 if i == 1 else 15) for i in range(1, 8)])


@dataclass
class LoadByteUnsigned(Instruction):
    src: Register
    addr: OffsetRegister

    def evaluate(self, program: Program, cur_block: Block, comments: bool = False):
        concater.rem(f"lbu {self.src} {self.addr.offset}({self.addr.register})", comments)
        LoadWord(self.src, self.addr).evaluate(program, cur_block, byte_count=1)


def _go_to_addr(mem_scraps: list[Cell], zero_scrap: Cell, addr_cells: list[Cell], addr_scrap: Cell):
    for i in range(MEMORY_ADDRESS_HALFBYTES):
        with addr_cells[i].loop():
            if i == 0:
                mem_scraps[-1].cell_rel(1).move(zero_scrap)
                for j in range(len(mem_scraps) - 1, 0, -1):
                    mem_scraps[j].move(mem_scraps[j].cell_rel(1))
                concater.raw("", pos_offset=-1)
            else:
                first_swap_cell = zero_scrap.cell_rel(16 ** i)
                first_swap_cell.move(zero_scrap)
                zero_swap_cell = first_swap_cell
                for j in range(1, len(mem_scraps)):
                    mem_scraps[j].move(zero_swap_cell)
                    first_swap_cell.cell_rel(j).move(mem_scraps[j])
                    zero_swap_cell.move(first_swap_cell.cell_rel(j))
                concater.raw("", pos_offset=-(16 ** i))
            addr_scrap.change(1)
            addr_cells[i].change(-1)
        addr_scrap.move(addr_cells[i])


def _go_from_addr(mem_scraps: list[Cell], zero_scrap: Cell, addr_cells: list[Cell]):
    for i in range(MEMORY_ADDRESS_HALFBYTES - 1, -1, -1):
        with addr_cells[i].loop():
            if i == 0:
                for j in range(1, len(mem_scraps)):
                    mem_scraps[j].move(mem_scraps[j].cell_rel(-1))
                mem_scraps[0].cell_rel(-1).move(mem_scraps[-1])
                concater.raw("", pos_offset=1)
            else:
                first_swap_cell = zero_scrap.cell_rel(-(16 ** i))
                first_swap_cell.move(zero_scrap)
                for j in range(1, len(mem_scraps)):
                    mem_scraps[j].move(first_swap_cell)
                    first_swap_cell.cell_rel(j).move(mem_scraps[j])
                    first_swap_cell.move(first_swap_cell.cell_rel(j))
                concater.raw("", pos_offset=16 ** i)
            addr_cells[i].change(-1)
