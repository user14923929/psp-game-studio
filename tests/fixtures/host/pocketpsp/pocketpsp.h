/* Host (non-PSP) stand-in for pocketpsp.h, used only to compile and run
 * generated code in unit tests. Not part of the shipped runtime. */
#ifndef POCKETPSP_HOST_H
#define POCKETPSP_HOST_H

#include "pocketpsp/core.h"

#define PSP_MODULE_INFO(name, attr, major, minor) extern int pp_host_module_info_unused
#define PSP_MAIN_THREAD_ATTR(attr) extern int pp_host_thread_attr_unused
#define PSP_THREAD_ATTR_USER 0

#define PSP_CTRL_LEFT 1u
#define PSP_CTRL_RIGHT 2u
#define PSP_CTRL_UP 4u
#define PSP_CTRL_DOWN 8u
#define PSP_CTRL_CROSS 16u
#define PSP_CTRL_CIRCLE 32u
#define PSP_CTRL_SQUARE 64u
#define PSP_CTRL_TRIANGLE 128u
#define PSP_CTRL_START 256u
#define PSP_CTRL_SELECT 512u
#define PSP_CTRL_LTRIGGER 1024u
#define PSP_CTRL_RTRIGGER 2048u

extern const char *const pp_game_title;
void pp_user_init(void);
void pp_user_update(void);
void pp_user_draw(void);

extern unsigned int host_buttons, host_prev;
extern int host_clears, host_draws;
static inline bool pp_button_held(unsigned int m) { return (host_buttons & m) != 0; }
static inline bool pp_button_pressed(unsigned int m) {
    return (host_buttons & m) != 0 && (host_prev & m) == 0;
}
static inline void pp_clear(int32_t r, int32_t g, int32_t b) { (void)r; (void)g; (void)b; host_clears++; }
static inline bool pp_sprite_load(pp_sprite *s, const char *p, float x, float y) {
    (void)p; s->x = x; s->y = y; s->width = 16; s->height = 16; return true;
}
static inline void pp_sprite_draw(const pp_sprite *s) { (void)s; host_draws++; }

#endif
