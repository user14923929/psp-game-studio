from pocketpsp import Button, Game, Sprite

game = Game(title="Pocket Jumper")

player = Sprite("assets/player.png", x=100, y=200)

GROUND = 240.0
velocity_y: float = 0
on_ground = True


def clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


@game.update
def update():
    global velocity_y, on_ground
    if Button.held("LEFT"):
        player.x -= 3
    if Button.held("RIGHT"):
        player.x += 3
    if Button.pressed("CROSS") and on_ground:
        velocity_y = -9.0
        on_ground = False
    velocity_y += 0.5
    player.y += velocity_y
    if player.y >= GROUND:
        player.y = GROUND
        velocity_y = 0.0
        on_ground = True
    player.x = clamp(player.x, 0, 480 - player.width)


@game.draw
def draw():
    game.clear(30, 40, 70)
    player.draw()


game.run()
