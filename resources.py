# resources.py

# TODO:
# Add countdown page between levels
# Add audio effects
# Add pause/play button
# Improve paths for later levels
# Add more levels
# Add menu system
# Add car loader
# Fix leaderboard for multi-level support

import pygame
import time
import math
import os
import csv

pygame.init()
pygame.font.init()

# --------------------------------------------------
# Helpers
# --------------------------------------------------
def scale_image(img, factor):
    size = round(img.get_width() * factor), round(img.get_height() * factor)
    return pygame.transform.scale(img, size)

def blit_text_center(win, font, text):
    render = font.render(text, True, (255, 0, 0))
    win.blit(
        render,
        (
            win.get_width() // 2 - render.get_width() // 2,
            win.get_height() // 2 - render.get_height() // 2,
        ),
    )

def blit_rotate_center(win, image, top_left, angle):
    rotated_image = pygame.transform.rotate(image, angle)
    new_rect = rotated_image.get_rect(
        center=image.get_rect(topleft=top_left).center
    )
    win.blit(rotated_image, new_rect.topleft)

# --------------------------------------------------
# Static assets
# --------------------------------------------------
GRASS = scale_image(pygame.image.load("assets/grass.jpg"), 2.5)
RED_CAR = scale_image(pygame.image.load("assets/red-car.png"), 0.55)
GREEN_CAR = scale_image(pygame.image.load("assets/green-car.png"), 0.55)
PURPLE_CAR = scale_image(pygame.image.load("assets/purple-car.png"), 0.55)
TEMPLATE_CAR = scale_image(pygame.image.load("assets/car_template.png"), 0.55)
WHITE_CAR = scale_image(pygame.image.load("assets/white-car.png"), 0.55)

level_active = False
FPS = 60
GRID_SIZE = 4
CHECKPOINT_RADIUS = 30
start_time = time.time()
last_winner = None

# --------------------------------------------------
# DEFAULT TRACK (LEVEL 1)
# --------------------------------------------------
TRACK = scale_image(pygame.image.load("assets/track.png"), 1)
TRACK_BORDER = scale_image(pygame.image.load("assets/track-border.png"), 1)
TRACK_BORDER_MASK = pygame.mask.from_surface(TRACK_BORDER)

FINISH = pygame.image.load("assets/finish.png")
FINISH_MASK = pygame.mask.from_surface(FINISH)
FINISH_POSITION = (135, 250)

# ✅ NEW: start position owned by track
START_POSITION = (200, 200)

HEIGHT, WIDTH = TRACK.get_size()

RACING_LINE = []

# --------------------------------------------------
# Results CSV
# --------------------------------------------------
RESULTS_CSV = "results.csv"
if not os.path.exists(RESULTS_CSV):
    with open(RESULTS_CSV, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["timestamp", "winner", "time_seconds", "level"])

# --------------------------------------------------
# Grid
# --------------------------------------------------
def build_grid(mask):
    width, height = mask.get_size()
    grid = []
    for y in range(0, height, GRID_SIZE):
        row = []
        for x in range(0, width, GRID_SIZE):
            row.append(mask.get_at((x, y)) == 0)
        grid.append(row)
    return grid

GRID = build_grid(TRACK_BORDER_MASK)

# --------------------------------------------------
# Rendering setup
# --------------------------------------------------
images = [
    (GRASS, (0, 0)),
    (TRACK, (0, 0)),
    (FINISH, FINISH_POSITION),
    (TRACK_BORDER, (0, 0)),
]

WIN = pygame.display.set_mode(TRACK.get_size())

# --------------------------------------------------
# TRACK SWITCHER
# --------------------------------------------------
def load_track_for_level(level):
    global TRACK, TRACK_BORDER, TRACK_BORDER_MASK
    global RACING_LINE, GRID, images, WIN
    global FINISH_POSITION, START_POSITION
    global level_active

    if level == 1:
        level_active = True
        track_img = "assets/track.png"
        border_img = "assets/track-border.png"

        FINISH_POSITION = (135, 250)
        START_POSITION = (200, 200)

        
        RACING_LINE = [
            (191,131),(138,80),(70,135),(70,514),(317,785),(397,811),
            (450,753),(457,586),(559,532),(663,596),(669,753),
            (741,814),(824,746),(821,469),(757,400),(502,398),
            (446,347),(514,288),(763,282),(822,238),(820,130),
            (749,83),(363,86),(316,150),(310,405),(255,460),
            (178,404),(193,193)
        ]

    elif level == 2:
        level_active = True
        track_img = "assets/track2.png"
        track_img = "assets/track4.png"
        border_img = "assets/track4-border.png"

        FINISH_POSITION = (20, 380)
        START_POSITION = (60, 288)

        
        RACING_LINE = [
            (60, 287), (60,138), (152, 64), (401, 64), (748, 64),
            (820, 104), (812, 217), (731, 411), (732, 475), (778, 583),
            (830, 660),
            (750, 750), (604, 810), (348, 810), (118, 810), (69, 744), (93, 696), (222, 632), (470, 527), (510, 416), (370, 392),
            (630, 699), (629, 589), (617, 262), (532, 194), (348, 195), (245, 237), (229, 357),
            (234, 452), (123, 457), (62, 395), (62, 287)
        ]

    TRACK = scale_image(pygame.image.load(track_img), 1)
    TRACK_BORDER = scale_image(pygame.image.load(border_img), 1)
    TRACK_BORDER_MASK = pygame.mask.from_surface(TRACK_BORDER)

    GRID = build_grid(TRACK_BORDER_MASK)

    images[:] = [
        (GRASS, (0, 0)),
        (TRACK, (0, 0)),
        (FINISH, FINISH_POSITION),
        (TRACK_BORDER, (0, 0)),
    ]

    WIN = pygame.display.set_mode(TRACK.get_size())

# --------------------------------------------------
# GameInfo
# --------------------------------------------------
class GameInfo:
    LEVELS = 5

    def __init__(self, level=0):
        self.level = level
        self.started = False
        self.level_start_time = 0.0

    def get_level(self):
        return self.level

    def next_level(self):
        if self.level < self.LEVELS:
            self.level += 1
            self.started = False
            self.level_start_time = 0.0
            return True
        return False

    def start_level(self):
        self.started = True
        self.level_start_time = time.time()

    

# --------------------------------------------------
# Car factories (UNCHANGED API)
# --------------------------------------------------
def create_player_car():
    from cars import PlayerCar
    return PlayerCar(RED_CAR, START_POSITION, 4, 4)

def create_computer_car():
    from cars import ComputerCar
    path_with_finish = RACING_LINE + [FINISH_POSITION]
    return ComputerCar(TEMPLATE_CAR, START_POSITION, 2, 4, path_with_finish)

def create_GBFS_car():
    from cars import GBFSDetourCar
    path_with_finish = RACING_LINE + [FINISH_POSITION]
    car = GBFSDetourCar(
        3, 4, path_with_finish, GRID_SIZE, 30,
        CHECKPOINT_RADIUS, GRID, TRACK_BORDER_MASK,
        GREEN_CAR, False, 0.6, 0.7
    )
    car.x, car.y = START_POSITION
    return car

def create_neat_car():
    from cars import NEATCar
    return NEATCar(
        PURPLE_CAR,
        START_POSITION,
        3, 4,
        RACING_LINE, TRACK_BORDER_MASK, GRID_SIZE, GRID
    )
def create_dijkstra_car(max_vel=3, rotation_vel=4):
    WAYPOINT_REACH = 50 # radius to consider a waypoint reached
    from cars import DijkstraCar
    path_with_finish = RACING_LINE + [FINISH_POSITION]
    return DijkstraCar(WHITE_CAR, START_POSITION, max_vel, 
                       rotation_vel, path_with_finish, GRID_SIZE, WAYPOINT_REACH, 
                       CHECKPOINT_RADIUS, GRID, TRACK_BORDER_MASK)

# --------------------------------------------------
# Raycast
# --------------------------------------------------
def raycast_mask(mask, origin, angle, max_distance=800, step=3):
    width, height = mask.get_size()
    ox, oy = origin
    dx = math.cos(angle)
    dy = math.sin(angle)

    dist = 0.0
    while dist < max_distance:
        px = int(ox + dx * dist)
        py = int(oy + dy * dist)

        if px < 0 or py < 0 or px >= width or py >= height:
            break

        if mask.get_at((px, py)) != 0:
            return {"hit": True, "distance": dist, "point": (px, py)}

        dist += step

    return {"hit": False, "distance": max_distance, "point": None}
