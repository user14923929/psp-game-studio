/* pocketpsp runtime API for the PSP. Generated game code includes this header. */
#ifndef POCKETPSP_H
#define POCKETPSP_H

#include <pspctrl.h>
#include <pspkernel.h>
#include <pspmoduleinfo.h>

#include "pocketpsp/core.h"

/* Provided by generated code. */
extern const char *const pp_game_title;
void pp_user_init(void);
void pp_user_update(void);
void pp_user_draw(void);

/* Provided by the runtime. */
bool pp_button_held(unsigned int mask);
bool pp_button_pressed(unsigned int mask);
void pp_clear(int32_t r, int32_t g, int32_t b);
bool pp_sprite_load(pp_sprite *s, const char *path, float x, float y);
void pp_sprite_draw(const pp_sprite *s);

#endif
