/*
 * pocketpsp runtime: window/GU setup, input, frame loop and sprite drawing.
 * Uses pspsdk APIs: pspkernel, pspdisplay, pspctrl, pspgu, psputils.
 * Image decoding: stb_image (public domain / MIT), PNG only.
 */
#include <malloc.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include <pspdisplay.h>
#include <pspgu.h>
#include <psputils.h>

#include "pocketpsp/pocketpsp.h"

#define STB_IMAGE_IMPLEMENTATION
#define STBI_ONLY_PNG
#define STBI_NO_LINEAR
#define STBI_NO_HDR
#include "stb_image.h"

#define BUF_WIDTH 512
#define SCR_WIDTH 480
#define SCR_HEIGHT 272
#define FRAME_SIZE (BUF_WIDTH * SCR_HEIGHT * 4)

static unsigned int __attribute__((aligned(16))) gu_list[262144];
static volatile int pp_running = 1;
static unsigned int pp_buttons = 0, pp_prev_buttons = 0;

/* ---- exit callback (HOME button) ---- */
static int exit_callback(int arg1, int arg2, void *common) {
    (void)arg1; (void)arg2; (void)common;
    pp_running = 0;
    return 0;
}

static int callback_thread(SceSize args, void *argp) {
    (void)args; (void)argp;
    int cbid = sceKernelCreateCallback("exit_callback", exit_callback, NULL);
    sceKernelRegisterExitCallback(cbid);
    sceKernelSleepThreadCB();
    return 0;
}

static void setup_callbacks(void) {
    int thid = sceKernelCreateThread("update_thread", callback_thread, 0x11, 0xFA0, 0, NULL);
    if (thid >= 0) sceKernelStartThread(thid, 0, NULL);
}

/* ---- graphics ---- */
static void gu_setup(void) {
    sceGuInit();
    sceGuStart(GU_DIRECT, gu_list);
    sceGuDrawBuffer(GU_PSM_8888, (void *)0, BUF_WIDTH);
    sceGuDispBuffer(SCR_WIDTH, SCR_HEIGHT, (void *)FRAME_SIZE, BUF_WIDTH);
    sceGuDepthBuffer((void *)(FRAME_SIZE * 2), BUF_WIDTH);
    sceGuOffset(2048 - (SCR_WIDTH / 2), 2048 - (SCR_HEIGHT / 2));
    sceGuViewport(2048, 2048, SCR_WIDTH, SCR_HEIGHT);
    sceGuDepthRange(65535, 0);
    sceGuScissor(0, 0, SCR_WIDTH, SCR_HEIGHT);
    sceGuEnable(GU_SCISSOR_TEST);
    sceGuFrontFace(GU_CW);
    sceGuEnable(GU_BLEND);
    sceGuBlendFunc(GU_ADD, GU_SRC_ALPHA, GU_ONE_MINUS_SRC_ALPHA, 0, 0);
    sceGuShadeModel(GU_SMOOTH);
    sceGuFinish();
    sceGuSync(0, 0);
    sceDisplayWaitVblankStart();
    sceGuDisplay(GU_TRUE);
}

void pp_clear(int32_t r, int32_t g, int32_t b) {
    r = r < 0 ? 0 : (r > 255 ? 255 : r);
    g = g < 0 ? 0 : (g > 255 ? 255 : g);
    b = b < 0 ? 0 : (b > 255 ? 255 : b);
    sceGuClearColor(0xFF000000u | ((unsigned)b << 16) | ((unsigned)g << 8) | (unsigned)r);
    sceGuClear(GU_COLOR_BUFFER_BIT);
}

static int32_t next_pow2(int32_t v) {
    int32_t p = 8;
    while (p < v) p <<= 1;
    return p;
}

bool pp_sprite_load(pp_sprite *s, const char *path, float x, float y) {
    int w = 0, h = 0, comp = 0;
    memset(s, 0, sizeof *s);
    s->x = x;
    s->y = y;
    unsigned char *img = stbi_load(path, &w, &h, &comp, 4);
    if (!img) return false;
    s->width = w;
    s->height = h;
    s->tex_w = next_pow2(w);
    s->tex_h = next_pow2(h);
    s->pixels = (uint32_t *)memalign(16, (size_t)s->tex_w * s->tex_h * 4);
    if (!s->pixels) { stbi_image_free(img); return false; }
    memset(s->pixels, 0, (size_t)s->tex_w * s->tex_h * 4);
    for (int row = 0; row < h; row++)
        memcpy(s->pixels + (size_t)row * s->tex_w, img + (size_t)row * w * 4, (size_t)w * 4);
    stbi_image_free(img);
    sceKernelDcacheWritebackAll();
    return true;
}

typedef struct { float u, v; float x, y, z; } pp_vertex;

void pp_sprite_draw(const pp_sprite *s) {
    if (!s->pixels) return;
    sceGuEnable(GU_TEXTURE_2D);
    sceGuTexMode(GU_PSM_8888, 0, 0, GU_FALSE);
    sceGuTexImage(0, s->tex_w, s->tex_h, s->tex_w, s->pixels);
    sceGuTexFunc(GU_TFX_REPLACE, GU_TCC_RGBA);
    sceGuTexFilter(GU_NEAREST, GU_NEAREST);
    pp_vertex *v = (pp_vertex *)sceGuGetMemory(2 * sizeof(pp_vertex));
    v[0].u = 0.0f; v[0].v = 0.0f;
    v[0].x = s->x; v[0].y = s->y; v[0].z = 0.0f;
    v[1].u = (float)s->width / (float)s->tex_w;
    v[1].v = (float)s->height / (float)s->tex_h;
    v[1].x = s->x + (float)s->width; v[1].y = s->y + (float)s->height; v[1].z = 0.0f;
    sceGuDrawArray(GU_SPRITES, GU_TEXTURE_32BITF | GU_VERTEX_32BITF | GU_TRANSFORM_2D, 2, NULL, v);
    sceGuDisable(GU_TEXTURE_2D);
}

/* ---- input ---- */
bool pp_button_held(unsigned int mask) { return (pp_buttons & mask) != 0; }
bool pp_button_pressed(unsigned int mask) {
    return (pp_buttons & mask) != 0 && (pp_prev_buttons & mask) == 0;
}

static void poll_input(void) {
    SceCtrlData pad;
    pp_prev_buttons = pp_buttons;
    if (sceCtrlPeekBufferPositive(&pad, 1) > 0) pp_buttons = pad.Buttons;
}

/* ---- main loop ---- */
int main(int argc, char **argv) {
    (void)argc; (void)argv;
    setup_callbacks();
    sceCtrlSetSamplingCycle(0);
    sceCtrlSetSamplingMode(PSP_CTRL_MODE_DIGITAL);
    gu_setup();
    pp_user_init();
    while (pp_running) {
        poll_input();
        pp_user_update();
        sceGuStart(GU_DIRECT, gu_list);
        pp_user_draw();
        sceGuFinish();
        sceGuSync(0, 0);
        sceDisplayWaitVblankStart();
        sceGuSwapBuffers();
    }
    sceGuTerm();
    sceKernelExitGame();
    return 0;
}
