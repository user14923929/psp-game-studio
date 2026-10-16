from pocketpsp import Button, Game, Sprite

game = Game(title="Hello World")

player = Sprite("assets/player.png", x=224, y=120)


@game.update
def update():
    if Button.held("LEFT"):
        player.x -= 2
    if Button.held("RIGHT"):
        player.x += 2
    if Button.held("UP"):
        player.y -= 2
    if Button.held("DOWN"):
        player.y += 2


@game.draw
def draw():
    game.clear(30, 40, 70)
    player.draw()


game.run()
