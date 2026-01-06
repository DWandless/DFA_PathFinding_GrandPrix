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
# GRID FOR GBFS
# -----------------------------
GRID_SIZE = 4  # pixels per grid cell
CHECKPOINT_RADIUS = 8
LOOKAHEAD_DIST = 35      # pixels ahead along path to aim at
WAYPOINT_REACH = 12       # radius to consider a waypoint reached
ALIGN_ANGLE = 30          # degrees; slow down when misaligned by more than this

def build_grid_overlay(grid, cell_color=(0, 255, 0, 50), wall_color=(255, 0, 0, 80), step=4):
    """
    Create a semi-transparent surface visualizing the grid.

    - grid: list-of-lists of booleans (True=walkable, False=blocked).
    - cell_color: RGBA for walkable cells.
    - wall_color: RGBA for blocked cells (track borders).
    - step: draw every `step`th cell to reduce cost (use step=1 for full resolution).
    Returns: Pygame surface with per-cell rectangles.

    NOTE: With GRID_SIZE=1, drawing every pixel is heavy. step=4 is a good compromise.
    """
    rows, cols = len(grid), len(grid[0])
    surf = pygame.Surface((cols * GRID_SIZE, rows * GRID_SIZE), pygame.SRCALPHA)
    cell_w = GRID_SIZE
    cell_h = GRID_SIZE

    # Pre-build small rect surfaces for faster blitting
    walk_surf = pygame.Surface((cell_w, cell_h), pygame.SRCALPHA)
    wall_surf = pygame.Surface((cell_w, cell_h), pygame.SRCALPHA)
    walk_surf.fill(cell_color)
    wall_surf.fill(wall_color)

    for r in range(0, rows, step):
        for c in range(0, cols, step):
            x = c * GRID_SIZE
            y = r * GRID_SIZE
            if grid[r][c]:
                surf.blit(walk_surf, (x, y))
            else:
                surf.blit(wall_surf, (x, y))
    return surf

def build_grid(mask, clearance_px=0, sample_step=2):
    """
    clearance_px: inflate walls by this many pixels (configuration space).
    sample_step: higher is faster but less accurate (2 is fine).
    """
    width, height = mask.get_size()
    grid = []

    # Precompute offsets inside a disk for speed
    offsets = []
    if clearance_px > 0:
        r = clearance_px
        r2 = r * r
        for dy in range(-r, r + 1, sample_step):
            for dx in range(-r, r + 1, sample_step):
                if dx*dx + dy*dy <= r2:
                    offsets.append((dx, dy))

    for y in range(0, height, GRID_SIZE):
        row = []
        for x in range(0, width, GRID_SIZE):
            # Base point check
            if mask.get_at((x, y)) != 0:
                row.append(False)
                continue

            # Clearance check
            ok = True
            if clearance_px > 0:
                for dx, dy in offsets:
                    sx, sy = x + dx, y + dy
                    if 0 <= sx < width and 0 <= sy < height:
                        if mask.get_at((sx, sy)) != 0:
                            ok = False
                            break
            row.append(ok)
        grid.append(row)
    return grid

CAR_CLEARANCE = int(max(GREEN_CAR.get_width(), GREEN_CAR.get_height()) * 0.5) + 2 # Approx "collision radius" in pixels: half car width + a safety margin
GRID = build_grid(TRACK_BORDER_MASK, clearance_px=CAR_CLEARANCE, sample_step=max(2, GRID_SIZE//2))
GRID_OVERLAY = build_grid_overlay(GRID, cell_color=(0, 255, 0, 40), wall_color=(255, 0, 0, 70), step=4)
SHOW_GRID = False  # start visible; you can toggle with a key
# -----------------------------
# GBFS PATHFINDING
# -----------------------------
def heuristic(a, b):

    return math.sqrt((abs(a[0] - b[0])**2) + (abs(a[1] - b[1])**2))

def nearest_walkable(grid, start_rc, max_radius=80):
    rows, cols = len(grid), len(grid[0])
    sr, sc = start_rc

    if 0 <= sr < rows and 0 <= sc < cols and grid[sr][sc]:
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
                if grid[nr][nc]:
                    return (nr, nc)
                seen.add((nr, nc))
                q.append((nr, nc, d+1))

    return start_rc

def greedy_best_first(grid, start, goal, mask, grid_size=GRID_SIZE, allow_diag=True, clearance_weight=0.4, max_expansions=50000):
    """
    Pure Greedy Best-First Search (no path cost), biased by local clearance.

    Priority = h(n, goal) - clearance_weight * clearance(n)

    Returns: list of (row, col) nodes from start(exclusive) -> goal(inclusive), or None.
    """
    rows, cols = len(grid), len(grid[0])

    def grid_to_world(rc):
        r, c = rc
        x = c * grid_size + grid_size / 2
        y = r * grid_size + grid_size / 2
        return x, y

    def local_clearance(rc, radius=6, step=2):
        x, y = grid_to_world(rc)
        width, height = mask.get_size()
        hits, samples = 0, 0
        ix, iy = int(x), int(y)
        for dx in range(-radius, radius+1, step):
            for dy in range(-radius, radius+1, step):
                sx, sy = ix + dx, iy + dy
                if 0 <= sx < width and 0 <= sy < height:
                    samples += 1
                    if mask.get_at((sx, sy)) != 0:
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
            if 0 <= nr < rows and 0 <= nc < cols and grid[nr][nc]:
                res.append((nr, nc))
        for (nr, nc, o1, o2) in diags:
            if (0 <= nr < rows and 0 <= nc < cols and
                grid[nr][nc] and
                0 <= o1[0] < rows and 0 <= o1[1] < cols and grid[o1[0]][o1[1]] and
                0 <= o2[0] < rows and 0 <= o2[1] < cols and grid[o2[0]][o2[1]]):
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
        """
        Collision using rotated sprite mask.
        x,y = world position of the mask (e.g. finish placed at (140,250))
        """
        # Rect of original image at car position
        orig_rect = self.img.get_rect(topleft=(self.x, self.y))

        # Rotate image and keep same centre
        rotated_img = pygame.transform.rotate(self.img, self.angle)
        rotated_rect = rotated_img.get_rect(center=orig_rect.center)
        car_mask = pygame.mask.from_surface(rotated_img)

        # Offset relative to the mask surface position
        offset = (int(rotated_rect.left - x), int(rotated_rect.top - y))
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
# GBFS AI CAR
# -----------------------------
class GBFSDetourCar(Car):
    IMG = GREEN_CAR
    START_POS = (165, 200)

    def __init__(self, max_vel, rotation_vel, checkpoints, allow_diag=True, clearance_weight=0.4, detour_alpha=0.5):
        super().__init__(max_vel, rotation_vel)
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
        # stuck detection
        self._last_dist = None
        self._stuck_frames = 0
        self._stuck_threshold = 45  # ~0.75s at 60 FPS

    def bounce(self):
        self.vel = -self.vel
        super().move()

    def world_to_grid(self, x, y):
        return int(y // GRID_SIZE), int(x // GRID_SIZE)

    def grid_to_world(self, gx, gy):
        x = gy * GRID_SIZE + GRID_SIZE / 2
        y = gx * GRID_SIZE + GRID_SIZE / 2
        return x, y

    def _clearance_at(self, x, y, radius=6, step=2):
        width, height = TRACK_BORDER_MASK.get_size()
        hits, samples = 0, 0
        ix, iy = int(x), int(y)
        for dx in range(-radius, radius+1, step):
            for dy in range(-radius, radius+1, step):
                sx, sy = ix + dx, iy + dy
                if 0 <= sx < width and 0 <= sy < height:
                    samples += 1
                    if TRACK_BORDER_MASK.get_at((sx, sy)) != 0:
                        hits += 1
        return 0.0 if samples == 0 else (1.0 - hits / samples)

    def _neighbor_candidates(self, start_grid, goal_grid):
        rows, cols = len(GRID), len(GRID[0])
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
            if 0 <= nr < rows and 0 <= nc < cols and GRID[nr][nc]:
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
        if d < max(WAYPOINT_REACH, CHECKPOINT_RADIUS):
            # Only advance if it is ahead in heading space
            rad = math.radians(self.angle)
            fwd = (-math.sin(rad), -math.cos(rad))
            vx, vy = (cx - self.x, cy - self.y)
            proj = vx * fwd[0] + vy * fwd[1]
            if proj > -8:
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
        start = nearest_walkable(GRID, start, max_radius=120)
        goal  = nearest_walkable(GRID, goal,  max_radius=120)
        
        if not GRID[start[0]][start[1]] or not GRID[goal[0]][goal[1]]:
            print("Start/Goal blocked even after snapping:", start, goal)

        grid_path = greedy_best_first(
            GRID, start, goal,
            mask=TRACK_BORDER_MASK, grid_size=GRID_SIZE,
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
            rest = greedy_best_first(
                GRID, pick, goal_grid,
                mask=TRACK_BORDER_MASK, grid_size=GRID_SIZE,
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
            if accum >= LOOKAHEAD_DIST:
                px, py = tx, ty
                break
            idx += 1
        target_x, target_y = px, py
        self._dbg_target = (target_x, target_y)

        # 5) Advance raw waypoint if very close (keeps index moving forward)
        nxt_x, nxt_y = self.path[self.current_point]
        if math.hypot(nxt_x - self.x, nxt_y - self.y) < WAYPOINT_REACH:
            self.current_point = min(self.current_point + 1, len(self.path) - 1)

        # 6) Heading & speed gating (then tiny kick if stuck at zero)
        angle_to_target = self._desired_angle_to(target_x, target_y)
        angle_diff = (angle_to_target - self.angle + 180) % 360 - 180
        if angle_diff > 0:
            self.angle += min(self.rotation_vel, angle_diff)
        else:
            self.angle -= min(self.rotation_vel, -angle_diff)

        if abs(angle_diff) > ALIGN_ANGLE:
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
        if TRACK_BORDER_MASK.overlap(car_mask, (int(rotated_rect.left), int(rotated_rect.top))):
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
    # Grid

    if SHOW_GRID:
        win.blit(GRID_OVERLAY, (0, 0))
  
    # Draw computer path in yellow lines
    if hasattr(computer_car, 'path') and computer_car.path:
        # small circles at the waypoints
        for (px, py) in computer_car.path:
            pygame.draw.circle(win, (255, 255, 0), (int(px), int(py)), 2)
        # lines between waypoints
        for i in range(1, len(computer_car.path)):
            x1, y1 = computer_car.path[i-1]
            x2, y2 = computer_car.path[i]
            pygame.draw.line(win, (255, 255, 0), (int(x1), int(y1)), (int(x2), int(y2)), 2)

    # Optional: highlight current target/lookahead if you stored it (e.g., computer_car._dbg_target)
    if hasattr(computer_car, "_dbg_target"):
        tx, ty = computer_car._dbg_target
        pygame.draw.circle(win, (255, 140, 0), (int(tx), int(ty)), 5)

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
computer_car = GBFSDetourCar(2.2, 4, CHECKPOINTS, allow_diag=False, clearance_weight=0.6, detour_alpha=0.7)

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
