
"""
Model selection screen for DFA Grand Prix.

- Shows a model carousel with large car preview pulled from assets directory.
- User can navigate with Left/Right or mouse, and confirm with Enter or "Select" button.
- Returns the selected model string, or None if the user cancels.

Author: Benjamin + Copilot
"""

import os
import pygame

# ---------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------

MODELS = ["Player", "Computer", "GBFS", "Dijkstra", "NEAT"]

MODEL_TO_IMAGE = {
    "Player":   "assets/red-car.png",
    "Computer": "assets/grey-car.png",
    "GBFS":     "assets/green-car.png",
    "Dijkstra": "assets/purple-car.png",
    "NEAT":     "assets/white-car.png",
}

FALLBACK_IMAGE = "assets/car_template.png"
SELECT_SOUND   = "assets/select-sound.ogg"
BG_FILE        = "assets/Menu3.png"          # ← NEW: use Menu4 for background

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
    def __init__(self, surface, assets_path="assets"):
        self.surface = surface
        self.assets_path = assets_path
        self.W = self.surface.get_width()
        self.H = self.surface.get_height()

        self.title_font = pygame.font.Font(None, 48)
        self.body_font  = pygame.font.Font(None, 26)

        # Layout
        self.title_pos = (int(self.W * 0.10), int(self.H * 0.12))
        self.preview_area = pygame.Rect(int(self.W * 0.30), int(self.H * 0.20),
                                        int(self.W * 0.40), int(self.H * 0.45))
        self.thumb_row_y = int(self.H * 0.70)

        # Buttons
        btn_w, btn_h = 220, 48
        self.btn_select = PillButton((self.W // 2 - btn_w // 2, int(self.H * 0.82), btn_w, btn_h), "Select", selected=True)
        self.btn_back   = PillButton((self.W - 120 - 20, 20, 120, 36), "Back", selected=False)

        # Arrows
        self.left_arrow  = ArrowButton((self.preview_area.left - 50, self.preview_area.centery), "left")
        self.right_arrow = ArrowButton((self.preview_area.right + 50, self.preview_area.centery), "right")

        self.models = MODELS[:]
        self.index = 0

        self.preview_cache = {}
        self.thumb_cache = {}
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

        # Background: Menu4.png (scaled)
        bg_path = BG_FILE
        try:
            bg = pygame.image.load(bg_path).convert()
            self._bg = pygame.transform.smoothscale(bg, (self.W, self.H))
        except Exception:
            self._bg = None

        # Car previews & thumbnails
        fallback = load_image_safe(FALLBACK_IMAGE)
        for m in self.models:
            fname = MODEL_TO_IMAGE.get(m, FALLBACK_IMAGE)
            img = load_image_safe(fname) or fallback
            if img is None:
                img = pygame.Surface((120, 60), pygame.SRCALPHA); img.fill((90, 90, 90))
            prev = scale_to_fit(img, self.preview_area.width - 40, self.preview_area.height - 40)
            self.preview_cache[m] = prev
            self.thumb_cache[m] = scale_to_fit(img, 110, 58)

    def _current_model(self):
        return self.models[self.index]

    def _move_left(self):  self.index = (self.index - 1) % len(self.models)
    def _move_right(self): self.index = (self.index + 1) % len(self.models)

    def _confirm(self):
        if self._select_sound:
            try: self._select_sound.play()
            except Exception: pass
        return self._current_model()

    def _draw_background(self):
        if self._bg is not None:
            self.surface.blit(self._bg, (0, 0))
        else:
            # Fallback fill if Menu4.png missing
            self.surface.fill((16, 18, 26))

    def _draw_title(self):
        title = self.title_font.render("Choose Your Model", True, (240, 240, 240))
        self.surface.blit(title, self.title_pos)
        sub = self.body_font.render("Use ←/→ to browse, Enter to select", True, (200, 200, 200))
        self.surface.blit(sub, (self.title_pos[0], self.title_pos[1] + 42))

    def _draw_preview(self):
        frame_rect = self.preview_area
        panel = pygame.Surface(frame_rect.size, pygame.SRCALPHA)
        panel.fill((10, 10, 30, 110))
        pygame.draw.rect(panel, (255, 215, 0, 180), panel.get_rect(), width=3, border_radius=12)
        self.surface.blit(panel, frame_rect.topleft)

        m = self._current_model()
        car = self.preview_cache.get(m)
        if car:
            r = car.get_rect(center=frame_rect.center)
            self.surface.blit(car, r.topleft)

        name_font = pygame.font.Font(None, 34)
        name = name_font.render(m, True, (235, 235, 235))
        self.surface.blit(name, (frame_rect.centerx - name.get_width() // 2, frame_rect.bottom + 10))

        self.left_arrow.draw(self.surface)
        self.right_arrow.draw(self.surface)

    def _draw_thumbnails(self):
        gap = 18
        total_w = len(self.models) * 120 + (len(self.models) - 1) * gap
        x = self.W // 2 - total_w // 2
        y = self.thumb_row_y
        for i, m in enumerate(self.models):
            thumb = self.thumb_cache[m]
            box = pygame.Rect(x, y, 120, 72)
            border = (70, 130, 250) if i == self.index else (100, 100, 100)
            pygame.draw.rect(self.surface, (25, 28, 40), box, border_radius=8)
            pygame.draw.rect(self.surface, border, box, width=2, border_radius=8)
            if thumb:
                r = thumb.get_rect(center=box.center)
                self.surface.blit(thumb, r.topleft)
            lbl = self.body_font.render(m, True, (220, 220, 220))
            self.surface.blit(lbl, (box.centerx - lbl.get_width() // 2, box.bottom + 6))
            setattr(self, f"_thumb_rect_{i}", box)
            x += 120 + gap

    def _draw_buttons(self):
        self.btn_select.draw(self.surface)
        self.btn_back.draw(self.surface)

    def _draw(self):
        self._draw_background()
        self._draw_title()
        self._draw_preview()
        self._draw_thumbnails()
        self._draw_buttons()

    def _handle_mouse(self, event):
        if self.left_arrow.handle_event(event):  self._move_left();  return "CONTINUE"
        if self.right_arrow.handle_event(event): self._move_right(); return "CONTINUE"

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            for i in range(len(self.models)):
                rect = getattr(self, f"_thumb_rect_{i}", None)
                if rect and rect.collidepoint(event.pos):
                    self.index = i
                    return "CONTINUE"

        if self.btn_select.handle_event(event):
            return self._confirm()
        if self.btn_back.handle_event(event):
            return None
        return "CONTINUE"

    def _handle_keyboard(self, event):
        if event.type == pygame.KEYDOWN:
            if event.key in (pygame.K_LEFT, pygame.K_a):   self._move_left()
            elif event.key in (pygame.K_RIGHT, pygame.K_d): self._move_right()
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