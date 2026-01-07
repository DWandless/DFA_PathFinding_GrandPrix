"""Small runner delegating to `resources` and `ui` modules.

This file only wires together factories and the main loop; game logic
and assets live in `resources.py`, `cars.py` and `ui.py`.
"""

import pygame
from resources import WIN, FPS, images, create_player_car, create_computer_car, create_GBFS_car
import ui


def run():
    player_car = create_player_car()
    computer_car = create_GBFS_car()

    running = True
    clock = pygame.time.Clock()

    while running:
        clock.tick(FPS)

        ui.draw(WIN, images, player_car, computer_car)

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
                break

        ui.move_player(player_car)
        computer_car.move()

        ui.handle_collision(player_car, computer_car)


if __name__ == "__main__":
    run()
    pygame.quit()