import pygame, math
from resources import (
    GameInfo, WIN, FPS, images,
    create_player_car, create_computer_car, create_GBFS_car,
    blit_text_center, create_neat_car, TRACK_BORDER_MASK, raycast_mask
)
import ui
from neatmanager import NEATManager
import neat

# -----------------------------
# NEAT setup (config must match your 6-in, 2-out controller)
# -----------------------------
config = neat.Config(
    neat.DefaultGenome,
    neat.DefaultReproduction,
    neat.DefaultSpeciesSet,
    neat.DefaultStagnation,
    'neat_config.ini'
)

# Manager drives training inside the loop
manager = NEATManager(
    neat_config=config,
    car_factory=create_neat_car,    # zero-arg factory that returns a NEATCar already wired to TRACK_BORDER_MASK & GRID
    track_mask=TRACK_BORDER_MASK,
    raycast_fn=raycast_mask,
    fps=FPS,
    time_limit_sec=20.0
)

# How long to train before racing (you can tweak this)
TRAIN_GENERATIONS = 10

def _font(size):
    """Safe font: avoids SysFont issues on some systems."""
    pygame.font.init()
    return pygame.font.Font(None, size)

def _build_winner_net():
    """
    Build a neat.nn.FeedForwardNetwork from the best genome we have so far.
    Prefer manager.winner (if available), else try manager.stats.best_genome(),
    else pick the best by fitness from current population.
    """
    best = None

    # 1) If manager captured a winner during run()
    if getattr(manager, 'winner', None) is not None:
        best = manager.winner

    # 2) Try StatisticsReporter best genome
    if best is None and hasattr(manager, 'stats'):
        try:
            best = manager.stats.best_genome()
        except Exception:
            best = None

    # 3) Fallback: best genome by fitness from current population
    if best is None and hasattr(manager, 'pop'):
        try:
            # manager.pop.population: dict {id: genome}
            pop_items = list(manager.pop.population.items())
            # Filter only genomes with a fitness attribute
            scored = [(gid, g) for gid, g in pop_items if hasattr(g, 'fitness')]
            if scored:
                best = max((g for _, g in scored), key=lambda g: g.fitness)
        except Exception:
            best = None

    if best is None:
        return None

    return neat.nn.FeedForwardNetwork.create(best, config)

def run():
    player_car = create_player_car()
    computer_car = create_computer_car()
    GBFS_car = create_GBFS_car()     # create GBFS car
    neat_car = create_neat_car()     # create NEAT car (controller attached after training)

    game_info = GameInfo()

    running = True
    clock = pygame.time.Clock()

    # -----------------------------
    # Pre-race training loop happens while game not started
    # -----------------------------
    training_done = True

    while running:
        dt = clock.tick(FPS) / 1000.0

        # ----- draw the whole scene when racing -----
        if game_info.started:
            ui.draw(WIN, images, player_car, computer_car, GBFS_car, neat_car)

        # ----- TRAINING PHASE: runs before user starts level -----
        while not game_info.started and running:
            # Process events during the training phase
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                    break
                if event.type == pygame.KEYDOWN:
                    # ENTER starts the race immediately
                    if event.key in (pygame.K_RETURN, pygame.K_SPACE):
                        training_done = True

            # Run one frame of NEAT training
            gen, idx, total = manager.update(dt)

            # Simple training HUD + render the manager's current car
            WIN.fill((25, 25, 25))
            # Draw whatever background/track your training wants (optional)
            manager.draw(WIN)

            # HUD
            hud_font = _font(24)
            hud_line1 = hud_font.render(f"Training NEAT: Gen {gen} | Genome {idx}/{total}", True, (255,255,255))
            hud_line2 = hud_font.render("Press ENTER/SPACE to start race now", True, (200,200,200))
            WIN.blit(hud_line1, (10, 10))
            WIN.blit(hud_line2, (10, 40))

            # Auto-finish training after N generations
            if gen >= TRAIN_GENERATIONS:
                training_done = True

            # If training is done, build winner net and attach to neat_car
            if training_done:
                net = _build_winner_net()
                if net is not None:
                    neat_car.set_net(net)
                # Countdown then start the level
                for n in ["3", "2", "1"]:
                    WIN.fill((0, 0, 0))
                    blit_text_center(WIN, _font(48), n)
                    pygame.display.update()
                    pygame.time.delay(700)
                game_info.start_level()
                break  # leave the "while not started" loop

            pygame.display.update()

        # ---- normal event processing when racing ----
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
                break

        if not running:
            break

        # ---- Update (racing) ----
        ui.move_player(player_car)
        computer_car.move()
        GBFS_car.move()

        # The NEAT car drives itself each frame:
        # If your NEATCar.move() already calls sense/think/apply, use neat_car.move().
        # If you separated these, do the 4-step sequence:
        # neat_car.sense(TRACK_BORDER_MASK, raycast_mask)
        # neat_car.think()
        # neat_car.apply_controls()
        # AbstractCar.move is called inside apply_controls or here depending on your design.
        neat_car.move()

        # Collisions & level flow
        ui.handle_collision(player_car, computer_car, GBFS_car, neat_car)

        pygame.display.flip()

if __name__ == "__main__":
    run()
    pygame.quit()
