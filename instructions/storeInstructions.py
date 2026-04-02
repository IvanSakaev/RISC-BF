from config import MEMORY_ADDRESS_HALFBYTES
from instructions.baseInstructions import *


@dataclass
class StoreWord(Instruction):
    src: Register
    addr: OffsetRegister

    def evaluate(self, program: Program, cur_block: Block, comments: bool = False):
        concater.rem(f"sw {self.src} {self.addr.offset}({self.addr.register})", comments)

        if self.addr.register == ZERO:
            assert self.addr.offset >= 0
            dst = memory_scraps[-1].cell_rel(1 + self.addr.offset)
            for i in range(8):
                small_src = self.src.get_cell(i)
                small_dst = dst.cell_rel(i // 2)
                small_src.copy(small_dst, scrap=memory_scraps[0], multiplier=16 if i % 2 == 0 else 1)
            return
        if self.addr.offset != 0:
            raise NotImplementedError

        zero_scrap = memory_scraps[0]
        addr_cell = memory_scraps[1: MEMORY_ADDRESS_HALFBYTES + 1]
        addr_scrap = memory_scraps[MEMORY_ADDRESS_HALFBYTES + 1]
        data_cell = memory_scraps[MEMORY_ADDRESS_HALFBYTES + 2:]
        first_mem_cell = data_cell[-1].cell_rel(1)

        if self.src != ZERO:
            for i in range(8):  # Move src to data
                small_src = self.src.get_cell(i)
                small_src.copy(data_cell[i // 2], scrap=zero_scrap, multiplier=16 if i % 2 == 0 else 1)
        for i in range(MEMORY_ADDRESS_HALFBYTES):
            self.addr.register.get_cell(i).copy(addr_cell[i], scrap=zero_scrap)

        # Moving to address
        for i in range(MEMORY_ADDRESS_HALFBYTES):
            with addr_cell[i].loop():
                if i == 0:
                    memory_scraps[-1].cell_rel(1).move(zero_scrap)
                    for j in range(len(memory_scraps) - 1, 0, -1):
                        memory_scraps[j].move(memory_scraps[j].cell_rel(1))
                    concater.raw("", pos_offset=-1)
                else:
                    first_swap_cell = zero_scrap.cell_rel(16 ** i)
                    first_swap_cell.move(zero_scrap)
                    zero_swap_cell = first_swap_cell
                    for j in range(1, len(memory_scraps)):
                        memory_scraps[j].move(zero_swap_cell)
                        first_swap_cell.cell_rel(j).move(memory_scraps[j])
                        zero_swap_cell.move(first_swap_cell.cell_rel(j))
                    concater.raw("", pos_offset=-(16 ** i))
                addr_scrap.change(1)
                addr_cell[i].change(-1)
            addr_scrap.move(addr_cell[i])

        # WARNING: You don't know your actual position now. It's impossible to use cells before zero_scrap
        for i in range(4):
            first_mem_cell.cell_rel(i).clear()
        if self.src != ZERO:
            for i in range(4):
                data_cell[i].move(first_mem_cell.cell_rel(i))
        zero_scrap.debug()

        # Moving back
        for i in range(MEMORY_ADDRESS_HALFBYTES - 1, -1, -1):
            with addr_cell[i].loop():
                if i == 0:
                    for j in range(1, len(memory_scraps)):
                        memory_scraps[j].move(memory_scraps[j].cell_rel(-1))
                    memory_scraps[0].cell_rel(-1).move(memory_scraps[-1])
                    concater.raw("", pos_offset=1)
                else:
                    first_swap_cell = zero_scrap.cell_rel(-(16 ** i))
                    first_swap_cell.move(zero_scrap)
                    for j in range(1, len(memory_scraps)):
                        memory_scraps[j].move(first_swap_cell)
                        first_swap_cell.cell_rel(j).move(memory_scraps[j])
                        first_swap_cell.move(first_swap_cell.cell_rel(j))
                    concater.raw("", pos_offset=16 ** i)
                addr_cell[i].change(-1)
        zero_scrap.debug()
