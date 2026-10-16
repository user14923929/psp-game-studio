# Python DSL reference

Only `from pocketpsp import Game, Sprite, Button` may be imported (no aliases).

## Module level (in any order, except `game.run()` must be last)

| Statement | Meaning |
|-----------|---------|
| `game = Game(title="...")` | Exactly one. Title is a string literal, 1-64 chars. |
| `name = Sprite("assets/x.png", x=0, y=0)` | PNG path relative to the project; x/y numeric literals. |
| `name = 5`, `ratio = 1.5`, `flag = True`, `speed: float = 2` | Global variables (int, float, bool literals). |
| `@game.update` / `@game.draw` on `def f():` | At most one each; no parameters. |
| `def f(a: int, b: float) -> float:` | Helper functions. Parameter annotations are required; `-> int/float/bool` for a return value. |
| `game.run()` | Last statement. |

## Statements in functions

Assignment (`x = ...`, `x: int = ...`, `x += ...`), `if/elif/else`, `while`, `for i in range(...)`
(literal non-zero step), `break`, `continue`, `return`, `pass`, `global name`, calls.

## Expressions

Literals (`int`, `float`, `bool`), variables, `+ - * / // %`, unary `- + not`,
comparisons (single, not chained), `and`/`or` (bool operands), calls.
Conditions must be `bool` (write `x != 0`, not `x`).

## API

- `Button.held("LEFT")`, `Button.pressed("CROSS")` (true on the first frame). Names:
  LEFT RIGHT UP DOWN CROSS CIRCLE SQUARE TRIANGLE START SELECT LTRIGGER RTRIGGER.
- `game.clear(r, g, b)` ints 0-255 (clamped).
- `sprite.x`, `sprite.y` (float, assignable), `sprite.width`, `sprite.height` (int, read-only),
  `sprite.draw()`.
- Builtins: `abs`, `min`, `max`, `int`, `float`, `range` (for loops only).

## Semantics (differences from Python)

- `int` is 32-bit and wraps on overflow; `float` is 32-bit.
- `/` always returns float; `//` and `%` are int-only and follow Python's floor semantics.
- Division by zero is a compile error for literals; at run time `//` and `%` return 0 (float `/` gives inf/nan).
- Local variables are initialised to 0/false; a variable keeps its first type (int may widen to float, never the reverse).
- Assigning a module variable inside a function needs `global`.
- `int(f)` truncates toward zero and saturates.

## Not supported (examples)

Strings (except API literals), lists, classes, imports other than `pocketpsp`, `try`, `with`,
lambdas, `**`, comprehensions, `for ... else`, keyword arguments in calls, recursion limits are C stack limits.
