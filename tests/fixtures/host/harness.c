/* Host test harness: runs generated update/draw and prints sprite/global state. */
#include <stdio.h>
#include <stdlib.h>
#include "pocketpsp/pocketpsp.h"

unsigned int host_buttons, host_prev;
int host_clears, host_draws;

int main(int argc, char **argv) {
    int frames = argc > 1 ? atoi(argv[1]) : 1;
    host_buttons = argc > 2 ? (unsigned)atoi(argv[2]) : 0;
    pp_user_init();
    for (int i = 0; i < frames; i++) {
        pp_user_update();
        pp_user_draw();
        host_prev = host_buttons;
    }
    printf("clears=%d draws=%d\n", host_clears, host_draws);
    return 0;
}
