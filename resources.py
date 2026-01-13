"""Resource loader: images, masks, constants and simple factories.

Centralises loading to avoid duplicating asset code across modules.
"""
import pygame
import time
import csv
import os
import math

# Initialise pygame subsystems needed for image/font handling
pygame.init()
pygame.font.init()

# --- Helper functions -----------------------------------------------------
def scale_image(img, factor):
    size = round(img.get_width() * factor), round(img.get_height() * factor)
    return pygame.transform.scale(img, size)


def blit_rotate_center(win, image, top_left, angle):
    rotated_image = pygame.transform.rotate(image, angle)
    new_rect = rotated_image.get_rect(
        center=image.get_rect(topleft=top_left).center)
    win.blit(rotated_image, new_rect.topleft)

def blit_text_center(win, font, text):
    render = font.render(text, True, (255, 0, 0))
    win.blit(render, (
        win.get_width() // 2 - render.get_width() // 2,
        win.get_height() // 2 - render.get_height() // 2
    ))

# --- Images and masks ----------------------------------------------------
GRASS = scale_image(pygame.image.load("assets/grass.jpg"), 2.5)
TRACK = scale_image(pygame.image.load("assets/track.png"), 1)
TRACK_BORDER = scale_image(pygame.image.load("assets/track-border.png"), 1)
TRACK_BORDER_MASK = pygame.mask.from_surface(TRACK_BORDER)
FINISH = pygame.image.load("assets/finish.png")
FINISH_MASK = pygame.mask.from_surface(FINISH)
FINISH_POSITION = (135, 250)

# Car sprites (scaled)
RED_CAR = scale_image(pygame.image.load("assets/red-car.png"), 0.55)
GREEN_CAR = scale_image(pygame.image.load("assets/green-car.png"), 0.55)
PURPLE_CAR = scale_image(pygame.image.load("assets/purple-car.png"), 0.55)
TEMPLATE_CAR = scale_image(pygame.image.load("assets/car_template.png"), 0.55)
WHITE_CAR = scale_image(pygame.image.load("assets/white-car.png"), 0.55)

# --- Window & frame rate ------------------------------------------------
WIDTH, HEIGHT = TRACK.get_width(), TRACK.get_height()
WIN = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("DFA Pathfinding Grand Prix")
FPS = 60
race_finished = False

# Results CSV
RESULTS_CSV = "results.csv"
if not os.path.exists(RESULTS_CSV):
    with open(RESULTS_CSV, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["timestamp", "winner", "time_seconds", "level"])

# --- Waypoints ----------------------------------------------------------- This will includes waypoints for each track (level)
PATH = [
    (191, 131), (138, 80), (70, 135), (70, 514), (317, 785), (397, 811), (450, 753),
    (457, 586), (559, 532), (663, 596), (669, 753), (741, 814), (824, 746), (821, 469),
    (757, 400), (502, 398), (446, 347), (514, 288), (763, 282), (822, 238), (820, 130),
    (749, 83), (363, 86), (316, 150), (310, 405), (255, 460), (178, 404), (193, 263)
]

GRID_SIZE = 4  # pixels per grid cell (used for GBFS car)
CHECKPOINT_RADIUS = 30
def build_grid(mask):
    """Build a boolean grid from a Pygame mask. Used for GBFS car

    Each cell corresponds to a GRID_SIZE x GRID_SIZE block of pixels.
    A cell is True when the corresponding pixel in `mask` is not set
    (i.e. considered road), and False when it overlaps the track border.

    The returned grid is indexed as grid[row][col] where row corresponds
    to the y axis and col to the x axis.
    """
    width, height = mask.get_size()
    grid = []
    for y in range(0, height, GRID_SIZE):
        row = []
        for x in range(0, width, GRID_SIZE):
            # ROAD = 1 in TRACK mask (mask.get_at returns 0 for transparent)
            walkable = mask.get_at((x, y)) == 0
            row.append(walkable)
        grid.append(row)
    return grid
GRID = build_grid(TRACK_BORDER_MASK)

class GameInfo:
    LEVELS = 5 # total number of levels in the game (each with their own tracks and waypoints)

    def __init__(self, level=1):
        self.level = level
        self.started = False
        self.level_start_time = 0.0
    
    def next_level(self):
        if self.level < self.LEVELS:
            self.level += 1
            self.started = False
            self.level_start_time = 0.0
            return True
        return False

    def reset(self):
        self.level = 1
        self.started = False
        self.level_start_time = 0.0

    def game_finished(self):
        return self.level > self.LEVELS
    
    def start_level(self):
        self.started = True
        self.level_start_time = time.time()
    
    def get_level_time(self):
        if not self.started:
            return 0.0
        return time.time() - self.level_start_time

images = [(GRASS, (0, 0)), (TRACK, (0, 0)), (FINISH, FINISH_POSITION), (TRACK_BORDER, (0, 0))]

# Shared state used by UI helpers
start_time = time.time()
last_winner = None
last_time = 0.0


def create_player_car(max_vel=4, rotation_vel=4):
    # Import here to avoid circular top-level imports during module load
    from cars import PlayerCar

    return PlayerCar(RED_CAR, (200, 200), max_vel, rotation_vel)


def create_computer_car(max_vel=2, rotation_vel=4, path=PATH):
    from cars import ComputerCar

    return ComputerCar(TEMPLATE_CAR, (170, 200), max_vel, rotation_vel, path)

def create_dijkstra_car(max_vel=3, rotation_vel=4):
    WAYPOINT_REACH = 30 # radius to consider a waypoint reached
    from cars import DijkstraCar
    return DijkstraCar(WHITE_CAR, (160, 200), max_vel, rotation_vel, PATH, GRID_SIZE, WAYPOINT_REACH, CHECKPOINT_RADIUS, GRID, TRACK_BORDER_MASK)

def create_GBFS_car(max_vel=3, rotation_vel=4):
    WAYPOINT_REACH = 30 # radius to consider a waypoint reached
    from cars import GBFSDetourCar
    return GBFSDetourCar(max_vel, rotation_vel, PATH, GRID_SIZE, WAYPOINT_REACH, CHECKPOINT_RADIUS, GRID, TRACK_BORDER_MASK, GREEN_CAR, allow_diag=False, clearance_weight=0.6, detour_alpha=0.7)

def create_neat_car(max_vel = 3, rotation_vel = 4):
    from cars import NEATCar
    return NEATCar(PURPLE_CAR, (165, 200), max_vel, rotation_vel, PATH ,TRACK_BORDER_MASK,  GRID_SIZE, GRID)

def raycast_mask(mask, origin, angle, max_distance=800, step=3):
    """
    Cast a ray in pixel space against a Pygame mask.

    Args:
        mask (pygame.Mask): Track mask. Nonzero pixels are obstacles/border.
        origin (tuple[int, int]): (x, y) starting point.
        angle (float): Ray angle in radians, 0 along +x, increasing counterclockwise.
        max_distance (float): Max length to cast (pixels).
        step (int): Step size in pixels. 2–4 is a good trade-off.

    Returns:
        dict with keys:
            'hit' (bool): True if hit border.
            'distance' (float): distance to hit or max_distance if no hit.
            'point' (tuple[int,int] or None): impact point if hit, else None.
            'samples' (int): number of iterations performed.
    """
    width, height = mask.get_size()
    ox, oy = origin
    dx = math.cos(angle)
    dy = math.sin(angle)

    # Early bounds check: if origin is outside, clamp ray to bounds
    # (optional; here we assume origin is valid)
    dist = 0.0
    samples = 0

    # Fast path: if starting on border, report distance 0
    if 0 <= ox < width and 0 <= oy < height and mask.get_at((ox, oy)) != 0:
        return {'hit': True, 'distance': 0.0, 'point': (ox, oy), 'samples': 0}

    while dist < max_distance:
        samples += 1
        # Increment position
        px = int(ox + dx * dist)
        py = int(oy + dy * dist)

        # If out of bounds, terminate with no hit
        if px < 0 or py < 0 or px >= width or py >= height:
            return {'hit': False, 'distance': dist, 'point': None, 'samples': samples}

        # Check border
        if mask.get_at((px, py)) != 0:
            # Optional: refine by binary search back one step for sub-pixel
            # but integer pixels are usually sufficient for sensors.
            return {'hit': True, 'distance': dist, 'point': (px, py), 'samples': samples}

        dist += step

    return {'hit': False, 'distance': max_distance, 'point': None, 'samples': samples}

