# Generated build file template: pocketpsp copies this next to game.c.
# Placeholders in @...@ are filled in by pocketpsp (see build/builder.py).
TARGET = game
OBJS = game.o runtime/src/pocketpsp.o

INCDIR = runtime/include runtime/third_party
CFLAGS = -O2 -G0 -Wall -fwrapv
CXXFLAGS = $(CFLAGS) -fno-exceptions -fno-rtti
ASFLAGS = $(CFLAGS)

LIBS = -lpspgu -lpspge -lpspdisplay -lpspctrl -lm

EXTRA_TARGETS = EBOOT.PBP
PSP_EBOOT_TITLE = @TITLE@

PSPSDK = $(shell psp-config --pspsdk-path)
include $(PSPSDK)/lib/build.mak
