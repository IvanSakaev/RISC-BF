from instructions.baseInstructions import *


@dataclass
class StoreWord(Instruction):
    src: Register
    addr: OffsetRegister

    def evaluate(self, program: Program, cur_block: Block, comments: bool = False):
        concater.rem(f"sw {self.src} {self.addr.offset}({self.addr.register})", comments)
        # TODO: use offset
        zero_scrap = memory_scraps[0]
        addr_cell = Register(memory_scraps[1])
        addr_scrap = memory_scraps[9]
        data_cell = memory_scraps[10:]
        first_mem_cell = data_cell[-1].cell_rel(1)

        for i in range(8):  # Move src to data
            small_src = self.src.get_cell(i)
            small_src.copy(data_cell[i // 2], scrap=addr_scrap, multiplier=1 if i % 2 == 0 else 16)
        self.addr.register.move_big(addr_cell)
        
        for i in range(8):
            with addr_cell.get_cell(i).loop():
                first_mem_cell.move(zero_scrap)
                for j in range(3, -1, -1):
                    data_cell[j].move(data_cell[j].cell_rel(1))
                addr_scrap.change(1)
                addr_scrap.move(data_cell[0])
                for j in range(7, -1, -1):
                    addr_cell.get_cell(j).move(addr_cell.get_cell(j).cell_rel(1))
                concater.raw("", pos_offset=-1)
                addr_cell.get_cell(i).change(-1)
            addr_scrap.move(addr_cell.get_cell(i))
        # WARNING: You don't know your actual position now. It's impossible to use default scraps.
        for i in range(4):
            data_cell[i].move(first_mem_cell.cell_rel(i))
        first_mem_cell.to()
        concater.debug()
