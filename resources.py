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
MENU = scale_image(pygame.image.load("assets/Menu.png"), 0.90)
MENU2 = scale_image(pygame.image.load("assets/Menu2.png"), 0.90)
GRASS = scale_image(pygame.image.load("assets/grass.jpg"), 1.5)
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

# -------------------------------
# SOUNDS
# -------------------------------

pygame.mixer.pre_init(44100, -16, 2, 512)
pygame.init()

pygame.mixer.music.load("assets/menu-music.ogg")
pygame.mixer.music.set_volume(0.1)   # 0.0 → 1.0 # maybe make this adjustable in settings

pygame.mixer.music.play(-1)          # loop forever
click_sound = pygame.mixer.Sound("assets/select-sound.ogg")
click_sound.set_volume(0.7)
#click_sound.play() TO PLAY CLICK SOUND

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

        # Two possible paths after checkpoint (830, 660)
        path_to_junction = [
            (60, 287), (60, 150), (160, 80), (455, 80), (750, 80),
            (830, 130), (816, 235), (740, 470), (778, 583),
            (830, 700), (730, 780)
        ]
        
        # Path A: through (750, 750)
        path_a = path_to_junction + [
            (750, 750), (604, 810), (348, 810), (118, 810), (69, 744), (93, 696), 
            (222, 632), (470, 527), (510, 416), (370, 392),
            (225, 470), (120, 470), 
        ]
        
        # Path B: through (630, 700)
        path_b = path_to_junction + [
            (640, 700), (640, 480), (620, 260), (532, 220), (348, 220), (255, 260), 
            (229, 357), 
            (235, 450), (115, 475), 
            
        ]
        
        # Choose the shorter path to the finish
        def compute_path_length(path):
            total = 0.0
            for i in range(len(path) - 1):
                x1, y1 = path[i]
                x2, y2 = path[i + 1]
                total += math.hypot(x2 - x1, y2 - y1)
            return total
        
        RACING_LINE = path_a if compute_path_length(path_a) <= compute_path_length(path_b) else path_b

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
        path_with_finish, GRID_SIZE, 30,
        CHECKPOINT_RADIUS, GRID, TRACK_BORDER_MASK,
        GREEN_CAR
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
# --------------------------------------------------
# Money Systems
# --------------------------------------------------
def CalculateMoney(TuningData: list):
    #TuningData Format looks like this:
    # a list of lists, each list inside tuning data should be like: [MINVAL, MAXVAL, CURRENTVAL]
    # If all values equate to 50% then money will return 0 
    # If the tunable is a toggle set min to 0 and max to 1

    # Definitions
    TotalMoney = 1000

    # Converting values into decimal percentages
    Percentages = []
    for Entry in TuningData:
        if Entry[0] == 0 and Entry[1] == 1:
            Percentages.append(str(Entry[2]))
        else:
            Percentages.append((Entry[2] - Entry[0]) / (Entry[1] - Entry[0]))
    # Calculate remaining money
    Costs = []
    for Percentage in Percentages:
        if isinstance(Percentage, str):
            if int(Percentage) == 0:
                Costs.append(0)
            else:
                Costs.append((TotalMoney / len(Percentages)))
        else:
            Costs.append(((TotalMoney / len(Percentages)) * 2) * Percentage)
    
    # Combine Costs
    FinalCost = sum(Costs)
    return TotalMoney - FinalCost

def SetCarTuning(CarObj, TuningData: list):
    # Tuning data should be in the same order as the car object's tuning options
    # a list of lists, each list inside tuning data should be like: [MINVAL, MAXVAL, CURRENTVAL]

    # Performing Checks
    MoneyLeft = CalculateMoney(TuningData)
    if MoneyLeft < 0: return False, MoneyLeft

    # Applying Changes
    TunablesToApply = lambda lst: list(map(lambda x: x[2], lst))
    CarObj.SetTunables(TunablesToApply(TuningData))
    return True, MoneyLeft