import pygame, math
from utils import scale_image, bilt_rotate_center
from astar import astar
# -----------------------------
# CAR CLASSES
# -----------------------------

RED_CAR = scale_image(pygame.image.load('assets/red-car.png'), 0.55)
GREEN_CAR = scale_image(pygame.image.load('assets/green-car.png'), 0.55)
GRASS = scale_image(pygame.image.load('assets/grass.jpg'), 2.5)
TRACK = scale_image(pygame.image.load('assets/track.png'), 1)
TRACK_BORDER = scale_image(pygame.image.load('assets/track-border.png'), 1)
TRACK_BORDER_MASK = pygame.mask.from_surface(TRACK_BORDER)
FINISH = pygame.image.load('assets/finish.png')
FINISH_MASK = pygame.mask.from_surface(FINISH)


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
        w, h = self.img.get_size()
        self.centre_x = self.x + w / 2.0
        self.centre_y = self.y + h / 2.0
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

    def __init__(self, max_vel, rotation_vel, checkpoints, grid_size, grid):
        super().__init__(max_vel, rotation_vel)
        self.checkpoints = checkpoints
        self.current_checkpoint = 0
        self.path = []
        self.current_point = 0
        self.vel = max_vel
        self.grid_size = grid_size
        self.grid = grid

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
        return int(y // self.grid_size), int(x // self.grid_size)

    def grid_to_world(self, gx, gy):
        # Convert grid (row, col) to world (x, y) centered in the cell
        row, col = gx, gy
        x = col * self.grid_size + self.grid_size / 2
        y = row * self.grid_size + self.grid_size / 2
        return x, y

    def compute_path(self):
        """Compute a new grid path from current position to the current checkpoint.

        The A* result is converted to world coordinates centered in each
        grid cell using `grid_to_world` and stored in `self.path`.
        """
        start = self.world_to_grid(self.x, self.y)
        goal_world = self.checkpoints[self.current_checkpoint]
        goal = self.world_to_grid(*goal_world)
        grid_path = astar(self.grid, start, goal)
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



def raycast_mask(mask, origin, angle, max_distance=800, step=3):
    """
    Cast a ray in pixel space against a Pygame mask.

    Args:
        mask (pygame.Mask): Track mask. Nonzero pixels are obstacles/border.
        origin (tuple[int, int]): (x, y) starting point.
        angle (float): Ray angle in radians, 0 along +x, increasing counterclockwise.
        max_distance (float): Max length to cast (pixels).
        step (int): Step size in pixels. 2–4 is a good trade-off.

    Returns:
        dict with keys:
            'hit' (bool): True if hit border.
            'distance' (float): distance to hit or max_distance if no hit.
            'point' (tuple[int,int] or None): impact point if hit, else None.
            'samples' (int): number of iterations performed.
    """
    width, height = mask.get_size()
    ox, oy = origin
    dx = math.cos(angle)
    dy = math.sin(angle)

    # Early bounds check: if origin is outside, clamp ray to bounds
    # (optional; here we assume origin is valid)
    dist = 0.0
    samples = 0

    # Fast path: if starting on border, report distance 0
    if 0 <= ox < width and 0 <= oy < height and mask.get_at((ox, oy)) != 0:
        return {'hit': True, 'distance': 0.0, 'point': (ox, oy), 'samples': 0}

    while dist < max_distance:
        samples += 1
        # Increment position
        px = int(ox + dx * dist)
        py = int(oy + dy * dist)

        # If out of bounds, terminate with no hit
        if px < 0 or py < 0 or px >= width or py >= height:
            return {'hit': False, 'distance': dist, 'point': None, 'samples': samples}

        # Check border
        if mask.get_at((px, py)) != 0:
            # Optional: refine by binary search back one step for sub-pixel
            # but integer pixels are usually sufficient for sensors.
            return {'hit': True, 'distance': dist, 'point': (px, py), 'samples': samples}

        dist += step

    return {'hit': False, 'distance': max_distance, 'point': None, 'samples': samples}






class NEATCar(Car):
    IMG = GREEN_CAR
    START_POS = (165, 200)

    def __init__(self, max_vel, rotation_vel, checkpoints, grid_size, grid, sensor_length=300):
        super().__init__(max_vel, rotation_vel)
        self.grid_size = grid_size
        self.grid = grid
        self.checkpoints = checkpoints or []
        self.next_checkpoint = 0
        self.fitness = 0.0

        self.sensor_length = sensor_length
        self.inputs = []
        self.outputs = [0.0, 0.0]
        self.net = None
        self._sensor_cache = None

        # Fixed relative angles (radians)
        self._rel_slight = math.radians(30)   # ±30° around forward
        self._rel_side   = math.radians(90)   # ±90° left/right

        # Populate cache initially so sensors draw even before first sense()
        self.sense(TRACK_BORDER_MASK, raycast_mask)

    # ---------- geometry ----------
    def _basis_vectors(self):
        """Forward & left unit vectors consistent with Car.move() (angle=0 up)."""
        r = math.radians(self.angle)
        fwd  = (-math.sin(r), -math.cos(r))
        left = (-math.cos(r),  math.sin(r))
        return fwd, left

    def _anchors(self, inset_front=2.0, inset_side=2.0):
        """
        Compute distinct origins for the 5 sensors:
        - front: nose midpoint
        - slight-left/right: near front corners (forward + left/right)
        - side-left/right: side midpoints
        """
        w, h = self.img.get_size()
        fwd, left = self._basis_vectors()
        right = (-left[0], -left[1])

        half_len = h/2 - inset_front
        half_wid = w/2 - inset_side

        # Base anchors
        front_nose = (self.centre_x + fwd[0]*half_len, self.centre_y + fwd[1]*half_len)
        side_left  = (self.centre_x + left[0]*half_wid,  self.centre_y + left[1]*half_wid)
        side_right = (self.centre_x + right[0]*half_wid, self.centre_y + right[1]*half_wid)

        # Front corners (slight sensors originate closer to corners than center)
        # We push toward the corners using a blend of forward + lateral.
        corner_scale_fwd = half_len * 0.9
        corner_scale_lat = half_wid * 0.9
        front_left_corner  = (self.centre_x + fwd[0]*corner_scale_fwd + left[0]*corner_scale_lat,
                              self.centre_y + fwd[1]*corner_scale_fwd + left[1]*corner_scale_lat)
        front_right_corner = (self.centre_x + fwd[0]*corner_scale_fwd + right[0]*corner_scale_lat,
                              self.centre_y + fwd[1]*corner_scale_fwd + right[1]*corner_scale_lat)

        return {
            'front':        front_nose,
            'slight_left':  front_left_corner,
            'slight_right': front_right_corner,
            'side_left':    side_left,
            'side_right':   side_right,
        }

    # ---------- directions ----------
    def _dir_rel(self, rel_rad):
        """dir = forward*cos(a) + left*sin(a) (relative to forward)."""
        fwd, left = self._basis_vectors()
        ca, sa = math.cos(rel_rad), math.sin(rel_rad)
        return (fwd[0]*ca + left[0]*sa, fwd[1]*ca + left[1]*sa)

    def _fixed_dirs(self):
        """Return 5 normalized direction vectors for front, slight L/R, side L/R."""
        fwd, left = self._basis_vectors()
        right = (-left[0], -left[1])

        # Front
        d0 = fwd
        # Slight ±30°
        d1 = self._dir_rel(+self._rel_slight)  # slight left
        d2 = self._dir_rel(-self._rel_slight)  # slight right
        # Full side ±90°
        d3 = left
        d4 = right
        return [d0, d1, d2, d3, d4]

    # ---------- sensing ----------
    def sense(self, track_mask, raycast_fn):
        """
        Cast 5 rays with distinct origins:
          1) front_nose (0°)
          2) front_left_corner (+30°)
          3) front_right_corner (-30°)
          4) side_left (left 90°)
          5) side_right (right 90°)
        """
        anchors = self._anchors()
        dirs = self._fixed_dirs()
        origins = [
            anchors['front'],
            anchors['slight_left'],
            anchors['slight_right'],
            anchors['side_left'],
            anchors['side_right'],
        ]

        distances = []
        rays = []
        for origin, d in zip(origins, dirs):
            ang = math.atan2(d[1], d[0])  # raycaster: 0 along +X, CCW+
            res = raycast_fn(track_mask, origin, ang,
                             max_distance=self.sensor_length, step=3)

            dist = min(res['distance'], self.sensor_length)
            distances.append(dist / float(self.sensor_length))

            # endpoint for drawing
            if res.get('hit') and res.get('point') is not None:
                end = res['point']
            else:
                end = (origin[0] + d[0]*self.sensor_length,
                       origin[1] + d[1]*self.sensor_length)

            rays.append((origin, end))

        # inputs: 5 sensor distances + speed
        speed_norm = self.vel / self.max_vel if self.max_vel > 0 else 0.0
        self.inputs = distances + [speed_norm]
        self._sensor_cache = rays
        return self.inputs

    # ---------- NEAT ----------
    def set_net(self, net): self.net = net
    def think(self):
        if self.net: self.outputs = self.net.activate(self.inputs)
    def apply_controls(self):
        steer, throttle = self.outputs
        if steer > 0.1: self.rotate(left=True)
        elif steer < -0.1: self.rotate(right=True)
        if throttle >= 0.6: self.move_forward()
        elif throttle <= 0.3: self.reduce_speed()

    # ---------- fitness ----------
    def update_fitness(self, on_road, dt):
        if on_road: self.fitness += (self.vel / max(1e-6, self.max_vel)) * dt
        else:       self.fitness -= 0.25 * dt
        if self.next_checkpoint < len(self.checkpoints):
            cp = self.checkpoints[self.next_checkpoint]
            cx, cy = cp[:2]
            radius = cp[2] if len(cp) > 2 else self.grid_size * 0.75
            if (self.x - cx)**2 + (self.y - cy)**2 <= radius**2:
                self.fitness += 10.0
                self.next_checkpoint += 1

    # ---------- drawing ----------
    def draw(self, win):
        bilt_rotate_center(win, self.img, (self.x, self.y), self.angle)
        # draw anchors (optional, helpful for debug)
        a = self._anchors()
        for pt in (a['front'], a['slight_left'], a['slight_right'], a['side_left'], a['side_right']):
            pygame.draw.circle(win, (255, 165, 0), (int(pt[0]), int(pt[1])), 3)
        # draw rays
        if self._sensor_cache:
            for origin, end in self._sensor_cache:
                pygame.draw.line(win, (0, 255, 0),
                                 (int(origin[0]), int(origin[1])),
                                 (int(end[0]),    int(end[1])), 2)
                pygame.draw.circle(win, (0, 255, 0), (int(end[0]), int(end[1])), 2)


