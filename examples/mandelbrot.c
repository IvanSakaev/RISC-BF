#include "dbf.h"

#define putch(a) dbf_putchar(a)

char	junk[256];

void _start()
{
	int f, i, x, y;
	int c, d, a, b, q, s, t, p;

#if 0
	printf("hit Enter key:");
	fflush(stdout);
	gets(junk);
#endif
	f = 50;
	for (y = -12; y <= 12; y++) {
		for (x = -39; x <= 39; x++) {
			c = x * 229 / 100;
			d = y * 416 / 100;
			a = c;
			b = d;
			for (i = 0; i <=15; i++) {
				q = b / f;
				s = b - q * f;
				t = (a * a - b * b) / f + c;
				b = 2 * (a * q + a * s / f) + d;
				a = t;
				p = a / f;
				q = b / f;
				if ((p * p + q * q) > 4) {
					break;
				}
			}
			putch("0123456789ABCDEF "[i]);
		}
		putch('\n');
	}
}
