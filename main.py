import pygame, math
from car import *
from neatmanager import NEATManager
from utils import scale_image, bilt_rotate_center

import neat
config = neat.Config(
    neat.DefaultGenome,
    neat.DefaultReproduction,
    neat.DefaultSpeciesSet,
    neat.DefaultStagnation,
    'neat_config.ini'  # your config file
)

pygame.font.init()

"""
DFA Path Finding Grand Prix

This file implements a small top-down racing simulation using Pygame.

- Loads track, border and car images and creates masks for collision.
- Uses a simple A* on a grid made from the track-border mask for AI pathfinding.
- Provides two car classes: a player-controlled car and an A*-driven car.
- The AI computes a grid path to the next checkpoint and follows it while
    avoiding collisions with the track borders and the finish line in the
    wrong direction.

To modify behavior, tune `GRID_SIZE`, car velocities, or the CHECKPOINTS list.
"""

# -----------------------------
# LOAD IMAGES
# -----------------------------
GRASS = scale_image(pygame.image.load('assets/grass.jpg'), 2.5)
TRACK = scale_image(pygame.image.load('assets/track.png'), 1)
TRACK_BORDER = scale_image(pygame.image.load('assets/track-border.png'), 1)
TRACK_BORDER_MASK = pygame.mask.from_surface(TRACK_BORDER)
FINISH = pygame.image.load('assets/finish.png')
FINISH_MASK = pygame.mask.from_surface(FINISH)


WIN = pygame.display.set_mode((TRACK.get_width(), TRACK.get_height()))
pygame.display.set_caption("DFA Path Finding Grand Prix")

FPS = 60

# -----------------------------
# CHECKPOINTS AROUND TRACK
# -----------------------------
CHECKPOINTS = [(191, 131), (138, 80), (70, 135), (70, 514), (317, 785), (397, 811), (450, 753), (457, 586), (559, 532), (663, 596), (669, 753), (741, 814), (824, 746), (821, 469), (757, 400), (502, 398), (446, 347), (514, 288), (763, 282), (822, 238), (820, 130), (749, 83), (363, 86), (316, 150), (310, 405), (255, 460), (198, 404), (193, 263)]
#CHECKPOINTS = [ (180, 180), (100, 300), (120, 500), (300, 700), (500, 750), (700, 650), (800, 500), (780, 300), (650, 200), (450, 150), (300, 180), (200, 250)] # near finish line 
# -----------------------------
# GRID FOR A*
# -----------------------------
GRID_SIZE = 1  # pixels per grid cell
CHECKPOINT_RADIUS = 8

def build_grid(mask):
    """Build a boolean grid from a Pygame mask.

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








# -----------------------------
# GAME LOOP FUNCTIONS
# -----------------------------
def draw(win, images, player_car, computer_car):
    for img, pos in images:
        win.blit(img, pos)
    # Draw checkpoints as visible markers so we can debug AI routing.
    # The AI's current checkpoint is highlighted in green.
    for idx, (cx, cy) in enumerate(CHECKPOINTS):
        color = (0, 200, 0) if hasattr(computer_car, 'current_checkpoint') and idx == computer_car.current_checkpoint else (0, 0, 200)
        pygame.draw.circle(win, color, (int(cx), int(cy)), CHECKPOINT_RADIUS)
    # Draw cars
    player_car.draw(win)
    computer_car.draw(win)


def move_player(player_car):
    """Handle keyboard input for the player car.

    - `A`/`D` rotate left/right
    - `W`/`S` accelerate forward/backward
    If no throttle keys are pressed the car will naturally slow down.
    """
    keys = pygame.key.get_pressed()
    moved = False
    if keys[pygame.K_a]:
        player_car.rotate(left=True)
    if keys[pygame.K_d]:
        player_car.rotate(right=True)
    if keys[pygame.K_w]:
        moved = True
        player_car.move_forward()
    if keys[pygame.K_s]:
        moved = True
        player_car.move_backward()
    if not moved:
        player_car.reduce_speed()

def handle_collision(player_car, computer_car):
    """High-level collision handling called each frame.

    - Player collision with track border -> bounce.
    - Computer collision with track border -> bounce (AI movement code also
      predicts and avoids collisions; this is an additional safety check).
    - Finish-line collision: if hit in the wrong direction (mask overlap y==0)
      the car bounces. If hit correctly and the car already has visited the
      last checkpoint, the corresponding side wins and both cars reset.
    """
    # Player border collision
    if player_car.collide(TRACK_BORDER_MASK):
        player_car.bounce()

    # AI border collision fallback
    if computer_car.collide(TRACK_BORDER_MASK):
        computer_car.bounce()

    # AI finish-line handling (safety check)
    comp_finish_hit = computer_car.collide(FINISH_MASK, 140, 250)
    if comp_finish_hit:
        if comp_finish_hit[1] == 0:
            computer_car.bounce()
        else:
            if computer_car.current_checkpoint == len(CHECKPOINTS) - 1:
                player_car.reset()
                computer_car.reset()
                print("COMPUTER WINS!")

    # Player finish-line handling
    finish_hit = player_car.collide(FINISH_MASK, 140, 250)
    if finish_hit:
        if finish_hit[1] == 0:
            player_car.bounce()
        else:
            player_car.reset()
            computer_car.reset()
            print("PLAYER WINS!")





 #--- car creation helper
def make_neat_car():
    return NEATCar(max_vel=4.0, rotation_vel=3.0,
                   checkpoints=CHECKPOINTS, grid_size=GRID_SIZE, grid=GRID,
                   sensor_length=300)

# --- manager ---
manager = NEATManager(neat_config=config,
                      car_factory=make_neat_car,
                      track_mask=TRACK_BORDER_MASK,
                      raycast_fn=raycast_mask,
                      fps=60,
                      time_limit_sec=20.0)


# -----------------------------
# MAIN GAME LOOP
# -----------------------------
run = True
clock = pygame.time.Clock()

images = [
    (GRASS, (0, 0)),
    (TRACK, (0, 0)),
    (FINISH, (140, 250)),
    (TRACK_BORDER, (0, 0)),
]

player_car = PlayerCar(4, 4)
astar_car = AStarCar(2, 4, CHECKPOINTS, GRID_SIZE, GRID)
neat_car = NEATCar(2, 4, CHECKPOINTS, GRID_SIZE, GRID)

mouse_pos = (0,0)

while run:
    clock.tick(FPS)
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            run = False
            break
        if event.type == pygame.MOUSEMOTION:
            mouse_pos = pygame.mouse.get_pos()
    
    gen, idx, total = manager.update(1.0/FPS)

    move_player(player_car)
    astar_car.move()
    handle_collision(player_car, astar_car)
    draw(WIN, images, player_car, astar_car)
    manager.draw(WIN)
    
    font = pygame.font.Font(None, 22)
    hud = font.render(f"Gen {gen} | Genome {idx}/{total}", True, (255,255,255))
    WIN.blit(hud, (10, 10))

    #neat_car.draw(WIN)
    pygame.display.update()


pygame.quit()
