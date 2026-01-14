import math
import pygame
from resources import blit_rotate_center
import heapq
from resources import raycast_mask, PATH


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

    def rotate(self, left=False, right=False):
        if left:
            self.angle += self.rotation_vel
        elif right:
            self.angle -= self.rotation_vel

    def draw(self, win):
        blit_rotate_center(win, self.img, (self.x, self.y), self.angle)

    def move_forward(self):
        self.vel = min(self.vel + self.acceleration, self.max_vel)
        self.move() # readded self.move() call here

    def move_backward(self):
        self.vel = max(self.vel - self.acceleration, -self.max_vel / 2)
        self.move() # readded self.move() call here

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

    def reset(self):
        self.x, self.y = self.START_POS
        self.angle = 0
        self.vel = 0
    def get_centre(self):
        w,h = self.img.get_size()
        return (self.x + w/2, self.y + h/2)


class PlayerCar(AbstractCar):
    def __init__(self, img, start_pos, max_vel, rotation_vel):
        super().__init__(img, start_pos, max_vel, rotation_vel)

    def reduce_speed(self):
        self.vel = max(self.vel - self.acceleration / 2, 0)
        self.move()

    def bounce(self):
        self.vel = -self.vel / 2
        self.move()


class ComputerCar(AbstractCar):
    def __init__(self, img, start_pos, max_vel, rotation_vel, path=None):
        super().__init__(img, start_pos, max_vel, rotation_vel)
        self.path = path or []
        self.current_point = 0
        self.vel = max_vel

    def draw_points(self, win): # draws the path points for debugging
        for point in self.path:
            pygame.draw.circle(win, (255, 0, 0), point, 2)

    def draw(self, win, show_points=True): # shows the car and optionally the path points
        blit_rotate_center(win, self.img, (self.x, self.y), self.angle)
        if show_points:
            self.draw_points(win)

    def calculate_angle(self):
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
        rect = pygame.Rect(self.x, self.y, self.img.get_width(), self.img.get_height())
        if rect.collidepoint(*target):
            self.current_point = min(self.current_point + 1, len(self.path))

    def move(self):
        if self.current_point >= len(self.path):
            return
        self.calculate_angle()
        self.update_path_point()
        super().move()
    
    def next_level(self, level): # this will be used for when the level changes to update the cars start position and speed
        self.reset()
        self.current_point = 0
        self.vel = self.max_vel + (level - 1) * 0.2# increase speed each level

class GBFSDetourCar(AbstractCar):
    START_POS = (165, 200)
    LOOKAHEAD_DIST = 35      # pixels ahead along path to aim at
    ALIGN_ANGLE = 30          # degrees; slow down when misaligned by more than this

    def __init__(self, max_vel, rotation_vel, checkpoints, GRIDSIZE, WAYPOINT_REACH, CHECKPOINT_RADIUS, GRID, TRACK_BORDER_MASK, img, allow_diag=True, clearance_weight=0.4, detour_alpha=0.5, ):
        super().__init__(img, self.START_POS, max_vel, rotation_vel)
        self.checkpoints = checkpoints
        self.current_checkpoint = 0
        self.path = []
        self.current_point = 0
        self.vel = max_vel
        self.allow_diag = allow_diag
        self.clearance_weight = clearance_weight
        self.detour_alpha = detour_alpha
        w, h = self.img.get_size()
        self.center_x = self.x + w / 2.0
        self.center_y = self.y + h / 2.0

        self.GRIDSIZE = GRIDSIZE
        self.WAYPOINT_REACH = WAYPOINT_REACH
        self.CHECKPOINT_RADIUS = CHECKPOINT_RADIUS
        self.GRID = GRID
        self.TRACK_BORDER_MASK = TRACK_BORDER_MASK

        self._last_dist = None
        self._stuck_frames = 0
        self._stuck_threshold = 45  # ~0.75s at 60 FPS

    def bounce(self):
        self.vel = -self.vel
        super().move()

    def greedy_best_first(self, start, goal, allow_diag=True, clearance_weight=0.4, max_expansions=50000):
        """
        Pure Greedy Best-First Search (no path cost), biased by local clearance.

        Priority = h(n, goal) - clearance_weight * clearance(n)

        Returns: list of (row, col) nodes from start(exclusive) -> goal(inclusive), or None.
        """
        rows, cols = len(self.GRID), len(self.GRID[0])

        def grid_to_world(rc):
            r, c = rc
            x = c * self.GRIDSIZE + self.GRIDSIZE / 2
            y = r * self.GRIDSIZE + self.GRIDSIZE / 2
            return x, y

        def local_clearance(rc, radius=6, step=2):
            x, y = grid_to_world(rc)
            width, height = self.TRACK_BORDER_MASK.get_size()
            hits, samples = 0, 0
            ix, iy = int(x), int(y)
            for dx in range(-radius, radius+1, step):
                for dy in range(-radius, radius+1, step):
                    sx, sy = ix + dx, iy + dy
                    if 0 <= sx < width and 0 <= sy < height:
                        samples += 1
                        if self.TRACK_BORDER_MASK.get_at((sx, sy)) != 0:
                            hits += 1
            return 0.0 if samples == 0 else (1.0 - hits / samples)

        def neighbors4(r, c):
            return [(r+1,c), (r-1,c), (r,c+1), (r,c-1)]

        def neighbors8_safe(r, c):
            """
            Diagonals allowed only if both adjacent orthogonals are open (prevents corner cutting).
            """
            cand = [(r+1,c), (r-1,c), (r,c+1), (r,c-1)]
            diags = [
                (r+1,c+1, (r+1,c), (r,c+1)),
                (r+1,c-1, (r+1,c), (r,c-1)),
                (r-1,c+1, (r-1,c), (r,c+1)),
                (r-1,c-1, (r-1,c), (r,c-1)),
            ]
            res = []
            for nr, nc in cand:
                if 0 <= nr < rows and 0 <= nc < cols and self.GRID[nr][nc]:
                    res.append((nr, nc))
            for (nr, nc, o1, o2) in diags:
                if (0 <= nr < rows and 0 <= nc < cols and
                    self.GRID[nr][nc] and
                    0 <= o1[0] < rows and 0 <= o1[1] < cols and self.GRID[o1[0]][o1[1]] and
                    0 <= o2[0] < rows and 0 <= o2[1] < cols and self.GRID[o2[0]][o2[1]]):
                    res.append((nr, nc))
            return res

        neigh_fn = neighbors8_safe if allow_diag else neighbors4

        open_set = []
        visited = set([start])
        h0 = abs(start[0] - goal[0]) + abs(start[1] - goal[1])
        p0 = h0 - clearance_weight * local_clearance(start)
        heapq.heappush(open_set, (p0, start))
        came_from = {}

        expansions = 0
        while open_set and expansions < max_expansions:
            _, current = heapq.heappop(open_set)
            expansions += 1

            if current == goal:
                path = []
                while current in came_from:
                    path.append(current)
                    current = came_from[current]
                path.reverse()
                return path

            r, c = current
            for nr, nc in neigh_fn(r, c):
                if (nr, nc) not in visited:
                    visited.add((nr, nc))
                    h = abs(nr - goal[0]) + abs(nc - goal[1])
                    p = h - clearance_weight * local_clearance((nr, nc))
                    heapq.heappush(open_set, (p, (nr, nc)))
                    came_from[(nr, nc)] = current

        return None

    def nearest_walkable(self, start_rc, max_radius=80):
        rows, cols = len(self.GRID), len(self.GRID[0])
        sr, sc = start_rc

        if 0 <= sr < rows and 0 <= sc < cols and self.GRID[sr][sc]:
            return (sr, sc)

        # simple queue without deque
        q = [(sr, sc, 0)]
        seen = {(sr, sc)}
        head = 0

        while head < len(q):
            r, c, d = q[head]
            head += 1
            if d > max_radius:
                break

            for nr, nc in ((r+1,c),(r-1,c),(r,c+1),(r,c-1)):
                if 0 <= nr < rows and 0 <= nc < cols and (nr, nc) not in seen:
                    if self.GRID[nr][nc]:
                        return (nr, nc)
                    seen.add((nr, nc))
                    q.append((nr, nc, d+1))

        return start_rc

    def world_to_grid(self, x, y):
        return int(y // self.GRIDSIZE), int(x // self.GRIDSIZE)

    def grid_to_world(self, gx, gy):
        x = gy * self.GRIDSIZE + self.GRIDSIZE / 2
        y = gx * self.GRIDSIZE + self.GRIDSIZE / 2
        return x, y

    def _clearance_at(self, x, y, radius=6, step=2):
        width, height = self.TRACK_BORDER_MASK.get_size()
        hits, samples = 0, 0
        ix, iy = int(x), int(y)
        for dx in range(-radius, radius+1, step):
            for dy in range(-radius, radius+1, step):
                sx, sy = ix + dx, iy + dy
                if 0 <= sx < width and 0 <= sy < height:
                    samples += 1
                    if self.TRACK_BORDER_MASK.get_at((sx, sy)) != 0:
                        hits += 1
        return 0.0 if samples == 0 else (1.0 - hits / samples)

    def _neighbor_candidates(self, start_grid, goal_grid):
        rows, cols = len(self.GRID), len(self.GRID[0])
        sx, sy = start_grid
        if self.allow_diag:
            neighs = [
                (sx+1,sy), (sx-1,sy), (sx,sy+1), (sx,sy-1),
                (sx+1,sy+1), (sx+1,sy-1), (sx-1,sy+1), (sx-1,sy-1)
            ]
        else:
            neighs = [(sx+1,sy), (sx-1,sy), (sx,sy+1), (sx,sy-1)]

        scored = []
        for nr, nc in neighs:
            if 0 <= nr < rows and 0 <= nc < cols and self.GRID[nr][nc]:
                h = abs(nr - goal_grid[0]) + abs(nc - goal_grid[1])
                wx, wy = self.grid_to_world(nr, nc)
                clear = self._clearance_at(wx, wy)
                # lower priority is better: closer & clearer
                priority = h - (self.detour_alpha * clear * 10.0)
                scored.append((priority, clear, h, (nr, nc)))
        scored.sort(key=lambda t: t[0])
        return [rc for _, _, _, rc in scored]

    def _next_ahead_index(self):
        """
        Return the index of the nearest path waypoint that is 'ahead' of the car
        in heading space (positive projection onto forward direction).
        Prevents turning back to points behind.
        """
        
        if not self.path:
            return 0

        # Ensure current_point is valid before scanning
        if self.current_point < 0:
            self.current_point = 0
        if self.current_point >= len(self.path):
            self.current_point = len(self.path) - 1


        # Car forward unit vector (sprite faces up -> angle 0 is forward up)
        rad = math.radians(self.angle)
        fwd = (-math.sin(rad), -math.cos(rad))  # (fx, fy) forward direction

        best_idx = self.current_point
        best_dist = float('inf')
        cx, cy = self.x, self.y

        # Search a window to avoid scanning whole path
        start_i = max(0, self.current_point - 3)
        end_i = min(len(self.path), self.current_point + 50)

        for i in range(start_i, end_i):
            px, py = self.path[i]
            vx, vy = (px - cx, py - cy)
            proj = vx * fwd[0] + vy * fwd[1]  # forward component
            if proj <= 0:
                continue  # behind or lateral -> ignore
            d = math.hypot(vx, vy)
            if d < best_dist:
                best_dist = d
                best_idx = i

        return best_idx
    
    def _forward_vector(self):
        """Unit forward vector for the car given sprite convention (0° faces up)."""
        rad = math.radians(self.angle)
        # With your sprite, moving forward is 'up', so forward vector is (-sin, -cos)
        return (-math.sin(rad), -math.cos(rad))

    def _advance_checkpoint_if_reached(self):
        cx, cy = self.checkpoints[self.current_checkpoint]
        d = math.hypot(cx - self.x, cy - self.y)
        if d < max(self.CHECKPOINT_RADIUS, self.CHECKPOINT_RADIUS):
            # print("Reached checkpoint!")
            # Only advance if it is ahead in heading space
            rad = math.radians(self.angle)
            fwd = (-math.sin(rad), -math.cos(rad))
            vx, vy = (cx - self.x, cy - self.y)
            proj = vx * fwd[0] + vy * fwd[1]
            if proj > 0:
                self.current_checkpoint = (self.current_checkpoint + 1) % len(self.checkpoints)
                return True
        return False
    
    def _desired_angle_to(self, tx, ty):
        """
        Compute the sprite angle that aligns the car's forward movement with the target (tx, ty).
        Car's forward step is (-sin(a), -cos(a)), so we solve for 'a' that matches the
        normalized vector from the car to the target.
        """
        vx = tx - self.x
        vy = ty - self.y
        d = math.hypot(vx, vy)
        if d < 1e-6:
            return self.angle  # already there
        fx, fy = vx / d, vy / d  # desired forward unit

        # We want (-sin(a), -cos(a)) ≈ (fx, fy)
        # -> sin(a) = -fx ; cos(a) = -fy
        # -> a = atan2(sin(a), cos(a)) = atan2(-fx, -fy)
        desired_rad = math.atan2(-fx, -fy)
        desired_deg = math.degrees(desired_rad)
        # normalize to [-180, 180) relative to current angle when you compute diff
        return desired_deg

    def compute_path(self):
        start = self.world_to_grid(self.x, self.y)
        goal_world = self.checkpoints[self.current_checkpoint]
        goal = self.world_to_grid(*goal_world)

        # NEW: snap both to nearest free cell so GBFS has a chance
        start = self.nearest_walkable(start, max_radius=120)
        goal  = self.nearest_walkable(goal,  max_radius=120)
        
        if not self.GRID[start[0]][start[1]] or not self.GRID[goal[0]][goal[1]]:
            print("Start/Goal blocked even after snapping:", start, goal)

        grid_path = self.greedy_best_first(
            start, goal,
            allow_diag=self.allow_diag, clearance_weight=self.clearance_weight
        )
        
        if grid_path is None:
            print("GBFS failed at checkpoint", self.current_checkpoint, "start", start, "goal", goal)

        if grid_path:
            self.path = [self.grid_to_world(gx, gy) for gx, gy in grid_path]
            self.current_point = self._next_ahead_index()
        else:
            detour = self.smart_detour(goal_world)
            if detour:
                self.path = detour
                self.current_point = self._next_ahead_index()
            else:
                self.path = []
                self.current_point = 0
            
    def smart_detour(self, goal_world):
        """
        GBFS-only smart detour:
        - pick a neighbor that is either closer or much clearer,
        - GBFS from that neighbor to the goal,
        - prepend a micro step to that neighbor in world space.
        """
        start_grid = self.world_to_grid(self.x, self.y)
        goal_grid = self.world_to_grid(*goal_world)

        candidates = self._neighbor_candidates(start_grid, goal_grid)
        if not candidates:
            return None

        K = 4  # try top-K candidates
        for pick in candidates[:K]:
            rest = self.greedy_best_first(
                pick, goal_grid,
                allow_diag=self.allow_diag, clearance_weight=self.clearance_weight
            )
            if rest:
                micro_world = [self.grid_to_world(*pick)]
                rest_world = [self.grid_to_world(gx, gy) for gx, gy in rest]
                return micro_world + rest_world

        # No full greedy path; still take one micro step to shake out
        best = candidates[0]
        return [self.grid_to_world(*best)]

    def move(self):

        # 1) Advance checkpoint if truly reached and ahead; replan but keep moving
        advanced = self._advance_checkpoint_if_reached()
        if advanced:
            self.compute_path()

        # 2) Replan when path is missing/exhausted
        if not self.path or self.current_point >= len(self.path):
            self.compute_path()
            if not self.path:
                return  # nothing to follow yet
        # 3) Choose nearest forward waypoint (prevents turn-back)
        self.current_point = self._next_ahead_index()

        if not self.path:
            self.compute_path()
            if not self.path:
                return

        self.current_point = max(0, min(self.current_point, len(self.path) - 1))

        # 4) Pure-pursuit lookahead from current_point forward
        idx = self.current_point
        px, py = self.path[idx]
        accum = 0.0
        lastx, lasty = self.x, self.y
        while idx < len(self.path):
            tx, ty = self.path[idx]
            d = math.hypot(tx - lastx, ty - lasty)
            accum += d
            lastx, lasty = tx, ty
            if accum >= self.LOOKAHEAD_DIST:
                px, py = tx, ty
                break
            idx += 1
        target_x, target_y = px, py
        self._dbg_target = (target_x, target_y)

        # 5) Advance raw waypoint if very close (keeps index moving forward)
        nxt_x, nxt_y = self.path[self.current_point]
        if math.hypot(nxt_x - self.x, nxt_y - self.y) < self.CHECKPOINT_RADIUS:
            self.current_point = min(self.current_point + 1, len(self.path) - 1)

        # 6) Heading & speed gating (then tiny kick if stuck at zero)
        angle_to_target = self._desired_angle_to(target_x, target_y)
        angle_diff = (angle_to_target - self.angle + 180) % 360 - 180
        if angle_diff > 0:
            self.angle += min(self.rotation_vel, angle_diff)
        else:
            self.angle -= min(self.rotation_vel, -angle_diff)

        if abs(angle_diff) > self.ALIGN_ANGLE:
            self.vel = max(self.vel - self.acceleration * 0.6, 0)
        else:
            self.vel = min(self.vel + self.acceleration, self.max_vel)
        if self.vel <= 0.01:
            self.vel = min(self.acceleration, self.max_vel)

        # 7) Predict next position; handle border (detour/replan); ignore finish here
        radians = math.radians(self.angle)
        vertical = math.cos(radians) * self.vel
        horizontal = math.sin(radians) * self.vel
        predicted_y = self.y - vertical
        predicted_x = self.x - horizontal

        
        orig_rect = self.img.get_rect(topleft=(predicted_x, predicted_y))
        rotated_img = pygame.transform.rotate(self.img, self.angle)
        rotated_rect = rotated_img.get_rect(center=orig_rect.center)
        car_mask = pygame.mask.from_surface(rotated_img)

        # Border collision predicted -> detour or replan (GBFS-only)
        if self.TRACK_BORDER_MASK.overlap(car_mask, (int(rotated_rect.left), int(rotated_rect.top))):
            detour = self.smart_detour(self.checkpoints[self.current_checkpoint])
            if detour:
                self.path = detour
                self.current_point = self._next_ahead_index()
                return
            else:
                self.compute_path()
                return

        # --- STUCK RESOLUTION ---
        d_to_lookahead = math.hypot(target_x - self.x, target_y - self.y)
        if self._last_dist is not None and d_to_lookahead >= self._last_dist - 0.1:
            self._stuck_frames += 1
        else:
            self._stuck_frames = 0
        self._last_dist = d_to_lookahead

        if self._stuck_frames >= self._stuck_threshold:
            detour = self.smart_detour(self.checkpoints[self.current_checkpoint])
            if detour:
                self.path = detour
                self.current_point = 0
                self._stuck_frames = 0
                self.vel = min(self.vel + self.acceleration, self.max_vel)
                return
            else:
                self.vel = max(self.vel - self.acceleration * 0.5, 0)

        # Move if safe
        super().move()


class NEATCar(AbstractCar):
    def __init__(self, img, start_pos, max_vel, rotation_vel,
                 checkpoints, track_mask, grid_size, grid, sensor_length=300):
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

        # Fixed relative angle for the “slight” sensors (±30° around forward)
        self._rel_slight = math.radians(30)

        # IMPORTANT: do NOT call sense() here; do it per-frame in your loop/manager.

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

        # “Slight” sensors originate near front corners
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
        Apply NEAT outputs using **AbstractCar’s control methods**.
        (rotate, move_forward, reduce_speed come from the base class.)
        """
        steer, throttle = self.outputs
        if steer > 0.1:
            self.rotate(left=True)
        elif steer < -0.1:
            self.rotate(right=True)

        if throttle >= 0.6:
            #self.move_forward()
            self.vel = min(self.vel + self.acceleration, self.max_vel)
            radians = math.radians(self.angle)
            vertical = math.cos(radians) * self.vel
            horizontal = math.sin(radians) * self.vel
            self.y -= vertical
            self.x -= horizontal
            # Manually included move logic here to avoid recursive move calls

        #elif throttle <= 0: causing car to move back indefinitely
            #self.move_backward()
        # else: coast (no change this frame)

    def move(self):
        self.sense(self.track_mask, raycast_mask)
        self.think()
        self.apply_controls()
        super().move()
    # ---------- fitness ----------
    def update_fitness(self, on_road, dt):
        # Base shaping
        if on_road:
            self.fitness += (self.vel / max(1e-6, self.max_vel)) * dt
        else:
            self.fitness -= 0.25 * dt

        # Checkpoint milestones (pixel coords with optional radius)
        if self.next_checkpoint < len(self.checkpoints):
            cp = self.checkpoints[self.next_checkpoint]
            cx, cy = cp[:2]
            radius = cp[2] if len(cp) > 2 else self.grid_size * 0.75
            # Using center (self.x, self.y)
            dx, dy = self.x - cx, self.y - cy
            if dx*dx + dy*dy <= radius*radius:
                self.fitness += 10.0
                self.next_checkpoint += 1

    # ---------- drawing ----------
    def draw(self, win):
        super().draw(win)

        # Anchors (optional debug dots)
        for pt in self._anchors():
            pygame.draw.circle(win, (255, 165, 0), (int(pt[0]), int(pt[1])), 3)

        # Rays (from last sense())
        if self._sensor_cache:
            for origin, end in self._sensor_cache:
                pygame.draw.line(win, (0, 255, 0),
                                 (int(origin[0]), int(origin[1])),
                                 (int(end[0]),    int(end[1])), 2)
                pygame.draw.circle(win, (0, 255, 0), (int(end[0]), int(end[1])), 2)
    
    def bounce(self):
        self.vel = -self.vel
        super().move()

class DijkstraCar(AbstractCar):
    def __init__(self, img, start_pos, max_vel, rotation_vel,
                 path, grid_size=None, waypoint_reach=10,
                 checkpoint_radius=None, grid=None,
                 track_border_mask=None, loop=True):
        super().__init__(img, start_pos, max_vel, rotation_vel)
        self.PATH = path
        self.WAYPOINT_REACH = waypoint_reach
        self.TRACK_BORDER_MASK = track_border_mask
        self.loop = loop

        self.vel = max_vel
        self.current_point = 0
        self.path = self.PATH[:]
        self.current_point = self._nearest_waypoint_index()

    # ------------------ HELPERS ------------------
    def _nearest_waypoint_index(self):
        cx, cy = self.x, self.y
        best_i, best_d = 0, float("inf")
        for i, (px, py) in enumerate(self.PATH):
            d = math.hypot(px - cx, py - cy)
            if d < best_d:
                best_d = d
                best_i = i
        return best_i

    # ------------------ MOVEMENT ------------------
    def calculate_angle(self, target_x, target_y):
    # Compute vector from car to target
        dx = target_x - self.x
        dy = target_y - self.y

        # In screen coords: 0 deg = up, 90 deg = right
        desired = math.degrees(math.atan2(dx, -dy))  # note the negative dy
        diff = (desired - self.angle + 180) % 360 - 180

        if diff > 0:
            self.angle += min(self.rotation_vel, diff)
        else:
            self.angle -= min(self.rotation_vel, -diff)

        self.angle %= 360

    def move(self):
        if self.current_point >= len(self.path):
            return

        tx, ty = self.path[self.current_point]

        # Rotate toward next waypoint
        self.calculate_angle(tx, ty)
    
        # Stepwise movement to avoid embedding in walls
        steps = max(int(self.vel), 1)
        rad = math.radians(self.angle)
        for i in range(1, steps + 1):
            step_size = self.vel / steps
            test_x = self.x + math.sin(rad) * step_size
            test_y = self.y - math.cos(rad) * step_size

            if self.TRACK_BORDER_MASK.get_at((int(test_x), int(test_y))) == 0:
                self.x = test_x
                self.y = test_y
            else:
                break

        # Update waypoint after movement
        if math.hypot(tx - self.x, ty - self.y) < self.WAYPOINT_REACH:
            self.current_point += 1
            if self.loop:
                self.current_point %= len(self.path)

    # ------------------ DEBUG DRAW ------------------
    def draw(self, win, show_points=True):
        blit_rotate_center(win, self.img, (self.x, self.y), -self.angle)
        if show_points:
            for p in self.path:
                pygame.draw.circle(win, (0, 0, 255), p, 3)
            if self.current_point < len(self.path):
                tx, ty = self.path[self.current_point]
                pygame.draw.circle(win, (0, 255, 0), (int(tx), int(ty)), 5)