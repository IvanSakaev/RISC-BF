li s0, 10  # count of printed numbers
li s1, 0
li s2, 1
loop:
    add t0, s1, s2
    mv s1, s2
    mv s2, t0
    out s2
    addi s0, s0, -1
    bgtz s0, loop
