/* pocketpsp core: portable helpers shared by the PSP runtime and host tests. */
#ifndef POCKETPSP_CORE_H
#define POCKETPSP_CORE_H

#include <math.h>
#include <stdbool.h>
#include <stdint.h>

#define PP_UNUSED __attribute__((unused))

typedef struct pp_sprite {
    float x, y;
    int32_t width, height;     /* image size in pixels */
    int32_t tex_w, tex_h;      /* power-of-two texture size */
    uint32_t *pixels;          /* RGBA8888, tex_w * tex_h */
} pp_sprite;

/* Python semantics: floor division and modulo. Division by zero yields 0. */
static inline int32_t pp_floordiv(int32_t a, int32_t b) {
    if (b == 0) return 0;
    if (b == -1) return (int32_t)(0u - (uint32_t)a);
    int32_t q = a / b;
    if ((a % b != 0) && ((a < 0) != (b < 0))) q -= 1;
    return q;
}

static inline int32_t pp_mod(int32_t a, int32_t b) {
    if (b == 0 || b == -1) return 0;
    int32_t r = a % b;
    if (r != 0 && ((r < 0) != (b < 0))) r += b;
    return r;
}

static inline int32_t pp_abs_i(int32_t a) { return a < 0 ? (int32_t)(0u - (uint32_t)a) : a; }
static inline float pp_abs_f(float a) { return fabsf(a); }
static inline int32_t pp_min_i(int32_t a, int32_t b) { return a < b ? a : b; }
static inline int32_t pp_max_i(int32_t a, int32_t b) { return a > b ? a : b; }
static inline float pp_min_f(float a, float b) { return a < b ? a : b; }
static inline float pp_max_f(float a, float b) { return a > b ? a : b; }

/* float -> int conversion truncating toward zero, saturating, NaN -> 0 */
static inline int32_t pp_f2i(float f) {
    if (f != f) return 0;
    if (f >= 2147483520.0f) return INT32_MAX;
    if (f <= -2147483648.0f) return INT32_MIN;
    return (int32_t)f;
}

#endif
