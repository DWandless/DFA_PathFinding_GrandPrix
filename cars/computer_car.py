from .abstract_car import AbstractCar


class ComputerCar(AbstractCar):
    """
    Simple computer-controlled car that follows a set, given path.
    """
    def __init__(self, img, start_pos, max_vel, rotation_vel, path=None):
        super().__init__(img, start_pos, max_vel, rotation_vel)
        self.path = path or []
        self.current_point = 0
        self.vel = max_vel
        self.autonomous = True  # Always autonomous

    def SetTunables(self, TuningData):
        # Add as many tunables as you like.
        self.max_vel = TuningData[0]
        self.acceleration = TuningData[1]
        # Breaking goes here -- dunno what to bind it to.
        self.rotation_vel = TuningData[2]

    def draw_points(self, win):  # draws the path points for debugging
        import pygame
        for point in self.path:
            pygame.draw.circle(win, (255, 0, 0), point, 2)

    def draw(self, win, show_points=True):  # shows the car and optionally the path points
        from resources import blit_rotate_center
        blit_rotate_center(win, self.img, (self.x, self.y), self.angle)
        if show_points:
            self.draw_points(win)

    def calculate_angle(self):
        import math
        if not self.path:
            return
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
        if not self.path:
            return
        target = self.path[self.current_point]
        import pygame
        rect = pygame.Rect(self.x, self.y, self.img.get_width(), self.img.get_height())
        if rect.collidepoint(*target):
            self.current_point = min(self.current_point + 1, len(self.path))

    def move(self):
        if self.current_point >= len(self.path):
            return
        self.calculate_angle()
        self.update_path_point()
        super().move()
    
    def next_level(self, level):  # this will be used for when the level changes to update the cars start position and speed
        self.reset()
        self.current_point = 0
        self.vel = self.max_vel + (level - 1) * 0.2  # increase speed each level

    def set_level(self, level):
        from resources import get_path_for_level
        self.path = get_path_for_level(level)
        self.current_point = 0
