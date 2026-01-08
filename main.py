"""Small runner delegating to `resources` and `ui` modules.

This file only wires together factories and the main loop; game logic
and assets live in `resources.py`, `cars.py` and `ui.py`.
"""

import pygame, math
from resources import GameInfo, WIN, FPS, images, create_player_car, create_computer_car, create_GBFS_car, blit_text_center, create_neat_car, TRACK_BORDER_MASK, raycast_mask
import ui
from neatmanager import NEATManager
import neat
config = neat.Config(
    neat.DefaultGenome,
    neat.DefaultReproduction,
    neat.DefaultSpeciesSet,
    neat.DefaultStagnation,
    'neat_config.ini'  # your config file
)
manager = NEATManager(neat_config=config,
                      car_factory=create_neat_car,
                      track_mask=TRACK_BORDER_MASK,
                      raycast_fn=raycast_mask,
                      fps=60,
                      time_limit_sec=20.0)

def run():
    player_car = create_player_car()
    computer_car = create_computer_car()
    GBFS_car = create_GBFS_car() # create GBFS car
    neat_car = create_neat_car() # create NEAT car

    game_info = GameInfo()

    running = True
    clock = pygame.time.Clock()

    while running:
        clock.tick(FPS)

        ui.draw(WIN, images, player_car, computer_car, GBFS_car, neat_car)

        while not game_info.started:
            WIN.fill((0, 0, 0))  # black screen until game starts

            # let a user upload/load however many cars they want here before the race starts, cars that are being uploaded should be added via a json file format
            # the car should have a name, image, stats but also a pathfinding algorithm defined in code that the user can upload

            blit_text_center(WIN, pygame.font.SysFont(None, 48), "Press any key to start level {}".format(game_info.level))
            pygame.display.update()
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                    break
                if event.type == pygame.KEYDOWN:
                    for n in ["3", "2", "1"]:
                        WIN.fill((0, 0, 0))  # clear screen
                        blit_text_center(WIN, pygame.font.SysFont(None, 48), n)
                        pygame.display.update()
                        pygame.time.delay(700)
                    game_info.start_level()

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
                break

        ui.move_player(player_car)
        computer_car.move()
        GBFS_car.move()
        neat_car.move()

        ui.handle_collision(player_car, computer_car, GBFS_car, neat_car)


if __name__ == "__main__":
    run()
    pygame.quit()