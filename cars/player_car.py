from .abstract_car import AbstractCar


class PlayerCar(AbstractCar):
    """
    Player-controlled car with speed reduction capability.
    """
    def __init__(self, img, start_pos, max_vel, rotation_vel):
        super().__init__(img, start_pos, max_vel, rotation_vel)

    def reduce_speed(self):
        self.vel = max(self.vel - self.acceleration / 2, 0)
        self.move()
    
    def position(self):
        return (self.x, self.y)
