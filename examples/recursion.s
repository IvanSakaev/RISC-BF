factorial:
	addi	sp, sp, -16
	sw	ra, 12(sp)                      # 4-byte Folded Spill
	sw	s0, 8(sp)                       # 4-byte Folded Spill
	addi	s0, sp, 16
	sw	a0, -16(s0)
	lw	a0, -16(s0)
	bnez	a0, LBB0_2
	j	LBB0_1
LBB0_1:
	li	a0, 1
	sw	a0, -12(s0)
	j	LBB0_3
LBB0_2:
	lw	a0, -16(s0)
	addi	a0, a0, -1
	call	factorial
	lw	a1, -16(s0)
	mul	a0, a0, a1
	sw	a0, -12(s0)
	j	LBB0_3
LBB0_3:
	lw	a0, -12(s0)
	lw	ra, 12(sp)                      # 4-byte Folded Reload
	lw	s0, 8(sp)                       # 4-byte Folded Reload
	addi	sp, sp, 16
	ret
_start:
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
