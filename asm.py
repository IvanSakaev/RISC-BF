#! /bin/python
import itertools
from urllib.parse import unquote

import instructions
from instructions import MNEMONICS, is_block_boundary
from registers import (
    ROOT,
    Immediate,
    Instruction,
    Register,
    RegisterOrImmediate,
    addressing,
    next1,
    next2,
    regs,
    scraps,
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

def sanitize(name):
    name = name \
        .replace("+", "_") \
        .replace("-", "_") \
        .replace("<", "_") \
        .replace(">", "_") \
        .replace("[", "_") \
        .replace("]", "_") \
        .replace(".", "_") \
        .replace(",", "_") \
        .replace("#", "_")
    return name

def move(src, *dsts, root=ROOT, negative=False):
    if not isinstance(negative, list):
        negative = itertools.repeat(negative)

    out = src.to(root)+"["
    cur_reg = src
    for dst, neg in zip(dsts, negative):
        out += dst.to(cur_reg)
        out += "-" if neg else "+"
        cur_reg = dst
    out += src.to(cur_reg)+"-]"
    out += root.to(src)
    return out

def change(from_, to):
    if from_ == to:
        return ""
    elif from_ > to:
        return "-"*(from_-to)
    return "+"*(to-from_)

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
        return (
        "+>+<["
        "[>>+<<-]>[>>+<<-]>>"
        )

    def program_epilogue(self):
        return "\n-" + "]" * len(self.kiloblocks) + "<<<]"
    
    def kiloblock_prologue(self, kiloblock: instructions.KiloBlock):
        name = f"kiloblock_{kiloblock.myid}"
        name_line = f"{sanitize(name)}:\n"
        return (
        f"\n{name_line}"
        # next1     next2   block_id1  'block_id2   0       0
        "->+>+<<"
        # next1     next2   block_id1  'block_id2   1       1
        "[>->-<]>[>-]<[-<"  # ifnot
        # next1     next2   block_id1  '0           0       0
        "<[>+<-]>\n"
        # next1     next2   0          'block_id1   0       0
        )

    def kiloblock_epilogue(self, kiloblock: instructions.KiloBlock):
        return "\nend_kiloblock -" + "]" * len(kiloblock.blocks) + " >]<["

    def block_prologue(self, block: instructions.Block):
        name = block.name
        if name is None:
            name = f"block_{block.myid}"
        name_line = f"{sanitize(name)}:\n"

        return (
        f"\n{name_line}"
        # next1     next2   0          'block_id1   0       0
        "->+>+<<"
        # next1     next2   0          'block_id1   1       1
        "[>->-<]>[>-]<[->\n"
        # next1     next2   0           block_id1   0      '0
        )

    def block_epilogue(self):
        return "\nend <]<["

    def assemble_instruction(self, inst: Instruction, cur_block: instructions.Block, comments=False):
        if comments:
            rem = lambda x: x + "\n    "
        else:
            rem = lambda x: ""

        if isinstance(inst, instructions.Jump):
            i, j = self.find_block(inst.target)
            return (
                rem(f"jmp {sanitize(inst.target)}")
              + next1.to()
              + change(0, i)
              + next2.to(next1)
              + change(0, j)
              + next2.back()
            )

        elif isinstance(inst, instructions.JumpConditional):
            next_i, next_j = self.find_next_block(cur_block)
            jump_i, jump_j = self.find_block(inst.target)
            return (
                rem(f"jnz {inst.cond} {sanitize(inst.target)}")
              + move(inst.cond, scraps[0], scraps[1])
              + move(scraps[1], inst.cond)
              + next1.to()
              + ("+" * next_i) # set the default value
              + next2.to(next1)
              + ("+" * next_j) # set the default value
              + scraps[0].to(next2)
              + "[" # condition is true
              +   next1.to(scraps[0])
              +   change(next_i, jump_i)
              +   next2.to(next1)
              +   change(next_j, jump_j)
              +   scraps[0].to(next2)
              +   "[-]"
              + "]"
              + scraps[0].back()
            )

        elif isinstance(inst, instructions.JumpRelative):
            next_i, next_j = self.find_next_block(cur_block)
            return (
                rem(f"jmr {inst.offset}")
              + next1.to()
              + "+" * next_i
              + next2.to(next1)
              + "+" * next_j
              + next2.back()
            )

        elif isinstance(inst, instructions.Move):
            header = rem(f"mov {inst.dst} {inst.src}")
            if isinstance(inst.src, Immediate):
                return (
                    header
                  + inst.dst.to()
                  + "[-]"
                  + "+"*inst.src
                  + inst.dst.back()
                )
            else:
                return (
                     header
                   + inst.dst.to()
                   + "[-]"
                   + move(inst.src, inst.dst, root=inst.dst)
                   + inst.dst.back()
                )

        elif isinstance(inst, instructions.Copy):
            return (
                rem(f"cpy {inst.dst} {inst.src}")
              + inst.dst.to()
              + "[-]"
              + move(inst.src, scraps[0], inst.dst, root=inst.dst)
              + move(scraps[0], inst.src, root=inst.dst)
              + inst.dst.back()
            )

        elif isinstance(inst, instructions.MovAdd):
            header = rem(f"addm {inst.dst} {inst.src}")

            if isinstance(inst.src, Immediate):
                return (
                    header
                  + inst.dst.to()
                  + "+"*inst.src
                  + inst.dst.back()
                )
            else:
                return (
                    header
                  + move(inst.src, inst.dst)
                )

        elif isinstance(inst, instructions.Add):
            return (
                rem(f"add {inst.dst} {inst.src}")
              + move(inst.src, inst.dst, scraps[0])
              + move(scraps[0], inst.src)
            )

        elif isinstance(inst, instructions.MovSub):
            header = rem(f"subm {inst.dst} {inst.src}")

            if isinstance(inst.src, Immediate):
                return (
                    header
                  + inst.dst.to()
                  + "-"*inst.src
                  + inst.dst.back()
                )
            else:
                return (
                    header
                  + move(inst.src, inst.dst, negative=True)
                )

        elif isinstance(inst, instructions.Sub):
            return (
                rem(f"sub {inst.dst} {inst.src}")
              + move(inst.src, inst.dst, scraps[0], negative=[1,0])
              + move(scraps[0], inst.src)
            )

        elif isinstance(inst, instructions.Raw):
            return inst.code

        elif isinstance(inst, instructions.Output):
            label = rem(f"out {inst.reg}")

            if isinstance(inst.reg, Immediate):
                return (
                    label
                  + scraps[0].to()
                  + change(0, inst.reg)
                  + ".[-]"
                  + scraps[0].back()
                )
            else:
                return (
                    label
                  + inst.reg.to()
                  + "."
                  + inst.reg.back()
                )

        elif isinstance(inst, instructions.Print):
            return (
                rem(f"prt {sanitize(inst.val)}")
              + scraps[0].to()
              + (''.join(map(
                lambda c: ("+"*ord(c))+".[-]",
                inst.val
              )))
              + scraps[0].back()
            )

        elif isinstance(inst, instructions.Load):
            label = rem(f"lda {inst.dst} {inst.addr}")

            if isinstance(inst.addr, Immediate):
                src = Register(13+inst.addr)
                return (
                    label
                  + inst.dst.to()
                  + "[-]"
                  + move(src, inst.dst, scraps[0], root=inst.dst)
                  + move(scraps[0], src, root=inst.dst)
                  + inst.dst.back()
                )
            else:
                return (
                    label
                  + move(inst.addr, addressing[0], addressing[1], scraps[0])
                  + move(scraps[0], inst.addr)
                  + inst.dst.to()
                  + "[-]"
                  + addressing[0].to(inst.dst)
                  + "[>>[>+<-]<[>+<-]<[>+<-] >>>>[<<<<+>>>>-]<<< -]"
                  + ">>>>[<+<+>>-]<[>+<-]<<"
                  + "[<<[>>>>+<<<<-] >>[<+>-]>[<+>-]<< -]<"
                  + move(addressing[2], inst.dst, root=addressing[0])
                  + addressing[0].back()
                )

        elif isinstance(inst, instructions.Store):
            label = rem(f"sta {inst.addr} {inst.src}")

            if isinstance(inst.addr, Immediate):
                dst = Register(13+inst.addr)
                return (
                    label
                  + dst.to()
                  + "[-]"
                  + dst.back()
                  + move(inst.src, scraps[0], dst)
                  + move(scraps[0], inst.src)
                )
            else:
                return (
                    label
                  + move(inst.addr, addressing[0], addressing[1], scraps[0])
                  + move(scraps[0], inst.addr)
                  + (
                      addressing[2].to()
                    + "+"*inst.src
                    + addressing[2].back() if isinstance(inst.src, Immediate) else move(inst.src, addressing[2], scraps[0])
                    + move(scraps[0], inst.src)
                    )
                  + addressing[0].to()
                  + "[>>[>+<-]<[>+<-]<[>+<-] >>>>[<<<<+>>>>-]<<< -]"
                  + ">>>>[-]<<[>>+<< -]<"
                  + "[<<[>>>>+<<<<-] >>[<+>-]< -]<"
                  + addressing[0].back()
                )

        elif isinstance(inst, instructions.Call):
            next_i, next_j = self.find_next_block(cur_block)
            return (
                rem(f"call {sanitize(inst.target)}")
              + self.assemble_instruction(
                    instructions.Store(
                        regs["SP"],
                        Immediate(next_i)
                    ),
                    cur_block
                )
              + regs["SP"].to()
              + "+"
              + regs["SP"].back()
              + self.assemble_instruction(
                    instructions.Store(
                        regs["SP"],
                        Immediate(next_j)
                    ),
                    cur_block
                )
              + regs["SP"].to()
              + "+"
              + regs["SP"].back()
              + self.assemble_instruction(
                    instructions.Jump(inst.target),
                    cur_block
                )
            )

        elif isinstance(inst, instructions.Return):
            return (
                rem("ret")
              + regs["SP"].to()
              + "-"
              + regs["SP"].back()
              + self.assemble_instruction(
                    instructions.Load(
                        next2,
                        regs["SP"]
                    ),
                    cur_block
                )
              + regs["SP"].to()
              + "-"
              + regs["SP"].back()
              + self.assemble_instruction(
                    instructions.Load(
                        next1,
                        regs["SP"]
                    ),
                    cur_block
                )
            )

        return type(inst).__name__

    def assemble_block(self, block: instructions.Block):
        return (
            self.block_prologue(block) +
            '\n'.join([
                    "  " + self.assemble_instruction(
                    inst, block, comments=True
                )
                for inst in block.insts
            ]) +
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
