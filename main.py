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
# try:
#    from js import console  # Access the browser's console object
# except ImportError:
#    console = None  # Not in a JS environment

# def js_console_log(*args):
#    """
#    Directly call JavaScript's console.log from Python.
#    Works only in pygbag/Pyodide environment.
#    """
#    console.log(*args)  # Pass arguments directly to JS console.log
from resources import (
    GameInfo, WIN, FPS, images,
    create_player_car, create_computer_car, create_GBFS_car,
    create_neat_car, blit_text_center,
    raycast_mask,
    load_track_for_level, create_dijkstra_car, MENU3
)
# NEW: tuning marketplace helpers
from tuning_registry import build_registry, apply_registry
from pricing import price_build, TRACK_MULT

# NEW: model selection screen
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
BUILD_SCREEN = "build_screen"
ASSETS_DIR = r"C:\Users\lelliottjack\Documents\DFA AI Racecar game\DFA_PathFinding_GrandPrix\assets"
GAME_BUDGET = 100_000.00
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


def create_all_cars():
    """Factory function to create all 5 car instances."""
    return (
        create_player_car(),
        create_computer_car(),
        create_GBFS_car(),
        create_neat_car(),
        create_dijkstra_car()
    )


def create_car_by_model(model_type, color="Red"):
    """Factory function to create a specific car by model type with a custom color."""
    if model_type == "Player":
        return create_player_car(color)
    elif model_type == "BFS":
        return create_computer_car(type='BFS', color=color)
    elif model_type == "DFS":
        return create_computer_car(type='DFS', color=color)
    elif model_type == "GBFS":
        return create_GBFS_car(color)
    elif model_type == "Dijkstra":
        return create_dijkstra_car(color=color)
    elif model_type == "NEAT":
        return create_neat_car(color)
    else:
        return create_player_car(color)


def load_trained_network(config):
    """Load trained NEAT network from file. Returns None if file doesn't exist."""
    try:
        with open("assets/winner_genome.pkl", "rb") as f:
            winner = pickle.load(f)
        return neat.nn.FeedForwardNetwork.create(winner, config)
    except FileNotFoundError:
        return None


async def main():
    pygame.init()
    #js_console_log("Game started")

    game_info = GameInfo()
    game_state = STATE_MENU

    player_car = computer_car = GBFS_car = neat_car = dijkstra_car = None

    level_result = None
    level_time = 0.0
    countdown_timer = 3.0

    # Marketplace state (persist across levels)
    last_model = None
    last_track_key = None
    last_reg = None
    last_total_price = 0.0
    selection = None
    chosen_model = None
    chosen_color = None
    
    # Track autonomous mode state for level progression
    is_autonomous = False

    trained_net = None
    clock = pygame.time.Clock()
    running = True

    menu = ui.Menu()
    menu.drawMain(WIN)

    # Build screen object (lazy-create)
    build_screen = None
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
                # Handle mouse wheel for scrolling on info page
                if event.type == pygame.MOUSEWHEEL and game_state == STATE_PAGE1:
                    mouse_pos = pygame.mouse.get_pos()
                    menu.info_scroll.handle_wheel(event, hover_pos=mouse_pos, step=40)
                
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
            
                # -------- LEVEL SELECTION and MODEL SELECT / COUNTDOWN --------
                elif action and action.startswith("level"):
                    resources.click_sound.play()

                    level_num = int(action[-1]) - 1
                    game_info.level = level_num
                    game_info.next_level()

                    load_track_for_level(game_info.get_level())
                    player_car, computer_car, GBFS_car, neat_car, dijkstra_car = create_all_cars()

                    if trained_net:
                        neat_car.set_net(trained_net)

                    selector = ModelSelectScreen(WIN, assets_path=ASSETS_DIR)
                    game_state = MODEL_SELECT
                    selector.model_index = selector.models.index("NEAT")
                    selector.color_index = 0  # Default to first color

            if game_state == MODEL_SELECT:
                result = selector.open(event)
                if result == "back":
                    game_state = STATE_LEVEL_SELECT
                    menu.drawLevels(WIN)
                    chosen_model = None
                    chosen_color = None
                elif result is not None and isinstance(result, tuple):
                    # Result is (model, color)
                    chosen_model, chosen_color = result
            elif game_state == BUILD_SCREEN:
                selection = build_screen.open(base_reg, manager,event, lock_model=chosen_model)
                if selection == "back":
                    game_state = MODEL_SELECT
                    chosen_model = None
                    chosen_color = None
                    selection = None
                #js_console_log("Reaching build screen event handling")

                    # -------- LEVEL END --------
            if game_state == STATE_LEVEL_END:
                if event.type == pygame.KEYDOWN and event.key == pygame.K_RETURN:
                    if level_result == "win" and game_info.next_level():
                        load_track_for_level(game_info.get_level())
                        
                        # Recreate cars with preserved autonomous mode and color
                        player_car = create_player_car(chosen_color if chosen_color else "Red", autonomous=is_autonomous)
                        computer_car = create_computer_car()
                        GBFS_car = create_GBFS_car()
                        neat_car = create_neat_car()
                        dijkstra_car = create_dijkstra_car()
                        
                        # Update paths for new level (RACING_LINE updated by load_track_for_level)
                        #if player_car.autonomous:
                            #player_car.set_path(resources.RACING_LINE + [resources.FINISH_POSITION])

                        if trained_net:
                            neat_car.set_net(trained_net)

                        countdown_timer = 3.0
                        game_state = STATE_COUNTDOWN
                    else:
                        menu.drawMain(WIN)
                        game_state = STATE_MENU
        if game_state == MODEL_SELECT:
            if chosen_model is not None:
                # Create temp cars for registry
                tmp_player, tmp_computer, tmp_gbfs, tmp_neat, tmp_dijk = create_all_cars()
                base_reg = build_registry(manager, [tmp_player, tmp_computer, tmp_gbfs, tmp_neat, tmp_dijk])

                if build_screen is None:
                    build_screen = ui.BuildScreen(WIN, GAME_BUDGET)

                build_screen.setup_open(base_reg, manager, lock_model=chosen_model)
                game_state = BUILD_SCREEN
        elif game_state == BUILD_SCREEN:
            if selection is not None:
                _model_from_ui, track_key, overrides, total_price = selection

                # Determine if player car should be autonomous (all non-Player models)
                is_autonomous = (chosen_model != "Player")
                
                # Create fresh cars for this level - apply chosen color and mode to player car
                player_car = create_player_car(chosen_color if chosen_color else "Red", autonomous=is_autonomous)
                computer_car = create_computer_car()
                GBFS_car = create_GBFS_car()
                neat_car = create_neat_car()
                dijkstra_car = create_dijkstra_car()
                
                trained_net = load_trained_network(config)
                if trained_net:
                    neat_car.net = trained_net

                # Merge overrides + apply registry
                base_reg = build_registry(manager, [player_car, computer_car, GBFS_car, neat_car, dijkstra_car])
                for grp, kv in (overrides or {}).items():
                    base_reg.setdefault(grp, {})
                    base_reg[grp].update(kv)

                apply_registry(base_reg, manager, [player_car, computer_car, GBFS_car, neat_car, dijkstra_car])

                # Persist build info
                last_model, last_track_key, last_reg, last_total_price = chosen_model, track_key, base_reg, total_price
                
                # Countdown to start
                countdown_timer = 3.0
                game_state = STATE_COUNTDOWN
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
        
        if game_state == STATE_LEVEL_SELECT:
            menu.drawLevels(WIN)

        elif game_state == STATE_PAGE1:
            menu.drawPage1(WIN)

        elif game_state == STATE_PAGE2:
            menu.drawPage2(WIN)

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

            # Player car movement (manual or autonomous)
            if player_car.autonomous:
                player_car.move()  # Autonomous mode: follow path
            else:
                ui.move_player(player_car)  # Manual mode: keyboard control
            
            # Other AI cars
            computer_car.move()
            GBFS_car.move()
            dijkstra_car.move()

            winner = ui.handle_collision( # winner stored based on first collision
                player_car,
                computer_car,
                GBFS_car,
                neat_car,
                dijkstra_car,
                chosen_model
            )

            if winner: # Someone won
                level_time = time.time() - game_info.level_start_time
                level_result = "win" if winner == "Player" else "lose" # level result set based on whether player car won
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
                        
                        #with open("assets/winner_genome.pkl", "wb") as f:
                        #    pickle.dump(manager.winner, f)


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