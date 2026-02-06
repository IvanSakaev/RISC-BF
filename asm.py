from dataclasses import dataclass
import itertools
from urllib.parse import unquote

class Instruction: ...

class Register:
    def __init__(self, num):
        self.num = num
    def is_immediate(self): return False

    def to(self):
        if self.num > 0:
            return ">"*self.num
        else:
            return "<"*(-self.num)

    def to_rel(self, reg):
        if self.num > reg.num:
            return ">"*(self.num - reg.num)
        else:
            return "<"*(reg.num - self.num)

    def back(self):
        if self.num > 0:
            return "<"*self.num
        else:
            return ">"*(-self.num)

    def back_rel(self, reg):
        if self.num > reg.num:
            return "<"*(self.num - reg.num)
        else:
            return ">"*(reg.num - self.num)

    def __repr__(self):
        if self.num == -2:
            return "J"
        elif self.num == -1:
            return "S"
        return f"R{self.num}"

ROOT = Register(0)

regs = {
    "R1": Register(1),
    "R2": Register(2),
    "R3": Register(3),
    "R4": Register(4),
    "R5": Register(5),
    "R6": Register(6),
    "R7": Register(7),
    "R8": Register(8)
}

class Immediate(int):
    def is_immediate(self): return True

class Label(str): ...

RegisterOrImmediate = Register | int

@dataclass
class LabelDefine(Instruction):
    name: Label

MNEMONICS = dict()

@dataclass
class Jump(Instruction):
    target: Label
MNEMONICS["jmp"] = Jump

@dataclass
class JumpConditional(Instruction):
    cond: Register
    target: Label
MNEMONICS["jnz"] = JumpConditional

@dataclass
class JumpRelative(Instruction):
    offset: Immediate
MNEMONICS["jmr"] = JumpRelative

@dataclass
class Move(Instruction):
    dst: Register
    src: RegisterOrImmediate
MNEMONICS["mov"] = Move

@dataclass
class Copy(Instruction):
    dst: Register
    src: Register
MNEMONICS["cpy"] = Copy

@dataclass
class MovAdd(Instruction):
    dst: Register
    src: RegisterOrImmediate
MNEMONICS["addm"] = MovAdd

@dataclass
class Add(Instruction):
    dst: Register
    src: Register
MNEMONICS["add"] = Add

@dataclass
class MovSub(Instruction):
    dst: Register
    src: RegisterOrImmediate
MNEMONICS["subm"] = MovSub

@dataclass
class Sub(Instruction):
    dst: Register
    src: Register
MNEMONICS["sub"] = Sub

@dataclass
class Raw(Instruction):
    code: str
MNEMONICS["raw"] = Raw

@dataclass
class Load(Instruction):
    dst: Register
    addr: RegisterOrImmediate
MNEMONICS["lda"] = Load

@dataclass
class Store(Instruction):
    addr: RegisterOrImmediate
    src: Register
MNEMONICS["sta"] = Store

@dataclass
class Output(Instruction):
    reg: RegisterOrImmediate
MNEMONICS["out"] = Output

@dataclass
class Print(Instruction):
    val: str
MNEMONICS["prt"] = Print

@dataclass
class Block(Instruction):
    name: str | None
    insts: list[Instruction]

class _ExitBlock:
    def __init__(self):
        self.name = "exit"
EXIT_BLOCK = _ExitBlock()

def is_block_boundary(inst):
    return isinstance(inst, (
        LabelDefine,
        JumpRelative,
        JumpConditional,
        Jump
    ))

def split_program_into_blocks(instructions):
    blocks = []
    cur_block = []
    block_name = None
    for i in instructions:
        if not isinstance(i, LabelDefine):
            cur_block.append(i)
        if is_block_boundary(i):
            if isinstance(i, LabelDefine):
                cur_block.append(JumpRelative(1))

            blocks.append(Block(
                block_name,
                cur_block
            ))
            cur_block = []
            if isinstance(i, LabelDefine):
                block_name = i.name
            else:
                block_name = None

    cur_block.append(JumpRelative(1))
    blocks.append(Block(
        block_name,
        cur_block
    ))

    blocks.append(EXIT_BLOCK)

    return blocks

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

    out = src.to_rel(root)+"["
    cur_reg = src
    for dst, neg in zip(dsts, negative):
        out += dst.to_rel(cur_reg)
        out += "-" if neg else "+"
        cur_reg = dst
    out += src.to_rel(cur_reg)+"-]"
    out += root.to_rel(src)
    return out

def change(from_, to):
    if from_ == to:
        return ""
    elif from_ > to:
        return "-"*(from_-to)
    return "+"*(to-from_)

class Program:
    def __init__(self, instructions):
        self.blocks = split_program_into_blocks(instructions)

    def find_block(self, name):
        for ind in range(len(self.blocks)):
            if self.blocks[ind].name == name:
                return ind+1
        raise ValueError(f"Block not found: {name}")

    def program_prologue(self):
        return (
        "+>+["
        "[-]<[>+<-]>"
        )

    def program_epilogue(self):
        return "]"

    def block_prologue(self, block_id):
        name = self.blocks[block_id].name
        if name is None:
            name = f"block_{block_id}"
        name_line = f"{sanitize(name)}:\n"

        return (
        f"\n{name_line}"
        # next  'block_id 0        0
        "-[->+>+<<]>>"
        # next   0        block_id'block_id
        "[<<+>>-]"
        # next   block_id block_id'0
        "+<[>-<[-]]>"
        # next   block_id 0       '(block_id==0)
        "[[-]\n"
        # next   the block begins
        # 0        0       '0  
        )

    def block_epilogue(self):
        return "\nend ]<<"

    def assemble_instruction(self, inst, cur_block_id):
        scrap = Register(-1)
        scrap2 = Register(-2)
        next = Register(-3)
        addr1 = Register(9)
        addr2 = Register(10)
        addr3 = Register(11)
        addr4 = Register(12)

        if isinstance(inst, Jump):
            return (
               f"jmp {sanitize(inst.target)}\n    "
              + next.to()
              + change(0, self.find_block(inst.target))
              + next.back()
            )

        elif isinstance(inst, JumpConditional):
            return (
               f"jnz {inst.cond} {sanitize(inst.target)}\n    "
              + move(inst.cond, scrap, scrap2)
              + move(scrap2, inst.cond)
              + next.to()
              + ("+"*(cur_block_id+2)) # set the default value
              + scrap.to_rel(next)
              + "[" # condition is true
              +   next.to_rel(scrap)
              +   change(cur_block_id, self.find_block(inst.target)-2)
              +   scrap.to_rel(next)
              +   "[-]"
              + "]"
              + scrap.back()
            )

        elif isinstance(inst, JumpRelative):
            return (
               f"jmr {inst.offset}\n    "
              + next.to()
              + "+"*(cur_block_id+inst.offset+1)
              + next.back()
            )

        elif isinstance(inst, Move):
            header = f"mov {inst.dst} {inst.src}\n    "
            if inst.src.is_immediate():
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
        
        elif isinstance(inst, Copy):
            return (
               f"cpy {inst.dst} {inst.src}\n    "
              + inst.dst.to()
              + "[-]"
              + move(inst.src, scrap, inst.dst, root=inst.dst)
              + move(scrap, inst.src, root=inst.dst)
              + inst.dst.back()
            )

        elif isinstance(inst, MovAdd):
            header = f"addm {inst.dst} {inst.src}\n    "

            if inst.src.is_immediate():
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

        elif isinstance(inst, Add):
            return (
               f"add {inst.dst} {inst.src}\n    "
             + move(inst.src, inst.dst, scrap)
             + move(scrap, inst.src)
            )

        elif isinstance(inst, MovSub):
            header = f"subm {inst.dst} {inst.src}\n    "

            if inst.src.is_immediate():
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

        elif isinstance(inst, Sub):
            return (
               f"sub {inst.dst} {inst.src}\n    "
             + move(inst.src, inst.dst, scrap, negative=[1,0])
             + move(scrap, inst.src)
            )

        elif isinstance(inst, Raw):
            return inst.code

        elif isinstance(inst, Output):
            if inst.reg.is_immediate():
                return (
                   f"out {inst.reg}\n    "
                  + scrap.to()
                  + change(0, inst.reg)
                  + ".[-]"
                  + scrap.back()
                )
            else:
                return (
                   f"out {inst.reg}\n    "
                  + inst.reg.to()
                  + "."
                  + inst.reg.back()
                )

        elif isinstance(inst, Print):
            return (
               f"prt {sanitize(inst.val)}\n    "
              + scrap.to()
              + (''.join(map(
                lambda c: ("+"*ord(c))+".[-]",
                inst.val
              )))
              + scrap.back()
            )

        elif isinstance(inst, Load):
            if inst.addr.is_immediate():
                src = Register(13+inst.addr)
                return (
                   f"lda {inst.dst} {inst.addr}\n    "
                  + inst.dst.to()
                  + "[-]"
                  + move(src, inst.dst, scrap, root=inst.dst)
                  + move(scrap, src, root=inst.dst)
                  + inst.dst.back()
                )
            else:
                return (
                   f"lda {inst.dst} {inst.addr}\n    "
                  + move(inst.addr, addr1, addr2, scrap)
                  + move(scrap, inst.addr)
                  + inst.dst.to()
                  + "[-]"
                  + addr1.to_rel(inst.dst)
                  + "[>>[>+<-]<[>+<-]<[>+<-] >>>>[<<<<+>>>>-]<<< -]"
                  + ">>>>[<<+<<+>>>> -]<<<<[>>>>+<<<< -]>"
                  + "[<<[>>>>+<<<<-] >>[<+>-]>[<+>-]<< -]<"
                  + move(addr3, inst.dst, root=addr1)
                  + addr1.back()
                )

        elif isinstance(inst, Store):
            if inst.addr.is_immediate():
                dst = Register(13+inst.addr)
                return (
                   f"sta {inst.addr} {inst.src}\n    "
                  + move(inst.src, scrap, scrap2)
                  + move(scrap2, inst.src)
                  + dst.to()
                  + "[-]"
                  + move(scrap, dst, root=dst)
                  + dst.back()
                )
            else:
                return (
                   f"sta {inst.addr} {inst.src}\n    "
                  + move(inst.addr, addr1, addr2, scrap)
                  + move(scrap, inst.addr)
                  + move(inst.src, addr3, scrap)
                  + move(scrap, inst.src)
                  + addr1.to()
                  + "[>>[>+<-]<[>+<-]<[>+<-] >>>>[<<<<+>>>>-]<<< -]"
                  + ">>>>[-]<<[>>+<< -]<"
                  + "[<<[>>>>+<<<<-] >>[<+>-]< -]<"
                  + addr1.back()
                )

        return type(inst).__name__

    def assemble_block(self, cur_block_id):
        block = self.blocks[cur_block_id]

        if block is EXIT_BLOCK:
            return "\n-"

        return (self.block_prologue(cur_block_id)
              + '\n'.join(map(
                  lambda i:
                      "  " + self.assemble_instruction(
                          i, cur_block_id
                      ),
                  block.insts
                ))
              + self.block_epilogue())

    def assemble(self):
        return (self.program_prologue()
              + ''.join(map(
                  self.assemble_block,
                  range(len(self.blocks))
                ))
              + self.program_epilogue())

def parse(s):
    insts = []
    for line in s.split("\n"):
        if ";" in line:
            line = line[:line.find(";")]
        if line.isspace() or not line: continue
        line = line.strip(" ")
        if line.endswith(":"):
            insts.append(LabelDefine(line[:-1]))
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
                    args.append(Label(arg[1:-1]))
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
            elif tp is Label:
                tps = ["label"]
            elif tp is str:
                tps = ["string"]
            else:
                raise NotImplementedError()

            if isinstance(arg, Register):
                arg_tp = "register"
            elif isinstance(arg, Immediate):
                arg_tp = "immediate"
            elif isinstance(arg, Label):
                arg_tp = "label"
            elif isinstance(arg, str):
                arg_tp = "string"
            else: raise NotImplementedError()

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

    instructions = parse(in_contents)
    prog = Program(instructions)
    out_contents = prog.assemble()

    with open(sys.argv[2], "w") as f:
        f.write(out_contents)
