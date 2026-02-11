# ui.py
import pygame
import csv
from datetime import datetime
import resources
from resources import MENU, MENU2, MENU3, MENU4
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
        self.titleFont = pygame.font.Font(None, 64)
        self.textFont = pygame.font.Font(None, 32)
        self.linkFont = pygame.font.Font(None, 32)
        self.github_url = "https://github.com/DWandless/DFA_PathFinding_GrandPrix"
        self.github_rect = None  # will store clickable area


        # MAIN MENU
        self.playButton = Button((width, height//2 + 25, 200, 50), "Play", BLUE, WHITE)
        self.page1Button = Button((width, height//2 + 150, 200, 50), "Info", GRAY, WHITE)
        self.page2Button = Button((width, height//2 + 275, 200, 50), "Credits", GRAY, WHITE)
        self.trainButton = Button((width, height//2 + 400, 200, 50), "Train NEAT", GRAY, WHITE)
        self.quitButton = Button((width, height//2 + 525, 200, 50), "Quit", GRAY, WHITE)

        # LEVEL SELECT
        self.level1Button = Button((width, height//2 + 25, 200, 50), "Level 1", BLUE, WHITE)
        self.level2Button = Button((width, height//2 + 150, 200, 50), "Level 2", GRAY, WHITE)
        self.level3Button = Button((width, height//2 + 275, 200, 50), "Level 3", GRAY, WHITE)
        self.level4Button = Button((width, height//2 + 400, 200, 50), "Level 4", GRAY, WHITE)
        self.levelInfoButton = Button((width, height//2 + 525, 200, 50), "Info", GRAY, WHITE)

        # BACK BUTTON (universal, top-right for all pages)
        self.backButton = PillButton((width - 140, 20, 120, 36), "Back", selected=False)

        # TOGGLE ICON BUTTON (top-left, main menu only)
        self.toggleIconButton = IconButton(
            (40, 40, 64, 64),
            "assets/icon_sound_off.png",
            "assets/icon_sound_on.png",
            initial_state=getattr(resources, "SOUND_ENABLED", True),
        )

        # Load lock icon
        try:
            lock_img = pygame.image.load("assets/icon_lock.png").convert_alpha()
            self.lock_icon = pygame.transform.smoothscale(lock_img, (48, 48))
        except (pygame.error, FileNotFoundError):
            self.lock_icon = None  # Fallback if icon missing

        # INFO SCROLL PANEL
        self.info_scroll = ScrollPanel(
            (150, 260, self.width + 120, self.height - 120),  # rect
            content_height=1300,  # adjust based on text amount
            bg=(15, 20, 35, 0),  # Transparent background
            radius=12
        )

    def disable_all_buttons(self):
        for btn in [
            self.playButton, self.trainButton,
            self.page1Button, self.page2Button, self.quitButton,
            self.level1Button, self.level2Button,
            self.level3Button, self.level4Button, self.levelInfoButton,
            self.backButton, self.toggleIconButton
        ]:
            btn.enabled = False

    # ---------------- MAIN MENU ----------------
    def drawMain(self, surface):
        self.disable_all_buttons()
        surface.blit(MENU, (0, 0))

        for btn in [
            self.playButton, self.trainButton,
            self.page1Button, self.page2Button,
            self.quitButton, self.toggleIconButton
        ]:
            btn.enabled = True
            btn.draw(surface)

    # ---------------- LEVEL SELECT ----------------
    def drawLevels(self, surface):
        self.disable_all_buttons()
        surface.blit(MENU4, (0, 0))

        hovered_level = None

        level_buttons = [
            (1, self.level1Button),
            (2, self.level2Button),
            (3, self.level3Button),
            (4, self.level4Button),
        ]
        
        for level, btn in level_buttons:
            # Check debug flag first - if True, unlock all levels for testing
            if resources.DEBUG_UNLOCK_ALL_LEVELS:
                btn.enabled = True
            elif resources.HIGHEST_LEVEL >= level:
                btn.enabled = True

            if btn.is_hovered():
                hovered_level = level

        # Draw preview FIRST (so buttons stay on top)
        if hovered_level:
            preview = resources.LEVEL_PREVIEWS.get(hovered_level)
            if preview:
                surface.blit(preview, (48, 434))  # left side
        
        # Enable and draw back button (top right, positioned by surface width)
        self.backButton.rect = pygame.Rect(surface.get_width() - 140, 20, 120, 36)
        self.backButton.enabled = True
        self.backButton.draw(surface)
        
        # Draw level buttons
        for _, btn in level_buttons:
            btn.draw(surface)
        
        # Draw lock icons over disabled buttons (skip if debug mode unlocks all levels)
        if self.lock_icon and not resources.DEBUG_UNLOCK_ALL_LEVELS:
            for level, btn in level_buttons:
                if resources.HIGHEST_LEVEL < level:
                    icon_rect = self.lock_icon.get_rect(center=btn.rect.center)
                    surface.blit(self.lock_icon, icon_rect)

        self.levelInfoButton.enabled = True
        self.levelInfoButton.draw(surface)

    # ---------------- PAGE 1 ----------------
    def drawPage1(self, surface):
        self.disable_all_buttons()
        surface.blit(MENU2, (0, 0))

        # Start scroll panel
        panel_surf, offset_y = self.info_scroll.begin(surface)

        # Draw text lines on panel_surf with offset_y
        info_lines = [
            "Welcome to DFA PathFinding Grand Prix!",
            "",
            "Race using AI pathfinding algorithms:",
            "- Depth-First Search (DFS)",
            "- Breadth-First Search (BFS)",
            "- A* Search Algorithm",
            "- Greedy Best-First Search (GBFS)",
            "- NEAT (Neural Evolution)",
            "",
            "Or take control of the car yourself!",
            "(Controls: W/A/S/D to move)",
            "",
            "1. Select a level.",
            "2. Figure out the best algorithm for the job!",
            "3. Tune your car, simpler algorithm = more money for", 
            "upgrades!",
            "4. Race to the finish line first!",
            "5. If you win, move to the next level...",
            "Or show the AI how it's done by beating them yourself!",
            "_____________________________________________________",
            "HINTS",
            "",
            "DFS: Commits to a direction one by one",
            "can be fast, cheap",
            "BFS: Explores a little bit every direction",
            "can be fast, cheap",
            "A*: Uses a heuristic to logically find the best path",
            "balanced speed and cost",
            "GBFS: Focuses on the most promising path",
            "faster but can go the wrong way",
            "NEAT: Learns to drive through trial and error",
            "unreliable but adaptable",
        ]

        y = 20 + offset_y
        for line in info_lines:
            text = self.textFont.render(line, True, WHITE)
            panel_surf.blit(text, (20, y))
            y += 35

        self.info_scroll.end(surface)

        # ---- GitHub Link Box (below scroll panel) ----
        # Calculate position below scroll panel
        link_box_y = self.info_scroll.rect.bottom + 30
        link_box_height = 60
        link_box_width = 320
        link_box_x = (surface.get_width() - link_box_width) // 2
        
        link_box_rect = pygame.Rect(link_box_x, link_box_y, link_box_width, link_box_height)
        #draw_glass_panel(surface, link_box_rect, border_color=(60, 130, 250), alpha=0)
        
        # Render link text centered in the box
        link_text = self.linkFont.render("GitHub Repository", True, WHITE)
        self.github_rect = link_text.get_rect(center=link_box_rect.center)
        surface.blit(link_text, self.github_rect)

        # underline to make it feel like a link
        pygame.draw.line(
            surface,
            BLUE,
            (self.github_rect.left, self.github_rect.bottom),
            (self.github_rect.right, self.github_rect.bottom),
            2
        )

        # Back button
        self.backButton.rect = pygame.Rect(surface.get_width() - 140, 20, 120, 36)
        self.backButton.enabled = True
        self.backButton.draw(surface)

    # ---------------- PAGE 2 ----------------
    def drawPage2(self, surface):
        self.disable_all_buttons()
        surface.blit(MENU2, (0, 0))

        center_x = surface.get_width() // 2
        y = 300

        # ---- Title ----
        title = self.titleFont.render("Credits", True, WHITE)
        surface.blit(title, title.get_rect(center=(center_x, y)))

        y += 70
        # ---- Names ----
        credits = [
            "Game Design & Programming:",
            "Drew Wandless, Ben Lopez, Nathan Miller",
            "",
            "AI & Pathfinding:",
            "Harry Fox, Matthew Cartwright, Leo Elliott-Jackson",
            "",
            "Built with Pygame"
        ]

        for line in credits:
            text = self.textFont.render(line, True, WHITE)
            surface.blit(text, text.get_rect(center=(center_x, y)))
            y += 36

        y += 80

        # ---- GitHub Link ----
        link_text = self.linkFont.render("GitHub Repository", True, WHITE)
        self.github_rect = link_text.get_rect(center=(center_x, y))
        surface.blit(link_text, self.github_rect)

        # underline to make it feel like a link
        pygame.draw.line(
            surface,
            BLUE,
            (self.github_rect.left, self.github_rect.bottom),
            (self.github_rect.right, self.github_rect.bottom),
            2
        )

        # ---- Back Button (top right, positioned by surface width) ----
        self.backButton.rect = pygame.Rect(surface.get_width() - 140, 20, 120, 36)
        self.backButton.enabled = True
        self.backButton.draw(surface)

    # ---------------- EVENTS ----------------
    def handle_event(self, event):
        # Handle scrolling on info page (check if currently on page1 via enabled state)
        if event.type == pygame.MOUSEWHEEL:
            mouse_pos = pygame.mouse.get_pos()
            self.info_scroll.handle_wheel(event, hover_pos=mouse_pos, step=40)
        
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.github_rect and self.github_rect.collidepoint(event.pos):
                import webbrowser
                webbrowser.open(self.github_url)

        if self.playButton.handle_event(event):
            return "play"
        if self.trainButton.handle_event(event):
            return "train"
        if self.page1Button.handle_event(event):
            return "page1"
        if self.page2Button.handle_event(event):
            return "page2"
        if self.toggleIconButton.handle_event(event):
            return "toggle_sound"
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

        if self.levelInfoButton.handle_event(event):
            return "page1"

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

class IconButton:
    """
    Icon-based button that toggles between two states.
    Each state displays a different icon image.
    """
    def __init__(self, rect, icon_path_state1, icon_path_state2, initial_state=True):
        self.rect = pygame.Rect(rect)
        self.icon_path_state1 = icon_path_state1
        self.icon_path_state2 = icon_path_state2
        self.state = initial_state  # False = state1, True = state2
        self.enabled = True
        # Load icon images with fallback handling
        self.image_state1 = self._load_icon(icon_path_state1)
        self.image_state2 = self._load_icon(icon_path_state2)
        
    def _load_icon(self, path):
        """
        Load an icon from the given path.
        Returns None if loading fails (will use fallback rendering).
        """
        try:
            img = pygame.image.load(path).convert_alpha()
            # Scale to fit button rect while maintaining aspect ratio
            return self._scale_to_fit(img, self.rect.width - 8, self.rect.height - 8)
        except (pygame.error, FileNotFoundError):
            # Return None, will render fallback in draw()
            print("Error loading icon:", path)
            return None
    
    def _scale_to_fit(self, surf, max_w, max_h):
        """
        Scale surface to fit within max dimensions while preserving aspect ratio.
        """
        w, h = surf.get_size()
        if w <= max_w and h <= max_h:
            return surf
        scale = min(max_w / w, max_h / h)
        new_w = max(1, int(w * scale))
        new_h = max(1, int(h * scale))
        return pygame.transform.smoothscale(surf, (new_w, new_h))
    
    def draw(self, surface):
        """
        Draw the icon button. Shows current state's icon with hover effect.
        """
        if not self.enabled:
            return
        
        # Determine colors based on hover state
        mouse_over = self.rect.collidepoint(pygame.mouse.get_pos())
        bg_color = (90, 90, 90) if mouse_over else (70, 70, 70)
        border_color = (120, 120, 120) if mouse_over else (100, 100, 100)
        
        # Draw rounded background
        pygame.draw.rect(surface, bg_color, self.rect, border_radius=12)
        pygame.draw.rect(surface, border_color, self.rect, width=2, border_radius=12)
        
        # Select current icon based on state
        current_icon = self.image_state2 if self.state else self.image_state1
        
        if current_icon:
            # Center the icon in the button
            icon_rect = current_icon.get_rect(center=self.rect.center)
            surface.blit(current_icon, icon_rect)
        else:
            # Fallback: draw a colored square to indicate the button exists
            fallback_color = (0, 200, 100) if self.state else (200, 100, 0)
            fallback_rect = pygame.Rect(0, 0, self.rect.width - 16, self.rect.height - 16)
            fallback_rect.center = self.rect.center
            pygame.draw.rect(surface, fallback_color, fallback_rect, border_radius=6)
    
    def toggle(self):
        """
        Toggle the button state and redraws.
        """
        self.state = not self.state
    
    def handle_event(self, event):
        """
        Handle mouse click events. Returns True if button was clicked.
        """
        if not self.enabled:
            return False
        
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.rect.collidepoint(event.pos):
                self.toggle()
                return True
        return False

# --------------------------------------------------
# Level End Screen
# --------------------------------------------------
# TODO: Enhance level end screen with more details / options (restart level, main menu, etc.)
def draw_level_end(win, result, level, time_sec, font):
    win.blit(MENU3, (0, 0))

    title = "YOU WIN!" if result == "win" else "YOU LOSE"
    color = (0, 200, 0) if result == "win" else (200, 0, 0)

    # If won, unlock next level
    if result == "win":
        resources.HIGHEST_LEVEL = max(resources.HIGHEST_LEVEL, level + 1)  # highest level is just a gloabal int within resources.py

    win.blit(font.render(title, True, color),
             font.render(title, True, color).get_rect(center=(win.get_width()//2, 200)))

    info = pygame.font.Font(None, 32)
    win.blit(info.render(f"Level: {level}", True, WHITE), (win.get_width()//2 - 80, 300))
    win.blit(info.render(f"Time: {time_sec:.2f}s", True, WHITE), (win.get_width()//2 - 80, 340))
    win.blit(info.render("Press ENTER to return to main menu", True, (180,180,180)),
             (win.get_width()//2 - 140, 420))
# Gameplay helpers
# --------------------------------------------------

def draw(win, images, player_car, computer_car, gbfs_car, neat_car, dijkstra_car):
    for img, pos in images:
        win.blit(img, pos)

    # Check if player_car has a draw method that accepts show_points parameter
    if hasattr(player_car, 'draw'):
        # For DijkstraCar, pass False to hide checkpoints
        if hasattr(player_car, 'CHECKPOINTS'):
            player_car.draw(win, False)
        else:
            player_car.draw(win)
    
    gbfs_car.draw(win)
    computer_car.draw(win)
    neat_car.draw(win)
    dijkstra_car.draw(win, False)


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


def handle_collision(player_car, computer_car, gbfs_car, neat_car, dijkstra_car, chosen_model=None):
    # Only apply wall collision bounce to player car when in manual mode
    # Autonomous mode: skip wall collision to prevent getting stuck
    if not getattr(player_car, 'autonomous', False):
        if player_car.collide(resources.TRACK_BORDER_MASK):
            player_car.bounce()

    cars = [
        ("Player", player_car),
        ("Computer", computer_car),
        ("GBFS", gbfs_car),
        ("NEAT", neat_car),
        ("Dijkstra", dijkstra_car),
    ]

    for name, car in cars:
        hit = car.collide(resources.FINISH_MASK, *resources.FINISH_POSITION)
        if hit:
            if hit[1] == 0:
                car.bounce()
            else:
                return name

    return None

# --------------------------------------------------
# ScrollPanel helper for right-column overflow
# --------------------------------------------------

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