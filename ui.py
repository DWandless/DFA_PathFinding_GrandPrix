# ui.py
import pygame
import time
import csv
from datetime import datetime
import resources
from resources import MENU, MENU2

# --------------------------------------------------
# Utilities
# --------------------------------------------------

WHITE = (255, 255, 255)
BLUE = (0, 120, 215)
GRAY = (200, 200, 200)


def format_time(seconds):
    return f"{seconds:.2f}s"


def log_result(winner, elapsed, level):
    with open("results.csv", "a", newline="") as f:
        writer = csv.writer(f)
        writer.writerow([
            datetime.now().isoformat(),
            winner,
            f"{elapsed:.3f}",
            level
        ])

# --------------------------------------------------
# Menu UI
# --------------------------------------------------

class Menu:
    def __init__(self, width=500, height=500):
        self.width = width
        self.height = height

        # MAIN MENU
        self.playButton = Button((width, height//2 + 25, 200, 50), "Play", BLUE, WHITE)
        self.trainButton = Button((width, height//2 + 150, 200, 50), "Train NEAT", GRAY, WHITE)
        self.page1Button = Button((width, height//2 + 275, 200, 50), "Page 1", GRAY, WHITE)
        self.page2Button = Button((width, height//2 + 400, 200, 50), "Page 2", GRAY, WHITE)
        self.quitButton = Button((width, height//2 + 525, 200, 50), "Quit", GRAY, WHITE)

        # LEVEL SELECT
        self.level1Button = Button((width, height//2 + 25, 200, 50), "Level 1", BLUE, WHITE)
        self.level2Button = Button((width, height//2 + 150, 200, 50), "Level 2", GRAY, WHITE)
        self.level3Button = Button((width, height//2 + 275, 200, 50), "Level 3", GRAY, WHITE)
        self.level4Button = Button((width, height//2 + 400, 200, 50), "Level 4", GRAY, WHITE)
        self.level5Button = Button((width, height//2 + 525, 200, 50), "Level 5", GRAY, WHITE)

        # BACK BUTTON (used by Page1 / Page2)
        self.backButton = Button((width/2 + 100, height//2 + 425, 200, 50), "Back", GRAY, WHITE)

    def disable_all_buttons(self):
        for btn in [
            self.playButton, self.trainButton,
            self.page1Button, self.page2Button, self.quitButton,
            self.level1Button, self.level2Button,
            self.level3Button, self.level4Button, self.level5Button,
            self.backButton
        ]:
            btn.enabled = False

    # ---------------- MAIN MENU ----------------
    def drawMain(self, surface):
        self.disable_all_buttons()
        surface.blit(MENU, (0, 0))

        for btn in [
            self.playButton, self.trainButton,
            self.page1Button, self.page2Button,
            self.quitButton
        ]:
            btn.enabled = True
            btn.draw(surface)

    # ---------------- LEVEL SELECT ----------------
    def drawLevels(self, surface):
        self.disable_all_buttons()
        surface.blit(MENU, (0, 0))

        for btn in [
            self.level1Button, self.level2Button,
            self.level3Button, self.level4Button,
            self.level5Button
        ]:
            btn.enabled = True
            btn.draw(surface)

    # ---------------- PAGE 1 ----------------
    def drawPage1(self, surface):
        self.disable_all_buttons()
        surface.blit(MENU2, (0, 0))

        self.backButton.enabled = True
        self.backButton.draw(surface)

    # ---------------- PAGE 2 ----------------
    def drawPage2(self, surface):
        self.disable_all_buttons()
        surface.blit(MENU2, (0, 0))

        self.backButton.enabled = True
        self.backButton.draw(surface)

    # ---------------- EVENTS ----------------
    def handle_event(self, event):
        if self.playButton.handle_event(event):
            return "play"
        if self.trainButton.handle_event(event):
            return "train"
        if self.page1Button.handle_event(event):
            return "page1"
        if self.page2Button.handle_event(event):
            return "page2"
        if self.quitButton.handle_event(event):
            return "quit"

        if self.level1Button.handle_event(event):
            return "level1"
        if self.level2Button.handle_event(event):
            return "level2"
        if self.level3Button.handle_event(event):
            return "level3"
        if self.level4Button.handle_event(event):
            return "level4"
        if self.level5Button.handle_event(event):
            return "level5"

        if self.backButton.handle_event(event):
            return "back"

        return None



class Button:
    def __init__(self, rect, label, bg_color, text_color):
        self.rect = pygame.Rect(rect)
        self.label = label
        self.bg_color = bg_color
        self.text_color = text_color
        self.font = pygame.font.Font(None, 50)
        self.enabled = True

    def draw(self, surface):
        if not self.enabled:
            return
        text = self.font.render(self.label, True, self.text_color)
        surface.blit(text, text.get_rect(center=self.rect.center))

    def handle_event(self, event):
        return (
            self.enabled
            and event.type == pygame.MOUSEBUTTONDOWN
            and event.button == 1
            and self.rect.collidepoint(event.pos)
        )

# --------------------------------------------------
# Level End Screen
# --------------------------------------------------

def draw_level_end(win, result, level, time_sec, font):
    win.fill((0, 0, 0))

    title = "YOU WIN!" if result == "win" else "YOU LOSE"
    color = (0, 200, 0) if result == "win" else (200, 0, 0)

    win.blit(font.render(title, True, color),
             font.render(title, True, color).get_rect(center=(win.get_width()//2, 200)))

    info = pygame.font.Font(None, 32)
    win.blit(info.render(f"Level: {level}", True, WHITE), (win.get_width()//2 - 80, 300))
    win.blit(info.render(f"Time: {time_sec:.2f}s", True, WHITE), (win.get_width()//2 - 80, 340))
    win.blit(info.render("Press ENTER to continue", True, (180,180,180)),
             (win.get_width()//2 - 140, 420))

# --------------------------------------------------
# Gameplay helpers
# --------------------------------------------------

def draw(win, images, player_car, computer_car, gbfs_car, neat_car, dijkstra_car):
    for img, pos in images:
        win.blit(img, pos)

    player_car.draw(win)
    gbfs_car.draw(win)
    computer_car.draw(win)
    neat_car.draw(win)
    dijkstra_car.draw(win)

    pygame.display.update()


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
        #print(player_car.position()) #  DEBUGGING prints cars current stopped position.


def handle_collision(player_car, computer_car, gbfs_car, neat_car, dijkstra_car):
    if player_car.collide(resources.TRACK_BORDER_MASK):
        player_car.bounce()

    cars = [
        ("player", player_car),
        ("computer", computer_car),
        ("gbfs", gbfs_car),
        ("neat", neat_car),
        ("dijkstra", dijkstra_car),
    ]

    for name, car in cars:
        hit = car.collide(resources.FINISH_MASK, *resources.FINISH_POSITION)
        if hit:
            if hit[1] == 0:
                car.bounce()
            else:
                return name

    return None



""" TODO: Currently unused removed leaderboard functions for time being - reimplement this at a later date
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
"""