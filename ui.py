"""
# UI helpers: drawing, leaderboard, input and collision handling
import pygame
import time
import csv
import os
from datetime import datetime
import resources


def format_time(seconds):
    return f"{seconds:.2f}s"


def log_result(winner, elapsed):
    with open(resources.RESULTS_CSV, "a", newline="") as f:
        writer = csv.writer(f)
        writer.writerow([
            datetime.now().isoformat(),
            winner,
            f"{elapsed:.3f}",
            resources.GameInfo().level
        ])


def load_leaderboard(limit=5):
    rows = []
    if not os.path.exists(resources.RESULTS_CSV):
        return rows

    with open(resources.RESULTS_CSV, "r", newline="") as f:
        reader = csv.DictReader(f)
        for r in reader:
            try:
                rows.append((r["timestamp"], r["winner"], float(r["time_seconds"])))
            except Exception:
                continue

    rows.sort(key=lambda x: x[2])
    return rows[:limit]


def draw(win, images, player_car, computer_car, GBFS_car, neat_car):
    for img, pos in images:
        win.blit(img, pos)

    player_car.draw(win)
    GBFS_car.draw(win)
    computer_car.draw(win)
    neat_car.draw(win)

    draw_timer_leaderboard_level(win)
    pygame.display.update()


def draw_timer_leaderboard_level(win):
    font = pygame.font.SysFont(None, 24)
    elapsed = time.time() - resources.start_time

    level_text = font.render(
        f"Level: {resources.GameInfo().level}",
        True,
        (255, 255, 255)
    )
    win.blit(level_text, (10, resources.HEIGHT - 160))

    timer_surf = font.render(
        f"Time: {format_time(elapsed)}",
        True,
        (255, 255, 255)
    )
    win.blit(timer_surf, (10, resources.HEIGHT - 140))

    if resources.last_winner is not None:
        last_surf = font.render(
            f"Last: {resources.last_winner} {format_time(resources.last_time)}",
            True,
            (255, 255, 0)
        )
        win.blit(last_surf, (10, resources.HEIGHT - 120))

    lb = load_leaderboard(5)
    x, y = 10, win.get_height() - 10

    title = font.render("Leaderboard (best times)", True, (255, 255, 255))
    y -= title.get_height()
    win.blit(title, (x, y))

    for i, (_, winner, t) in enumerate(lb, start=1):
        entry = font.render(
            f"{i}. {winner}: {format_time(t)}",
            True,
            (255, 255, 255)
        )
        y -= entry.get_height()
        win.blit(entry, (x, y))


def move_player(player_car):
    keys = pygame.key.get_pressed()
    moved = False

    if keys[pygame.K_a]:
        player_car.rotate(left=True)
    if keys[pygame.K_d]:
        player_car.rotate(right=True)
    if keys[pygame.K_w]:
        moved = True
        player_car.move_forward()
    if keys[pygame.K_s]:
        moved = True
        player_car.move_backward()

    if not moved:
        player_car.reduce_speed()


def handle_collision(player_car, computer_car, gbfs_car, neat_car):
    # Prevent multiple winners in one race
    if getattr(resources, "race_finished", False):
        return

    if player_car.collide(resources.TRACK_BORDER_MASK):
        player_car.bounce()

    winner = None

    if computer_car.collide(resources.FINISH_MASK, *resources.FINISH_POSITION):
        winner = "Computer"

    elif gbfs_car.collide(resources.FINISH_MASK, *resources.FINISH_POSITION):
        winner = "GBFS Car"

    elif neat_car.collide(resources.FINISH_MASK, *resources.FINISH_POSITION):
        neat_finish = neat_car.collide(resources.FINISH_MASK, *resources.FINISH_POSITION)
        if neat_finish[1] == 0:
            neat_car.bounce()
        else:
            winner = "NEAT Car"
    else:
        player_finish = player_car.collide(
            resources.FINISH_MASK,
            *resources.FINISH_POSITION
        )
        if player_finish:
            if player_finish[1] == 0:
                player_car.bounce()
            else:
                winner = "Player"

    if winner:
        resources.race_finished = True

        elapsed = time.time() - resources.start_time
        resources.last_winner = winner
        resources.last_time = elapsed
        log_result(winner, elapsed)

        player_car.reset()
        computer_car.reset()
        gbfs_car.reset()
        neat_car.reset()

        resources.start_time = time.time()
        resources.race_finished = False
"""

"""UI helpers: drawing, leaderboard, input and collision handling."""
import pygame
import time
import csv
import os
from datetime import datetime
import resources


def format_time(seconds):
    return f"{seconds:.2f}s"


def log_result(winner, elapsed):
    with open("results.csv", "a", newline="") as f:
        writer = csv.writer(f)
        writer.writerow([
            datetime.now().isoformat(),
            winner,
            f"{elapsed:.3f}",
            resources.GameInfo().get_level()
        ])


def load_leaderboard(limit=5):
    rows = []
    if not os.path.exists("results.csv"):
        return rows

    with open("results.csv", "r", newline="") as f:
        reader = csv.reader(f)
        for r in reader:
            try:
                rows.append((r[0], r[1], float(r[2])))
            except Exception:
                continue

    rows.sort(key=lambda x: x[2])
    return rows[:limit]


def draw(win, images, player_car, computer_car, GBFS_car, neat_car):
    for img, pos in images:
        win.blit(img, pos)

    player_car.draw(win)
    GBFS_car.draw(win)
    computer_car.draw(win)
    neat_car.draw(win)

    draw_timer_leaderboard_level(win)
    pygame.display.update()


def draw_timer_leaderboard_level(win):
    font = pygame.font.SysFont(None, 24)
    elapsed = time.time() - resources.start_time

    level_text = font.render(
        f"Level: {resources.GameInfo().get_level()}",
        True, (255, 255, 255)
    )
    win.blit(level_text, (10, win.get_height() - 160))

    timer_surf = font.render(
        f"Time: {format_time(elapsed)}",
        True, (255, 255, 255)
    )
    win.blit(timer_surf, (10, win.get_height() - 140))

    if getattr(resources, "last_winner", None):
        last_surf = font.render(
            f"Last: {resources.last_winner} {format_time(resources.last_time)}",
            True, (255, 255, 0)
        )
        win.blit(last_surf, (10, win.get_height() - 120))

    lb = load_leaderboard(5)
    x, y = 10, win.get_height() - 10

    title = font.render("Leaderboard", True, (255, 255, 255))
    y -= title.get_height()
    win.blit(title, (x, y))

    for i, (_, winner, t) in enumerate(lb, start=1):
        entry = font.render(
            f"{i}. {winner}: {format_time(t)}",
            True, (255, 255, 255)
        )
        y -= entry.get_height()
        win.blit(entry, (x, y))


def move_player(player_car):
    keys = pygame.key.get_pressed()
    moved = False

    if keys[pygame.K_a]:
        player_car.rotate(left=True)
    if keys[pygame.K_d]:
        player_car.rotate(right=True)
    if keys[pygame.K_w]:
        moved = True
        player_car.move_forward()
    if keys[pygame.K_s]:
        moved = True
        player_car.move_backward()

    if not moved:
        player_car.reduce_speed()


def handle_collision(player_car, computer_car, gbfs_car, neat_car):
    """
    Returns True exactly once when a car legally finishes the race.
    Cars bounce if they cross the finish line in the wrong direction.
    """

    # Track border collision
    if player_car.collide(resources.TRACK_BORDER_MASK):
        player_car.bounce()

    winner = None

    # -----------------------
    # COMPUTER CAR
    # -----------------------
    comp_finish = computer_car.collide(
        resources.FINISH_MASK, *resources.FINISH_POSITION
    )
    if comp_finish:
        if comp_finish[1] == 0:
            computer_car.bounce()
        else:
            winner = "Computer"

    # -----------------------
    # GBFS CAR
    # -----------------------
    gbfs_finish = gbfs_car.collide(
        resources.FINISH_MASK, *resources.FINISH_POSITION
    )
    if gbfs_finish and winner is None:
        if gbfs_finish[1] == 0:
            gbfs_car.bounce()
        else:
            winner = "GBFS"

    # -----------------------
    # NEAT CAR
    # -----------------------
    neat_finish = neat_car.collide(
        resources.FINISH_MASK, *resources.FINISH_POSITION
    )
    if neat_finish and winner is None:
        if neat_finish[1] == 0:
            neat_car.bounce()
        else:
            winner = "NEAT"

    # -----------------------
    # PLAYER CAR
    # -----------------------
    player_finish = player_car.collide(
        resources.FINISH_MASK, *resources.FINISH_POSITION
    )
    if player_finish and winner is None:
        if player_finish[1] == 0:
            player_car.bounce()
        else:
            winner = "Player"

    if winner is None:
        return False

    # -----------------------
    # RACE FINISHED
    # -----------------------
    elapsed = time.time() - resources.start_time
    resources.last_winner = winner
    resources.last_time = elapsed
    log_result(winner, elapsed)

    # Reset cars for next level
    player_car.reset()
    computer_car.reset()
    gbfs_car.reset()
    neat_car.reset()

    resources.start_time = time.time()

    return True

