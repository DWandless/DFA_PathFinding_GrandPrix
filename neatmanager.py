import time
import math
import pygame

from cars import *

import pygame
import neat
import math


class NEATManager:
    """
    Integrates neat-python into your existing game loop:
      - Iterates genomes one-by-one across frames.
      - Builds a net for the current genome and runs a NEATCar episode.
      - Records fitness; when all genomes are done, advances one generation.
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

        # Runtime state
        self.generation = 0
        self._genomes_list = []            # [(id, genome), ...] for current generation
        self._fitness_map = {}             # genome_id -> fitness collected by loop
        self._current_index = -1
        self._car = None
        self._net = None
        self._elapsed = 0.0
        self._speed_history = []
        self._speed_window_frames = max(1, int(self.stuck_time_sec * self.fps))
        self.done = False                  # True when max generations reached (optional)
        self.winner = None

        self._begin_generation()

    # ---------------------------
    # Generation / genome control
    # ---------------------------
    def _begin_generation(self):
        """Prepare genomes list for the current population and reset per-episode state."""
        self._genomes_list = list(self.pop.population.items())  # [(genome_id, genome), ...]
        self._fitness_map.clear()
        self._current_index = -1
        self._net = None
        self._car = None
        self._elapsed = 0.0
        self._speed_history = []
        self.generation = getattr(self.stats, 'generation', self.generation)

    def _advance_to_next_genome(self):
        """Move to next genome; build car and network."""
        self._current_index += 1
        if self._current_index >= len(self._genomes_list):
            # All genomes evaluated -> advance one generation through neat-python
            self._advance_generation()
            return

        genome_id, genome = self._genomes_list[self._current_index]
        self._net = neat.nn.FeedForwardNetwork.create(genome, self.config)
        self._car = self.car_factory()
        self._car.set_net(self._net)
        self._elapsed = 0.0
        self._speed_history = []

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
        # Immediately start with the first genome of the new generation
        self._advance_to_next_genome()

    # ---------------------------
    # Utility
    # ---------------------------
    def _on_road(self, car):
        cx, cy = car.get_centre()
        cx, cy = int(cx), int(cy)
        w, h = self.track_mask.get_size()
        if cx < 0 or cy < 0 or cx >= w or cy >= h:
            return False
        return self.track_mask.get_at((cx, cy)) == 0

    def _episode_done(self, car, on_road):
        # Off-road ends the episode (simple rule; replace with precise overlap if desired)
        if not on_road:
            return True, "off-road"

        # Stuck: speed < thresh for N frames
        self._speed_history.append(car.vel)
        if len(self._speed_history) > self._speed_window_frames:
            self._speed_history.pop(0)
        if len(self._speed_history) == self._speed_window_frames and all(v < self.stuck_thresh for v in self._speed_history):
            return True, "stuck"

        # Time limit
        if self._elapsed >= self.time_limit:
            return True, "time"

        return False, ""

    # ---------------------------
    # Loop hooks
    # ---------------------------
    def update(self, dt):
        """
        Call from your game loop each frame.
        - If no current genome, loads the next.
        - Steps one frame of sensing/thinking/movement.
        - When an episode ends, records fitness and loads the next genome or generation.
        Returns:
            (gen, idx, total) for HUD/debug (current generation, current genome index, total genomes).
        """
        if self._car is None:
            self._advance_to_next_genome()
            # If there were zero genomes (shouldn't happen), bail
            if self._car is None:
                return (self.generation, 0, 0)

        # Sense -> think -> control -> move
        self._car.move()

        # Fitness update
        on_road = self._on_road(self._car)
        self._car.update_fitness(on_road, dt)
        self._elapsed += dt

        # Episode termination?
        done, reason = self._episode_done(self._car, on_road)
        if done:
            gid, _ = self._genomes_list[self._current_index]
            self._fitness_map[gid] = self._car.fitness
            # Move on
            self._advance_to_next_genome()

        return (self.generation, self._current_index + 1, len(self._genomes_list))

    def draw(self, win):
        """Draw the current car & sensors."""
        if self._car:
            self._car.draw(win)