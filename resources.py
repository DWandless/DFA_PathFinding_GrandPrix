# resources.py

#TODO:
# ADD dynamic start positions for each level/track - not hardcoded to the car factories
# Add a page between each of the levels before the next one begins/countdown
# Add audio effects
# Add pause/play button
# Add better path for level 2
# Add more levels
# Add menu system before the game
# Add a car loader
# Fix leaderboard to accomodate for extra levels

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
        center=image.get_rect(topleft=top_left).center)
    win.blit(rotated_image, new_rect.topleft)

# --------------------------------------------------
# Static assets
# --------------------------------------------------
GRASS = scale_image(pygame.image.load("assets/grass.jpg"), 2.5)
RED_CAR = scale_image(pygame.image.load("assets/red-car.png"), 0.55)
GREEN_CAR = scale_image(pygame.image.load("assets/green-car.png"), 0.55)
PURPLE_CAR = scale_image(pygame.image.load("assets/purple-car.png"), 0.55)
TEMPLATE_CAR = scale_image(pygame.image.load("assets/car_template.png"), 0.55)

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
FINISH_MASK = pygame.mask.from_surface(pygame.image.load("assets/finish.png"))
FINISH = pygame.image.load("assets/finish.png")
FINISH_POSITION = (135, 250)
HEIGHT, WIDTH = TRACK.get_size()

PATH = [
    (191,131),(138,80),(70,135),(70,514),(317,785),(397,811),
    (450,753),(457,586),(559,532),(663,596),(669,753),
    (741,814),(824,746),(821,469),(757,400),(502,398),
    (446,347),(514,288),(763,282),(822,238),(820,130),
    (749,83),(363,86),(316,150),(310,405),(255,460),
    (178,404),(193,263)
]

# Results CSV
RESULTS_CSV = "results.csv"
if not os.path.exists(RESULTS_CSV):
    with open(RESULTS_CSV, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["timestamp", "winner", "time_seconds", "level"])

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

images = [
    (GRASS, (0, 0)),
    (TRACK, (0, 0)),
    (FINISH, FINISH_POSITION),
    (TRACK_BORDER, (0, 0)),
]

WIN = pygame.display.set_mode(TRACK.get_size())

# --------------------------------------------------
# TRACK SWITCHER (SAFE, GLOBAL UPDATE)
# --------------------------------------------------
def load_track_for_level(level):
    global TRACK, TRACK_BORDER, TRACK_BORDER_MASK
    global PATH, GRID, images, WIN, FINISH_POSITION

    if level == 1:
        track_img = "assets/track.png"
        border_img = "assets/track-border.png"
        FINISH_POSITION = (135, 250)
        PATH = PATH  # same path

    elif level == 2:
        track_img = "assets/track2.png"
        border_img = "assets/track2-border.png"
        FINISH_POSITION = (775, 400)
        PATH = [
            (720,520),(680,480),(600,450),(400,400),(200,350),
            (150,300),(100,250),(120,150),(200,100),(400,80),
            (600,120),(750,200),(800,300),(780,400),(720,480)
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
# Factories (UNCHANGED API)
# --------------------------------------------------
def create_player_car():
    from cars import PlayerCar
    return PlayerCar(RED_CAR, (200, 200), 4, 4)

def create_computer_car():
    from cars import ComputerCar
    return ComputerCar(TEMPLATE_CAR, (170, 200), 2, 4, PATH)

def create_GBFS_car():
    from cars import GBFSDetourCar
    return GBFSDetourCar(
        3, 4, PATH, GRID_SIZE, 30,
        CHECKPOINT_RADIUS, GRID, TRACK_BORDER_MASK,
        GREEN_CAR, False, 0.6, 0.7
    )

def create_neat_car():
    from cars import NEATCar
    return NEATCar(
        PURPLE_CAR, (165, 200), 3, 4,
        PATH, TRACK_BORDER_MASK, GRID_SIZE, GRID
    )

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
            return {'hit': True, 'distance': dist, 'point': (px, py)}

        dist += step

    return {'hit': False, 'distance': max_distance, 'point': None}

