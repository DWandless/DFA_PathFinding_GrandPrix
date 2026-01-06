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
    with open(resources.RESULTS_CSV, "a", newline="") as f:
        writer = csv.writer(f)
        writer.writerow([datetime.now().isoformat(), winner, f"{elapsed:.3f}"])


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


def draw(win, images, player_car, computer_car):
    for img, pos in images:
        win.blit(img, pos)

    player_car.draw(win)
    computer_car.draw(win)
    draw_timer_and_leaderboard(win)
    pygame.display.update()


def draw_timer_and_leaderboard(win):
    font = pygame.font.SysFont(None, 24)
    elapsed = time.time() - resources.start_time
    timer_surf = font.render(f"Time: {format_time(elapsed)}", True, (255, 255, 255))
    win.blit(timer_surf, (10, 10))

    if resources.last_winner is not None:
        last_surf = font.render(f"Last: {resources.last_winner} {format_time(resources.last_time)}", True, (255, 255, 0))
        win.blit(last_surf, (10, 36))

    lb = load_leaderboard(5)
    padding = 10
    x = 10
    y = win.get_height() - padding
    title = font.render("Leaderboard (best times)", True, (200, 200, 200))
    y -= title.get_height()
    win.blit(title, (x, y))
    y -= 6
    for i, row in enumerate(lb, start=1):
        ts, winner, t = row
        entry = font.render(f"{i}. {winner}: {format_time(t)}", True, (180, 180, 180))
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


def handle_collision(player_car, computer_car):
    if player_car.collide(resources.TRACK_BORDER_MASK) is not None:
        player_car.bounce()

    computer_finish_poi_collide = computer_car.collide(resources.FINISH_MASK, *resources.FINISH_POSITION)
    if computer_finish_poi_collide is not None:
        elapsed = time.time() - resources.start_time
        resources.last_winner = "Computer"
        resources.last_time = elapsed
        log_result("Computer", elapsed)
        player_car.reset()
        computer_car.reset()
        resources.start_time = time.time()

    player_finish_poi_collide = player_car.collide(resources.FINISH_MASK, *resources.FINISH_POSITION)
    if player_finish_poi_collide is not None:
        if player_finish_poi_collide[1] == 0:
            player_car.bounce()
        else:
            elapsed = time.time() - resources.start_time
            resources.last_winner = "Player"
            resources.last_time = elapsed
            log_result("Player", elapsed)
            player_car.reset()
            computer_car.reset()
            resources.start_time = time.time()
