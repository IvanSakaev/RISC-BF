#! /bin/python
from urllib.parse import unquote

import instructions
import registers
from instructions import (
    MNEMONICS,
    is_block_boundary,
)
from registers import (
    Immediate,
    Register,
    RegisterOrImmediate,
    concater,
    regs,
)


def split_program_into_blocks(instrs):
    blocks = []
    cur_block = []
    block_name = None
    for i in instrs:
        if not isinstance(i, instructions.LabelDefine):
            cur_block.append(i)
        if is_block_boundary(i):
            if isinstance(i, instructions.LabelDefine):
                cur_block.append(instructions.JumpRelative(1))

            blocks.append(instructions.Block(
                None,
                None,
                block_name,
                cur_block
            ))
            cur_block = []
            if isinstance(i, instructions.LabelDefine):
                block_name = i.name
            else:
                block_name = None

    cur_block.append(instructions.JumpRelative(1))
    blocks.append(instructions.Block(
        None,
        None,
        block_name,
        cur_block
    ))

    return blocks

def split_blocks_into_kiloblocks(blocks: list[instructions.Block]):
    kiloblocks = [instructions.KiloBlock(1, [])]
    i = 0
    for block in blocks:
        i += 1
        if i >= 256:
            i = 1
            kiloblocks.append(instructions.KiloBlock(len(kiloblocks) + 1, []))
        block.myid = i
        block.kiloblock = kiloblocks[-1]
        kiloblocks[-1].blocks.append(block)
    return kiloblocks

class Program:
    def __init__(self, instrs):
        blocks = split_program_into_blocks(instrs)
        self.kiloblocks = split_blocks_into_kiloblocks(blocks)

    def find_block(self, name):
        if name == "exit":
            return 0, 0
        for kiloblock in self.kiloblocks:
            for block in kiloblock.blocks:
                if block.name == name:
                    i = kiloblock.myid
                    j = block.myid
                    return i, j
        raise ValueError(f"Block not found: {name}")
    
    def find_next_block(self, block: instructions.Block):
        i = block.kiloblock.myid
        j = block.myid
        j += 1
        if j >= 255:
            j -= 255
            i += 1
            assert i < 255
        return i, j

    def program_prologue(self):
        return "+>+<[[>>+<<-]>[>>+<<-]>>"

    def program_epilogue(self):
        return "\n-]" * len(self.kiloblocks) + "<<<]"
    
    def kiloblock_prologue(self, kiloblock: instructions.KiloBlock):
        name = f"kiloblock_{kiloblock.myid}"
        name_line = f"{concater.sanitize(name)}:"
        return f"\n{name_line}\n->+<[>-]>[>]<[-<<[>+<-]>\n"

    def kiloblock_epilogue(self, kiloblock: instructions.KiloBlock):
        return "\nend_kiloblock -" + "]" * len(kiloblock.blocks) + " >]<["

    def block_prologue(self, block: instructions.Block):
        name = block.name
        if name is None:
            name = f"block_{block.myid}"
        name_line = f"{concater.sanitize(name)}:"

        return f"\n{name_line}\n->+<[>-]>[>]<[-"

    def block_epilogue(self):
        return "\n]<["

    def assemble_block(self, block: instructions.Block):
        concater.init_block()
        for inst in block.insts:
            inst.evaluate(self, block, True)
        return (
            self.block_prologue(block) +
            concater.get_block_code() +
            self.block_epilogue()
        )

    def assemble_kiloblock(self, kiloblock: instructions.KiloBlock):
        return (
            self.kiloblock_prologue(kiloblock) +
            '\n'.join([
                self.assemble_block(block)
                for block in kiloblock.blocks
            ]) +
            self.kiloblock_epilogue(kiloblock)
        )

    def assemble(self):
        return (
            self.program_prologue() +
            '\n'.join([
                self.assemble_kiloblock(kiloblock)
                for kiloblock in self.kiloblocks
            ]) +
            self.program_epilogue()
        )

def parse(s):
    insts = []
    for line in s.split("\n"):
        if ";" in line:
            line = line[:line.find(";")]
        if line.isspace() or not line:
            continue
        line = line.strip(" ")
        if line.endswith(":"):
            insts.append(instructions.LabelDefine(line[:-1]))
            continue
        if " " not in line:
            mnemonic = line
            args = []
        else:
            mnemonic = line[:line.find(" ")]
            args_str = line[line.find(" "):].strip(" ")
            args = []
            for arg_s in args_str.split(" "):
                arg = arg_s.strip()
                if arg in regs:
                    args.append(regs[arg])
                    continue
                if arg[0] == "<" and arg[-1] == ">":
                    args.append(instructions.Label(arg[1:-1]))
                    continue
                if arg[0] == '"' and arg[-1] == '"':
                    args.append(unquote(arg[1:-1]))
                    continue

                if arg.startswith("0x"):
                    imm = int(arg[2:], 16)
                elif arg.startswith("0o"):
                    imm = int(arg[2:], 8)
                elif arg.startswith("0b"):
                    imm = int(arg[2:], 2)
                else:
                    imm = int(arg)
                args.append(Immediate(imm))

        op = MNEMONICS[mnemonic]
        op_args = op.__match_args__
        op_fields = op.__dataclass_fields__
        if len(args) != len(op_args):
            raise ValueError(f"Wrong number of arguments for {mnemonic}, expected {len(op_args)}, got {len(args)}")

        for op_arg, arg in zip(op_args, args):
            tp = op_fields[op_arg].type
            if isinstance(tp, str):
                tp = getattr(instructions, tp, None) or getattr(registers, tp, None)
            if tp is Register:
                tps = ["register"]
            elif tp is RegisterOrImmediate:
                tps = ["register", "immediate"]
            elif tp is int:
                tps = ["immediate"]
            elif tp is instructions.Label:
                tps = ["label"]
            elif tp is str:
                tps = ["string"]
            else:
                raise NotImplementedError()

            if isinstance(arg, Register):
                arg_tp = "register"
            elif isinstance(arg, Immediate):
                arg_tp = "immediate"
            elif isinstance(arg, instructions.Label):
                arg_tp = "label"
            elif isinstance(arg, str):
                arg_tp = "string"
            else:
                raise NotImplementedError()

            if arg_tp not in tps:
                expected = " or ".join(tps)
                raise ValueError(f"Wrong type for argument {op_arg} or {mnemonic}, expected: {expected}, got {arg_tp}")

        insts.append(op(*args))
    return insts

if __name__ == "__main__":
    import sys
    if len(sys.argv) != 3:
        print("usage: asm in.cbf out.b", file=sys.stderr)
        exit(1)

    with open(sys.argv[1]) as f:
        in_contents = f.read()

    instrs = parse(in_contents)
    prog = Program(instrs)
    out_contents = prog.assemble()

    with open(sys.argv[2], "w") as f:
        f.write(out_contents)
        f.write("\n")
