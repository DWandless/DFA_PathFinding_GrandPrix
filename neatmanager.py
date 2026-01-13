import time
import math
import pygame
from collections import deque

from cars import *

import neat



class NEATEpisode:
    """Holds per-genome runtime state for simultaneous evaluation."""
    __slots__ = ("gid", "genome", "net", "car", "elapsed", "speed_history", "finished", "finish_reason")

    def __init__(self, gid, genome, net, car, speed_window_frames):
        self.gid = gid
        self.genome = genome
        self.net = net
        self.car = car
        self.elapsed = 0.0
        self.speed_history = deque(maxlen=speed_window_frames)
        self.finished = False
        self.finish_reason = ""


class NEATManager:
    """
    Simultaneous evaluation of all genomes in the generation:
      - Builds all nets & cars for current generation.
      - Steps them together every frame.
      - Ends each episode independently; records fitness.
      - When all are finished, advances one generation.
    """

    def __init__(self,
                 neat_config: neat.Config,
                 car_factory,                # callable -> NEATCar
                 track_mask,                 # pygame.Mask (border: nonzero; road: 0)
                 raycast_fn,                 # callable(mask, origin, angle, max_distance, step)
                 fps=60,
                 time_limit_sec=20.0,
                 stuck_speed_thresh=0.1,
                 stuck_time_sec=2.0):
        self.config = neat_config
        self.pop = neat.Population(self.config)
        self.pop.add_reporter(neat.StdOutReporter(True))
        self.stats = neat.StatisticsReporter()
        self.pop.add_reporter(self.stats)

        # Environment
        self.track_mask = track_mask
        self.raycast_fn = raycast_fn
        self.car_factory = car_factory

        # Episode controls
        self.fps = fps
        self.time_limit = time_limit_sec
        self.stuck_thresh = stuck_speed_thresh
        self.stuck_time_sec = stuck_time_sec
        self._speed_window_frames = max(1, int(self.stuck_time_sec * self.fps))

        # Runtime state
        self.generation = 0
        self._genomes_list = []            # [(id, genome), ...] for current generation
        self._fitness_map = {}             # genome_id -> fitness
        self._episodes = []                # list[NEATEpisode]
        self.done = False                  # True when max generations reached (if you add a cap)
        self.winner = None

        # Prepare first generation
        self._begin_generation()

    # ---------------------------
    # Generation / genome control
    # ---------------------------
    def _begin_generation(self):
        """Prepare episodes list for the current population and reset per-gen state."""
        # Grab current generation's genomes
        self._genomes_list = list(self.pop.population.items())  # [(genome_id, genome), ...]
        self._fitness_map.clear()
        self._episodes = []

        # For neat-python StatisticsReporter, try to keep generation number in sync
        self.generation = getattr(self.stats, 'generation', self.generation)

        # Build car + net for every genome, all at once
        for gid, genome in self._genomes_list:
            net = neat.nn.FeedForwardNetwork.create(genome, self.config)
            car = self.car_factory()
            # Provide the net to the car
            car.set_net(net)
            # If your car needs raycast_fn or track_mask, ensure car_factory wired them in.
            ep = NEATEpisode(gid, genome, net, car, speed_window_frames=self._speed_window_frames)
            self._episodes.append(ep)

    def _advance_generation(self):
        """
        Advance one generation by calling pop.run with a callback that simply
        assigns our collected fitnesses to the genomes. This is very fast and non-blocking.
        """
        def _assign_fitnesses(genomes, config):
            for gid, g in genomes:
                g.fitness = self._fitness_map.get(gid, 0.0)

        # Advance one generation
        self.winner = self.pop.run(_assign_fitnesses, 1)

        # Prepare the next generation list
        self._begin_generation()

    # ---------------------------
    # Utility
    # ---------------------------
    def _on_road(self, car):
        cx, cy = car.get_centre()
        cx, cy = int(cx), int(cy)
        w, h = self.track_mask.get_size()
        if cx < 0 or cy < 0 or cx >= w or cy >= h:
            return False
        # Road is 0, border is nonzero per your comment
        return self.track_mask.get_at((cx, cy)) == 0

    def _episode_done_state(self, on_road, elapsed, speed_history):
        """Termination check for one car's episode based on its own state."""
        if not on_road:
            return True, "off-road"

        # Stuck: speed < thresh for N frames
        if len(speed_history) == self._speed_window_frames and all(v < self.stuck_thresh for v in speed_history):
            return True, "stuck"

        # Time limit
        if elapsed >= self.time_limit:
            return True, "time"

        return False, ""

    # ---------------------------
    # Loop hooks
    # ---------------------------
    def update(self, dt):
        """
        Call from your game loop each frame.
        Steps all active cars simultaneously.
        Records fitness when a car finishes.
        When all cars are finished, advances generation.
        Returns:
            (gen, finished_count, total) for HUD/debug.
        """
        if not self._episodes:
            # Shouldn't happen, but guard against empty generation
            return (self.generation, 0, 0)

        finished_count = 0
        total = len(self._episodes)

        for ep in self._episodes:
            if ep.finished:
                finished_count += 1
                continue

            # Sense -> think -> control -> move
            ep.car.move()

            # Fitness update
            on_road = self._on_road(ep.car)
            ep.car.update_fitness(on_road, dt)
            ep.elapsed += dt

            # Track speed history for stuck detection
            # Assuming car.vel is scalar speed; if it's a vector, use magnitude
            speed_val = ep.car.vel if isinstance(ep.car.vel, (int, float)) else (ep.car.vel.length() if hasattr(ep.car.vel, "length") else float(ep.car.vel))
            ep.speed_history.append(speed_val)

            # Episode termination?
            done, reason = self._episode_done_state(on_road, ep.elapsed, ep.speed_history)
            if done:
                ep.finished = True
                ep.finish_reason = reason
                self._fitness_map[ep.gid] = ep.car.fitness
                finished_count += 1

        # All cars finished? Advance generation immediately.
        if finished_count >= total:
            self._advance_generation()
            # After advancing, the new generation starts with 0 finished
            return (self.generation, 0, len(self._episodes))

        return (self.generation, finished_count, total)

    def draw(self, win, draw_sensors=True):
        """Draw all cars (and optionally sensors) simultaneously."""
        for ep in self._episodes:
            # Draw every car; if your car.draw already handles sensors toggling, this is enough.
            # Otherwise, add logic to skip expensive sensor visualization when many cars exist.
            ep.car.draw(win)
