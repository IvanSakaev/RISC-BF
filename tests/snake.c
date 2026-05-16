#include "dbf.h"

#define WIDTH 20
#define HEIGHT 20

int gameover, score;
int x, y, fruitx, fruity, flag;
int tailX[100], tailY[100];
int tailLen;


void setup() {
    gameover = 0;
    x = WIDTH / 2;
    y = HEIGHT / 2;
    fruitx = dbf_rand() % (WIDTH - 1) + 1; // Avoid borders
    fruity = dbf_rand() % (HEIGHT - 1) + 1;
    score = 0;
    tailLen = 0;
    flag = 0; // No initial direction
}

void draw() {
    dbf_print("\n");
    for (int i = 0; i < WIDTH + 2; i++) dbf_print("#");
    dbf_print("\n");

    for (int i = 0; i < HEIGHT; i++) {
        for (int j = 0; j < WIDTH; j++) {
            if (j == 0) dbf_print("#");
            if (i == y && j == x) dbf_print("O");
            else if (i == fruity && j == fruitx) dbf_print("*");
            else {
                int isTail = 0;
                for (int k = 0; k < tailLen; k++) {
                    if (tailX[k] == j && tailY[k] == i) {
                        dbf_print("o");
                        isTail = 1;
                        break;
                    }
                }
                if (!isTail) dbf_print(" ");
            }
            if (j == WIDTH - 1) dbf_print("#");
        }
        dbf_print("\n");
    }

    for (int i = 0; i < WIDTH + 2; i++) dbf_print("#");
    dbf_print("\n");
    dbf_print("Score: ");
    dbf_print_num(score);
    dbf_print("\nPress W/A/S/D to move, X to quit.\n");
}

void move_snake() {
    int prevX = tailX[0];
    int prevY = tailY[0];
    int prev2X, prev2Y;
    tailX[0] = x;
    tailY[0] = y;
    for (int i = 1; i < tailLen; i++) {
        prev2X = tailX[i];
        prev2Y = tailY[i];
        tailX[i] = prevX;
        tailY[i] = prevY;
        prevX = prev2X;
        prevY = prev2Y;
    }

    switch (flag) {
        case 1: x--;
            break;
        case 2: x++;
            break;
        case 3: y--;
            break;
        case 4: y++;
            break;
    }

    if (x >= WIDTH || x < 0 || y >= HEIGHT || y < 0) gameover = 1;

    for (int i = 0; i < tailLen; i++) {
        if (tailX[i] == x && tailY[i] == y) gameover = 1;
    }

    if (x == fruitx && y == fruity) {
        score += 10;
        fruitx = dbf_rand() % (WIDTH - 1) + 1;
        fruity = dbf_rand() % (HEIGHT - 1) + 1;
        tailLen++;
    }
}

void input() {
    char ch[2];
    dbf_read_ecall(ch, 1);
    switch (ch[0]) {
        case 'a':
            if (flag != 2) flag = 1;
            break; // Left, not if right
        case 'd':
            if (flag != 1) flag = 2;
            break; // Right, not if left
        case 'w':
            if (flag != 4) flag = 3;
            break; // Up, not if down
        case 's':
            if (flag != 3) flag = 4;
            break; // Down, not if up
        case '\n':
            move_snake();
            draw();
            break;
        case 'x':
            dbf_println("bye");
            gameover = 1;
            break;
    }
}

void _start() {
    setup();
    draw();
    while (!gameover) {
        input();
    }
    dbf_print("Game Over! Final Score: ");
    dbf_print_num(score);
    dbf_print("\n");
}
