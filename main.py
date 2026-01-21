# main.py
import asyncio
import pygame
import neat
import ui
import math
import time
from neatmanager import NEATManager
import resources
import sys
from resources import (
    GameInfo, WIN, FPS, images,
    create_player_car, create_computer_car, create_GBFS_car,
    create_neat_car, blit_text_center,
    raycast_mask,
    load_track_for_level, create_dijkstra_car, MENU3
)

# -----------------------------
# Game States
# -----------------------------
STATE_MENU = "menu"
STATE_LEVEL_SELECT = "level_select"
STATE_COUNTDOWN = "countdown"
STATE_RACING = "racing"
STATE_LEVEL_END = "level_end"
STATE_PAGE1 = "page1"
STATE_PAGE2 = "page2"
STATE_TRAINING = "training"

# -----------------------------
# NEAT setup
# -----------------------------
config = neat.Config(
    neat.DefaultGenome,
    neat.DefaultReproduction,
    neat.DefaultSpeciesSet,
    neat.DefaultStagnation,
    'neat_config.ini'
)

manager = NEATManager(
    neat_config=config,
    car_factory=create_neat_car,
    track_mask=resources.TRACK_BORDER_MASK,
    raycast_fn=raycast_mask,
    fps=FPS,
    time_limit_sec=20.0
)

TRAIN_GENERATIONS = 10


def _font(size):
    return pygame.font.Font(None, size)


async def main():
    pygame.init()

    game_info = GameInfo()
    game_state = STATE_MENU

    player_car = computer_car = GBFS_car = neat_car = dijkstra_car = None

    level_result = None
    level_time = 0.0
    countdown_timer = 3.0

    trained_net = None
    clock = pygame.time.Clock()
    running = True

    menu = ui.Menu()
    menu.drawMain(WIN)

    # -----------------------------
    # MAIN LOOP
    # -----------------------------
    while running:
        dt = clock.tick(FPS) / 1000.0

        # -----------------------------
        # EVENTS
        # -----------------------------
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

            # -------- MENU / UI STATES --------
            if game_state in (STATE_MENU, STATE_LEVEL_SELECT, STATE_PAGE1, STATE_PAGE2):
                action = menu.handle_event(event)

                if action == "play":
                    resources.click_sound.play()
                    game_state = STATE_LEVEL_SELECT
                    menu.drawLevels(WIN)

                elif action == "train":
                    resources.click_sound.play()
                    game_state = STATE_TRAINING
                

                elif action == "page1":
                    resources.click_sound.play()
                    menu.drawPage1(WIN)
                    game_state = STATE_PAGE1

                elif action == "page2":
                    resources.click_sound.play()
                    menu.drawPage2(WIN)
                    game_state = STATE_PAGE2
                
                elif action == "back":
                    resources.click_sound.play()
                    game_state = STATE_MENU
                    menu.drawMain(WIN)

                elif action == "quit":
                    resources.click_sound.play()
                    running = False

                # -------- LEVEL SELECTION --------
                elif action and action.startswith("level"):
                    resources.click_sound.play()

                    level_num = int(action[-1]) - 1
                    game_info.level = level_num
                    game_info.next_level()

                    load_track_for_level(game_info.get_level())

                    player_car = create_player_car()
                    computer_car = create_computer_car()
                    GBFS_car = create_GBFS_car()
                    neat_car = create_neat_car()
                    dijkstra_car = create_dijkstra_car()

                    if trained_net:
                        neat_car.set_net(trained_net)

                    countdown_timer = 3.0
                    game_state = STATE_COUNTDOWN

            # -------- LEVEL END --------
            elif game_state == STATE_LEVEL_END:
                if event.type == pygame.KEYDOWN and event.key == pygame.K_RETURN:
                    if level_result == "win" and game_info.next_level():
                        load_track_for_level(game_info.get_level())

                        player_car = create_player_car()
                        computer_car = create_computer_car()
                        GBFS_car = create_GBFS_car()
                        neat_car = create_neat_car()
                        dijkstra_car = create_dijkstra_car()

                        if trained_net:
                            neat_car.set_net(trained_net)

                        countdown_timer = 3.0
                        game_state = STATE_COUNTDOWN
                    else:
                        menu.drawMain(WIN)
                        game_state = STATE_MENU

        # -----------------------------
        # UPDATE / DRAW
        # -----------------------------
        if game_state == STATE_COUNTDOWN:
            countdown_timer -= dt
            WIN.blit(MENU3, (0, 0))
            blit_text_center(WIN, _font(48), str(max(1, math.ceil(countdown_timer))))

            if countdown_timer <= 0:
                game_info.start_level()
                game_state = STATE_RACING

        elif game_state == STATE_RACING:
            ui.draw(
                WIN,
                images,
                player_car,
                computer_car,
                GBFS_car,
                neat_car,
                dijkstra_car
            )

            # AI logic
            neat_car.move()
            neat_car.sense(neat_car.track_mask, raycast_mask)
            neat_car.think()
            neat_car.apply_controls()

            # Other cars
            ui.move_player(player_car)
            computer_car.move()
            GBFS_car.move()
            dijkstra_car.move()

            winner = ui.handle_collision(
                player_car,
                computer_car,
                GBFS_car,
                neat_car,
                dijkstra_car
            )

            if winner:
                level_time = time.time() - game_info.level_start_time
                level_result = "win" if winner == "player" else "lose"
                game_state = STATE_LEVEL_END
        
        elif game_state == STATE_TRAINING:
            # Run multiple NEAT updates per frame for speed
            for _ in range(5):
                gen, finished, total = manager.update(dt)

                if gen >= TRAIN_GENERATIONS:
                    # Extract best genome and build trained network
                    if manager.winner is not None:
                        trained_net = neat.nn.FeedForwardNetwork.create(
                            manager.winner,
                            config
                        )   
                    # Return to menu
                    menu.drawMain(WIN)
                    game_state = STATE_MENU
                    break

            # Draw training visuals
            WIN.fill((20, 20, 20))
            manager.draw(WIN, images)

            font = pygame.font.Font(None, 26)
            WIN.blit(
                font.render(
                    f"Training NEAT | Generation {manager.generation}/{TRAIN_GENERATIONS}",
                    True,
                    (255, 255, 255)
                ),
                (10, 10)
            )

        elif game_state == STATE_LEVEL_END:
            ui.draw_level_end(
                WIN,
                level_result,
                game_info.get_level(),
                level_time,
                _font(48)
            )

        pygame.display.flip()
        await asyncio.sleep(0)

    pygame.quit()


if __name__ == "__main__":
    asyncio.run(main())