"""
Model selection screen for DFA Grand Prix.

- Shows a model carousel with large car preview pulled from assets directory.
- User can navigate with Left/Right or mouse, and confirm with Enter or "Select" button.
- Returns the selected model string, or None if the user cancels.

Author: Benjamin + Copilot
"""

import os
import pygame
import resources

# ---------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------

MODELS = ["Player", "BFS", "DFS", "GBFS", "AStar", "NEAT"]
COLORS = ["Red", "Blue", "Green", "Purple", "White", "Grey", "Pink", "Yellow"]
BLUE = (0, 120, 215)

# Map color and model names to image files
COLOR_TO_IMAGE = {
    "Red": "assets/red-car.png",
    "Blue": "assets/blue-car.png",
    "Green": "assets/green-car.png",
    "Purple": "assets/purple-car.png",
    "White": "assets/white-car.png",
    "Grey": "assets/grey-car.png",
    "Pink": "assets/pink-car.png",
    "Yellow": "assets/yellow-car.png",
}
MODEL_TO_IMAGE = {
    "Player": "assets/icon_brain.png",
    "BFS": "assets/icon_BFS.png",
    "DFS": "assets/icon_DFS.png",
    "GBFS": "assets/icon_GBFS.png",
    "AStar": "assets/icon_astar.png",
    "NEAT": "assets/icon_neat.png",
}

FALLBACK_IMAGE = "assets/car_template.png"
SELECT_SOUND   = "assets/select-sound.ogg"
BG_FILE        = "assets/Menu3.png"

class PillButton:
    def __init__(self, rect, text, selected=False, font_size=24):
        self.rect = pygame.Rect(rect)
        self.text = text
        self.selected = selected
        self.font = pygame.font.Font(None, font_size)
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

class ArrowButton:
    def __init__(self, center, direction="left", size=48):
        self.center = center
        self.direction = direction
        self.size = size
        self.rect = pygame.Rect(0, 0, size, size)
        self.rect.center = center
    def draw(self, surf):
        over = self.rect.collidepoint(pygame.mouse.get_pos())
        base = (60, 60, 60) if not over else (90, 90, 90)
        pygame.draw.circle(surf, base, self.rect.center, self.rect.width // 2)
        cx, cy = self.rect.center; s = self.rect.width // 3
        if self.direction == "left":
            tri = [(cx + s//2, cy - s), (cx + s//2, cy + s), (cx - s, cy)]
        else:
            tri = [(cx - s//2, cy - s), (cx - s//2, cy + s), (cx + s, cy)]
        pygame.draw.polygon(surf, (230, 230, 230), tri)
    def handle_event(self, event):
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.rect.collidepoint(event.pos):
                return True
        return False

def load_image_safe(path):
    try:
        return pygame.image.load(path).convert_alpha()
    except Exception:
        return None

def scale_to_fit(surf, max_w, max_h):
    w, h = surf.get_size()
    if w <= max_w and h <= max_h:
        return surf
    scale = min(max_w / w, max_h / h)
    return pygame.transform.smoothscale(surf, (max(1, int(w*scale)), max(1, int(h*scale))))

class ModelSelectScreen:
    def __init__(self, surface, assets_path="assets", currentLevel = 1, completed = 0):
        self.surface = surface
        self.assets_path = assets_path
        self.W = self.surface.get_width()
        self.H = self.surface.get_height()

        self.title_font = pygame.font.Font(None, 48)
        self.section_font = pygame.font.Font(None, 36)
        self.body_font  = pygame.font.Font(None, 26)

        # Layout - split screen into two sections
        self.title_pos = (int(self.W * 0.10), int(self.H * 0.08))
        
        # Model type selection (top half)
        self.model_label_pos = (int(self.W * 0.10), int(self.H * 0.18))
        self.model_preview_area = pygame.Rect(int(self.W * 0.30), int(self.H * 0.23),
                                              int(self.W * 0.40), int(self.H * 0.20))
        self.model_thumb_row_y = int(self.H * 0.46)
        
        # Color selection (bottom half)
        self.color_label_pos = (int(self.W * 0.10), int(self.H * 0.54))
        self.color_preview_area = pygame.Rect(int(self.W * 0.30), int(self.H * 0.59),
                                              int(self.W * 0.40), int(self.H * 0.20))
        self.color_thumb_row_y = int(self.H * 0.82)

        # Buttons
        btn_w, btn_h = 220, 48
        self.btn_select = PillButton((self.W // 2 - btn_w // 2, int(self.H * 0.90), btn_w, btn_h), "Select", selected=True)
        self.btn_back   = PillButton((self.W - 120 - 20, 20, 120, 36), "Back", selected=False)

        # Arrows for model selection
        self.model_left_arrow  = ArrowButton((self.model_preview_area.left - 50, self.model_preview_area.centery), "left")
        self.model_right_arrow = ArrowButton((self.model_preview_area.right + 50, self.model_preview_area.centery), "right")
        
        # Arrows for color selection
        self.color_left_arrow  = ArrowButton((self.color_preview_area.left - 50, self.color_preview_area.centery), "left")
        self.color_right_arrow = ArrowButton((self.color_preview_area.right + 50, self.color_preview_area.centery), "right")

        if resources.HIGHEST_LEVEL > currentLevel:
            self.models = MODELS[:]
        else:
            self.models = MODELS[1:] # Exclude "Player" if level not completed
        self.colors = COLORS[:]
        self.model_index = 0
        self.color_index = 0

        self.model_preview_cache = {}
        self.model_thumb_cache = {}
        self.color_preview_cache = {}
        self.color_thumb_cache = {}
        self._select_sound = None
        self._bg = None

        self._load_assets()

    def _load_assets(self):
        # Sound (optional)
        sel_path = SELECT_SOUND
        if os.path.exists(sel_path):
            try:
                self._select_sound = pygame.mixer.Sound(sel_path)
            except Exception:
                self._select_sound = None

        if self._select_sound:
            try:
                self._select_sound.set_volume(resources.SFX_VOLUME if getattr(resources, "SOUND_ENABLED", True) else 0.0)
            except Exception:
                pass

        # Background: Menu3.png (scaled)
        bg_path = BG_FILE
        try:
            bg = pygame.image.load(bg_path).convert()
            self._bg = pygame.transform.smoothscale(bg, (self.W, self.H))
        except Exception:
            self._bg = None

        # Model type previews & thumbnails (using MODEL_TO_IMAGE)
        fallback = load_image_safe(FALLBACK_IMAGE)
        for m in self.models:
            # Try to load from MODEL_TO_IMAGE dict, fall back to template
            fname = MODEL_TO_IMAGE.get(m, FALLBACK_IMAGE)
            img = load_image_safe(fname) or fallback
            if img is None:
                img = pygame.Surface((120, 60), pygame.SRCALPHA)
                img.fill((90, 90, 90))
            prev = scale_to_fit(img, self.model_preview_area.width - 40, self.model_preview_area.height - 40)
            self.model_preview_cache[m] = prev
            self.model_thumb_cache[m] = scale_to_fit(img, 90, 48)
        
        # Color previews & thumbnails (using COLOR_TO_IMAGE)
        for c in self.colors:
            fname = COLOR_TO_IMAGE.get(c, FALLBACK_IMAGE)
            img = load_image_safe(fname) or fallback
            if img is None:
                img = pygame.Surface((120, 60), pygame.SRCALPHA)
                img.fill((90, 90, 90))
            prev = scale_to_fit(img, self.color_preview_area.width - 40, self.color_preview_area.height - 40)
            self.color_preview_cache[c] = prev
            self.color_thumb_cache[c] = scale_to_fit(img, 90, 48)

    def _current_model(self):
        return self.models[self.model_index]
    
    def _current_color(self):
        return self.colors[self.color_index]

    def _move_model_left(self):  
        self.model_index = (self.model_index - 1) % len(self.models)
    
    def _move_model_right(self): 
        self.model_index = (self.model_index + 1) % len(self.models)
    
    def _move_color_left(self):  
        self.color_index = (self.color_index - 1) % len(self.colors)
    
    def _move_color_right(self): 
        self.color_index = (self.color_index + 1) % len(self.colors)

    def _confirm(self):
        if self._select_sound and getattr(resources, "SOUND_ENABLED", True):
            try: self._select_sound.play()
            except Exception: pass
        # Return both model and color as a tuple
        return (self._current_model(), self._current_color())

    def _draw_background(self):
        if self._bg is not None:
            self.surface.blit(self._bg, (0, 0))
        else:
            # Fallback fill if Menu3.png missing
            self.surface.fill((16, 18, 26))

    def _draw_title(self):
        title = self.title_font.render("Pick Your Winner", True, BLUE)
        self.surface.blit(title, self.title_pos)

    def _draw_model_section(self):
        # Section label
        label = self.section_font.render("Model Type", True, BLUE)
        self.surface.blit(label, self.model_label_pos)
        
        # Preview panel
        frame_rect = self.model_preview_area
        panel = pygame.Surface(frame_rect.size, pygame.SRCALPHA)
        # Draw rounded filled background
        pygame.draw.rect(
            panel,
            (10, 10, 30, 110),       # interior color with transparency
            panel.get_rect(),
            border_radius=12
        )
        pygame.draw.rect(panel, (255, 215, 0, 180), panel.get_rect(), width=3, border_radius=12)
        self.surface.blit(panel, frame_rect.topleft)

        m = self._current_model()
        car = self.model_preview_cache.get(m)
        if car:
            r = car.get_rect(center=frame_rect.center)
            self.surface.blit(car, r.topleft)

        name = self.body_font.render(m, True, BLUE)
        self.surface.blit(name, (frame_rect.centerx - name.get_width() // 2, frame_rect.bottom + 10))

        self.model_left_arrow.draw(self.surface)
        self.model_right_arrow.draw(self.surface)
    
    def _draw_color_section(self):
        # Section label
        label = self.section_font.render("Car Color", True, BLUE)
        self.surface.blit(label, self.color_label_pos)
        
        # Preview panel
        frame_rect = self.color_preview_area
        panel = pygame.Surface(frame_rect.size, pygame.SRCALPHA)
        # Draw rounded filled background
        pygame.draw.rect(
            panel,
            (10, 10, 30, 110),       # interior color with transparency
            panel.get_rect(),
            border_radius=12
        )
        pygame.draw.rect(panel, (255, 215, 0, 180), panel.get_rect(), width=3, border_radius=12)
        self.surface.blit(panel, frame_rect.topleft)

        c = self._current_color()
        car = self.color_preview_cache.get(c)
        if car:
            r = car.get_rect(center=frame_rect.center)
            self.surface.blit(car, r.topleft)

        name = self.body_font.render(c, True, BLUE)
        self.surface.blit(name, (frame_rect.centerx - name.get_width() // 2, frame_rect.bottom + 10))

        self.color_left_arrow.draw(self.surface)
        self.color_right_arrow.draw(self.surface)

    def _draw_model_thumbnails(self):
        gap = 12
        total_w = len(self.models) * 100 + (len(self.models) - 1) * gap
        x = self.W // 2 - total_w // 2
        y = self.model_thumb_row_y
        for i, m in enumerate(self.models):
            thumb = self.model_thumb_cache[m]
            box = pygame.Rect(x, y, 100, 60)
            border = (70, 130, 250) if i == self.model_index else (100, 100, 100)
            pygame.draw.rect(self.surface, (25, 28, 40), box, border_radius=8)
            pygame.draw.rect(self.surface, border, box, width=2, border_radius=8)
            if thumb:
                r = thumb.get_rect(center=box.center)
                self.surface.blit(thumb, r.topleft)
            lbl = pygame.font.Font(None, 20).render(m, True, (220, 220, 220))
            self.surface.blit(lbl, (box.centerx - lbl.get_width() // 2, box.bottom + 4))
            setattr(self, f"_model_thumb_rect_{i}", box)
            x += 100 + gap
    
    def _draw_color_thumbnails(self):
        gap = 12
        total_w = len(self.colors) * 100 + (len(self.colors) - 1) * gap
        x = self.W // 2 - total_w // 2
        y = self.color_thumb_row_y
        for i, c in enumerate(self.colors):
            thumb = self.color_thumb_cache[c]
            box = pygame.Rect(x, y, 100, 60)
            border = (70, 130, 250) if i == self.color_index else (100, 100, 100)
            pygame.draw.rect(self.surface, (25, 28, 40), box, border_radius=8)
            pygame.draw.rect(self.surface, border, box, width=2, border_radius=8)
            if thumb:
                r = thumb.get_rect(center=box.center)
                self.surface.blit(thumb, r.topleft)
            lbl = pygame.font.Font(None, 20).render(c, True, (220, 220, 220))
            self.surface.blit(lbl, (box.centerx - lbl.get_width() // 2, box.bottom + 4))
            setattr(self, f"_color_thumb_rect_{i}", box)
            x += 100 + gap

    def _draw_buttons(self):
        self.btn_select.draw(self.surface)
        self.btn_back.draw(self.surface)

    def _draw(self):
        self._draw_background()
        self._draw_title()
        self._draw_model_section()
        self._draw_model_thumbnails()
        self._draw_color_section()
        self._draw_color_thumbnails()
        self._draw_buttons()

    def _handle_mouse(self, event):
        # Check model arrows
        if self.model_left_arrow.handle_event(event):  
            self._move_model_left()
            return "CONTINUE"
        if self.model_right_arrow.handle_event(event): 
            self._move_model_right()
            return "CONTINUE"
        
        # Check color arrows
        if self.color_left_arrow.handle_event(event):  
            self._move_color_left()
            return "CONTINUE"
        if self.color_right_arrow.handle_event(event): 
            self._move_color_right()
            return "CONTINUE"

        # Check buttons first (higher priority)
        if self.btn_select.handle_event(event):
            resources.click_sound.play()
            return self._confirm()
        if self.btn_back.handle_event(event):
            resources.click_sound.play()
            return "back"

        # Then check thumbnail clicks
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            # Model thumbnails
            for i in range(len(self.models)):
                rect = getattr(self, f"_model_thumb_rect_{i}", None)
                if rect and rect.collidepoint(event.pos):
                    self.model_index = i
                    return "CONTINUE"
            
            # Color thumbnails
            for i in range(len(self.colors)):
                rect = getattr(self, f"_color_thumb_rect_{i}", None)
                if rect and rect.collidepoint(event.pos):
                    self.color_index = i
                    return "CONTINUE"

        return "CONTINUE"

    def _handle_keyboard(self, event):
        if event.type == pygame.KEYDOWN:
            # Use Up/Down for model selection, Left/Right for color selection
            if event.key in (pygame.K_UP, pygame.K_w):   
                self._move_model_left()
            elif event.key in (pygame.K_DOWN, pygame.K_s): 
                self._move_model_right()
            elif event.key in (pygame.K_LEFT, pygame.K_a):   
                self._move_color_left()
            elif event.key in (pygame.K_RIGHT, pygame.K_d): 
                self._move_color_right()
            elif event.key in (pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_SPACE):
                return self._confirm()
            elif event.key in (pygame.K_ESCAPE, pygame.K_BACKSPACE):
                return None
        return "CONTINUE"

    def open(self, event):
        
        if event.type in (pygame.MOUSEBUTTONDOWN, pygame.MOUSEBUTTONUP):
            result = self._handle_mouse(event)
            if result is None: return None
            if result != "CONTINUE": return result
        result = self._handle_keyboard(event)
        if result is None: return None
        if result != "CONTINUE": return result
        self._draw()