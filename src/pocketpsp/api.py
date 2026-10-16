"""Type declarations for the game API.

These classes exist so editors and type checkers can offer completion for
``from pocketpsp import Game, Sprite, Button``. Game code is never executed by
Python: ``pocketpsp build`` parses it and generates C instead.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import TypeVar

_F = TypeVar("_F", bound=Callable[[], None])

_MSG = "pocketpsp game code is compiled to C, not executed by Python"


class Game:
    """The game instance. Declare exactly one per project."""

    def __init__(self, title: str) -> None:
        raise NotImplementedError(_MSG)

    def update(self, func: _F) -> _F:
        """Decorator: register the per-frame update function."""
        raise NotImplementedError(_MSG)

    def draw(self, func: _F) -> _F:
        """Decorator: register the per-frame draw function."""
        raise NotImplementedError(_MSG)

    def clear(self, r: int, g: int, b: int) -> None:
        """Clear the screen with an RGB colour (0-255 each)."""
        raise NotImplementedError(_MSG)

    def run(self) -> None:
        """Start the game loop. Must be the last statement of the module."""
        raise NotImplementedError(_MSG)


class Sprite:
    """A PNG image drawn at a position."""

    x: float
    y: float
    width: int
    height: int

    def __init__(self, path: str, x: float = 0, y: float = 0) -> None:
        raise NotImplementedError(_MSG)

    def draw(self) -> None:
        """Draw the sprite at its current position."""
        raise NotImplementedError(_MSG)


class Button:
    """PSP controller buttons."""

    @staticmethod
    def held(name: str) -> bool:
        """True while the button is down."""
        raise NotImplementedError(_MSG)

    @staticmethod
    def pressed(name: str) -> bool:
        """True only on the frame the button went down."""
        raise NotImplementedError(_MSG)
