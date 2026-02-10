import math
import pygame
import heapq
from resources import raycast_mask, CHECKPOINT_RADIUS
from .abstract_car import AbstractCar


class GBFSDetourCar(AbstractCar):
    """
    Computer-controlled car that uses Greedy Best-First Search with detours
    to navigate through a grid-based track to reach checkpoints.
    """
    START_POS = (165, 200)

    def __init__(self, checkpoints, maxVel, maxRot, GRIDSIZE, WAYPOINT_REACH, CHECKPOINT_RADIUS, GRID, TRACK_BORDER_MASK, img):
        super().__init__(img, self.START_POS, maxVel, maxRot)
        
        # Basics
        self.checkpoints = checkpoints
        self.current_checkpoint = 0
        self.path = []
        self.current_point = 0
        self.vel = 3

        # Tunables Defaults (In order)
        self.max_vel = maxVel
        self.acceleration = 0.1
        self.rotation_vel = maxRot
        self.brake_factor = 0.6
        self.Lookahead_Dist = 32
        self.ahead_window = 50
        self.clearance_weight = 0.4
        self.detour_alpha = 0.5
        self.max_expansions = 50000
        self.Align_Angle = 30
        self.allow_diag = False
        

        # Map Specific
        self.GRIDSIZE = GRIDSIZE
        self.WAYPOINT_REACH = WAYPOINT_REACH
        self.CHECKPOINT_RADIUS = CHECKPOINT_RADIUS
        self.GRID = GRID
        self.TRACK_BORDER_MASK = TRACK_BORDER_MASK

        # Stuck detection
        self._last_dist = None
        self._stuck_frames = 0
        self._stuck_threshold = 45  # ~0.75s at 60 FPS
        self._frames_since_replan = 0  # Grace period after replan before checking collisions

    def SetTunables(self, TuningData):
        # Basic params
        self.max_vel = TuningData[0] # Speed
        self.acceleration = TuningData[1] # Acceleration
        self.rotation_vel = TuningData[2] # Steering
        self.brake_factor = TuningData[3] # Braking
        # GBFS specific params
        self.Lookahead_Dist = TuningData[4] # How far it looks ahead
        self.ahead_window = TuningData[5] # Reduces fixation and turning back
        self.clearance_weight = TuningData[6] # Higher = prefers open space, lower hugs tight lines, more crashes
        self.detour_alpha = TuningData[7] # Higher = detoures chose clearer neighbores
        self.max_expansions = TuningData[8] # Higher = more likely to find a path, lower = faster but can fail more
        self.Align_Angle = TuningData[9]
        self.allow_diag = bool(TuningData[10]) # Either 0 or 1 to represent true or false

    # ------------------ HELPERS ------------------
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
        For newly computed paths, prefer starting close to the beginning.
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
        # Start closer to current point to avoid jumping too far ahead
        start_i = max(0, self.current_point - 3)
        end_i = min(len(self.path), self.current_point + 20)  # Reduced from 50 to 20

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
        reach = max(self.WAYPOINT_REACH, self.CHECKPOINT_RADIUS)
        if d < reach:
            # Prefer advancing only when the checkpoint is ahead,
            # but allow advancing when we've clearly reached it (overshoot case).
            rad = math.radians(self.angle)
            fwd = (-math.sin(rad), -math.cos(rad))
            vx, vy = (cx - self.x, cy - self.y)
            proj = vx * fwd[0] + vy * fwd[1]

            if proj > 0 or d < (reach * 0.5):
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
        
        # Normalize desired_deg to [0, 360)
        desired_deg = desired_deg % 360
        
        # Normalize current angle to [0, 360)
        current_normalized = self.angle % 360
        
        # Calculate shortest rotation direction
        diff = (desired_deg - current_normalized + 180) % 360 - 180
        
        return current_normalized + diff  # Return the target angle directly, not delta

    # ------------------ MOVEMENT ------------------
    def bounce(self):
        self.vel = -self.vel
        super().move()
    
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
            allow_diag=self.allow_diag
        )
        
        if grid_path is None:
            pass

        if grid_path:
            self.path = [self.grid_to_world(gx, gy) for gx, gy in grid_path]
            # Start at beginning of new path, not using heading which is from previous checkpoint
            self.current_point = 0
        else:
            detour = self.smart_detour(goal_world)
            if detour:
                self.path = detour
                self.current_point = 0  # Start at beginning of detour path
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
                allow_diag=self.allow_diag
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
            self._frames_since_replan = 0  # Reset grace period
            # After recomputing path, don't immediately jump ahead - start fresh
            # Skip the _next_ahead_index() call this frame
            if not self.path:
                return

        # 2) Replan when path is missing/exhausted
        elif not self.path or self.current_point >= len(self.path):
            self.compute_path()
            if not self.path:
                return  # nothing to follow yet
        else:
            # Only call _next_ahead_index if we're continuing on the same path
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
            if accum >= self.Lookahead_Dist:
                px, py = tx, ty
                break
            idx += 1
        target_x, target_y = px, py
        self._dbg_target = (target_x, target_y)

        # 5) Advance raw waypoint if very close (keeps index moving forward)
        nxt_x, nxt_y = self.path[self.current_point]
        if math.hypot(nxt_x - self.x, nxt_y - self.y) < self.WAYPOINT_REACH:
            self.current_point = min(self.current_point + 1, len(self.path) - 1)

        # 6) Heading & speed gating (then tiny kick if stuck at zero)
        angle_to_target = self._desired_angle_to(target_x, target_y)
        angle_diff = (angle_to_target - self.angle + 180) % 360 - 180
        if angle_diff > 0:
            self.angle += min(self.rotation_vel, angle_diff)
        else:
            self.angle -= min(self.rotation_vel, -angle_diff)

        if abs(angle_diff) > self.Align_Angle:
            self.vel = max(self.vel - self.acceleration * self.brake_factor, 0)
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
        # But skip collision check for a few frames after replanning to let car orient
        if self._frames_since_replan > 5 and self.TRACK_BORDER_MASK.overlap(car_mask, (int(rotated_rect.left), int(rotated_rect.top))):
            detour = self.smart_detour(self.checkpoints[self.current_checkpoint])
            if detour:
                self.path = detour
                self.current_point = self._next_ahead_index()
                self._frames_since_replan = 0
                return
            else:
                self.compute_path()
                self._frames_since_replan = 0
                return
        
        self._frames_since_replan += 1

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
        
    def set_level(self, level):
        import resources
        self.checkpoints = resources.GBFS_RACING_LINE[:] + [resources.FINISH_POSITION]
        self.GRID = resources.GRID
        self.TRACK_BORDER_MASK = resources.TRACK_BORDER_MASK

        self.current_checkpoint = 0
        self.current_point = 0
        self.reset()
        self.compute_path()
