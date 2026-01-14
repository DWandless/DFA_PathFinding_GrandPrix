# main.py
import pygame
import neat
import ui
from neatmanager import NEATManager
import resources
from resources import (
    GameInfo, WIN, FPS, images,
    create_player_car, create_computer_car, create_GBFS_car,
    create_neat_car, blit_text_center,
    TRACK_BORDER_MASK, raycast_mask,
    load_track_for_level
)

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
    track_mask=TRACK_BORDER_MASK,
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

def run():
    # --------------------------------------------------
    # Initial setup
    # --------------------------------------------------
    player_car = create_player_car()
    computer_car = create_computer_car()
    GBFS_car = create_GBFS_car()
    neat_car = create_neat_car()

    game_info = GameInfo()

    setup = True
    running = True
    clock = pygame.time.Clock()
    training_done = False

    menu = ui.Menu()
    menu.drawMain(WIN)

    while running:
        dt = clock.tick(FPS) / 1000.0

        # -------------------------------
        # Draw Menu (before racing)
        # -------------------------------
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

            if setup:                                          # <---
                action = menu.handle_event(event)
                if action == "play":
                    game_info.next_level()  # Start at level 1
                    setup = False
                    game_info.start_level()
                elif action == "train":
                    game_info.next_level()  # Start at level 1
                    setup = False
                elif action == "page1":
                    menu.drawPage1(WIN)
                elif action == "page1Back":
                    menu.backPage1(WIN)
                elif action == "page2":
                    menu.drawPage2(WIN)
                elif action == "page2Back":
                    menu.backPage2(WIN)
                elif action == "quit":
                    running = False

                if event.type == pygame.KEYDOWN and event.key in (pygame.K_RETURN, pygame.K_SPACE):
                    setup = False
                    game_info.started = True


        # -------------------------------
        # Draw (when racing)
        # -------------------------------
        if game_info.started:
            ui.draw(WIN, images, player_car, computer_car, GBFS_car, neat_car)

        # -------------------------------
        # TRAINING PHASE
        # -------------------------------
        while not game_info.started and not setup:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                    break
                if event.type == pygame.KEYDOWN:
                    if event.key in (pygame.K_RETURN, pygame.K_SPACE):
                        training_done = True

            for i in range(5):
                gen, idx, total = manager.update(dt)
                if gen >= TRAIN_GENERATIONS:
                    training_done = True
                    break

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
        # Events (racing)
        # -------------------------------
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
                break

        if not running:
            break

        # -------------------------------
        # Update cars
        # -------------------------------
        if game_info.started:
            neat_car.move()
            neat_car.sense(neat_car.track_mask, raycast_mask)
            neat_car.think()
            neat_car.apply_controls()
            ui.move_player(player_car)
            computer_car.move()
            GBFS_car.move()

        # -------------------------------
        # Collisions & LEVEL SWITCH
        # -------------------------------
        level_finished = ui.handle_collision(
            player_car, computer_car, GBFS_car, neat_car
        )

        if level_finished:
            if game_info.next_level():
                # 🔹 SWITCH TRACK (updates globals)
                load_track_for_level(game_info.get_level())

                # 🔹 update NEAT manager + cars to new mask/path
                manager.track_mask = TRACK_BORDER_MASK

                start_pos = resources.START_POSITION

                player_car.set_start_pos(start_pos)
                computer_car.set_start_pos(start_pos)
                GBFS_car.set_start_pos(start_pos)
                neat_car.set_start_pos(start_pos)

                player_car.reset()
                computer_car.reset()
                GBFS_car.reset()
                neat_car.reset()

                new_path = resources.PATH
                new_grid = resources.GRID
                
                neat_car.track_mask = TRACK_BORDER_MASK
                neat_car.path = new_path

                computer_car.path = new_path
                GBFS_car.grid = new_grid
                GBFS_car.track_mask = TRACK_BORDER_MASK

                game_info.start_level()

        pygame.display.flip()

if __name__ == "__main__":
    run()
    pygame.quit()
