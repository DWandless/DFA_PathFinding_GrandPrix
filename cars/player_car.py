from .abstract_car import AbstractCar
import math
import pygame


class PlayerCar(AbstractCar):
    """
    Player-controlled car with speed reduction capability.
    
    Can operate in two modes:
    - Manual mode (autonomous=False): Controlled by keyboard input, starts with vel=0
    - Autonomous mode (autonomous=True): Follows predefined path automatically, starts at max_vel
    """
    def __init__(self, img, start_pos, max_vel, rotation_vel, path=None, autonomous=False):
        super().__init__(img, start_pos, max_vel, rotation_vel)
        self.autonomous = autonomous
        self.path = path or []
        self.current_point = 0
        
        # Set initial velocity for autonomous mode
        if self.autonomous and self.path:
            self.vel = max_vel

    def reduce_speed(self):
        """Manual control method - reduces car speed."""
        self.vel = max(self.vel - self.acceleration / 2, 0)
        self.move()
    
    def position(self):
        return (self.x, self.y)
    
    # ===== Autonomous mode methods (similar to ComputerCar) =====
    
    def calculate_angle(self):
        """Calculate and adjust angle to face the current target point."""
        if not self.path or self.current_point >= len(self.path):
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
        """Advance to next path point when current target is reached."""
        if not self.path or self.current_point >= len(self.path):
            return
        
        from resources import CHECKPOINT_RADIUS
        
        target_x, target_y = self.path[self.current_point]
        distance_to_target = math.hypot(target_x - self.x, target_y - self.y)
        
        if distance_to_target < CHECKPOINT_RADIUS:
            self.current_point += 1
    
    def set_path(self, path):
        """Update the path for autonomous mode (used when level changes)."""
        self.path = path or []
        self.current_point = 0
    
    def next_level(self, level=None):
        """Reset car state for next level (maintains autonomous mode)."""
        self.reset()
        self.current_point = 0
        if self.autonomous:
            self.vel = self.max_vel

    def move(self):
        """Override move to handle both manual and autonomous modes."""
        if self.autonomous:
            # Autonomous mode: follow the path
            if self.current_point >= len(self.path):
                return
            
            # Maintain velocity in autonomous mode (recover from bounces)
            if self.vel < self.max_vel:
                self.vel = min(self.vel + self.acceleration * 2, self.max_vel)
            
            self.calculate_angle()
            self.update_path_point()
        
        # Call parent move method to apply velocity
        super().move()
