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

# --------------------------------------------------
# GAME MENU
# --------------------------------------------------

WHITE = (255, 255, 255)
BLUE = (0, 120, 215)
GRAY = (200, 200, 200)

class Menu():
    
    def __init__(self, width=500, height=500):
        self.width = width
        self.height = height
        self.play = Button((width//2 - 100, height//2 - 60, 200, 50), "Play", BLUE, WHITE)
        self.quit = Button((width//2 - 100, height//2 + 10, 200, 50), "Quit", GRAY, (50, 50, 50))
        self.train = Button((width//2 - 100, height//2 + 80, 200, 50), "Train NEAT", GRAY, (50, 50, 50))
        self.bg = (0, 0, 0)

    def draw(self, surface):
        surface.fill(self.bg)
        self.play.draw(surface)
        self.quit.draw(surface)
        self.train.draw(surface)
        pygame.display.flip()

    def handle_event(self, event):
        if self.play.handle_event(event):
            return "play"
        if self.quit.handle_event(event):
            return "quit"
        if self.train.handle_event(event):
            return "train"
        return None
    
class Button():

    def __init__(self, rect, label, bg_color, text_color):
        self.rect = pygame.Rect(rect)
        self.label = label
        self.bg_color = bg_color
        self.text_color = text_color
        self.font = pygame.font.Font(None, 50)

    def draw(self, surface):
        pygame.draw.rect(surface, self.bg_color, self.rect)
        text = self.font.render(self.label, True, self.text_color)
        # center text
        text_rect = text.get_rect(center=self.rect.center)
        surface.blit(text, text_rect)

    def handle_event(self, event):
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.rect.collidepoint(event.pos):
                return True
        return False




# Possibly redundant
# def loadMenu(win):
#     win.fill((0, 0, 0))
#     font_large = pygame.font.SysFont(None, 48)
#     font_small = pygame.font.SysFont(None, 24)

    
#     WHITE = (255, 255, 255)
#     BLUE = (0, 120, 215)
#     GRAY = (200, 200, 200)

#     # Font
#     font = pygame.font.Font(None, 50)

#     # Button setup
#     play_button = pygame.Rect(500//2 - 100, 500//2 - 60, 200, 50)
#     quit_button = pygame.Rect(500//2 - 100, 500//2 + 10, 200, 50)


    
#     pygame.draw.rect(win, BLUE, play_button)
#     pygame.draw.rect(win, GRAY, quit_button)
#     # Draw text
#     play_text = font.render("Play", True, WHITE)
#     quit_text = font.render("Quit", True, (50, 50, 50))
#     win.blit(play_text, (play_button.x + 60, play_button.y + 5))
#     win.blit(quit_text, (quit_button.x + 60, quit_button.y + 5))
#     pygame.display.flip()

    


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


def draw(win, images, player_car, computer_car, GBFS_car, neat_car, dijkstra_car):
    for img, pos in images:
        win.blit(img, pos)

    player_car.draw(win)
    GBFS_car.draw(win)
    computer_car.draw(win)
    neat_car.draw(win)
    dijkstra_car.draw(win)

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
        # print(player_car.position()) #  DEBUGGING prints cars current stopped position.


def handle_collision(player_car, computer_car, gbfs_car, neat_car, dijkstra_car):
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

    # -----------------------
    # DIJKSTRA CAR
    # -----------------------            
    dijkstra_finish = dijkstra_car.collide(
        resources.FINISH_MASK, *resources.FINISH_POSITION
    )
    if dijkstra_finish and winner is None:
        if dijkstra_finish[1] == 0:
            dijkstra_car.bounce()
        else:
            winner = "DIJKSTRA"
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

