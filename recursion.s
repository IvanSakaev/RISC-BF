	.attribute	4, 16
	.attribute	5, "rv32i2p1_m2p0_zmmul1p0"
	.file	"recursion.c"
	.text
	.globl	factorial                       # -- Begin function factorial
	.p2align	2
	.type	factorial,@function
factorial:                              # @factorial
# %bb.0:
	addi	sp, sp, -16
	sw	ra, 12(sp)                      # 4-byte Folded Spill
	sw	s0, 8(sp)                       # 4-byte Folded Spill
	addi	s0, sp, 16
	sw	a0, -16(s0)
	lw	a0, -16(s0)
	bnez	a0, .LBB0_2
	j	.LBB0_1
.LBB0_1:
	li	a0, 1
	sw	a0, -12(s0)
	j	.LBB0_3
.LBB0_2:
	lw	a0, -16(s0)
	addi	a0, a0, -1
	call	factorial
	lw	a1, -16(s0)
	mul	a0, a0, a1
	sw	a0, -12(s0)
	j	.LBB0_3
.LBB0_3:
	lw	a0, -12(s0)
	lw	ra, 12(sp)                      # 4-byte Folded Reload
	lw	s0, 8(sp)                       # 4-byte Folded Reload
	addi	sp, sp, 16
	ret
.Lfunc_end0:
	.size	factorial, .Lfunc_end0-factorial
                                        # -- End function
	.globl	_start                          # -- Begin function _start
	.p2align	2
	.type	_start,@function
_start:                                 # @_start
# %bb.0:
	addi	sp, sp, -16
	sw	ra, 12(sp)                      # 4-byte Folded Spill
	sw	s0, 8(sp)                       # 4-byte Folded Spill
	addi	s0, sp, 16
	li	a0, 3
	call	factorial
	lw	ra, 12(sp)                      # 4-byte Folded Reload
	lw	s0, 8(sp)                       # 4-byte Folded Reload
	addi	sp, sp, 16
	ret
.Lfunc_end1:
	.size	_start, .Lfunc_end1-_start
                                        # -- End function
	.ident	"clang version 22.1.1"
	.section	".note.GNU-stack","",@progbits
	.addrsig
	.addrsig_sym factorial
