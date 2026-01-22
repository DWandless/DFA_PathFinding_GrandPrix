
# main.py
import pygame
import neat
import ui
print("Loaded UI:", getattr(ui, "__UI_VERSION__", "unknown"))
import resources
from neatmanager import NEATManager
from resources import (
    GameInfo, WIN, FPS, images,
    create_player_car, create_computer_car, create_GBFS_car,
    create_neat_car, blit_text_center,
    raycast_mask, load_track_for_level, create_dijkstra_car
)

# NEW: tuning marketplace helpers
from tuning_registry import build_registry, apply_registry
from pricing import price_build, TRACK_MULT

# NEW: model selection screen
from model_select import ModelSelectScreen

TRAIN_GENERATIONS = 10
GAME_BUDGET = 100_000.00

# 📂 Adjust this path if your project assets live elsewhere
ASSETS_DIR = r"C:\Users\bvelasteguil\Desktop\DFA_Pathfinding_GrandPrix_3\assets"

def _font(size: int):
    pygame.font.init()
    return pygame.font.Font(None, size)

def _build_winner_net(manager, config):
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
            scored = [g for g in manager.pop.population.values() if hasattr(g, 'fitness')]
            if scored:
                best = max(scored, key=lambda g: g.fitness)
        except Exception:
            best = None
    if best is None:
        return None
    return neat.nn.FeedForwardNetwork.create(best, manager.config)

def draw_budget_hud(win, total_price, budget, y_offset=10):
    f = _font(22)
    txt = f"Build Price: £{total_price:,.2f} Budget: £{budget:,.2f}"
    col = (0, 200, 0) if total_price <= budget else (220, 120, 0)
    surf = f.render(txt, True, col)
    win.blit(surf, (10, y_offset))

def run():
    # --- NEAT setup ---
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

    game_info = GameInfo()

    # Cars created when a level starts
    player_car = None
    computer_car = None
    GBFS_car = None
    neat_car = None
    dijkstra_car = None

    # Marketplace state (persist across levels)
    last_model = None
    last_track_key = None
    last_reg = None
    last_total_price = 0.0

    setup = True
    running = True
    clock = pygame.time.Clock()
    training_done = False

    # Pass actual window size to the Menu
    menu = ui.Menu(resources.WIN.get_width(), resources.WIN.get_height())
    menu.drawMain(WIN)

    # Build screen object (lazy-create)
    build_screen = None

    while running:
        dt = clock.tick(FPS) / 1000.0

        # -----------------------------
        # Menu / pre-race phase
        # -----------------------------
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

            if setup:
                action = menu.handle_event(event)
                if action == "play" or action == "train":
                    resources.click_sound.play()

                    # ──────────────────────────────────────────────
                    # 1) FIRST: Model selection (with preview)
                    # ──────────────────────────────────────────────
                    selector = ModelSelectScreen(WIN, assets_path=ASSETS_DIR)
                    chosen_model = selector.open(initial_model=last_model or "NEAT")
                    if not chosen_model:
                        # Backed out → remain on main menu
                        continue

                    # ──────────────────────────────────────────────
                    # 2) Build/Tuning screen (dial-only now)
                    #    We keep the tuning flow so the user can
                    #    tweak car.common before starting.
                    # ──────────────────────────────────────────────

                    # Create temp cars (registry can read current defaults)
                    tmp_player = create_player_car()
                    tmp_computer = create_computer_car()
                    tmp_gbfs = create_GBFS_car()
                    tmp_neat = create_neat_car()
                    tmp_dijk = create_dijkstra_car()
                    base_reg = build_registry(manager, [tmp_player, tmp_computer, tmp_gbfs, tmp_neat, tmp_dijk])

                    if build_screen is None:
                        build_screen = ui.BuildScreen(WIN, GAME_BUDGET)

                    # Open Build UI (mouse dials) — returns a tuple, but we'll
                    # override the model with `chosen_model` from the selector.
                    selection = build_screen.open(base_reg, manager, lock_model=chosen_model)
                    if selection is None:
                        # Cancelled → stay on menu
                        continue

                    _model_from_ui, track_key, overrides, total_price = selection

                    # Use the chosen model from the new ModelSelect step
                    model_name = chosen_model

                    # Apply chosen track immediately
                    selected_level = 1 if track_key == "level1" else 2
                    load_track_for_level(selected_level)
                    game_info.level = selected_level  # start from selected level

                    # Create fresh cars for this level
                    player_car = create_player_car()
                    computer_car = create_computer_car()
                    GBFS_car = create_GBFS_car()
                    neat_car = create_neat_car()
                    dijkstra_car = create_dijkstra_car()

                    # Merge overrides + apply registry everywhere
                    # (Budget already enforced in BuildScreen)
                    base_reg = build_registry(manager, [player_car, computer_car, GBFS_car, neat_car, dijkstra_car])
                    # Shallow merge overrides
                    for grp, kv in (overrides or {}).items():
                        base_reg.setdefault(grp, {})
                        base_reg[grp].update(kv)

                    apply_registry(base_reg, manager, [player_car, computer_car, GBFS_car, neat_car, dijkstra_car])

                    # Persist build info
                    last_model, last_track_key, last_reg, last_total_price = model_name, track_key, base_reg, total_price

                    setup = False
                    # If this was "train", we drop into the training loop below
                    if action == "train":
                        game_info.started = False  # training screen renders until ENTER
                    else:
                        # Countdown & race
                        for n in ["3", "2", "1"]:
                            WIN.fill((0, 0, 0))
                            ui.blit_text_center(WIN, _font(48), n)
                            pygame.display.update()
                            pygame.time.delay(700)
                        game_info.start_level()

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
                setup = False
                game_info.started = True

        # Draw menu background (idle)
        if not game_info.started and setup:
            pygame.display.update()
            continue

        # --------------------------------
        # Training phase (NEAT generations)
        # --------------------------------
        while not game_info.started and not setup:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                    break
                if event.type == pygame.KEYDOWN:
                    if event.key in (pygame.K_RETURN, pygame.K_SPACE):
                        training_done = True

            for _ in range(5):
                gen, idx, total = manager.update(dt)
                if gen >= TRAIN_GENERATIONS:
                    training_done = True
                    break

            WIN.fill((25, 25, 25))
            manager.draw(WIN, images)

            # HUD
            hud_font = _font(24)
            WIN.blit(
                hud_font.render(
                    f"Training NEAT: Gen {gen} Genome {idx}/{total}",
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

            if last_total_price:
                draw_budget_hud(WIN, last_total_price, GAME_BUDGET, y_offset=70)

            if training_done:
                net = _build_winner_net(manager, config)
                if net is not None and neat_car is not None:
                    neat_car.set_net(net)

                for n in ["3", "2", "1"]:
                    WIN.fill((0, 0, 0))
                    ui.blit_text_center(WIN, _font(48), n)
                    pygame.display.update()
                    pygame.time.delay(700)
                game_info.start_level()
                break

            pygame.display.update()

        # -----------------------------
        # In-race events
        # -----------------------------
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
                break
        if not running:
            break

        # -----------------------------
        # Update cars while racing
        # -----------------------------
        if game_info.started and player_car is not None:
            # NEAT autonomous flow
            neat_car.move()
            neat_car.sense(neat_car.track_mask, raycast_mask)
            neat_car.think()
            neat_car.apply_controls()

            # Player & others
            ui.move_player(player_car)
            computer_car.move()
            GBFS_car.move()
            dijkstra_car.move()

        # -----------------------------
        # Draw
        # -----------------------------
        if game_info.started and player_car is not None:
            ui.draw(WIN, images, player_car, computer_car, GBFS_car, neat_car, dijkstra_car)
            if last_total_price:
                draw_budget_hud(WIN, last_total_price, GAME_BUDGET, y_offset=10)

        # -----------------------------
        # Collisions & level switch
        # -----------------------------
        level_finished = False
        if player_car is not None:
            level_finished = ui.handle_collision(
                player_car, computer_car, GBFS_car, neat_car, dijkstra_car
            )

        if level_finished:
            if game_info.next_level():
                # 1) Load new track + racing line
                load_track_for_level(game_info.get_level())
                # 2) Update NEAT manager mask
                manager.track_mask = resources.TRACK_BORDER_MASK
                # 3) Recreate all cars cleanly (they auto-pull resources)
                player_car = create_player_car()
                computer_car = create_computer_car()
                GBFS_car = create_GBFS_car()
                neat_car = create_neat_car()
                dijkstra_car = create_dijkstra_car()
                # 4) Re-apply the last purchased build to keep parameters consistent
                if last_reg is not None and last_model is not None and last_track_key is not None:
                    apply_registry(last_reg, manager,
                        [player_car, computer_car, GBFS_car, neat_car, dijkstra_car])
                game_info.start_level()

        pygame.display.flip()

if __name__ == "__main__":
    run()
    pygame.quit()
