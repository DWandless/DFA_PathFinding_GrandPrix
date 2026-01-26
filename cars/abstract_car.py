import math
import pygame
from resources import blit_rotate_center


class AbstractCar:
    """Base car providing position, movement, rotation and collisions.

    This implementation takes the sprite and start position as constructor
    arguments so callers (e.g. factories) can supply different images.
    """

    def __init__(self, img, start_pos, max_vel, rotation_vel):
        self.img = img
        self.START_POS = start_pos
        self.max_vel = max_vel
        self.vel = 0
        self.rotation_vel = rotation_vel
        self.angle = 0
        self.x, self.y = self.START_POS
        self.acceleration = 0.1
    
    def SetTunables(self, TuningData):
        # Add as many tunables as you like.
        self.max_vel = TuningData[0]
        self.acceleration = TuningData[1]
        # Breaking goes here -- dunno what to bind it to.
        self.rotation_vel = TuningData[2]

    def rotate(self, left=False, right=False):
        if left:
            self.angle += self.rotation_vel
        elif right:
            self.angle -= self.rotation_vel

    def draw(self, win):
        blit_rotate_center(win, self.img, (self.x, self.y), self.angle)

    def move_forward(self):
        self.vel = min(self.vel + self.acceleration, self.max_vel)
        self.move()

    def move_backward(self):
        self.vel = max(self.vel - self.acceleration, -self.max_vel / 2)
        self.move()

    def move(self):
        radians = math.radians(self.angle)
        vertical = math.cos(radians) * self.vel
        horizontal = math.sin(radians) * self.vel
        self.y -= vertical
        self.x -= horizontal

    def collide(self, mask, x=0, y=0):
        car_mask = pygame.mask.from_surface(self.img)
        car_mask = car_mask.scale(
            (int(car_mask.get_size()[0] * 0.85), int(car_mask.get_size()[1] * 0.85))
        )
        offset = (
            int(self.x - x + self.img.get_width() * 0.075),
            int(self.y - y + self.img.get_height() * 0.075),
        )
        return mask.overlap(car_mask, offset)

    def set_start_pos(self, pos):
        self.START_POS = pos

    def reset(self):
        self.x, self.y = self.START_POS
        self.angle = 0
        self.vel = 0
    
    def get_centre(self):
        w, h = self.img.get_size()
        return (self.x + w/2, self.y + h/2)

    def bounce(self):
        self.vel = -self.vel / 2
        self.move()

    def set_level(self, level):
        """
        Called when the level changes.
        Subclasses may override or extend.
        """
        pass
