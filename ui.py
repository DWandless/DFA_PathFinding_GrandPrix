# ui.py
import pygame
import time
import csv
from datetime import datetime
import resources
from resources import MENU, MENU2, MENU3, MENU4
from pricing import price_build, RANGE, MODEL_BASE_PRICE, TRACK_MULT
from tuning_registry import build_registry
# --------------------------------------------------
# Utilities
# --------------------------------------------------

WHITE = (255, 255, 255)
BLUE = (0, 120, 215)
GRAY = (200, 200, 200)
DARK  = (18, 18, 18)

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
        surface.blit(MENU4, (0, 0)) # TODO: Change to level select background if available to one to accomodate for the level preview on the left hand side of the screen

        hovered_level = None

        level_buttons = [
            (1, self.level1Button),
            (2, self.level2Button),
            (3, self.level3Button),
            (4, self.level4Button),
            (5, self.level5Button),
        ]

        for level, btn in level_buttons:
            btn.enabled = True
            if btn.is_hovered():
                hovered_level = level

        # Draw preview FIRST (so buttons stay on top)
        if hovered_level:
            preview = resources.LEVEL_PREVIEWS.get(hovered_level)
            if preview:
                surface.blit(preview, (48, 425))  # left side
        # Draw buttons
        for _, btn in level_buttons:
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
    
    def is_hovered(self):
        return self.enabled and self.rect.collidepoint(pygame.mouse.get_pos())

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
# TODO: Enhance level end screen with more details / options (restart level, main menu, etc.)
def draw_level_end(win, result, level, time_sec, font):
    win.blit(MENU3, (0, 0))

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


# ──────────────────────────────────────────────────────────────────────────────
# Marketplace / Build UI widgets
# ──────────────────────────────────────────────────────────────────────────────

class PillButton:
    def __init__(self, rect, text, selected=False):
        self.rect = pygame.Rect(rect)
        self.text = text
        self.selected = selected
        self.font = pygame.font.Font(None, 24)

    def draw(self, surf):
        mouse_over = self.rect.collidepoint(pygame.mouse.get_pos())
        base = (60, 130, 250) if self.selected else (70, 70, 70)
        if mouse_over and not self.selected:
            base = (90, 90, 90)
        pygame.draw.rect(surf, base, self.rect, border_radius=14)
        pygame.draw.rect(surf, (255, 255, 255, 40), self.rect, width=1, border_radius=14)
        txt = self.font.render(self.text, True, (255, 255, 255))
        surf.blit(txt, txt.get_rect(center=self.rect.center))

    def handle_event(self, event):
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.rect.collidepoint(event.pos):
                return True
        return False

class ToggleButton:
    def __init__(self, rect, label, initial=False):
        self.rect = pygame.Rect(rect)
        self.label = label
        self.on = bool(initial)
        self.font = pygame.font.Font(None, 22)

    def draw(self, surf):
        color = (80, 160, 80) if self.on else (100, 100, 100)
        pygame.draw.rect(surf, color, self.rect, border_radius=8)
        text = self.font.render(f"{self.label}: {'ON' if self.on else 'OFF'}", True, (255, 255, 255))
        surf.blit(text, text.get_rect(center=self.rect.center))

    def handle_event(self, event):
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.rect.collidepoint(event.pos):
                self.on = not self.on
                return True
        return False

class Slider:
    def __init__(self, rect, min_v, max_v, value, label, fmt="{:.2f}", step=None):
        self.rect = pygame.Rect(rect)
        self.min_v = min_v
        self.max_v = max_v
        self.value = max(min_v, min(max_v, value))
        self.label = label
        self.fmt = fmt
        self.step = step
        self.dragging = False
        self.font = pygame.font.Font(None, 22)

    def draw(self, surf):
        lbl = self.font.render(f"{self.label}: {self.fmt.format(self.value)}", True, (235, 235, 235))
        surf.blit(lbl, (self.rect.x, self.rect.y - 18))
        track_rect = pygame.Rect(self.rect.x, self.rect.y, self.rect.w, 6)
        pygame.draw.rect(surf, (50, 50, 70), track_rect, border_radius=3)
        t = (self.value - self.min_v) / max(1e-9, (self.max_v - self.min_v))
        knob_x = int(self.rect.x + t * self.rect.w)
        fill_rect = pygame.Rect(self.rect.x, self.rect.y, knob_x - self.rect.x, 6)
        pygame.draw.rect(surf, (60, 160, 255), fill_rect, border_radius=3)
        pygame.draw.circle(surf, (230, 230, 230), (knob_x, self.rect.y + 3), 10)

    def _set_from_mouse(self, mouse_x):
        t = (mouse_x - self.rect.x) / max(1e-9, self.rect.w)
        t = max(0.0, min(1.0, t))
        v = self.min_v + t * (self.max_v - self.min_v)
        if self.step:
            steps = round((v - self.min_v) / self.step)
            v = self.min_v + steps * self.step
        self.value = max(self.min_v, min(self.max_v, v))

    def handle_event(self, event):
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            hit = pygame.Rect(self.rect.x - 10, self.rect.y - 10, self.rect.w + 20, 24).collidepoint(event.pos)
            if hit:
                self.dragging = True
                self._set_from_mouse(event.pos[0]); return True
        elif event.type == pygame.MOUSEMOTION and self.dragging:
            self._set_from_mouse(event.pos[0]); return True
        elif event.type == pygame.MOUSEBUTTONUP and event.button == 1 and self.dragging:
            self.dragging = False; return True
        return False

class Dial:
    """
    Rotary knob with min/max mapping.
    Mouse wheel controls the dial ONLY when it has focus (after clicking it).
    """
    def __init__(self, center, radius, min_v, max_v, value, label, fmt="{:.2f}", step=None):
        self.cx, self.cy = center
        self.r = radius
        self.min_v = min_v
        self.max_v = max_v
        self.value = max(min_v, min(max_v, value))
        self.label = label
        self.fmt = fmt
        self.step = step
        self.dragging = False
        self.focused = False
        self.font = pygame.font.Font(None, 22)
        # Dial angles (in radians): start at 225°, end at -45° (clockwise)
        self.a_min = 5 * 3.14159 / 4
        self.a_max = -1 * 3.14159 / 4

    def _val_to_angle(self, v):
        t = (v - self.min_v) / max(1e-9, (self.max_v - self.min_v))
        return self.a_min + (self.a_max - self.a_min) * t

    def _angle_to_val(self, a):
        # wrap to [-pi, pi]
        while a < -3.14159: a += 2 * 3.14159
        while a > 3.14159:  a -= 2 * 3.14159
        # clamp by nearest end if outside arc
        d_min = abs(a - self.a_min)
        d_max = abs(a - self.a_max)
        if (self.a_max < self.a_min and not (self.a_max <= a <= self.a_min)) or \
           (self.a_max > self.a_min and not (self.a_min <= a <= self.a_max)):
            a = self.a_min if d_min < d_max else self.a_max
        t = (a - self.a_min) / max(1e-9, (self.a_max - self.a_min))
        t = max(0.0, min(1.0, t))
        v = self.min_v + t * (self.max_v - self.min_v)
        if self.step:
            steps = round((v - self.min_v) / self.step)
            v = self.min_v + steps * self.step
        return max(self.min_v, min(self.max_v, v))

    def draw(self, surf):
        pygame.draw.circle(surf, (30, 35, 55), (self.cx, self.cy), self.r)
        pygame.draw.circle(surf, (70, 80, 110), (self.cx, self.cy), self.r, width=3)
        for i in range(0, 11):
            t = i / 10.0
            a = self.a_min + (self.a_max - self.a_min) * t
            vec = pygame.math.Vector2(1, 0).rotate_rad(a)
            x1 = int(self.cx + (self.r - 10) * vec.x)
            y1 = int(self.cy + (self.r - 10) * vec.y)
            x2 = int(self.cx + (self.r - 2) * vec.x)
            y2 = int(self.cy + (self.r - 2) * vec.y)
            pygame.draw.line(surf, (120, 130, 160), (x1, y1), (x2, y2), 2)
        a = self._val_to_angle(self.value)
        vec = pygame.math.Vector2(1, 0).rotate_rad(a)
        px = int(self.cx + (self.r - 16) * vec.x)
        py = int(self.cy + (self.r - 16) * vec.y)
        pygame.draw.circle(surf, (255, 215, 0), (px, py), 6)
        lbl = self.font.render(self.label, True, (235, 235, 235))
        val = self.font.render(self.fmt.format(self.value), True, (180, 220, 255))
        surf.blit(lbl, lbl.get_rect(center=(self.cx, self.cy + self.r + 16)))
        surf.blit(val, val.get_rect(center=(self.cx, self.cy + self.r + 34)))

    def nudge_wheel(self, wheel_y):
        """Adjust value using mouse wheel delta (positive up, negative down). Only used when focused."""
        step = self.step if self.step else (self.max_v - self.min_v) / 100.0
        self.value += step * wheel_y
        self.value = max(self.min_v, min(self.max_v, self.value))

    def handle_event(self, event):
        # focus + drag handling
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if pygame.Rect(self.cx - self.r, self.cy - self.r, 2 * self.r, 2 * self.r).collidepoint(event.pos):
                self.dragging = True
                self.focused = True
                return True
        elif event.type == pygame.MOUSEMOTION and self.dragging:
            mx, my = event.pos
            a = pygame.math.Vector2(mx - self.cx, my - self.cy).as_polar()[1]
            a = -a * 3.14159 / 180.0
            self.value = self._angle_to_val(a)
            return True
        elif event.type == pygame.MOUSEBUTTONUP and event.button == 1 and self.dragging:
            self.dragging = False
            return True
        # NOTE: mouse wheel is not handled here.
        #       BuildScreen intercepts wheel and sends it to the focused dial via nudge_wheel().
        return False

def draw_glass_panel(surf, rect, border_color=(255, 215, 0), alpha=140):
    panel = pygame.Surface(rect.size, pygame.SRCALPHA)
    panel.fill((10, 10, 30, alpha))
    pygame.draw.rect(panel, (*border_color, 200), panel.get_rect(), width=3, border_radius=12)
    surf.blit(panel, rect.topleft)

# ──────────────────────────────────────────────────────────────────────────────
# ScrollPanel helper for right-column overflow
# ──────────────────────────────────────────────────────────────────────────────

class ScrollPanel:
    """A simple vertical scroll panel that clips its contents."""
    def __init__(self, rect, content_height, bg=None, radius=8):
        self.rect = pygame.Rect(rect)
        self.content_h = max(content_height, self.rect.height)
        self.offset_y = 0
        self.bg = bg
        self.radius = radius
        self._surf = pygame.Surface((self.rect.width, self.rect.height), pygame.SRCALPHA)

    def scroll(self, dy):
        self.offset_y = max(min(self.offset_y + dy, 0), self.rect.height - self.content_h)

    def begin(self, target_surface):
        self._surf.fill((0, 0, 0, 0))
        if self.bg is not None:
            pygame.draw.rect(self._surf, self.bg, self._surf.get_rect(), border_radius=self.radius)
        return self._surf, self.offset_y

    def end(self, target_surface):
        target_surface.blit(self._surf, self.rect.topleft)

    def handle_wheel(self, event, hover_pos=None, step=40):
        # Allow global wheel; hover_pos is ignored here
        if event.type == pygame.MOUSEWHEEL:
            self.scroll(event.y * step)
            return True
        return False

# ──────────────────────────────────────────────────────────────────────────────
# Build Screen (full: tabs + dials + sliders in scroll; lockable to model)
# ──────────────────────────────────────────────────────────────────────────────

class BuildScreen:
    def __init__(self, surface, budget):
        self.surface = surface
        self.budget = budget
        self.font = pygame.font.Font(None, 28)
        self.h2 = pygame.font.Font(None, 34)
        self.small = pygame.font.Font(None, 22)

        # Tabs (models only — tracks hidden here)
        self.models = ["Player", "Computer", "GBFS", "Dijkstra", "NEAT"]
        self.model_buttons = []

        # Dials & sliders
        self.dials = []          # shared car tunables
        self.sliders_gbfs = []
        self.sliders_dij = []
        self.sliders_neat = []
        self.toggle_gbfs_diag = None

        # BUY / Back buttons — EXACT POSITIONS
        W, H = self.surface.get_width(), self.surface.get_height()
        buy_w, buy_h = 220, 48
        cancel_w = 120
        bottom_bar_y = int(H * 0.95)  # keep BUY low as per your layout
        self.btn_buy    = PillButton((W // 2 - buy_w // 2, bottom_bar_y - buy_h // 2, buy_w, buy_h), "BUY")
        self.btn_cancel = PillButton((W - cancel_w - 20, 20, cancel_w, 36), "Back")  # top-right

        self.selected_model = "NEAT"
        self.selected_track_key = "level1"  # default track (not displayed here)
        self.total_price = 0.0

        # Panel placement (lowered panel)
        self.big_panel = pygame.Rect(int(W * 0.12), int(H * 0.48), int(W * 0.76), int(H * 0.35))

        # Right-column scroll panel (created in layout)
        self._right_scroll = None

        # Lock flag (hide tabs & restrict sliders to chosen model when set)
        self._locked_model = False

        # Currently focused dial (for wheel control)
        self._dial_focus = None

    # ── layout/build helpers ─────────────────────────────────────────

    def _build_tabs(self):
        self.model_buttons = []
        if self._locked_model:
            # When locked, tabs are hidden/disabled
            return
        tab_y = self.big_panel.top - 38
        tab_w, tab_h, gap = 120, 34, 10
        total_w = len(self.models) * tab_w + (len(self.models) - 1) * gap
        start_x = self.big_panel.centerx - total_w // 2
        for i, m in enumerate(self.models):
            b = PillButton((start_x + i * (tab_w + gap), tab_y, tab_w, tab_h), m, selected=(m == self.selected_model))
            self.model_buttons.append(b)

    def _build_first4_dials(self, cc, rc):
        self.dials = []
        left_area = self.big_panel.inflate(-40, 40)
        left_w = left_area.width * 0.52
        cell_w = int(left_w // 2)
        col_x0 = left_area.left + cell_w // 2
        col_x1 = left_area.left + int(1.5 * cell_w)
        row_y0 = left_area.top + 90
        row_y1 = row_y0 + 136
        r = 54

        specs = [
            ((col_x0, row_y0), rc["max_vel"][0],        rc["max_vel"][1],        cc.get("max_vel",        (rc["max_vel"][0]        + rc["max_vel"][1])        / 2), "max_vel",        "{:.2f}", 0.1),
            ((col_x1, row_y0), rc["acceleration"][0],   rc["acceleration"][1],   cc.get("acceleration",   (rc["acceleration"][0]   + rc["acceleration"][1])   / 2), "acceleration",   "{:.3f}", 0.01),
            ((col_x0, row_y1), rc["rotation_vel"][0],   rc["rotation_vel"][1],   cc.get("rotation_vel",   (rc["rotation_vel"][0]   + rc["rotation_vel"][1])   / 2), "rotation_vel",   "{:.2f}", 0.1),
            ((col_x1, row_y1), rc["brake_factor"][0],   rc["brake_factor"][1],   cc.get("brake_factor",   (rc["brake_factor"][0]   + rc["brake_factor"][1])   / 2), "brake_factor",   "{:.2f}", 0.02),
        ]
        for (cx, cy), lo, hi, val, name, fmt, step in specs:
            self.dials.append(Dial((int(cx), int(cy)), r, lo, hi, val, name, fmt, step))

    def _build_model_sliders(self, reg):
        # GBFS
        rg = RANGE["gbfs"]; g = reg.get("gbfs", {})
        self.sliders_gbfs = [
            Slider((0, 0, 270, 6), rg["Lookahead_Dist"][0],  rg["Lookahead_Dist"][1],  g.get("Lookahead_Dist", 40),    "Lookahead_Dist",    "{:.0f}", 2),
            Slider((0, 0, 270, 6), rg["ahead_window"][0],    rg["ahead_window"][1],    g.get("ahead_window", 60),      "ahead_window",      "{:.0f}", 2),
            Slider((0, 0, 270, 6), rg["clearance_weight"][0],rg["clearance_weight"][1],g.get("clearance_weight", 0.40),"clearance_weight",  "{:.2f}", 0.05),
            Slider((0, 0, 270, 6), rg["detour_alpha"][0],    rg["detour_alpha"][1],    g.get("detour_alpha", 0.50),    "detour_alpha",      "{:.2f}", 0.05),
            Slider((0, 0, 270, 6), rg["max_expansions"][0],  rg["max_expansions"][1],  g.get("max_expansions", 50000), "max_expansions",    "{:.0f}", 1000),
            Slider((0, 0, 270, 6), rg["Align_Angle"][0],     rg["Align_Angle"][1],     g.get("Align_Angle", 30),       "Align_Angle",       "{:.0f}", 1),
        ]
        self.toggle_gbfs_diag = ToggleButton((0, 0, 160, 28), "allow_diag", bool(g.get("allow_diag", 0)))

        # Dijkstra
        rd = RANGE["dijkstra"]; d = reg.get("dijkstra", {})
        self.sliders_dij = [
            Slider((0, 0, 270, 6), rd["GRID_SIZE"][0],          rd["GRID_SIZE"][1],          d.get("GRID_SIZE", 4),           "GRID_SIZE",          "{:.0f}", 1),
            Slider((0, 0, 270, 6), rd["WAYPOINT_REACH"][0],     rd["WAYPOINT_REACH"][1],     d.get("WAYPOINT_REACH", 12),     "WAYPOINT_REACH",     "{:.0f}", 1),
            Slider((0, 0, 270, 6), rd["CHECKPOINT_RADIUS"][0],  rd["CHECKPOINT_RADIUS"][1],  d.get("CHECKPOINT_RADIUS", 30),  "CHECKPOINT_RADIUS",  "{:.0f}", 1),
        ]

        # NEAT
        rn = RANGE["neat"]; n = reg.get("neat", {})
        self.sliders_neat = [
            Slider((0, 0, 270, 6), rn["pop_size"][0],            rn["pop_size"][1],            n.get("pop_size", 120),            "pop_size",            "{:.0f}", 5),
            Slider((0, 0, 270, 6), rn["weight_mutate_rate"][0],  rn["weight_mutate_rate"][1],  n.get("weight_mutate_rate", 0.6),  "weight_mutate_rate",  "{:.2f}", 0.05),
            Slider((0, 0, 270, 6), rn["weight_mutate_power"][0], rn["weight_mutate_power"][1], n.get("weight_mutate_power", 0.5), "weight_mutate_power", "{:.2f}", 0.05),
            Slider((0, 0, 270, 6), rn["node_add_prob"][0],       rn["node_add_prob"][1],       n.get("node_add_prob", 0.05),      "node_add_prob",       "{:.2f}", 0.01),
            Slider((0, 0, 270, 6), rn["conn_add_prob"][0],       rn["conn_add_prob"][1],       n.get("conn_add_prob", 0.10),      "conn_add_prob",       "{:.2f}", 0.01),
            Slider((0, 0, 270, 6), rn["survival_threshold"][0],  rn["survival_threshold"][1],  n.get("survival_threshold", 0.20),  "survival_threshold",  "{:.2f}", 0.01),
            Slider((0, 0, 270, 6), rn["max_stagnation"][0],      rn["max_stagnation"][1],      n.get("max_stagnation", 12),       "max_stagnation",      "{:.0f}", 1),
        ]

    def _layout_model_sliders(self):
        inner = self.big_panel.inflate(-40, -4)
        split_x = inner.left + int(inner.width * 0.52)
        x0 = split_x + 20
        y0 = inner.top + 170  # room for price box + section title

        def place(list_sliders, start_y):
            y = start_y
            for s in list_sliders:
                s.rect.update(x0, y, 270, 6)  # global rects; draw translated
                y += 52
            return y

        content_y = y0
        if self.selected_model == "GBFS":
            content_y = place(self.sliders_gbfs, y0)
            if self.toggle_gbfs_diag:
                self.toggle_gbfs_diag.rect.update(x0, y0 + 6 + 6 * 52, 160, 28)
                content_y = max(content_y, self.toggle_gbfs_diag.rect.bottom + 8)
        elif self.selected_model == "Dijkstra":
            content_y = place(self.sliders_dij, y0)
        elif self.selected_model == "NEAT":
            content_y = place(self.sliders_neat, y0)

        right_rect = pygame.Rect(split_x + 10, inner.top + 10, inner.width - int(inner.width * 0.52) - 20, inner.height - 20)
        content_height = max(right_rect.height, (content_y - (inner.top + 10)) + 40)
        if self._right_scroll is None:
            self._right_scroll = ScrollPanel(right_rect, content_height, bg=(15, 20, 35, 90), radius=12)
        else:
            self._right_scroll.rect = right_rect
            self._right_scroll.content_h = max(content_height, right_rect.height)
            self._right_scroll.offset_y = max(min(self._right_scroll.offset_y, 0), right_rect.height - self._right_scroll.content_h)

    # NEW: guard the right-panel offset so sliders can't overlap the price box
    def _guard_right_scroll_offset(self):
        """
        Prevent the sliders list from scrolling upward into the fixed price box.
        Ensures the first slider row stays at/under (price_box.bottom + padding).
        """
        if not self._right_scroll:
            return

        # Panel-local geometry: price box at (10, 10) with height 120
        panel_top_local = 10
        price_box_h     = 120
        guard_padding   = 16  # breathing room under price box

        # Sliders' first-row global Y is laid out at inner.top + 170 in _layout_model_sliders
        inner = self.big_panel.inflate(-40, -4)
        y0_global = inner.top + 170
        # Convert to panel-local coords by subtracting panel's global Y (right panel rect's top)
        y0_local  = y0_global - self._right_scroll.rect.y

        # Guard line is the bottom of the price box plus padding, in panel-local
        price_bottom_local = panel_top_local + price_box_h
        guard_line = price_bottom_local + guard_padding

        # Compute the most negative offset allowed so that the first slider top never crosses guard_line
        guard_limit = -(y0_local - guard_line)  # (<= 0)

        # Default scroll clamps (content bounds)
        min_offset = self._right_scroll.rect.height - self._right_scroll.content_h  # most negative
        max_offset = 0  # most positive

        # Apply guard — do not allow more negative than guard_limit
        min_with_guard = max(min_offset, guard_limit)
        self._right_scroll.offset_y = max(min(self._right_scroll.offset_y, max_offset), min_with_guard)

    # ── public entry ─────────────────────────────────────────────────
    # lock_model: if provided, hides tabs & restricts sliders to that model.
    def setup_open(self, base_reg, manager, lock_model=None):
        if lock_model:
            self.selected_model = lock_model
            self._locked_model = True
            self.model_buttons = []  # hard empty to avoid any stray interaction
        else:
            self._locked_model = False

        clock = pygame.time.Clock()
        rc = RANGE["car.common"]
        cc = base_reg.get("car.common", {})

        self._build_tabs()
        self._build_first4_dials(cc, rc)
        self._build_model_sliders(base_reg)
        self._layout_model_sliders()
        self._guard_right_scroll_offset()  # ensure initial offset obeys guard
    def open(self, base_reg, manager, event, lock_model=None):

        # ---------- Global wheel routing ----------
        if event.type == pygame.MOUSEWHEEL:
            if self._dial_focus is not None:
                # Focused dial receives wheel
                self._dial_focus.nudge_wheel(event.y)
            else:
                # Otherwise, wheel always scrolls the right panel
                if self._right_scroll:
                    self._right_scroll.handle_wheel(event)
                    self._guard_right_scroll_offset()
            #continue  # consume wheel

        # ---------- Tabs (skip if locked) ----------
        if not self._locked_model:
            for b in self.model_buttons:
                if b.handle_event(event):
                    self.selected_model = b.text
                    for bb in self.model_buttons:
                        bb.selected = (bb is b)
                    self._layout_model_sliders()
                    self._guard_right_scroll_offset()

        # ---------- Dials ----------
        dial_consumed = False
        for d in self.dials:
            if d.handle_event(event):
                dial_consumed = True
                # If user clicked on this dial, focus it; else keep current focus
                if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    # Clear previous, set new
                    if self._dial_focus and self._dial_focus is not d:
                        self._dial_focus.focused = False
                    self._dial_focus = d
                break

        # If mouse down didn't hit any dial, clear focus so wheel returns to panel
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1 and not dial_consumed:
            if self._dial_focus:
                self._dial_focus.focused = False
            self._dial_focus = None

        # ---------- Right sliders (translate for scroll offset) ----------
        def handle_slider_list(sliders, toggle=None):
            if not self._right_scroll:
                return None
            mouse_pos = pygame.mouse.get_pos()
            if event.type in (pygame.MOUSEBUTTONDOWN, pygame.MOUSEBUTTONUP, pygame.MOUSEMOTION):
                if not self._right_scroll.rect.collidepoint(mouse_pos):
                    return None
            oy = self._right_scroll.offset_y
            for s in sliders:
                orig = s.rect.copy()
                s.rect.y = orig.y + oy
                s.handle_event(event)
                s.rect = orig
            if toggle:
                orig_t = toggle.rect.copy()
                toggle.rect.y = orig_t.y + oy
                toggle.handle_event(event)
                toggle.rect = orig_t

        if self.selected_model == "GBFS":
            handle_slider_list(self.sliders_gbfs, toggle=self.toggle_gbfs_diag)
        elif self.selected_model == "Dijkstra":
            handle_slider_list(self.sliders_dij)
        elif self.selected_model == "NEAT":
            handle_slider_list(self.sliders_neat)
        # Player/Computer: no right-side sliders (shared dials only)

        # ---------- Buttons ----------
        if self.btn_buy.handle_event(event):
            if self.total_price <= self.budget:
                overrides = self._compose_overrides()
                return (self.selected_model, self.selected_track_key, overrides, self.total_price)

        if self.btn_cancel.handle_event(event):
            return None
    

        # recompute price and re-layout as values change
        reg_for_price = self._compose_overrides(as_registry=True, base_reg=base_reg)
        self.total_price = price_build(self.selected_model, self.selected_track_key, reg_for_price)
        self._layout_model_sliders()
        self._guard_right_scroll_offset()  # keep respecting guard even after layout/price changes
        self._draw()
        return None

    # ── compose / draw ──────────────────────────────────────────────

    def _compose_overrides(self, as_registry=False, base_reg=None):
        cc = {
            "max_vel":       self.dials[0].value,
            "acceleration":  self.dials[1].value,
            "rotation_vel":  self.dials[2].value,
            "brake_factor":  self.dials[3].value,
        }
        out = {"car.common": cc}

        if self.selected_model == "GBFS":
            g = {
                "Lookahead_Dist":   self.sliders_gbfs[0].value,
                "ahead_window":     self.sliders_gbfs[1].value,
                "clearance_weight": self.sliders_gbfs[2].value,
                "detour_alpha":     self.sliders_gbfs[3].value,
                "max_expansions":   self.sliders_gbfs[4].value,
                "Align_Angle":      self.sliders_gbfs[5].value,
                "allow_diag":       1 if (self.toggle_gbfs_diag and self.toggle_gbfs_diag.on) else 0,
            }
            out["gbfs"] = g

        if self.selected_model == "Dijkstra":
            d = {
                "GRID_SIZE":          self.sliders_dij[0].value,
                "WAYPOINT_REACH":     self.sliders_dij[1].value,
                "CHECKPOINT_RADIUS":  self.sliders_dij[2].value,
            }
            out["dijkstra"] = d

        if self.selected_model == "NEAT":
            n = {
                "pop_size":            self.sliders_neat[0].value,
                "weight_mutate_rate":  self.sliders_neat[1].value,
                "weight_mutate_power": self.sliders_neat[2].value,
                "node_add_prob":       self.sliders_neat[3].value,
                "conn_add_prob":       self.sliders_neat[4].value,
                "survival_threshold":  self.sliders_neat[5].value,
                "max_stagnation":      self.sliders_neat[6].value,
            }
            out["neat"] = n

        if as_registry:
            reg = base_reg.copy() if base_reg else {"car.common": {}, "gbfs": {}, "dijkstra": {}, "neat": {}}
            for grp, kv in out.items():
                reg.setdefault(grp, {})
                reg[grp].update(kv)
            return reg
        return out

    def _draw_background(self):
        W, H = self.surface.get_width(), self.surface.get_height()
        try:
            bg = pygame.transform.smoothscale(resources.MENU2, (W, H))
            self.surface.blit(bg, (0, 0))
        except Exception:
            self.surface.fill(DARK)

    def _draw_tabs_and_titles(self):
        # Tabs only when not locked
        if not self._locked_model:
            for b in self.model_buttons:
                b.draw(self.surface)

        # Titles + HUD (above panel)
        title_text = "Build Your Car" if not self._locked_model else f"Tune: {self.selected_model}"
        title = self.h2.render(title_text, True, (240, 240, 240))
        self.surface.blit(title, (self.big_panel.left + 24, self.big_panel.top - 72))

        price_col = (0, 220, 120) if self.total_price <= self.budget else (240, 140, 20)
        budget_text = self.font.render(f"Budget: £{self.budget:,.2f}", True, (220, 220, 220))
        price_text  = self.font.render(f"Price: £{self.total_price:,.2f}", True, price_col)
        hud_y = self.big_panel.top - 42
        self.surface.blit(budget_text, (self.big_panel.left + 24, hud_y))
        self.surface.blit(price_text,  (self.big_panel.left + 24 + budget_text.get_width() + 16, hud_y))

    def _draw_big_panel(self):
        draw_glass_panel(self.surface, self.big_panel, border_color=(255, 215, 0), alpha=130)

    def _draw_first4_dials(self):
        inner = self.big_panel.inflate(-40, -40)
        sub = self.small.render("Shared (4)", True, (230, 230, 230))
        self.surface.blit(sub, (inner.left, inner.top))
        for d in self.dials:
            d.draw(self.surface)

    def _draw_model_section(self):
        inner = self.big_panel.inflate(-40, -80)
        right_title_x = inner.left + int(inner.width * 0.52)

        # Right column heading (only for models with sliders)
        if self.selected_model in ("GBFS", "Dijkstra", "NEAT"):
            self.surface.blit(self.h2.render(self.selected_model, True, (230, 230, 230)), (right_title_x + 10, inner.top + 132))

        if self._right_scroll:
            panel_surf, offset_y = self._right_scroll.begin(self.surface)

            # Price box (inside the panel)
            price_rect = pygame.Rect(10, 10, self._right_scroll.rect.width - 20, 120)
            draw_glass_panel(panel_surf, price_rect)
            model_base = MODEL_BASE_PRICE.get(self.selected_model, 0.0)
            lines = [
                f"Model Base: £{model_base:,.0f}",
                f"Track ×: {TRACK_MULT.get(self.selected_track_key, 1.0):.2f}",
                f"Total: £{self.total_price:,.0f}",
            ]
            y = price_rect.top + 12
            for line in lines[:-1]:
                panel_surf.blit(self.font.render(line, True, (230, 230, 230)), (price_rect.left + 12, y))
                y += 28
            total_surf = self.h2.render(lines[-1], True, (255, 235, 120))
            panel_surf.blit(total_surf, (price_rect.left + 12, price_rect.bottom - total_surf.get_height() - 10))

            # Draw sliders within the panel (translate from global -> local)
            def draw_slider_list(sliders, toggle=None):
                for s in sliders:
                    local_rect = s.rect.copy()
                    local_rect.x = local_rect.x - self._right_scroll.rect.x
                    local_rect.y = (s.rect.y - self._right_scroll.rect.y) + offset_y
                    orig = s.rect
                    s.rect = local_rect
                    s.draw(panel_surf)
                    s.rect = orig
                if toggle:
                    local_rect = toggle.rect.copy()
                    local_rect.x = local_rect.x - self._right_scroll.rect.x
                    local_rect.y = (toggle.rect.y - self._right_scroll.rect.y) + offset_y
                    orig = toggle.rect
                    toggle.rect = local_rect
                    toggle.draw(panel_surf)
                    toggle.rect = orig

            if self.selected_model == "GBFS":
                draw_slider_list(self.sliders_gbfs, toggle=self.toggle_gbfs_diag)
            elif self.selected_model == "Dijkstra":
                draw_slider_list(self.sliders_dij)
            elif self.selected_model == "NEAT":
                draw_slider_list(self.sliders_neat)
            # Player/Computer: no right-side sliders (shared dials only)

            self._right_scroll.end(self.surface)

    def _draw_bottom_bar(self):
        can_buy = (self.total_price <= self.budget)
        self.btn_buy.selected = can_buy
        self.btn_buy.draw(self.surface)
        self.btn_cancel.draw(self.surface)

    def _draw(self):
        self._draw_background()
        self._draw_tabs_and_titles()
        self._draw_big_panel()
        self._draw_first4_dials()
        self._draw_model_section()
        self._draw_bottom_bar()



































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