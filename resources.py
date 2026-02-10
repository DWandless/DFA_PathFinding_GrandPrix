# resources.py

import pygame
import time
import math
import os
import csv

# --------------------------------------------------
# Pygame Init (ONCE)
# --------------------------------------------------
pygame.init()
pygame.font.init()
pygame.mixer.pre_init(44100, -16, 2, 512)
pygame.mixer.init()

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

def blit_text_center(win, font, text, color=(255, 0, 0)):
    render = font.render(text, True, color)
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
# Constants
# --------------------------------------------------
FPS = 60
GRID_SIZE = 4
CHECKPOINT_RADIUS = 45 # Increased by 5 pixels for easier checkpoint detection
DEBUG_SHOW_CHECKPOINTS = True  # Set to True to show red checkpoint dots and pathfinding visualization
DEBUG_UNLOCK_ALL_LEVELS = False  # Set to True to unlock all levels for testing/debugging

# --------------------------------------------------
# Static assets
# --------------------------------------------------
MENU = scale_image(pygame.image.load("assets/Menu.png"), 0.90)
MENU2 = scale_image(pygame.image.load("assets/Menu2.png"), 0.90)
MENU3 = scale_image(pygame.image.load("assets/Menu3.png"), 0.90)
MENU4 = scale_image(pygame.image.load("assets/Menu4.png"), 0.90)

# BACKGROUND IMAGES
GRASS= scale_image(pygame.image.load("assets/grass.jpg"), 1.5)
DESERT = scale_image(pygame.image.load("assets/desert.png"), 0.75)
SNOW = scale_image(pygame.image.load("assets/snow.png"), 0.75)

BLUE_CAR = scale_image(pygame.image.load("assets/blue-car.png"), 0.55)
RED_CAR = scale_image(pygame.image.load("assets/red-car.png"), 0.55)
GREEN_CAR = scale_image(pygame.image.load("assets/green-car.png"), 0.55)
PURPLE_CAR = scale_image(pygame.image.load("assets/purple-car.png"), 0.55)
WHITE_CAR = scale_image(pygame.image.load("assets/white-car.png"), 0.55)
TEMPLATE_CAR = scale_image(pygame.image.load("assets/car_template.png"), 0.55)
GREY_CAR = scale_image(pygame.image.load("assets/grey-car.png"), 0.55)
PINK_CAR = scale_image(pygame.image.load("assets/pink-car.png"), 0.55)
YELLOW_CAR = scale_image(pygame.image.load("assets/yellow-car.png"), 0.55)

# Color name to car image mapping
CAR_COLOR_MAP = {
    "Red": RED_CAR,
    "Blue": BLUE_CAR,
    "Green": GREEN_CAR,
    "Purple": PURPLE_CAR,
    "White": WHITE_CAR,
    "Grey": GREY_CAR,
    "Pink": PINK_CAR,
    "Yellow": YELLOW_CAR,
}

# --------------------------------------------------
# Default Track (Level 1)
# --------------------------------------------------
BACKGROUND = scale_image(pygame.image.load("assets/grass.jpg"), 1.5)
TRACK = scale_image(pygame.image.load("assets/track1.png"), 1)
TRACK_BORDER = scale_image(pygame.image.load("assets/track_border1.png"), 1)
TRACK_BORDER_MASK = pygame.mask.from_surface(TRACK_BORDER)

FINISH = pygame.image.load("assets/finish.png")
FINISH_MASK = pygame.mask.from_surface(FINISH)

FINISH_POSITION = (135, 250)
START_POSITION = (200, 200)

# Level 3 specific finish image (cropped and positioned for left side of track)
FINISH_LEVEL3 = None
FINISH_MASK_LEVEL3 = None

HEIGHT, WIDTH = TRACK.get_size()
WIN = pygame.display.set_mode((WIDTH, HEIGHT))

RACING_LINE = []
DFS_RACING_LINE = []
BFS_RACING_LINE = []
ASTAR_RACING_LINE = []  
GBFS_RACING_LINE = []

HIGHEST_LEVEL = 1 # This is updated during gameplay - initially set to 1 - represents the highest level unlocked

# --------------------------------------------------
# Level Previews for hovering
# --------------------------------------------------
# TODO: Ensure these images exist and are up to date

LEVEL_PREVIEWS = {
    1: pygame.image.load("assets/track1.png").convert_alpha(),
    2: pygame.image.load("assets/track2.png").convert_alpha(),
    3: pygame.image.load("assets/track3.png").convert_alpha(),
    4: pygame.image.load("assets/track4.png").convert_alpha(),
}   

for k, img in LEVEL_PREVIEWS.items():
    LEVEL_PREVIEWS[k] = pygame.transform.smoothscale(img, (290, 290))


# --------------------------------------------------
# Sounds
# --------------------------------------------------
pygame.mixer.music.load("assets/menu-music.ogg")
pygame.mixer.music.set_volume(0.1)
pygame.mixer.music.play(-1)

click_sound = pygame.mixer.Sound("assets/select-sound.ogg")
click_sound.set_volume(0.7)

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
# Rendering stack
# --------------------------------------------------
images = [
    (BACKGROUND, (0, 0)),
    (TRACK, (0, 0)),
    (FINISH, FINISH_POSITION),
    (TRACK_BORDER, (0, 0)),
]

# --------------------------------------------------
# Algorithm Delay Configuration (Level-Specific)
# --------------------------------------------------
# Maps algorithm types to delay times (in seconds) per level
# Delay = 0 means the car can win that level
# Delay > 0 means the car is handicapped and likely won't win
ALGORITHM_DELAY_CONFIG = {
    1: {  # Level 1: Only DFS can win
        "Player": 0.0,
        "BFS": 5.0,      # 2 second delay
        "DFS": 0.0,      # No delay - can win
        "GBFS": 5.0,     # 2 second delay
        "AStar": 5.0,    # 2 second delay
        "Dijkstra": 5.0, # 2 second delay
        "NEAT": 2.0,     # 2 second delay
    },
    2: {  # Level 2: Only BFS can win
        "Player": 0.0,
        "BFS": 0.0,      # No delay - can win
        "DFS": 2.0,      # 2 second delay
        "GBFS": 2.0,     # 2 second delay
        "AStar": 2.0,    # 2 second delay
        "Dijkstra": 2.0, # 2 second delay
        "NEAT": 2.0,     # 2 second delay
    },
    3: {  # Level 3: Only Dijkstra/AStar can win
        "Player": 0.0,
        "BFS": 2.0,      # 2 second delay
        "DFS": 2.0,      # 2 second delay
        "GBFS": 2.0,     # 2 second delay
        "AStar": 0.0,    # No delay - can win
        "Dijkstra": 0.0, # No delay - can win
        "NEAT": 2.0,     # 2 second delay
    },
    4: {  # Level 4: Only GBFS can win
        "Player": 0.0,
        "BFS": 2.0,      # 2 second delay
        "DFS": 2.0,      # 2 second delay
        "GBFS": 0.0,     # No delay - can win
        "AStar": 2.0,    # 2 second delay
        "Dijkstra": 2.0, # 2 second delay
        "NEAT": 2.0,     # 2 second delay
    },
}

def get_algorithm_delay(algorithm, level):
    """Get the delay time for a specific algorithm on a specific level."""
    level_config = ALGORITHM_DELAY_CONFIG.get(level, {})
    return level_config.get(algorithm, 0.0)

# --------------------------------------------------
# Track Loader
# --------------------------------------------------

def load_track_for_level(level):
    global BACKGROUND
    global TRACK, TRACK_BORDER, TRACK_BORDER_MASK
    global FINISH_POSITION, START_POSITION
    global RACING_LINE, GRID, images
    global DFS_RACING_LINE, BFS_RACING_LINE, ASTAR_RACING_LINE, GBFS_RACING_LINE

    def compute_path_length(path):
        total = 0.0
        for i in range(len(path) - 1):
            x1, y1 = path[i]
            x2, y2 = path[i + 1]
            total += math.hypot(x2 - x1, y2 - y1)
        return total

    if level == 1:

        background_img = "assets/grass.jpg"
        background_img = scale_image(pygame.image.load(background_img), 1.5)
        
        track_img = "assets/track1.png"
        border_img = "assets/track_border1.png"

        FINISH_POSITION = (135, 250)
        START_POSITION = (200, 200)

        RACING_LINE = [
            (191,131),(138,80),(70,135),(50,514),(317,785),(397,811),
            (450,753),(457,586),(559,532),(663,596),(650,753),
            (741,814),(824,746),(821,469),(730,400),(450,410),
            (446,347),(514,288),(763,282),(822,238),(820,130),
            (749,83),(363,86),(316,150),(310,405),(255,460),
            (178,404),(193,193)
        ]

        DFS_RACING_LINE = [
            (191,131),(138,80),(70,135),(50,514),(317,785),(397,811),
            (450,753),(457,586),(559,532),(663,596),(650,753),
            (741,814),(824,746),(821,469),(730,400),(450,398),
            (446,347),(514,288),(763,282),(822,238),(820,130),
            (749,83),(363,86),(316,150),(310,405),(255,460),
            (178,404),(193,193)
        ]

        BFS_RACING_LINE = [
            (191,131),(138,80),(70,135),(50,514),(317,785),(397,811),
            (450,753),(457,586),(559,532),(663,596),(650,753),
            (741,814),(824,746),(821,469),(730,400),(450,398),
            (446,347),(514,288),(763,282),(822,238),(820,130),
            (749,83),(363,86),(316,150),(310,405),(255,460),
            (178,404),(193,193)
        ]

        ASTAR_RACING_LINE = [
            (191,131),(138,80),(70,135),(50,514),(317,785),(397,811),
            (450,753),(457,586),(559,532),(663,596),(650,753),
            (741,814),(824,746),(821,469),(730,400),(450,398),
            (446,347),(514,288),(763,282),(822,238),(820,130),
            (749,83),(363,86),(316,150),(310,405),(255,460),
            (178,404),(193,193)
        ]

        GBFS_RACING_LINE = [
            (191,131),(138,80),(70,135),(50,514),(317,785),(397,811),
            (450,753),(457,586),(559,532),(663,596),(650,753),
            (741,814),(824,746),(821,469),(757,400),(450,398),
            (446,347),(514,288),(763,282),(822,238),(820,130),
            (749,83),(363,86),(316,150),(310,405),(255,460),
            (178,404),(193,193)
        ]


    elif level == 2:
        background_img = "assets/desert.png"
        background_img = scale_image(pygame.image.load(background_img), 1)

        track_img = "assets/track2.png"
        border_img = "assets/track_border2.png"

        FINISH_POSITION = (30, 420)
        START_POSITION = (70, 288)

        
        # Two possible paths after checkpoint (830, 660)
        path_to_junction = [
            (70, 287), (80, 130), (125, 70), (300, 70), (600, 70), (760, 85),
            (830, 130), (816, 235), (730, 470), (750, 583),
            (820, 750),
        ]
        
        # Path A: through (750, 750)
        path_a = path_to_junction + [
            (750, 800), (348, 810), (118, 810), (69, 744), (93, 696), 
            (222, 632), (485, 527), (510, 416), (370, 392),
            (225, 470), (120, 470), 
        ]
        
        # Path B: through (630, 700)
        path_b = path_to_junction + [
            (640, 700), (640, 480), (620, 260), (532, 220), (348, 220), (255, 260), 
            (229, 357), 
            (235, 450), (115, 475), 
            
        ]
        
        # Choose the shorter path to the finish

        
        RACING_LINE = path_a if compute_path_length(path_a) <= compute_path_length(path_b) else path_b

        DFS_RACING_LINE = path_a
        BFS_RACING_LINE = path_b
        ASTAR_RACING_LINE = path_a
        GBFS_RACING_LINE = path_a


    elif level == 3:
        background_img = "assets/snow.png"
        background_img = scale_image(pygame.image.load(background_img), 1)

        track_img = "assets/track3.png"
        border_img = "assets/track_border3.png"

        FINISH_POSITION = (410, 190)
        START_POSITION = (430, 150)

        zero_to_one = [(450, 110), (600, 100), (765, 100), (800, 180), (767, 250), (600, 275), (580, 390)]
        one_to_twoA = [(450, 390), (429, 485), (482, 544), (607, 556), (624, 671)]
        one_to_twoB = [(718, 381), (785, 442), (787,689)]
        one_to_four = [(440, 390)]
        two_to_three = [(573, 761), (257, 727), (83, 644), (84, 475), (157, 445), (241, 372)]
        two_to_four = [(624, 671), (607, 556), (482, 544), (429, 485), (440, 390)]
        three_to_four = [(440, 390)]
        three_to_zero = [(192, 307), (101, 298), (82, 124), (170, 80), (275, 124), (296, 213), (440, 241)]
        four_to_three = [(241, 372)]
        four_to_zero = [(440, 241)]

        # shortest route to 1
        zero_to_one = zero_to_one   

        #shortest route to 2
        zero_to_twoA = zero_to_one + one_to_twoA
        zero_to_twoB = zero_to_one + one_to_twoB
        zero_to_two = zero_to_twoA if compute_path_length(zero_to_twoA) <= compute_path_length(zero_to_twoB) else zero_to_twoB

        #shortest route to 3
        zero_to_threeA = zero_to_two + two_to_three
        zero_to_threeB = zero_to_one + one_to_twoB + two_to_four + four_to_three
        zero_to_three = zero_to_threeA if compute_path_length(zero_to_threeA) <= compute_path_length(zero_to_threeB) else zero_to_threeB

        #shortest route to 4
        zero_to_fourA = zero_to_one + one_to_four   
        zero_to_fourB = zero_to_three + three_to_four
        zero_to_four = zero_to_fourA if compute_path_length(zero_to_fourA) <= compute_path_length(zero_to_fourB) else zero_to_fourB 

        #shortest route to 0
        zero_to_zeroA = zero_to_three + three_to_zero
        zero_to_zeroB = zero_to_four + four_to_zero
        zero_to_zero = zero_to_zeroA if compute_path_length(zero_to_zeroA) <= compute_path_length(zero_to_zeroB) else zero_to_zeroB

        RACING_LINE = zero_to_zero

        DFS_RACING_LINE = zero_to_zeroA
        BFS_RACING_LINE = zero_to_fourA + four_to_three + three_to_zero
        ASTAR_RACING_LINE = zero_to_zero
        GBFS_RACING_LINE = zero_to_one + one_to_twoB + two_to_four + four_to_zero

    elif level == 4:
        print("Loading level 4")
        background_img = "assets/grass.jpg"
        background_img = scale_image(pygame.image.load(background_img), 1.5)

        track_img = "assets/track4.png"
        border_img = "assets/track_border4.png"

        FINISH_POSITION = (270, 265)
        START_POSITION = (290, 225)

        zero_to_one = [(310, 130), (410, 130), (490, 100), (635, 75)]
        one_to_twoA = [(794, 51), (820, 131), (787, 206), (760, 276)]
        one_to_twoB = [(635, 145), (594, 223), (459, 245), (488, 317), (469, 377), (593, 382), (707, 370)]
        one_to_three = [(635, 145), (594, 245), (480, 245), (460, 317), (460, 385), (423, 470), (280, 470), (282, 592), (352, 650), (469, 650), (500, 715), (500, 820)]
        three_to_one = [(500, 820), (500, 715), (469, 650), (352, 650), (282, 592), (280, 470), (423, 470), (460, 385), (460, 317), (480, 245), (594, 245), (635, 145)]
        two_to_three = [(811, 468), (737, 522), (737, 597), (743, 709), (709, 799), (594, 781), (489, 781)]
        three_to_four = [(319, 820), (157, 796), (157, 645), (157, 572), (100, 515), (75, 450), (75, 355)]
        four_to_five = [(75, 126), (115, 58), (175, 75)]
        five_to_four = [(175, 75), (115, 58), (75, 126)]
        four_to_zero = [(195, 355), (300, 355)]

        # shortest route to 1
        zero_to_one = zero_to_one

        #shortest route to 2
        zero_to_twoA = zero_to_one + one_to_twoA
        zero_to_twoB = zero_to_one + one_to_twoB
        zero_to_two = zero_to_twoA if compute_path_length(zero_to_twoA) <= compute_path_length(zero_to_twoB) else zero_to_twoB

        #shortest route to 3
        zero_to_threeA = zero_to_one + one_to_three
        zero_to_threeB = zero_to_two + two_to_three
        zero_to_three = zero_to_threeA if compute_path_length(zero_to_threeA) <= compute_path_length(zero_to_threeB) else zero_to_threeB

        #shortest route to 4
        zero_to_four = zero_to_three + three_to_four

        #shortest route to 5
        zero_to_five = zero_to_four + four_to_five

        #shortest route to 0
        zero_to_zero = zero_to_four + four_to_zero

        RACING_LINE = zero_to_zero

        DFS_RACING_LINE = zero_to_one + one_to_twoB + two_to_three + three_to_one + one_to_three + three_to_four + four_to_five + five_to_four + four_to_zero
        BFS_RACING_LINE = zero_to_one + one_to_three + three_to_one + one_to_twoB + two_to_three + three_to_four + four_to_zero
        ASTAR_RACING_LINE = zero_to_five + five_to_four + four_to_zero
        #ASTAR_RACING_LINE = zero_to_zero
        GBFS_RACING_LINE = zero_to_zero
    else:
        raise ValueError(f"Unknown level: {level}")

    BACKGROUND = background_img
    TRACK = scale_image(pygame.image.load(track_img), 1)
    TRACK_BORDER = scale_image(pygame.image.load(border_img), 1)
    TRACK_BORDER_MASK = pygame.mask.from_surface(TRACK_BORDER)

    GRID = build_grid(TRACK_BORDER_MASK)

    # For level 3, create a cropped finish image bound by the track
    global FINISH, FINISH_MASK
    if level == 3:
        # Load the original finish image and crop it to be bound by the track
        finish_original = pygame.image.load("assets/finish.png")
        # Crop the right side to remove overflow - keep left 60 pixels
        crop_rect = pygame.Rect(0, 0, 60, finish_original.get_height())
        FINISH = finish_original.subsurface(crop_rect).copy()
        FINISH_MASK = pygame.mask.from_surface(FINISH)
    else:
        # Use default finish image for other levels
        FINISH = pygame.image.load("assets/finish.png")
        FINISH_MASK = pygame.mask.from_surface(FINISH)

    images[:] = [
        (BACKGROUND, (0, 0)),
        (TRACK, (0, 0)),
        (FINISH, FINISH_POSITION),
        (TRACK_BORDER, (0, 0)),
    ]

# --------------------------------------------------
# GameInfo
# --------------------------------------------------
class GameInfo:
    LEVELS = 4

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
# Car factories
# --------------------------------------------------
def create_player_car(color="Red", autonomous=False):
    """Create a player car with optional autonomous mode.
    
    Args:
        color: Car color (Red, Blue, Green, Purple, White, Grey, Pink, Yellow)
        autonomous: If True, car follows path automatically instead of manual control
    """
    if autonomous:
        from cars import dijkstra_car
        car_image = CAR_COLOR_MAP.get(color, RED_CAR)
        return dijkstra_car.DijkstraCar(
            car_image,
            START_POSITION,
            2.5,
            4,
            ASTAR_RACING_LINE + [FINISH_POSITION],
            GRID_SIZE,
            50,
            CHECKPOINT_RADIUS,
            GRID,
            TRACK_BORDER_MASK
        )
    else:
        from cars import PlayerCar
        car_image = CAR_COLOR_MAP.get(color, RED_CAR)
        path = (RACING_LINE + [FINISH_POSITION]) if autonomous else [] # Legacy automated support
        return PlayerCar(car_image, START_POSITION, 2.8, 4, path=path, autonomous=autonomous)

def create_computer_car(type='DFS', color="Grey"):
    from cars import ComputerCar
    car_image = CAR_COLOR_MAP.get(color, GREY_CAR if type == 'DFS' else BLUE_CAR)
    return ComputerCar(car_image, START_POSITION, 2.5, 4, DFS_RACING_LINE + [FINISH_POSITION])

def create_GBFS_car(color="Green"):
    from cars import GBFSDetourCar
    car_image = CAR_COLOR_MAP.get(color, GREEN_CAR)
    car = GBFSDetourCar(
        GBFS_RACING_LINE + [FINISH_POSITION], 2.5, 4,
        GRID_SIZE, 30,
        CHECKPOINT_RADIUS, GRID, TRACK_BORDER_MASK,
        car_image
    )
    car.x, car.y = START_POSITION
    return car

def create_neat_car(color="Purple"):
    from cars import NEATCar
    car_image = CAR_COLOR_MAP.get(color, PURPLE_CAR)
    return NEATCar(
        car_image,
        START_POSITION,
        2.5, 4,
        RACING_LINE, TRACK_BORDER_MASK, GRID_SIZE, GRID
    )

def create_dijkstra_car(max_vel=2.5, rotation_vel=4, color="White"):
    from cars import DijkstraCar
    car_image = CAR_COLOR_MAP.get(color, WHITE_CAR)
    return DijkstraCar(
        car_image,
        START_POSITION,
        max_vel,
        rotation_vel,
        ASTAR_RACING_LINE + [FINISH_POSITION],
        GRID_SIZE,
        50,
        CHECKPOINT_RADIUS,
        GRID,
        TRACK_BORDER_MASK
    )

# --------------------------------------------------
# Raycast
# --------------------------------------------------
def raycast_mask(mask, origin, angle, max_distance=800, step=3):
    ox, oy = origin
    dx, dy = math.cos(angle), math.sin(angle)

    dist = 0.0
    while dist < max_distance:
        px = int(ox + dx * dist)
        py = int(oy + dy * dist)

        if not (0 <= px < mask.get_size()[0] and 0 <= py < mask.get_size()[1]):
            break

        if mask.get_at((px, py)) != 0:
            return {"hit": True, "distance": dist, "point": (px, py)}

        dist += step

    return {"hit": False, "distance": max_distance, "point": None}