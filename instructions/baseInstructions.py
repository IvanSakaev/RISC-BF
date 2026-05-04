from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from config import BLOCK_SIZE
from cell import Cell, scraps, concater, nexts, memory_scraps
from registers import (
    ZERO,
    Cell,
    Immediate,
    Register,
    OffsetRegister,
    scraps,
)

if TYPE_CHECKING:
    from instructions.jumpInstructions import LabelDefine
    from asm import Program


class Instruction:
    def evaluate(self, program: Program, cur_block: Block, comments: bool = False): ...


@dataclass
class Block:
    myid: int | None
    daughter_blocks: list[Block] | list[Instruction]
    mother_block: Block | None

    def get_full_id(self):
        myid = []
        cur_block = self
        for i in range(4):
            assert cur_block is not None
            myid.append(cur_block.myid)
            cur_block = cur_block.mother_block
        return myid

    def find_block_rel(self, offset):
        assert offset % 4 == 0
        out = self.get_full_id()
        number = 0
        for i in range(4):
            number += out[i] * (BLOCK_SIZE ** i)
        number += offset
        assert number >= 0
        for i in range(4):
            out[i] = (number // (BLOCK_SIZE ** i)) % BLOCK_SIZE
        return out
