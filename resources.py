"""Resource loader: images, masks, constants and simple factories.

Centralises loading to avoid duplicating asset code across modules.
"""
import pygame
import time
import csv
import os
from utils import scale_image

# Initialise pygame subsystems needed for image/font handling
pygame.init()
pygame.font.init()

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

# --- Window & frame rate ------------------------------------------------
WIDTH, HEIGHT = TRACK.get_width(), TRACK.get_height()
WIN = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("DFA Pathfinding Grand Prix")
FPS = 60

# Results CSV
RESULTS_CSV = "results.csv"
if not os.path.exists(RESULTS_CSV):
    with open(RESULTS_CSV, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["timestamp", "winner", "time_seconds"])

# --- Waypoints -----------------------------------------------------------
PATH = [
    (191, 131), (138, 80), (70, 135), (70, 514), (317, 785), (397, 811), (450, 753),
    (457, 586), (559, 532), (663, 596), (669, 753), (741, 814), (824, 746), (821, 469),
    (757, 400), (502, 398), (446, 347), (514, 288), (763, 282), (822, 238), (820, 130),
    (749, 83), (363, 86), (316, 150), (310, 405), (255, 460), (198, 404), (193, 263)
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

def create_GBFS_car():
    WAYPOINT_REACH = 30 # radius to consider a waypoint reached
    from cars import GBFSDetourCar
    return GBFSDetourCar(2.2, 4, PATH, GRID_SIZE, WAYPOINT_REACH, CHECKPOINT_RADIUS, TRACK_BORDER_MASK, allow_diag=False, clearance_weight=0.6, detour_alpha=0.7,)