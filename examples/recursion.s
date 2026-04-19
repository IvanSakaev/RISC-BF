_start:
    li a0, 5        # n = 5
    jal ra, fact    # fact(n)

    # результат уже в a0 -> возвращаем как код выхода
    out a0
    j last


# fact(n)
# a0 = n
# return a0 = n!

fact:
    addi sp, sp, -16
    sw ra, 12(sp)
    sw a0, 8(sp)

    li t0, 1
    ble a0, t0, base_case

    addi a0, a0, -1
    jal ra, fact

    lw t1, 8(sp)
    mul a0, a0, t1
    j end

base_case:
    li a0, 1

end:
    lw ra, 12(sp)
    addi sp, sp, 16
    ret
last:
    nop
