import math
import pygame
import heapq
from .abstract_car import AbstractCar


class DijkstraCar(AbstractCar):
    """
    Computer-controlled car that uses Dijkstra's algorithm to navigate
    through a grid-based track to reach checkpoints.
    """
    def __init__(self, img, start_pos, max_vel, rotation_vel,
                 path, grid_size=None, waypoint_reach=10,
                 checkpoint_radius=None, grid=None,
                 track_border_mask=None, loop=True):
        super().__init__(img, start_pos, max_vel, rotation_vel)
        self.CHECKPOINTS = path  # Expected path becomes checkpoints for Dijkstra to plan between
        self.WAYPOINT_REACH = waypoint_reach
        self.CHECKPOINT_RADIUS = checkpoint_radius or 30
        self.TRACK_BORDER_MASK = track_border_mask
        self.GRID = grid
        self.GRID_SIZE = grid_size or 4
        self.loop = loop
        self.autonomous = True  # Always autonomous

        self.vel = max_vel
        self.current_checkpoint = 0
        self.path = []  # Dijkstra-computed path
        self.current_point = 0
        
        # Compute initial path to first checkpoint
        self._compute_path_to_checkpoint()

    # ------------------ DIJKSTRA ALGORITHM ------------------
    def _world_to_grid(self, x, y):
        """Convert world coordinates to grid coordinates."""
        gx = int(y / self.GRID_SIZE)
        gy = int(x / self.GRID_SIZE)
        return (gx, gy)

    def _grid_to_world(self, gx, gy):
        """Convert grid coordinates to world coordinates."""
        x = gy * self.GRID_SIZE + self.GRID_SIZE / 2
        y = gx * self.GRID_SIZE + self.GRID_SIZE / 2
        return (x, y)

    def _dijkstra_path(self, start_world, goal_world):
        """
        Compute shortest path using Dijkstra's algorithm.
        Returns list of (x, y) world coordinates from start to goal.
        """
        start_grid = self._world_to_grid(*start_world)
        goal_grid = self._world_to_grid(*goal_world)
        
        rows, cols = len(self.GRID), len(self.GRID[0])
        
        # Check if start/goal are walkable
        if not (0 <= start_grid[0] < rows and 0 <= start_grid[1] < cols):
            return []
        if not (0 <= goal_grid[0] < rows and 0 <= goal_grid[1] < cols):
            return []
        if not self.GRID[start_grid[0]][start_grid[1]]:
            return []
        if not self.GRID[goal_grid[0]][goal_grid[1]]:
            return []
        
        # Dijkstra: (cost, node)
        open_set = [(0, start_grid)]
        visited = set()
        came_from = {}
        cost_so_far = {start_grid: 0}
        
        while open_set:
            current_cost, current = heapq.heappop(open_set)
            
            if current in visited:
                continue
            visited.add(current)
            
            if current == goal_grid:
                # Reconstruct path
                path = []
                node = current
                while node in came_from:
                    path.append(node)
                    node = came_from[node]
                path.append(start_grid)
                path.reverse()
                
                # Convert grid path to world path
                world_path = [self._grid_to_world(gx, gy) for gx, gy in path]
                return world_path
            
            # Explore 8 neighbors (diagonal allowed)
            cr, cc = current
            neighbors = [
                (cr - 1, cc), (cr + 1, cc), (cr, cc - 1), (cr, cc + 1),  # 4-neighbors
                (cr - 1, cc - 1), (cr - 1, cc + 1), (cr + 1, cc - 1), (cr + 1, cc + 1)  # diagonals
            ]
            
            for nr, nc in neighbors:
                if not (0 <= nr < rows and 0 <= nc < cols):
                    continue
                if not self.GRID[nr][nc]:  # Blocked cell
                    continue
                if (nr, nc) in visited:
                    continue
                
                # Cost: 1 for 4-neighbors, sqrt(2) for diagonals
                move_cost = 1.0 if abs(nr - cr) + abs(nc - cc) == 1 else 1.414
                new_cost = cost_so_far[current] + move_cost
                
                if (nr, nc) not in cost_so_far or new_cost < cost_so_far[(nr, nc)]:
                    cost_so_far[(nr, nc)] = new_cost
                    came_from[(nr, nc)] = current
                    heapq.heappush(open_set, (new_cost, (nr, nc)))
        
        return []  # No path found

    def _compute_path_to_checkpoint(self):
        """Compute Dijkstra path to current checkpoint."""
        if self.current_checkpoint >= len(self.CHECKPOINTS):
            if self.loop:
                self.current_checkpoint = 0
            else:
                return
        
        checkpoint = self.CHECKPOINTS[self.current_checkpoint]
        start_pos = (self.x, self.y)
        
        new_path = self._dijkstra_path(start_pos, checkpoint)
        if new_path:
            self.path = new_path
            self.current_point = 0
        else:
            # Fallback: direct point if no path found
            self.path = [checkpoint]
            self.current_point = 0

    # ------------------ MOVEMENT ------------------
    def calculate_angle(self, target_x, target_y):
        """Compute and smoothly rotate towards target."""
        dx = target_x - self.x
        dy = target_y - self.y

        # In screen coords: 0 deg = up, 90 deg = right
        desired = math.degrees(math.atan2(dx, -dy))
        diff = (desired - self.angle + 180) % 360 - 180

        if diff > 0:
            self.angle += min(self.rotation_vel, diff)
        else:
            self.angle -= min(self.rotation_vel, -diff)

        self.angle %= 360

    def move(self):
        """Move along Dijkstra path, replanning at checkpoints."""
        # Replan if path is empty or exhausted
        if not self.path or self.current_point >= len(self.path):
            self.current_checkpoint += 1
            if self.loop:
                self.current_checkpoint %= len(self.CHECKPOINTS)
            self._compute_path_to_checkpoint()
            if not self.path:
                return
        
        tx, ty = self.path[self.current_point]
        
        # Rotate toward next waypoint
        self.calculate_angle(tx, ty)
        
        # Stepwise movement to avoid embedding in walls
        steps = max(int(self.vel), 1)
        rad = math.radians(self.angle)
        width, height = self.TRACK_BORDER_MASK.get_size()
        for i in range(1, steps + 1):
            step_size = self.vel / steps
            test_x = self.x + math.sin(rad) * step_size
            test_y = self.y - math.cos(rad) * step_size
            
            # Boundary check
            if (0 <= int(test_x) < width and
                0 <= int(test_y) < height):
                if self.TRACK_BORDER_MASK.get_at((int(test_x), int(test_y))) == 0:
                    self.x = test_x
                    self.y = test_y
                else:
                    break
        
        # Update waypoint after movement
        if math.hypot(tx - self.x, ty - self.y) < self.WAYPOINT_REACH:
            self.current_point += 1

    # ------------------ DEBUG DRAW ------------------
    def draw(self, win, show_points=True):
        from resources import blit_rotate_center
        blit_rotate_center(win, self.img, (self.x, self.y), -self.angle)
        if show_points:
            # Draw checkpoints in red
            for p in self.CHECKPOINTS:
                pygame.draw.circle(win, (255, 0, 0), p, 5)
            # Draw computed path in blue
            for p in self.path:
                pygame.draw.circle(win, (0, 0, 255), p, 2)
            if self.current_point < len(self.path):
                tx, ty = self.path[self.current_point]
                pygame.draw.circle(win, (0, 255, 0), (int(tx), int(ty)), 5)

    def set_level(self, level):
        import resources
        self.CHECKPOINTS = resources.get_path_for_level(level)
        self.TRACK_BORDER_MASK = resources.TRACK_BORDER_MASK
        self.GRID = resources.GRID
        self.reset()
        self.current_checkpoint = 0
        self.path = []
        self.current_point = 0
        self._compute_path_to_checkpoint()
