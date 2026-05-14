#include <stdio.h>
#include <stdlib.h>
#include <time.h>
#include <ctype.h>  // For tolower()

#ifdef _WIN32
#include <conio.h>    // For kbhit() and getch()
#include <windows.h>  // For Sleep()
#else
#include <termios.h>  // For terminal modes
#include <unistd.h>   // For usleep(), STDIN_FILENO
#include <sys/select.h>  // For select()
#include <fcntl.h>    // For fcntl()
#endif

#define WIDTH 20
#define HEIGHT 20

int gameover, score;
int x, y, fruitx, fruity, flag;
int tailX[100], tailY[100];
int tailLen;

#ifndef _WIN32
// Unix implementation of kbhit() using select()
struct termios orig_termios;

void reset_terminal_mode() {
    tcsetattr(STDIN_FILENO, TCSANOW, &orig_termios);
}

void set_terminal_mode() {
    struct termios new_termios;
    tcgetattr(STDIN_FILENO, &orig_termios);
    new_termios = orig_termios;
    new_termios.c_lflag &= ~(ICANON | ECHO);
    tcsetattr(STDIN_FILENO, TCSANOW, &new_termios);
    atexit(reset_terminal_mode);  // Reset on exit
}

int kbhit() {
    struct timeval tv = {0L, 0L};
    fd_set fds;
    FD_ZERO(&fds);
    FD_SET(STDIN_FILENO, &fds);
    return select(1, &fds, NULL, NULL, &tv);
}
#endif

void setup() {
    gameover = 0;
    x = WIDTH / 2;
    y = HEIGHT / 2;
    fruitx = rand() % (WIDTH - 1) + 1;  // Avoid borders
    fruity = rand() % (HEIGHT - 1) + 1;
    score = 0;
    tailLen = 0;
    flag = 0;  // No initial direction
}

void draw() {
#ifdef _WIN32
    system("cls");
#else
    system("clear");
#endif

    for (int i = 0; i < WIDTH + 2; i++) printf("#");
    printf("\n");

    for (int i = 0; i < HEIGHT; i++) {
        for (int j = 0; j < WIDTH; j++) {
            if (j == 0) printf("#");
            if (i == y && j == x) printf("O");
            else if (i == fruity && j == fruitx) printf("*");
            else {
                int isTail = 0;
                for (int k = 0; k < tailLen; k++) {
                    if (tailX[k] == j && tailY[k] == i) {
                        printf("o");
                        isTail = 1;
                        break;
                    }
                }
                if (!isTail) printf(" ");
            }
            if (j == WIDTH - 1) printf("#");
        }
        printf("\n");
    }

    for (int i = 0; i < WIDTH + 2; i++) printf("#");
    printf("\n");
    printf("Score: %d\n", score);
    printf("Press W/A/S/D to move, X to quit.\n");
}

void input() {
    if (kbhit()) {
        char ch;
#ifdef _WIN32
        ch = tolower(getch());
#else
        ch = tolower(getchar());
#endif
        switch (ch) {
            case 'a': if (flag != 2) flag = 1; break;  // Left, not if right
            case 'd': if (flag != 1) flag = 2; break;  // Right, not if left
            case 'w': if (flag != 4) flag = 3; break;  // Up, not if down
            case 's': if (flag != 3) flag = 4; break;  // Down, not if up
            case 'x': gameover = 1; break;
        }
    }
}

void logic() {
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
        case 1: x--; break;
        case 2: x++; break;
        case 3: y--; break;
        case 4: y++; break;
    }

    if (x >= WIDTH || x < 0 || y >= HEIGHT || y < 0) gameover = 1;

    for (int i = 0; i < tailLen; i++) {
        if (tailX[i] == x && tailY[i] == y) gameover = 1;
    }

    if (x == fruitx && y == fruity) {
        score += 10;
        fruitx = rand() % (WIDTH - 1) + 1;
        fruity = rand() % (HEIGHT - 1) + 1;
        tailLen++;
    }
}

int main() {
    srand(time(NULL));  // Seed random
#ifndef _WIN32
    set_terminal_mode();
#endif
    setup();
    while (!gameover) {
        draw();
        input();
        logic();
#ifdef _WIN32
        Sleep(100);  // ms
#else
        usleep(100000);  // microseconds (100ms)
#endif
    }
    printf("Game Over! Final Score: %d\n", score);
    return 0;
}