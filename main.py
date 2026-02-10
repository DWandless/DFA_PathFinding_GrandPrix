# main.py
import asyncio
import pygame
import neat
import ui
import math
import time
import pickle
from neatmanager import NEATManager
import resources
import sys

from resources import (
    GameInfo, WIN, FPS, images,
    create_player_car, create_computer_car, create_GBFS_car,
    create_neat_car, blit_text_center, raycast_mask,
    load_track_for_level, create_dijkstra_car, MENU3,
    get_algorithm_delay
)

from model_select import ModelSelectScreen


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
MODEL_SELECT = "model_select"
STATE_NEAT_LIVE_TRAINING = "neat_live_training"   # NEW


# -----------------------------
# NEAT config
# -----------------------------
config = neat.Config(
    neat.DefaultGenome,
    neat.DefaultReproduction,
    neat.DefaultSpeciesSet,
    neat.DefaultStagnation,
    "neat_config.ini"
)

manager = NEATManager(
    neat_config=config,
    car_factory=create_neat_car,
    track_mask=resources.TRACK_BORDER_MASK,
    raycast_fn=raycast_mask,
    fps=FPS,
    time_limit_sec=50
)

TRAIN_GENERATIONS = 10


def _font(size):
    return pygame.font.Font(None, size)


def create_car_by_model(model_type, color="Red"):
    if model_type == "Player":
        return create_player_car(color)
    elif model_type == "BFS":
        return create_computer_car(type="BFS", color=color)
    elif model_type == "DFS":
        return create_computer_car(type="DFS", color=color)
    elif model_type == "GBFS":
        return create_GBFS_car(color)
    elif model_type == "Dijkstra":
        return create_dijkstra_car(color=color)
    elif model_type == "NEAT":
        return create_neat_car(color)
    return create_player_car(color)


def load_trained_network(config):
    try:
        with open("assets/winner_genome.pkl", "rb") as f:
            winner = pickle.load(f)
        return neat.nn.FeedForwardNetwork.create(winner, config)
    except FileNotFoundError:
        return None


async def main():
    pygame.init()

    game_info = GameInfo()
    game_state = STATE_MENU

    player_car = computer_car = GBFS_car = neat_car = dijkstra_car = None

    level_result = None
    level_time = 0.0
    countdown_timer = 3.0

    chosen_model = None
    chosen_color = None

    trained_net = None
    player_trained_net = None

    clock = pygame.time.Clock()
    running = True

    menu = ui.Menu()
    menu.drawMain(WIN)

    # -----------------------------------
    # MAIN LOOP
    # -----------------------------------
    while running:
        dt = clock.tick(FPS) / 1000.0

        for event in pygame.event.get():
            # Quit
            if event.type == pygame.QUIT:
                running = False

            # Navigation states
            if game_state in (STATE_MENU, STATE_LEVEL_SELECT, STATE_PAGE1, STATE_PAGE2):

                if event.type == pygame.MOUSEWHEEL and game_state == STATE_PAGE1:
                    menu.info_scroll.handle_wheel(
                        event,
                        hover_pos=pygame.mouse.get_pos(),
                        step=40
                    )

                action = menu.handle_event(event)

                if action == "play":
                    game_state = STATE_LEVEL_SELECT
                    menu.drawLevels(WIN)

                elif action == "train":
                    game_state = STATE_TRAINING

                elif action == "page1":
                    menu.drawPage1(WIN)
                    game_state = STATE_PAGE1

                elif action == "page2":
                    menu.drawPage2(WIN)
                    game_state = STATE_PAGE2

                elif action == "back":
                    game_state = STATE_MENU
                    menu.drawMain(WIN)

                elif action == "quit":
                    running = False

                elif action and action.startswith("level"):
                    level_num = int(action[-1]) - 1
                    game_info.level = level_num
                    game_info.next_level()

                    load_track_for_level(game_info.get_level())

                    selector = ModelSelectScreen(WIN, "", currentLevel=(level_num+1))
                    game_state = MODEL_SELECT
                    selector.model_index = selector.models.index("BFS")
                    selector.color_index = 0

            # -----------------------------------
            # MODEL SELECT
            # -----------------------------------
            if game_state == MODEL_SELECT:
                result = selector.open(event)

                if result == "back":
                    game_state = STATE_LEVEL_SELECT
                    menu.drawLevels(WIN)

                elif isinstance(result, tuple):
                    chosen_model, chosen_color = result
                    color = chosen_color or "Red"

                    player_car = create_car_by_model(chosen_model, color)

                    # NEAT Chosen → enter LIVE TRAINING immediately
                    if chosen_model == "NEAT":
                        manager.reset()
                        game_state = STATE_NEAT_LIVE_TRAINING
                    else:
                        game_state = STATE_COUNTDOWN
                        

                    # Otherwise create other AI cars normally
                    computer_car = create_computer_car()
                    GBFS_car = create_GBFS_car()
                    neat_car = create_neat_car()
                    dijkstra_car = create_dijkstra_car()

                    # Spawn positions
                    spawns = getattr(resources, "SPAWN_POSITIONS", {})
                    def _place(car, key):
                        if car and key in spawns:
                            car.x, car.y = spawns[key]
                            if hasattr(car, "set_start_pos"):
                                car.set_start_pos(spawns[key])

                    _place(player_car, "player")
                    _place(computer_car, "computer")
                    _place(GBFS_car, "gbfs")
                    _place(neat_car, "neat")
                    _place(dijkstra_car, "dijkstra")

                    trained_net = load_trained_network(config)
                    if trained_net:
                        neat_car.net = trained_net

                    countdown_timer = 3.0
                    

            # -----------------------------------
            # LEVEL END screen
            # -----------------------------------
            if game_state == STATE_LEVEL_END:
                if event.type == pygame.KEYDOWN and event.key == pygame.K_RETURN:
                    menu.drawMain(WIN)
                    game_state = STATE_MENU

        # -----------------------------------
        # DRAW STATES
        # -----------------------------------
        if game_state == STATE_MENU:
            menu.drawMain(WIN)

        elif game_state == STATE_LEVEL_SELECT:
            menu.drawLevels(WIN)

        elif game_state == STATE_PAGE1:
            menu.drawPage1(WIN)

        elif game_state == STATE_PAGE2:
            menu.drawPage2(WIN)

        # -----------------------------------
        # COUNTDOWN
        # -----------------------------------
        if game_state == STATE_COUNTDOWN:

            countdown_timer -= dt
            WIN.blit(MENU3, (0, 0))

            blit_text_center(WIN, _font(48),
                             str(max(1, math.ceil(countdown_timer))))

            if countdown_timer <= 0:
                game_info.start_level()

                delay = get_algorithm_delay(chosen_model, game_info.get_level())
                player_car.set_delay(delay)

                game_state = STATE_RACING

        # -----------------------------------
        # 🔥 NEW — LIVE NEAT TRAINING (NO BUTTON)
        # Press SPACE to stop training at any time
        # -----------------------------------
        elif game_state == STATE_NEAT_LIVE_TRAINING:

            # Run NEAT faster
            for _ in range(5):
                manager.update(dt)

            # Draw NEAT population
            WIN.fill((20, 20, 20))
            manager.draw(WIN, images)

            msg = f"NEAT Training Live | Gen {manager.generation}"
            WIN.blit(_font(26).render(msg, True, (255,255,255)), (10, 10))

            hint = "Press SPACE to use current best model"
            WIN.blit(_font(22).render(hint, True, (200,200,200)), (10, 40))

            # SPACE → Exit training
            keys = pygame.key.get_pressed()
            if keys[pygame.K_SPACE]:

                if manager.winner:
                    trained_net = neat.nn.FeedForwardNetwork.create(
                        manager.winner, config
                    )
                    player_car.set_net(trained_net)

                countdown_timer = 3.0
                game_state = STATE_COUNTDOWN

        # -----------------------------------
        # REGULAR RACING
        # -----------------------------------
        elif game_state == STATE_RACING:

            ui.draw(WIN, images,
                player_car, computer_car, GBFS_car,
                neat_car, dijkstra_car
            )

            player_car.update_delay(dt)

            neat_car.move()
            neat_car.sense(neat_car.track_mask, raycast_mask)
            neat_car.think()
            neat_car.apply_controls()

            if player_car.can_move():
                if getattr(player_car, "autonomous", True):
                    player_car.move()
                else:
                    ui.move_player(player_car)

            computer_car.move()
            GBFS_car.move()
            dijkstra_car.move()

            winner = ui.handle_collision(
                player_car, computer_car, GBFS_car,
                neat_car, dijkstra_car, chosen_model
            )

            if winner:
                level_time = time.time() - game_info.level_start_time
                level_result = "win" if winner == "Player" else "lose"
                game_state = STATE_LEVEL_END

        # -----------------------------------
        # ORIGINAL TRAINING (unchanged)
        # -----------------------------------
        elif game_state == STATE_TRAINING:
            for _ in range(5):
                gen, finished, total = manager.update(dt)

                if gen >= TRAIN_GENERATIONS:
                    if manager.winner:
                        trained_net = neat.nn.FeedForwardNetwork.create(
                            manager.winner, config
                        )
                    game_state = STATE_MENU
                    break

            WIN.fill((20, 20, 20))
            manager.draw(WIN, images)

            txt = f"Training NEAT | Gen {manager.generation}/{TRAIN_GENERATIONS}"
            WIN.blit(_font(26).render(txt, True, (255,255,255)), (10, 10))

        # -----------------------------------
        # LEVEL END
        # -----------------------------------
        elif game_state == STATE_LEVEL_END:
            ui.draw_level_end(
                WIN, level_result,
                game_info.get_level(),
                level_time, _font(48)
            )

        pygame.display.flip()
        await asyncio.sleep(0)

    pygame.quit()


if __name__ == "__main__":
    asyncio.run(main())