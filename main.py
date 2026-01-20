import asyncio
import pygame
import neat
import ui
from neatmanager import NEATManager
import resources
from resources import (
    GameInfo, WIN, FPS, images,
    create_player_car, create_computer_car, create_GBFS_car,
    create_neat_car, blit_text_center,
    raycast_mask,
    load_track_for_level, create_dijkstra_car
)

# -----------------------------
# NEAT setup
# -----------------------------
config = neat.Config(
    neat.DefaultGenome,
    neat.DefaultReproduction,
    neat.DefaultSpeciesSet,
    neat.DefaultStagnation,
    'assets/neat_config.ini'
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
    pygame.font.init()
    return pygame.font.Font(None, size)


def _build_winner_net():
    best = None

    if getattr(manager, 'winner', None) is not None:
        best = manager.winner

    if best is None and hasattr(manager, 'stats'):
        try:
            best = manager.stats.best_genome()
        except Exception:
            best = None

    if best is None and hasattr(manager, 'pop'):
        try:
            scored = [
                g for g in manager.pop.population.values()
                if hasattr(g, 'fitness')
            ]
            if scored:
                best = max(scored, key=lambda g: g.fitness)
        except Exception:
            best = None

    if best is None:
        return None

    return neat.nn.FeedForwardNetwork.create(best, config)


async def main():
    # --------------------------------------------------
    # Initial setup (module-level asset init is OK)
    # --------------------------------------------------
    player_car = create_player_car()
    computer_car = create_computer_car()
    GBFS_car = create_GBFS_car()
    neat_car = create_neat_car()
    dijkstra_car = create_dijkstra_car()

    # Tuning (unchanged)
    Result_gbfs, MoneyLeft_gbfs = resources.SetCarTuning(
        GBFS_car,
        [[1, 5, 3], [0.0, 0.2, 0.1], [2, 6, 4], [0.2, 1.0, 0.6],
         [16, 48, 32], [20, 80, 50], [0.1, 0.7, 0.4], [0.2, 0.8, 0.5],
         [20000, 80000, 50000], [15, 45, 30], [0, 1, 0]]
    )
    result_neat, moneyleft_neat = resources.SetCarTuning(
        neat_car,
        [
            [1, 5, 3],          # 0  (handled elsewhere)
            [0.0, 0.2, 0.1],    # 1  (handled elsewhere)
            [2, 6, 4],          # 2  (handled elsewhere)
            [0.2, 1.0, 0.6],    # 3  (handled elsewhere)

            # --- NEAT tunables used here ---
            [0.2, 0.9, 0.6],     # 4  weight_mutate_rate
            [0.05, 1.0, 0.3],    # 5  weight_mutate_power
            [0.005, 0.1, 0.03],  # 6  node_add_prob
            [0.02, 0.2, 0.05],   # 7  conn_add_prob
            [0.1, 0.5, 0.2],     # 8  survival_threshold
            [5, 30, 15],         # 9  max_stagnation
            [20, 150, 2],        # 10 pop_size
        ]
    )

    game_info = GameInfo()
    
    # Cars will be created when level starts
    player_car = None
    computer_car = None
    GBFS_car = None
    neat_car = None
    dijkstra_car = None

    setup = True
    running = True
    clock = pygame.time.Clock()
    training_done = False

    menu = ui.Menu()
    menu.drawMain(WIN)

    # Modes:
    # - setup == True  → menu page(s)
    # - not setup and not started:
    #       * either training (if do_training True)
    #       * or countdown to race (pending_countdown True)
    # - game_info.started == True → racing
    setup = True
    do_training = False
    trained_net = None
    training_done = False
    pending_countdown = False
    countdown_time = 0.0  # seconds remaining (visual "3,2,1")
    clock = pygame.time.Clock()
    running = True
    while running:
        dt = clock.tick(FPS) / 1000.0

        # -------------------------------
        # Handle events (common)
        # -------------------------------
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

            if setup:
                action = menu.handle_event(event)
                if action == "play":
                    resources.click_sound.play()
                    game_info.next_level()  # Start at level 1
                    load_track_for_level(game_info.get_level())
                    # Create fresh cars for this level
                    player_car = create_player_car()
                    computer_car = create_computer_car()
                    GBFS_car = create_GBFS_car()
                    neat_car = create_neat_car()
                    dijkstra_car = create_dijkstra_car()
                    setup = False
                    do_training = False
                    pending_countdown = True
                    countdown_time = 2.1  # ~ "3,2,1"
                elif action == "train":
                    game_info.next_level()  # Start at level 1
                    load_track_for_level(game_info.get_level())
                    # Create fresh cars for training
                    player_car = create_player_car()
                    computer_car = create_computer_car()
                    GBFS_car = create_GBFS_car()
                    neat_car = create_neat_car()
                    dijkstra_car = create_dijkstra_car()
                    setup = False
                    do_training = True
                    training_done = False
                elif action == "page1":
                    resources.click_sound.play()
                    menu.drawPage1(WIN)
                elif action == "page1Back":
                    resources.click_sound.play()
                    menu.backPage1(WIN)
                elif action == "page2":
                    resources.click_sound.play()
                    menu.drawPage2(WIN)
                elif action == "page2Back":
                    resources.click_sound.play()
                    menu.backPage2(WIN)
                elif action == "quit":
                    resources.click_sound.play()
                    running = False

                if event.type == pygame.KEYDOWN and event.key in (pygame.K_RETURN, pygame.K_SPACE):
                    # Keyboard shortcut from menu → start race directly
                    setup = False
                    do_training = False
                    pending_countdown = True
                    countdown_time = 2.1

            else:
                # Non-menu key shortcuts
                if event.type == pygame.KEYDOWN:
                    if event.key in (pygame.K_RETURN, pygame.K_SPACE):
                        # During training, allow early exit to race
                        if not game_info.started and do_training:
                            training_done = True
                            setup = False
                            do_training = False
                            pending_countdown = True
                            countdown_time = 2.1


        # -------------------------------
        # Draw (when racing)
        # -------------------------------
        if game_info.started and player_car is not None:
            ui.draw(WIN, images, player_car, computer_car, GBFS_car, neat_car, dijkstra_car)               

        # -------------------------------
        # TRAINING (non-blocking)
        # -------------------------------
        if (not game_info.started) and do_training and (not training_done):
            # Advance NEAT multiple steps per frame
            gen = idx = total = 0
            for i in range(5):
                gen, idx, total = manager.update(dt)
                if gen >= TRAIN_GENERATIONS:
                    training_done = True
                    break

            # Draw training HUD
            WIN.fill((25, 25, 25))
            manager.draw(WIN, images)
            hud_font = _font(24)
            WIN.blit(
                hud_font.render(
                    f"Training NEAT: Gen {gen} | Genome {idx}/{total}",
                    True, (255, 255, 255)
                ),
                (10, 10)
            )
            WIN.blit(
                hud_font.render(
                    "Press ENTER/SPACE to start race now",
                    True, (200, 200, 200)
                ),
                (10, 40)
            )

            
            summary_text = manager.get_generation_summary()
            WIN.blit(hud_font.render(summary_text, True, (200, 200, 200)), (10, 70))

            # If training finished or user requested to start:
            if training_done:
                net = _build_winner_net()
                if net is not None:
                    neat_car.set_net(net)

                for n in ["3", "2", "1"]:
                    WIN.fill((0, 0, 0))
                    blit_text_center(WIN, _font(48), n)
                    pygame.display.update()
                    pygame.time.delay(700)

                game_info.start_level()
                break

            pygame.display.update()

        # -------------------------------
        # COUNTDOWN (non-blocking)
        # -------------------------------
        if (not game_info.started) and pending_countdown:
            WIN.fill((0, 0, 0))
            # Visual "3,2,1" based on remaining time
            n = "3"
            if countdown_time < 1.4:
                n = "2"
            if countdown_time < 0.7:
                n = "1"

            blit_text_center(WIN, _font(48), n)
            pygame.display.flip()
            countdown_time -= dt
            if countdown_time <= 0:
                game_info.next_level()  # start at level 1
                game_info.start_level()
                pending_countdown = False


        # -------------------------------
        # RACING
        # -------------------------------
        if game_info.started and player_car is not None:
            ui.draw(WIN, images, player_car, computer_car, GBFS_car, neat_car, dijkstra_car)

            # Update cars + agents
            neat_car.move()
            neat_car.sense(neat_car.track_mask, raycast_mask)
            neat_car.think()
            neat_car.apply_controls()

            ui.move_player(player_car)
            computer_car.move()
            GBFS_car.move()
            dijkstra_car.move()

        # -------------------------------
        # Collisions & LEVEL SWITCH
        # -------------------------------
        level_finished = False
        if player_car is not None:
            level_finished = ui.handle_collision(
                player_car, computer_car, GBFS_car, neat_car, dijkstra_car)
        

        if level_finished:
            if game_info.next_level():

                # 1️⃣ Load new track + racing line
                load_track_for_level(game_info.get_level())

                # 2️⃣ Update NEAT manager mask
                manager.track_mask = resources.TRACK_BORDER_MASK

                # 3️⃣ Recreate all cars cleanly (they auto-pull RACING_LINE)
                player_car = create_player_car()
                computer_car = create_computer_car()
                GBFS_car = create_GBFS_car()
                neat_car = create_neat_car()
                dijkstra_car = create_dijkstra_car()

                game_info.start_level()

        pygame.display.flip()
        await asyncio.sleep(0)


# --- Required pygbag entry point: nothing after asyncio.run(main()) ---
if __name__ == "__main__":
    asyncio.run(main())
