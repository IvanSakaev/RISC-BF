from dataclasses import dataclass

class Instruction: ...

class Register:
    def __init__(self, num):
        self.num = num

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

def reg(n): return Register(n)

@dataclass
class LabelDefine(Instruction):
    name: str

@dataclass
class Jump(Instruction):
    target: str

@dataclass
class JumpConditional(Instruction):
    cond: Register
    target: str

@dataclass
class JumpRelative(Instruction):
    offset: int

@dataclass
class AddI(Instruction):
    reg: Register
    val: int

@dataclass
class SubI(Instruction):
    reg: Register
    val: int

@dataclass
class SetI(Instruction):
    reg: Register
    val: int

@dataclass
class MovAdd(Instruction):
    dst: Register
    src: Register

@dataclass
class CopyAdd(Instruction):
    dst: Register
    src: Register

@dataclass
class Raw(Instruction):
    code: str

@dataclass
class Output(Instruction):
    reg: Register

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

def move(src, *dsts, root=reg(0)):
    out = src.to_rel(root)+"["
    cur_reg = src
    for dst in dsts:
        out += dst.to_rel(cur_reg)
        out += "+"
        cur_reg = dst
    out += src.to_rel(cur_reg)+"-]"
    out += root.to_rel(src)
    return out

class Program:
    def __init__(self, instructions):
        self.blocks = split_program_into_blocks(instructions)

    def find_block(self, name):
        for ind in range(len(self.blocks)):
            if self.blocks[ind].name == name:
                return ind
        raise ValueError(f"Block not found: {name}")

    def resolve_jump(self, target, cur_block_id):
        new_block_id = self.find_block(target)
        out = (new_block_id - cur_block_id) % len(self.blocks)
        if out == 0:
            out = len(self.blocks)
        return out

    def program_prologue(self):
        return "+["

    def program_epilogue(self):
        return "]"

    def block_prologue(self, block_id):
        name = self.blocks[block_id].name
        if name is None:
            name = f"block_{block_id}"
        name_line = f"{sanitize(name)}:\n"

        return (
        f"\n{name_line}"
        #'block_id 0        0
        "-[->+>+<<]>>"
        # 0        block_id'block_id
        "[<<+>>-]"
        # block_id block_id'0
        "+<[>-<[-]]>"
        # block_id 0       '(block_id==0)
        "[[-]\n"
        # the block begins
        # 0        0       '0  
        )

    def block_epilogue(self):
        return "\nend ]<<"

    def assemble_instruction(self, inst, cur_block_id):
        scrap = reg(-1)
        jmp = reg(-2)
        scrap2 = jmp

        if isinstance(inst, Raw):
            return inst.code
        elif isinstance(inst, Output):
            return (
               f"out {inst.reg}\n    "
              + inst.reg.to()
              + "."
              + inst.reg.back()
            )
        elif isinstance(inst, Jump):
            return (
               f"jmp {sanitize(inst.target)}\n    "
              + jmp.to()
              + "+"*self.resolve_jump(
                    inst.target,
                    cur_block_id
                )
              + jmp.back()
            )
        elif isinstance(inst, JumpConditional):
            return (
               f"jnz {inst.cond} {sanitize(inst.target)}\n    "
              + move(inst.cond, scrap, scrap2)
              + move(scrap2, inst.cond)
              + jmp.to()
              + "+" # set the default value
              + scrap.to_rel(jmp)
              + "[" # condition is true
              +   jmp.to_rel(scrap)
              +   ("+"*(self.resolve_jump(
                      inst.target,
                      cur_block_id
                  )-1))
              +   scrap.to_rel(jmp)
              +   "[-]"
              + "]"
              + scrap.back()
            )
        elif isinstance(inst, JumpRelative):
            return (
               f"jmr {inst.offset}\n    "
              + jmp.to()
              + "+"*inst.offset
              + jmp.back()
            )
        elif isinstance(inst, MovAdd):
            return (
               f"addm {inst.dst} {inst.src}\n    "
             + move(inst.src, inst.dst)
            )
        elif isinstance(inst, CopyAdd):
            return (
               f"add {inst.dst} {inst.src}\n    "
             + move(inst.src, inst.dst, scrap)
             + move(scrap, inst.src)
            )
        elif isinstance(inst, SubI):
            return (
               f"subi {inst.reg} {inst.val}\n    "
              + inst.reg.to()
              + "-"*inst.val
              + inst.reg.back()
            )
        elif isinstance(inst, SetI):
            return (
               f"seti {inst.reg} {inst.val}\n    "
              + inst.reg.to()
              + "[-]"
              + "+"*inst.val
              + inst.reg.back()
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


if __name__ == "__main__":
    # pseudocode:
    # if False:
    #   print("!")
    # rep = 9
    # n1 = 0
    # n2 = 1
    # while rep:
    #   sum = 0
    #   sum += n1
    #   sum += n2
    #   n1 = n2
    #   n2 = sum
    #   rep -= 1
    # print(n1)

    rep = reg(1)
    n1 = reg(2)
    n2 = reg(3)
    sum = reg(4)

    instructions = [
        Jump("begin"),
          SetI(n1, ord("!")),
          Output(n1),
        LabelDefine("begin"),
          SetI(rep, 9),
          SetI(n1, 0),
          SetI(n2, 1),
        LabelDefine("loop"),
          SetI(sum, 0),
          MovAdd(sum, n1),
          CopyAdd(sum, n2),
          SetI(n1, 0),
          MovAdd(n1, n2),
          MovAdd(n2, sum),
          SubI(rep, 1),
        JumpConditional(rep, "loop"),
          Output(n1)
    ]

    prog = Program(instructions)
    print(prog.assemble())
