import time
import math
import pygame
from collections import deque

from cars import NEATCar

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
        self._crash_markers = []           # list[{"pos":(x,y), "reason":str}]

        # Prepare first generation
        self._begin_generation()

    def reset(self):
        """
        Completely restarts NEAT training from generation 0.
        Creates a fresh population and resets all runtime state.
        """
        # Fresh NEAT population
        self.pop = neat.Population(self.config)
        self.pop.add_reporter(neat.StdOutReporter(True))
        self.stats = neat.StatisticsReporter()
        self.pop.add_reporter(self.stats)

        # Reset state
        self.generation = 0
        self._genomes_list = []
        self._fitness_map.clear()
        self._episodes.clear()
        self._crash_markers.clear()
        self.winner = None
        self.done = False

        # Build generation 0
        self._begin_generation()

    def RestartWithNewPopulationSize(self):
        self.pop = neat.Population(self.config)
        self.pop.add_reporter(neat.StdOutReporter(True))
        self.pop.add_reporter(self.stats)
        self._begin_generation()

    def SetTunables(self, TuningData):
        for genome in self._genomes_list:
            genome[1].SetTunables(TuningData)

        gc = self.config.genome_config

        gc.weight_mutate_rate = TuningData[4]

        # How often connection weights mutate (0.0–1.0)
        # Higher = faster exploration, noisier learning
        gc.weight_mutate_rate = TuningData[5]

        # How large each weight mutation is
        # Higher = more drastic behavior changes
        gc.weight_mutate_power = TuningData[6]

        # Probability of adding a new node during mutation
        # Controls network complexity growth
        gc.node_add_prob = TuningData[7]

        # Probability of adding a new connection
        # Higher = denser networks
        gc.conn_add_prob = TuningData[8]

        # frcation of genomes allowed to reproduce
        gc.survival_threshold = TuningData[9]

        # --------------------------------------------------
        # 3) Species-level NEAT parameters (diversity control)
        # --------------------------------------------------
        sc = self.config.species_set_config

        # generations before a species is killed
        sc.max_stagnation = TuningData[10]
        # population size
        self.config.pop_size = TuningData[11]
        # RestartWithNewPopulationSize()

    

    # ---------------------------
    # Generation / genome control
    # ---------------------------
    def _begin_generation(self):
        """Prepare episodes list for the current population and reset per-gen state."""
        # Grab current generation's genomes
        self._genomes_list = list(self.pop.population.items())  # [(genome_id, genome), ...]
        self._fitness_map.clear()
        self._episodes = []
        
        self._crash_markers.clear()

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
        Advance one generation by calling pop.run with a callback that assigns fitnesses.
        """
        def _assign_fitnesses(genomes, config):
            for gid, g in genomes:
                g.fitness = self._fitness_map.get(gid, 0.0)

        # Advance one generation
        self.winner = self.pop.run(_assign_fitnesses, 1)
        self.generation += 1

        # Prepare next generation
        self._begin_generation()



    
    
    def get_generation_summary(self) -> str:
        """
        Returns a string similar to NEAT's StdOutReporter output:
        - Generation number
        - Population stats
        - Species table (ID, size, fitness, adj fitness, stagnation)
        """
        species_set = self.pop.species
        population_size = len(self.pop.population)
        num_species = len(species_set.species)

        # Best genome and fitness
        best_genome = max(self.pop.population.values(), key=lambda g: g.fitness if g.fitness is not None else -float("inf"))
        best_fitness = best_genome.fitness if best_genome.fitness is not None else 0.0

        # Compute averages
        fitnesses = [g.fitness for g in self.pop.population.values() if g.fitness is not None]
        avg_fitness = sum(fitnesses) / len(fitnesses) if fitnesses else 0.0
        stdev = (sum((f - avg_fitness) ** 2 for f in fitnesses) / len(fitnesses)) ** 0.5 if fitnesses else 0.0

        # Header
        lines = [
            f"****** Running generation {self.generation} ******",
            f"Population's average fitness: {avg_fitness:.5f} stdev: {stdev:.5f}",
            f"Best fitness: {best_fitness:.5f} - id {best_genome.key}",
            f"Population of {population_size} members in {num_species} species:",
            "   ID  size   fitness   adj fit  stag",
            "  ====  ====  =========  =======  ===="
        ]

        # Species details
        for sid, species in species_set.species.items():
            fitness = species.fitness if species.fitness is not None else 0.0
            adj_fit = species.adjusted_fitness if species.adjusted_fitness is not None else 0.0
            stag = species.last_improved if species.last_improved is not None else 0
            lines.append(
                f"{sid:6d}{len(species.members):6d}"
                f"{fitness:11.3f}{adj_fit:9.3f}{stag:7d}"
            )

        return "\n".join(lines)




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
            #on_road = self._on_road(ep.car)
            if ep.car.collide(self.track_mask) == None:
                on_road = True
            else:
                on_road = False
            ep.car.update_fitness(on_road, dt, ep.elapsed)
            ep.elapsed += dt

            # Track speed history for stuck detection
            # Assuming car.vel is scalar speed; if it's a vector, use magnitude
            speed_val = ep.car.vel if isinstance(ep.car.vel, (int, float)) else (ep.car.vel.length() if hasattr(ep.car.vel, "length") else float(ep.car.vel))
            ep.speed_history.append(speed_val)

            # Episode termination?
            done, reason = self._episode_done_state(on_road, ep.elapsed, ep.speed_history)
            if done:
                ep.finished = True
                self._fitness_map[ep.gid] = ep.car.fitness
                
                # add a red cross marker at the final position
                cx, cy = ep.car.get_centre()
                self._crash_markers.append({
                    "pos": (int(cx), int(cy)),
                    "reason": reason
                })

                finished_count += 1

        # All cars finished? Advance generation immediately.
        if finished_count >= total:
            self._advance_generation()
            # After advancing, the new generation starts with 0 finished
            return (self.generation, 0, len(self._episodes))

        return (self.generation, finished_count, total)

    
    def draw(self, win, images, draw_sensors=True, draw_crosses=True):
        
        """Draw all cars (optionally with sensors) and overlay crash markers (crosses)."""

        # 1) Draw track 
        for img, pos in images:
            win.blit(img, pos)

        # 2) Draw cars (and optionally sensors)
        for ep in self._episodes:
            if ep.finished is False:
                ep.car.draw(win, draw_sensors=draw_sensors)
            else:
                color = (255, 0, 0)
                self._draw_cross(win, ep.car.get_centre(), color=color, size=10, width=2)
                
    def _draw_cross(self, surface, pos, color=(220, 20, 60), size=10, width=2):
        """Draws a simple 'X' centered at pos."""
        x, y = pos
        pygame.draw.line(surface, color, (x - size, y - size), (x + size, y + size), width)
        pygame.draw.line(surface, color, (x - size, y + size), (x + size, y - size), width)