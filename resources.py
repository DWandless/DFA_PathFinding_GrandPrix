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
CHECKPOINT_RADIUS = 30

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

BLUE_CAR = scale_image(pygame.image.load("assets/blue-car.png"), 0.55)
RED_CAR = scale_image(pygame.image.load("assets/red-car.png"), 0.55)
GREEN_CAR = scale_image(pygame.image.load("assets/green-car.png"), 0.55)
PURPLE_CAR = scale_image(pygame.image.load("assets/purple-car.png"), 0.55)
WHITE_CAR = scale_image(pygame.image.load("assets/white-car.png"), 0.55)
TEMPLATE_CAR = scale_image(pygame.image.load("assets/car_template.png"), 0.55)
GREY_CAR = scale_image(pygame.image.load("assets/grey-car.png"), 0.55)

# Color name to car image mapping
CAR_COLOR_MAP = {
    "Red": RED_CAR,
    "Blue": BLUE_CAR,
    "Green": GREEN_CAR,
    "Purple": PURPLE_CAR,
    "White": WHITE_CAR,
    "Grey": GREY_CAR,
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
    5: pygame.image.load("assets/track5.png").convert_alpha(),
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
# Track Loader
# --------------------------------------------------



def load_track_for_level(level):
    global BACKGROUND
    global TRACK, TRACK_BORDER, TRACK_BORDER_MASK
    global FINISH_POSITION, START_POSITION
    global RACING_LINE, GRID, images

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
            (191,131),(138,80),(70,135),(70,514),(317,785),(397,811),
            (450,753),(457,586),(559,532),(663,596),(669,753),
            (741,814),(824,746),(821,469),(757,400),(502,398),
            (446,347),(514,288),(763,282),(822,238),(820,130),
            (749,83),(363,86),(316,150),(310,405),(255,460),
            (178,404),(193,193)
        ]

    elif level == 2:
        background_img = "assets/desert.png"
        background_img = scale_image(pygame.image.load(background_img), 1)

        track_img = "assets/track2.png"
        border_img = "assets/track_border2.png"

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

        
        RACING_LINE = path_a if compute_path_length(path_a) <= compute_path_length(path_b) else path_b
    
    elif level == 3:
        print("Loading level 3")
        background_img = "assets/desert.png"
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


    elif level == 4:
        print("Loading level 4")
        background_img = "assets/grass.jpg"
        background_img = scale_image(pygame.image.load(background_img), 1.5)

        track_img = "assets/track4.png"
        border_img = "assets/track_border4.png"

        FINISH_POSITION = (270, 265)
        START_POSITION = (317, 225)

        zero_to_one = [(320, 130), (410, 130), (490, 100), (635, 75)]
        one_to_twoA = [(794, 51), (820, 131), (787, 206), (760, 276)]
        one_to_twoB = [(635, 145), (594, 223), (459, 245), (488, 317), (469, 377), (593, 382), (707, 370)]
        one_to_three = [(635, 145), (594, 245), (480, 245), (460, 317), (460, 385), (423, 470), (280, 470), (282, 592), (352, 650), (469, 650), (500, 715), (500, 820)]
        two_to_three = [(811, 468), (737, 522), (737, 597), (743, 709), (709, 799), (594, 781), (489, 781)]
        three_to_four = [(319, 820), (157, 796), (157, 645), (157, 572), (100, 515), (75, 450), (75, 355)]
        four_to_five = [(75, 126), (91, 58), (170, 94)]
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


    elif level == 5:
        
        background_img = "assets/grass.jpg"
        background_img = scale_image(pygame.image.load(background_img), 1.5)
        
        track_img = "assets/track5.png"
        border_img = "assets/track_border5.png"

        FINISH_POSITION = (18, 260)
        START_POSITION = (30, 200)

        zero_to_oneA =   [(50, 100), (115, 60)]
        zero_to_oneB =   [(115,210), (193, 125)]
        one_to_two =     [(292, 60)]
        two_to_three =   [(523, 90)]
        two_to_four =    [(415, 92), (380, 180), (330, 221), (340, 300)]
        three_to_five =  [(648, 115), (620, 163), (545, 163), (522, 295)]
        three_to_six =   [(746, 40), (841, 101)]
        six_to_five =    [(762, 169), (743, 271), (522, 295)]
        five_to_four =   [(331, 291)]
        six_to_seven =   [(841, 238), (841, 523)]
        seven_to_eight = [(841, 777), (795, 822), (594, 828), (554, 816), (579, 758), (677, 759), (696, 636), (702, 502), (674, 400), (566, 396), (462, 423), 
                          (477, 518), (562, 527), (586, 596), (534, 633), (375, 622)]
        four_to_eight =  [(345, 450), (345, 585)]
        eight_to_zero =  [(345, 585), (175, 600), (170, 520), (220, 450), (220, 376), (198, 315), (119, 315), (18, 260)]
        eight_to_nine =  [(356, 698), (376, 746), (423, 771), (390, 822), (240, 825)]
        nine_to_zeroA =  [(92, 825), (36, 787), (36, 697), (36, 529), (36, 326), (18, 260)]
        nine_to_zeroB =  [(193, 717), (123, 718), (36, 697), (36, 529), (36, 326), (18, 260)]
         
        #shortest route to 1
        zero_to_one = zero_to_oneA if compute_path_length(zero_to_oneA) <= compute_path_length(zero_to_oneB) else zero_to_oneB

        #shortest route to 2
        zero_to_two = zero_to_one + one_to_two

        #shortest route to 3
        zero_to_three = zero_to_two + two_to_three

        #shortest route to 4
        zero_to_fourA = zero_to_two + two_to_four
        zero_to_fourB = zero_to_three + three_to_five + five_to_four
        zero_to_fourC = zero_to_three + three_to_six + six_to_five + five_to_four
        zero_to_four = zero_to_fourA if compute_path_length(zero_to_fourA) <= compute_path_length(zero_to_fourB) and compute_path_length(zero_to_fourA) <= compute_path_length(zero_to_fourC) else (zero_to_fourB if compute_path_length(zero_to_fourB) <= compute_path_length(zero_to_fourC) else zero_to_fourC)

        #shortest route to 5
        zero_to_fiveA = zero_to_three + three_to_five
        zero_to_fiveB = zero_to_three + three_to_six + six_to_five
        zero_to_five = zero_to_fiveA if compute_path_length(zero_to_fiveA) <= compute_path_length(zero_to_fiveB) else zero_to_fiveB

        #shortest route to 6
        zero_to_six = zero_to_three + three_to_six

        #shortest route to 7
        zero_to_seven = zero_to_six + six_to_seven

        #shortest route to 8
        zero_to_eightA = zero_to_seven + seven_to_eight
        zero_to_eightB = zero_to_four + four_to_eight   
        zero_to_eight = zero_to_eightA if compute_path_length(zero_to_eightA) <= compute_path_length(zero_to_eightB) else zero_to_eightB

        #shortest route to 9
        zero_to_nine = zero_to_eight + eight_to_nine

        #shortest route to 0
        zero_to_zero = zero_to_eight + eight_to_zero
        zero_to_zeroA = zero_to_nine + nine_to_zeroA
        zero_to_zeroB = zero_to_nine + nine_to_zeroB
        zero_to_zero = zero_to_zero if compute_path_length(zero_to_zero) <= compute_path_length(zero_to_zeroA) and compute_path_length(zero_to_zero) <= compute_path_length(zero_to_zeroB) else (zero_to_zeroA if compute_path_length(zero_to_zeroA) <= compute_path_length(zero_to_zeroB) else zero_to_zeroB)

        RACING_LINE = zero_to_zero

        


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
# Car factories
# --------------------------------------------------
def create_player_car(color="Red", autonomous=False):
    """Create a player car with optional autonomous mode.
    
    Args:
        color: Car color (Red, Blue, Green, Purple, White, Grey)
        autonomous: If True, car follows path automatically instead of manual control
    """
    from cars import PlayerCar
    car_image = CAR_COLOR_MAP.get(color, RED_CAR)
    path = (RACING_LINE + [FINISH_POSITION]) if autonomous else []
    return PlayerCar(car_image, START_POSITION, 4, 4, path=path, autonomous=autonomous)

def create_computer_car(type='DFS', color="Grey"):
    from cars import ComputerCar
    car_image = CAR_COLOR_MAP.get(color, GREY_CAR if type == 'DFS' else BLUE_CAR)
    return ComputerCar(car_image, START_POSITION, 2, 4, RACING_LINE + [FINISH_POSITION])

def create_GBFS_car(color="Green"):
    from cars import GBFSDetourCar
    car_image = CAR_COLOR_MAP.get(color, GREEN_CAR)
    car = GBFSDetourCar(
        RACING_LINE + [FINISH_POSITION],
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
        3, 4,
        RACING_LINE, TRACK_BORDER_MASK, GRID_SIZE, GRID
    )

def create_dijkstra_car(max_vel=3, rotation_vel=4, color="White"):
    from cars import DijkstraCar
    car_image = CAR_COLOR_MAP.get(color, WHITE_CAR)
    return DijkstraCar(
        car_image,
        START_POSITION,
        max_vel,
        rotation_vel,
        RACING_LINE + [FINISH_POSITION],
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