import pygame
import math
import heapq
from utils import scale_image, bilt_rotate_center

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
RED_CAR = scale_image(pygame.image.load('assets/red-car.png'), 0.55)
GREEN_CAR = scale_image(pygame.image.load('assets/green-car.png'), 0.55)

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
# A* PATHFINDING
# -----------------------------
def heuristic(a, b):
    """Manhattan heuristic for grid A*.

    `a` and `b` are (row, col) grid coordinates.
    Using Manhattan distance keeps costs admissible for 4-connected grids.
    """
    return abs(a[0] - b[0]) + abs(a[1] - b[1])

def astar(grid, start, goal):
    """A simple A* implementation on a 4-connected boolean grid.

    - `grid` is a list-of-lists of booleans returned by `build_grid`.
    - `start` and `goal` are `(row, col)` tuples.
    Returns a list of grid coordinates from start (exclusive) to goal (inclusive),
    or `None` if no path exists.
    """
    rows, cols = len(grid), len(grid[0])
    open_set = []
    heapq.heappush(open_set, (0, start))
    came_from = {}
    g_score = {start: 0}

    while open_set:
        _, current = heapq.heappop(open_set)

        if current == goal:
            path = []
            while current in came_from:
                path.append(current)
                current = came_from[current]
            path.reverse()
            return path

        x, y = current
        # 4-connected neighbors (up/down/left/right)
        neighbors = [(x+1,y), (x-1,y), (x,y+1), (x,y-1)]

        for nx, ny in neighbors:
            if 0 <= nx < rows and 0 <= ny < cols and grid[nx][ny]:
                tentative_g = g_score[current] + 1
                if (nx, ny) not in g_score or tentative_g < g_score[(nx, ny)]:
                    g_score[(nx, ny)] = tentative_g
                    f_score = tentative_g + heuristic((nx, ny), goal)
                    heapq.heappush(open_set, (f_score, (nx, ny)))
                    came_from[(nx, ny)] = current

    return None

# -----------------------------
# CAR CLASSES
# -----------------------------
class Car:
    """Base car class.

    Holds position, velocity, rotation and image. Subclasses define the
    `IMG` and `START_POS` class attributes.
    """
    def __init__(self, max_vel, rotation_vel):
        self.img = self.IMG
        self.max_vel = max_vel
        self.vel = 0
        self.rotation_vel = rotation_vel
        self.angle = 0
        self.x, self.y = self.START_POS
        self.acceleration = 0.5
    
    def rotate(self, left=False, right=False):
        if left:
            self.angle += self.rotation_vel
        elif right:
            self.angle -= self.rotation_vel
    
    def draw(self, win):
        bilt_rotate_center(win, self.img, (self.x, self.y), self.angle)

    def move_forward(self):
        self.vel = min(self.vel + self.acceleration, self.max_vel)
        self.move()
    
    def move_backward(self):
        self.vel = max(self.vel - self.acceleration, -self.max_vel/2)
        self.move()
    
    def move(self):
        radians = math.radians(self.angle)
        vertical = math.cos(radians) * self.vel
        horizontal = math.sin(radians) * self.vel
        self.y -= vertical
        self.x -= horizontal
    
    def reduce_speed(self):
        self.vel = max(self.vel - self.acceleration/2, 0)
        self.move()
    
    def collide(self, mask, x=0, y=0):
        car_mask = pygame.mask.from_surface(self.img)
        offset = (int(self.x - x), int(self.y - y))
        return mask.overlap(car_mask, offset)
    
    def reset(self):
        self.x, self.y = self.START_POS
        self.angle = 0
        self.vel = 0

class PlayerCar(Car):
    IMG = RED_CAR
    START_POS = (185, 200)

    """Human-controlled car; simple bounce behaviour on collision.

    The `bounce` method reverses current velocity and steps the car to avoid
    getting stuck inside wall geometry.
    """
    def bounce(self):
        self.vel = -self.vel
        self.move()

# -----------------------------
# A* AI CAR
# -----------------------------
class AStarCar(Car):
    IMG = GREEN_CAR
    START_POS = (165, 200)

    def __init__(self, max_vel, rotation_vel, checkpoints):
        super().__init__(max_vel, rotation_vel)
        self.checkpoints = checkpoints
        self.current_checkpoint = 0
        self.path = []
        self.current_point = 0
        self.vel = max_vel

        """A car driven by A* pathfinding.

                Behavior summary:
                - Uses `world_to_grid` / `grid_to_world` to convert between pixel
                    coordinates and the boolean grid used by A*.
                - `compute_path` runs A* from the car's current grid cell to the
                    checkpoint's grid cell and stores the resulting path as world
                    coordinates in `self.path`.
                - `move` steers the car toward the next point on the path while
                    predicting collisions; if the next move would hit a wall or the
                    finish line in the wrong direction it will try to choose a nearby
                    alternative grid cell and reroute.
"""

    def bounce(self):
        # Reverse velocity and use base movement to avoid calling AStarCar.move()
        self.vel = -self.vel
        super().move()

    def world_to_grid(self, x, y):
        return int(y // GRID_SIZE), int(x // GRID_SIZE)

    def grid_to_world(self, gx, gy):
        # Convert grid (row, col) to world (x, y) centered in the cell
        row, col = gx, gy
        x = col * GRID_SIZE + GRID_SIZE / 2
        y = row * GRID_SIZE + GRID_SIZE / 2
        return x, y

    def compute_path(self):
        """Compute a new grid path from current position to the current checkpoint.

        The A* result is converted to world coordinates centered in each
        grid cell using `grid_to_world` and stored in `self.path`.
        """
        start = self.world_to_grid(self.x, self.y)
        goal_world = self.checkpoints[self.current_checkpoint]
        goal = self.world_to_grid(*goal_world)
        grid_path = astar(GRID, start, goal)
        if grid_path:
            # convert grid path (row,col) -> world pixel coordinates
            self.path = [self.grid_to_world(gx, gy) for gx, gy in grid_path]
            self.current_point = 0

    def move(self):
        if not self.path or self.current_point >= len(self.path):
            self.compute_path()
            return

        target_x, target_y = self.path[self.current_point]
        dx = target_x - self.x
        dy = target_y - self.y
        dist = math.hypot(dx, dy)

        if dist < 10:
            self.current_point += 1
            if self.current_point >= len(self.path):
                # reached checkpoint
                self.current_checkpoint = (self.current_checkpoint + 1) % len(self.checkpoints)
                self.compute_path()
            return

        angle_to_target = math.degrees(math.atan2(dy, dx)) - 90
        angle_diff = (angle_to_target - self.angle + 180) % 360 - 180

        if angle_diff > 0:
            self.angle += min(self.rotation_vel, angle_diff)
        else:
            self.angle -= min(self.rotation_vel, -angle_diff)

        # Predict next position and avoid moving into track borders or wrong-direction finish
        radians = math.radians(self.angle)
        vertical = math.cos(radians) * self.vel
        horizontal = math.sin(radians) * self.vel
        predicted_y = self.y - vertical
        predicted_x = self.x - horizontal

        # Check collision with track border at predicted position
        car_mask = pygame.mask.from_surface(self.img)
        offset = (int(predicted_x), int(predicted_y))
        # If overlap with TRACK_BORDER_MASK, recompute path instead of moving into wall
        if TRACK_BORDER_MASK.overlap(car_mask, offset):
            self.compute_path()
            return

        # Check finish line wrong-direction collision (treat as wall)
        finish_overlap = FINISH_MASK.overlap(car_mask, (int(predicted_x - 140), int(predicted_y - 250)))
        if finish_overlap:
            # If hitting the finish line in the 'wrong' direction (y offset == 0), treat as obstacle
            if finish_overlap[1] == 0:
                self.compute_path()
                return

        # No blocking collision, perform movement
        super().move()

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
    pygame.display.update()

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
computer_car = AStarCar(2, 4, CHECKPOINTS)

while run:
    clock.tick(FPS)
    draw(WIN, images, player_car, computer_car)

    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            run = False
            break

    move_player(player_car)
    computer_car.move()
    handle_collision(player_car, computer_car)

pygame.quit()
