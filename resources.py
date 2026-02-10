# resources.py

import pygame
import time
import math

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
DEBUG_DRAW_POINTS = False # Enables drawing and plotting of points on levels during them being played
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

SPAWN_POSITIONS = {}

def update_spawn_positions():
    global SPAWN_POSITIONS
    sx, sy = START_POSITION
    SPAWN_POSITIONS = {
        "player": (sx, sy),
        "computer": (sx - 10, sy),
        "gbfs": (sx, sy + 10),
        "neat": (sx - 10, sy + 10),
        "dijkstra": (sx - 10 , sy + 20),
    }

update_spawn_positions()

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
# Algorithm Speed Tuning (Level-Specific)
# --------------------------------------------------
# Multiplier applied to the *player-selected* car's max velocity per level.
# This replaces the old "start delay" handicap.
SPEED_MULTIPLIER_CONFIG = {
    1: {
        "Player": 1.00,
        "DFS": 1.06,
        "BFS": 0.92,
        "GBFS": 0.92,
        "AStar": 0.92,
        "Dijkstra": 0.92,
        "NEAT": 0.92,
    },
    2: {
        "Player": 1.00,
        "BFS": 1.06,
        "DFS": 0.8,
        "GBFS": 0.8,
        "AStar": 0.92,
        "Dijkstra": 0.92,
        "NEAT": 0.92,
    },
    3: {
        "Player": 1.00,
        "AStar": 1.06,
        "Dijkstra": 1.06,
        "BFS": 0.92,
        "DFS": 0.92,
        "GBFS": 0.92,
        "NEAT": 0.92,
    },
    4: {
        "Player": 1.00,
        "GBFS": 1.06,
        "BFS": 0.92,
        "DFS": 0.92,
        "AStar": 0.92,
        "Dijkstra": 0.92,
        "NEAT": 0.92,
    },
}

def apply_level_speed_tuning(car, algorithm, level):
    """Apply level-specific max velocity tuning to a car (intended for the player-selected model)."""
    if car is None:
        return
    if not hasattr(car, "max_vel"):
        return

    if not hasattr(car, "_base_max_vel"):
        car._base_max_vel = car.max_vel

    level_cfg = SPEED_MULTIPLIER_CONFIG.get(level, {})
    multiplier = level_cfg.get(algorithm, 1.0)

    car.max_vel = car._base_max_vel * multiplier
    if hasattr(car, "vel"):
        try:
            car.vel = min(car.vel, car.max_vel)
        except TypeError:
            car.vel = car.max_vel
        if getattr(car, "autonomous", False):
            car.vel = car.max_vel

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

        FINISH_POSITION = (135, 280)
        START_POSITION = (200, 200)

        RACING_LINE = [
            (191,131),(138,50),(70,110),(50,530),(317,800),(397,811),
            (450,753),(457,586),(559,515),(665,596),(670,775),
            (745,850),(840,746),(840,450),(730,400),(475,410),
            (425,347),(500,250),(763,282),(840,238),(840,130),
            (749,45),(363,45),(316,150),(310,405),(255,460),
            (178,404),(193,193)
        ]

        DFS_RACING_LINE = RACING_LINE
        BFS_RACING_LINE = RACING_LINE
        ASTAR_RACING_LINE = RACING_LINE
        GBFS_RACING_LINE = RACING_LINE


    elif level == 2:
        background_img = "assets/desert.png"
        background_img = scale_image(pygame.image.load(background_img), 1)

        track_img = "assets/track2.png"
        border_img = "assets/track_border2.png"

        FINISH_POSITION = (30, 420)
        START_POSITION = (70, 288)

        
        # Two possible paths after checkpoint (830, 660)
        path_to_junction = [
            (80, 130), (125, 90), (250, 75), (400, 83), (450, 83), (500, 83), (760, 85),
            (830, 130), (816, 235), (730, 470), (750, 583),(820, 750),
        ]
        
        # Path A: through (750, 750)
        path_a = path_to_junction + [
            (750, 800), (348, 810), (118, 810), (69, 744), (93, 696), 
            (222, 632), (485, 527), (510, 416), (370, 392),
            (225, 470), (120, 470), 
        ]
        
        # Path B: through (630, 700)
        path_b = path_to_junction + [
            (640, 700), (640, 480), (620, 280), (532, 220), (348, 220), (255, 260), 
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

        FINISH_POSITION = (395, 435)
        START_POSITION = (440, 350)

        level3_path = [
            (442, 108), (486, 48), (661, 49), (795, 75), (842, 108), (849, 200),
            (764, 248), (620, 252), (589, 302), (587, 389), (792, 398), (859, 443),
            (855, 654), (842, 773), (708, 781), (661, 712), (655, 627), (610, 582),
            (541, 578), (473, 581), (443, 535), (445, 425),
        ]

        level3_alt_path = [
            (444, 235), (323, 227), (284, 189), (277, 101), (231, 43), (96, 49),
            (56, 103), (52, 281), (122, 316), (239, 356), (231, 430), (178, 472),
            (97, 473), (48, 520), (47, 685), (122, 783), (312, 804), (477, 819),
            (654, 818), (653, 628), (608, 581), (482, 577), (443, 535), (444, 425),
        ]

        RACING_LINE = level3_path

        DFS_RACING_LINE = level3_alt_path
        BFS_RACING_LINE = level3_alt_path
        ASTAR_RACING_LINE = level3_path
        GBFS_RACING_LINE = level3_path


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

    global FINISH, FINISH_MASK
    FINISH = pygame.image.load("assets/finish.png")
    FINISH_MASK = pygame.mask.from_surface(FINISH)

    images[:] = [
        (BACKGROUND, (0, 0)),
        (TRACK, (0, 0)),
        (FINISH, FINISH_POSITION),
        (TRACK_BORDER, (0, 0)),
    ]

    update_spawn_positions()

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
            3,
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
        return PlayerCar(car_image, START_POSITION, 3.2, 4, path=path, autonomous=autonomous)

def create_computer_car(type='DFS', color="Grey"):
    from cars import ComputerCar
    car_image = CAR_COLOR_MAP.get(color, GREY_CAR if type == 'DFS' else BLUE_CAR)
    if type == 'BFS':
        path = BFS_RACING_LINE
    else:
        path = DFS_RACING_LINE
    return ComputerCar(car_image, START_POSITION, 2.5, 4, path + [FINISH_POSITION])

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