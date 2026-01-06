import heapq, math

# -----------------------------
# A* PATHFINDING
# -----------------------------
def heuristic(a, b):
    """Manhattan heuristic for grid A*.

    `a` and `b` are (row, col) grid coordinates.
    Using Manhattan distance keeps costs admissible for 4-connected grids.
    """
    return abs(a[0] - b[0]) + abs(a[1] - b[1])

def astar(grid, start, goal):
    """A simple A* implementation on a 4-connected boolean grid.

    - `grid` is a list-of-lists of booleans returned by `build_grid`.
    - `start` and `goal` are `(row, col)` tuples.
    Returns a list of grid coordinates from start (exclusive) to goal (inclusive),
    or `None` if no path exists.
    """
    rows, cols = len(grid), len(grid[0])
    open_set = []
    heapq.heappush(open_set, (0, start))
    came_from = {}
    g_score = {start: 0}

    while open_set:
        _, current = heapq.heappop(open_set)

        if current == goal:
            path = []
            while current in came_from:
                path.append(current)
                current = came_from[current]
            path.reverse()
            return path

        x, y = current
        # 4-connected neighbors (up/down/left/right)
        neighbors = [(x+1,y), (x-1,y), (x,y+1), (x,y-1)]

        for nx, ny in neighbors:
            if 0 <= nx < rows and 0 <= ny < cols and grid[nx][ny]:
                tentative_g = g_score[current] + 1
                if (nx, ny) not in g_score or tentative_g < g_score[(nx, ny)]:
                    g_score[(nx, ny)] = tentative_g
                    f_score = tentative_g + heuristic((nx, ny), goal)
                    heapq.heappush(open_set, (f_score, (nx, ny)))
                    came_from[(nx, ny)] = current

    return None