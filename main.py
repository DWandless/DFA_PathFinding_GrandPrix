"""Top-down racing demo using Pygame.

This file provides a small demo with a player-controlled car and a
computer car that follows a fixed waypoint path. Code is intentionally
simple: collision detection uses Pygame masks and movement is driven by
basic trig-based kinematics.

This patch adds comments and docstrings to clarify the behaviour of
each function and class while keeping program logic unchanged.
"""

import pygame
import time
import math
from utils import scale_image, blit_rotate_center

# --- Images and masks ----------------------------------------------------
# Background texture and track surface (scaled to fit window)
GRASS = scale_image(pygame.image.load("assets/grass.jpg"), 2.5)
TRACK = scale_image(pygame.image.load("assets/track.png"), 1)

# Track border image used to create a mask for collision detection
TRACK_BORDER = scale_image(pygame.image.load("assets/track-border.png"), 1)
TRACK_BORDER_MASK = pygame.mask.from_surface(TRACK_BORDER)

# Finish line image and mask; position is the top-left where it will be drawn
FINISH = pygame.image.load("assets/finish.png")
FINISH_MASK = pygame.mask.from_surface(FINISH)
FINISH_POSITION = (135, 250)

# Car sprites (scaled)
RED_CAR = scale_image(pygame.image.load("assets/red-car.png"), 0.55)
GREEN_CAR = scale_image(pygame.image.load("assets/green-car.png"), 0.55)
PURPLE_CAR = scale_image(pygame.image.load("assets/purple-car.png"), 0.55)

# --- Window & frame rate ------------------------------------------------
WIDTH, HEIGHT = TRACK.get_width(), TRACK.get_height()
WIN = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Racing Game!")
FPS = 60

# --- Waypoints -----------------------------------------------------------
# Points that approximate the centerline of the track used by the AI car
PATH = [(191, 131), (138, 80), (70, 135), (70, 514), (317, 785), (397, 811), (450, 753), (457, 586), (559, 532), (663, 596), (669, 753), (741, 814), (824, 746), (821, 469), (757, 400), (502, 398), (446, 347), (514, 288), (763, 282), (822, 238), (820, 130), (749, 83), (363, 86), (316, 150), (310, 405), (255, 460), (198, 404), (193, 263)]


class AbstractCar:
    """Base car providing position, movement, rotation and collisions.

    Subclasses should set the class attributes `IMG` and `START_POS`.
    """

    def __init__(self, max_vel, rotation_vel):
        # Sprite and motion parameters
        self.img = self.IMG
        self.max_vel = max_vel
        self.vel = 0
        self.rotation_vel = rotation_vel
        self.angle = 0
        self.x, self.y = self.START_POS
        # Small acceleration for smooth motion
        self.acceleration = 0.1

    def rotate(self, left=False, right=False):
        """Rotate the car by `rotation_vel` degrees in a frame.

        `left=True` increases the angle, `right=True` decreases it.
        """
        if left:
            self.angle += self.rotation_vel
        elif right:
            self.angle -= self.rotation_vel

    def draw(self, win):
        """Draw the car rotated around its center using helper function."""
        blit_rotate_center(win, self.img, (self.x, self.y), self.angle)

    def move_forward(self):
        """Increase forward velocity and move the car one step."""
        self.vel = min(self.vel + self.acceleration, self.max_vel)
        self.move()

    def move_backward(self):
        """Decrease velocity (reverse) and move the car one step."""
        self.vel = max(self.vel - self.acceleration, -self.max_vel / 2)
        self.move()

    def move(self):
        """Translate the car in the world according to current angle/velocity.

        Uses cos/sin on `angle` to compute vertical/horizontal displacements.
        Note: screen y increases downwards, hence `self.y -= vertical`.
        """
        radians = math.radians(self.angle)
        vertical = math.cos(radians) * self.vel
        horizontal = math.sin(radians) * self.vel
        self.y -= vertical
        self.x -= horizontal

    def collide(self, mask, x=0, y=0):
        """Return mask overlap tuple if this car overlaps `mask`.

        The method scales down the car mask slightly to reduce false
        positives at sprite edges and uses an offset to align masks.
        """
        car_mask = pygame.mask.from_surface(self.img)
        car_mask = car_mask.scale(
            (int(car_mask.get_size()[0] * 0.85), int(car_mask.get_size()[1] * 0.85))
        )
        offset = (
            int(self.x - x + self.img.get_width() * 0.075),
            int(self.y - y + self.img.get_height() * 0.075),
        )
        return mask.overlap(car_mask, offset)

    def reset(self):
        """Reset car to its starting coordinates and zero velocity."""
        self.x, self.y = self.START_POS
        self.angle = 0
        self.vel = 0


class PlayerCar(AbstractCar):
    """Human-driven car using keyboard input.

    The player car implements friction via `reduce_speed` and a `bounce`
    response to collisions.
    """
    IMG = RED_CAR
    START_POS = (200, 200)

    def reduce_speed(self):
        """Apply friction when no throttle is pressed."""
        self.vel = max(self.vel - self.acceleration / 2, 0)
        self.move()

    def bounce(self):
        """Small reverse impulse when colliding with obstacles."""
        self.vel = -self.vel / 2
        self.move()


class ComputerCar(AbstractCar):
    """Path-following AI car.

    The car rotates toward the current waypoint and moves forward.
    When a waypoint is reached it advances to the next point in `path`.
    """
    IMG = PURPLE_CAR
    START_POS = (170, 200)

    def __init__(self, max_vel, rotation_vel, path=[]):
        super().__init__(max_vel, rotation_vel)
        self.path = path
        self.current_point = 0
        # Start at top speed so the car moves immediately
        self.vel = max_vel

    def draw_points(self, win):
        """Optional debug draw of all waypoints as small circles."""
        for point in self.path:
            pygame.draw.circle(win, (255, 0, 0), point, 2)

    def draw(self, win):
        """Render the car (and optionally the path debug points)."""
        super().draw(win)
        self.draw_points(win)  # enable to visualise waypoints

    def calculate_angle(self):
        """Compute and apply a rotation toward the current waypoint.

        This method mirrors the approach used elsewhere in the project
        and ensures the car turns smoothly toward its target.
        """
        target_x, target_y = self.path[self.current_point]
        x_diff = target_x - self.x
        y_diff = target_y - self.y

        if y_diff == 0:
            desired_radian_angle = math.pi / 2
        else:
            desired_radian_angle = math.atan(x_diff / y_diff)

        if target_y > self.y:
            desired_radian_angle += math.pi

        difference_in_angle = self.angle - math.degrees(desired_radian_angle)
        if difference_in_angle >= 180:
            difference_in_angle -= 360

        if difference_in_angle > 0:
            self.angle -= min(self.rotation_vel, abs(difference_in_angle))
        else:
            self.angle += min(self.rotation_vel, abs(difference_in_angle))

    def update_path_point(self):
        """Advance to next waypoint when the current one is inside the car rect.

        This is a simple proximity test that works for reasonably spaced
        waypoints; if the car appears to miss points, consider switching
        to a distance-based threshold instead.
        """
        target = self.path[self.current_point]
        rect = pygame.Rect(self.x, self.y, self.img.get_width(), self.img.get_height())
        if rect.collidepoint(*target):
            self.current_point += 1

    def move(self):
        """Steer and move the car toward active waypoint each frame."""
        if self.current_point >= len(self.path):
            return

        self.calculate_angle()
        self.update_path_point()
        super().move()


def draw(win, images, player_car, computer_car):
    """Render the whole scene: background layers then cars."""
    for img, pos in images:
        win.blit(img, pos)

    player_car.draw(win)
    computer_car.draw(win)
    pygame.display.update()


def move_player(player_car):
    """Handle keyboard input and update the player car accordingly."""
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
    """Perform collision checks and apply appropriate responses.

    Uses mask overlap to check border collisions and finish-line
    interactions. For this demo we reset both cars when the finish is
    reached by the computer; the player has a more nuanced bounce when
    crossing the finish from the wrong direction.
    """
    if player_car.collide(TRACK_BORDER_MASK) != None:
        player_car.bounce()

    computer_finish_poi_collide = computer_car.collide(FINISH_MASK, *FINISH_POSITION)
    if computer_finish_poi_collide != None:
        player_car.reset()
        computer_car.reset()

    player_finish_poi_collide = player_car.collide(FINISH_MASK, *FINISH_POSITION)
    if player_finish_poi_collide != None:
        if player_finish_poi_collide[1] == 0:
            player_car.bounce()
        else:
            player_car.reset()
            computer_car.reset()


# -----------------------------
# Main loop
# -----------------------------
run = True
clock = pygame.time.Clock()
images = [(GRASS, (0, 0)), (TRACK, (0, 0)), (FINISH, FINISH_POSITION), (TRACK_BORDER, (0, 0))]
player_car = PlayerCar(4, 4)
computer_car = ComputerCar(2, 4, PATH)

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

print(computer_car.path)
pygame.quit()