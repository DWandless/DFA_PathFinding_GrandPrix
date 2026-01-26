import math
import pygame
from resources import raycast_mask, CHECKPOINT_RADIUS
from .abstract_car import AbstractCar


class NEATCar(AbstractCar):
    """
    NEAT-controlled car that uses raycasting sensors to navigate a track.
    """
    def __init__(self, img, start_pos, max_vel, rotation_vel, checkpoints, track_mask, grid_size, grid, sensor_length=300):
        # Base init (image, spawn, dynamics)
        super().__init__(img, start_pos, max_vel, rotation_vel)

        # Environment references
        self.track_mask = track_mask
        self.grid_size = grid_size
        self.grid = grid
        self.checkpoints = checkpoints or []

        # NEAT I/O state
        self.sensor_length = sensor_length
        self.inputs = []             # 5 sensor distances + speed
        self.outputs = [0.0, 0.0]    # [steer, throttle]
        self.net = None
        self._sensor_cache = None    # list of (origin, end) tuples for drawing

        # Fitness
        self.fitness = 0.0
        self.next_checkpoint = 0
        self.stuck = False
        self.timeSinceLastCheckpoint = 0

        # Fixed relative angle for the "slight" sensors (±30° around forward)
        self._rel_slight = math.radians(30)

        # IMPORTANT: do NOT call sense() here; do it per-frame in your loop/manager.

    def SetTunables(self, TuningData):
        # Basic params
        self.max_vel = TuningData[0] # Speed
        self.acceleration = TuningData[1] # Acceleration
        self.rotation_vel = TuningData[2] # Steering
        self.brake_factor = TuningData[3] # Braking

    # ---------- geometry ----------
    def _basis_vectors(self):
        """
        Forward & left unit vectors consistent with AbstractCar.move():
        angle=0° points up; forward = (-sinθ, -cosθ), left = (-cosθ, +sinθ)
        """
        r = math.radians(self.angle)
        fwd  = (-math.sin(r), -math.cos(r))
        left = (-math.cos(r),  math.sin(r))
        return fwd, left

    def _anchors(self, inset_front=2.0, inset_side=2.0):
        """
        Distinct origins for the 5 sensors, computed from the sprite **center** (self.x, self.y):
          0 front nose, 1 front-left corner, 2 front-right corner,
          3 side-left midpoint, 4 side-right midpoint
        """
        cx, cy = self.get_centre()
        w, h = self.img.get_size()
        fwd, left = self._basis_vectors()
        right = (-left[0], -left[1])

        half_len = h/2 - inset_front
        half_wid = w/2 - inset_side

        front_nose = (cx + fwd[0]*half_len, cy + fwd[1]*half_len)
        side_left  = (cx + left[0]*half_wid,  cy + left[1]*half_wid)
        side_right = (cx + right[0]*half_wid, cy + right[1]*half_wid)

        # "Slight" sensors originate near front corners
        corner_scale_fwd = half_len * 0.9
        corner_scale_lat = half_wid * 0.9
        front_left_corner  = (cx + fwd[0]*corner_scale_fwd + left[0]*corner_scale_lat,
                              cy + fwd[1]*corner_scale_fwd + left[1]*corner_scale_lat)
        front_right_corner = (cx + fwd[0]*corner_scale_fwd + right[0]*corner_scale_lat,
                              cy + fwd[1]*corner_scale_fwd + right[1]*corner_scale_lat)

        return [
            front_nose,         # 0
            front_left_corner,  # 1
            front_right_corner, # 2
            side_left,          # 3
            side_right          # 4
        ]

    def _dir_rel(self, rel_rad):
        """dir = forward*cos(a) + left*sin(a)  (relative to forward)."""
        fwd, left = self._basis_vectors()
        ca, sa = math.cos(rel_rad), math.sin(rel_rad)
        return (fwd[0]*ca + left[0]*sa, fwd[1]*ca + left[1]*sa)

    def _fixed_dirs(self):
        """
        Direction vectors for the 5 sensors:
          front, slight-left (+30°), slight-right (-30°), side-left (90°), side-right (-90°).
        """
        fwd, left = self._basis_vectors()
        right = (-left[0], -left[1])
        return [
            fwd,                         # front
            self._dir_rel(+self._rel_slight),  # slight-left
            self._dir_rel(-self._rel_slight),  # slight-right
            left,                        # side-left
            right                        # side-right
        ]

    # ---------- sensing ----------
    def sense(self, track_mask, raycast_fn):
        """
        Cast 5 rays with distinct origins and cache endpoints for drawing.
        Returns NEAT inputs: 5 normalized distances + normalized speed.
        """
        origins = self._anchors()
        dirs = self._fixed_dirs()

        distances = []
        rays = []
        for origin, d in zip(origins, dirs):
            ang = math.atan2(d[1], d[0])  # raycaster convention: 0 along +X, CCW+
            res = raycast_fn(track_mask, origin, ang,
                             max_distance=self.sensor_length, step=3)

            dist = min(res['distance'], self.sensor_length)
            distances.append(dist / float(self.sensor_length))

            end = res['point'] if (res.get('hit') and res.get('point') is not None) \
                  else (origin[0] + d[0]*self.sensor_length,
                        origin[1] + d[1]*self.sensor_length)
            rays.append((origin, end))

        speed_norm = self.vel / self.max_vel if self.max_vel > 0.0 else 0.0
        self.inputs = distances + [speed_norm]
        self._sensor_cache = rays
        return self.inputs

    # ---------- NEAT ----------
    def set_net(self, net):
        self.net = net

    def think(self):
        if self.net:
            self.outputs = self.net.activate(self.inputs)

    def apply_controls(self):
        """
        Apply NEAT outputs using **AbstractCar's control methods**.
        (rotate, move_forward, reduce_speed come from the base class.)
        """
        steer, throttle = self.outputs
        if steer > 0.1:
            self.rotate(left=True)
        elif steer < -0.1:
            self.rotate(right=True)

        if throttle >= 0.6:
            self.vel = min(self.vel + self.acceleration, self.max_vel)

        elif throttle <= -0.2:
            self.vel = max(self.vel - self.acceleration, -self.max_vel / 2)

    def move(self):
        self.sense(self.track_mask, raycast_mask)
        self.think()
        self.apply_controls()
        super().move()

    # ---------- fitness ----------
   
    def update_fitness(self, on_road, dt, elapsed):
        self.timeSinceLastCheckpoint += dt
        # base shaping
        if on_road: self.fitness += (self.vel / max(1e-6, self.max_vel)) * dt
        else:       self.fitness -= 0.25 * dt
        # checkpoint milestones (pixel coords with optional radius)
        if self.next_checkpoint < len(self.checkpoints):
            cp = self.checkpoints[self.next_checkpoint]
            cx, cy = cp[:2]
            radius = CHECKPOINT_RADIUS
            if (self.x - cx)**2 + (self.y - cy)**2 <= radius**2:
                self.timeSinceLastCheckpoint = 0
                self.fitness += 2.0
                self.next_checkpoint += 1
        
        if self.timeSinceLastCheckpoint > 1.5:
            self.fitness -= 0.3*dt  # Small penalty for making no progress too long
        if self.timeSinceLastCheckpoint > 3:
            self.fitness -= 0.3*dt  # Small penalty for making no progress too long

    def draw(self, win, draw_sensors: bool = True):
        super().draw(win)

        for pt in self._anchors():
            pygame.draw.circle(win, (255, 165, 0), (int(pt[0]), int(pt[1])), 3)

        # draw sensors only when requested
        if draw_sensors:
            self._draw_sensors(win)

    def _draw_sensors(self, win):
        # Rays (from last sense())
        if self._sensor_cache:
            for origin, end in self._sensor_cache:
                pygame.draw.line(win, (0, 255, 0),
                                 (int(origin[0]), int(origin[1])),
                                 (int(end[0]),    int(end[1])), 2)

    def set_level(self, level):
        import resources
        self.path = resources.get_path_for_level(level)
        self.grid = resources.GRID
        self.track_mask = resources.TRACK_BORDER_MASK
        self.checkpoints = resources.PATH[:]

        self.next_checkpoint = 0
        self.reset()
        
    def bounce(self):
        self.vel = -self.vel
        super().move()
