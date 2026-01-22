
# tuning_registry.py

from typing import Dict, Any, List

CarList = List[Any]
FIRST4_KEYS = ["max_vel", "acceleration", "rotation_vel", "brake_factor"]

def _get_first4_from_car(car: Any) -> Dict[str, Any]:
    d = {}
    for k in FIRST4_KEYS:
        d[k] = getattr(car, k, None) if hasattr(car, k) else None
    return d

def build_registry(manager: Any, cars: CarList) -> Dict[str, Dict[str, Any]]:
    reg: Dict[str, Dict[str, Any]] = {
        "car.common": {k: None for k in FIRST4_KEYS},
        "gbfs": {},
        "dijkstra": {},
        "neat": {}
    }

    # First 4 (first non-None wins)
    for car in cars:
        for k, v in _get_first4_from_car(car).items():
            if reg["car.common"][k] is None and v is not None:
                reg["car.common"][k] = v

    # GBFS extras
    gbfs = next((c for c in cars if c.__class__.__name__ == "GBFSDetourCar"), None)
    if gbfs is not None:
        reg["gbfs"] = {
            "Lookahead_Dist": getattr(gbfs, "Lookahead_Dist", None),
            "ahead_window": getattr(gbfs, "ahead_window", None),
            "clearance_weight": getattr(gbfs, "clearance_weight", None),
            "detour_alpha": getattr(gbfs, "detour_alpha", None),
            "max_expansions": getattr(gbfs, "max_expansions", None),
            "Align_Angle": getattr(gbfs, "Align_Angle", None),
            "allow_diag": int(getattr(gbfs, "allow_diag", 0)),
            "WAYPOINT_REACH": getattr(gbfs, "WAYPOINT_REACH", None),
            "CHECKPOINT_RADIUS": getattr(gbfs, "CHECKPOINT_RADIUS", None),
            "GRIDSIZE": getattr(gbfs, "GRIDSIZE", None),
        }

    # Dijkstra extras
    dijk = next((c for c in cars if c.__class__.__name__ == "DijkstraCar"), None)
    if dijk is not None:
        reg["dijkstra"] = {
            "WAYPOINT_REACH": getattr(dijk, "WAYPOINT_REACH", None),
            "CHECKPOINT_RADIUS": getattr(dijk, "CHECKPOINT_RADIUS", None),
            "GRID_SIZE": getattr(dijk, "GRID_SIZE", None),
        }

    # NEAT config
    cfg = manager.config
    gc = getattr(cfg, "genome_config", None)
    rep = getattr(cfg, "reproduction_config", None)
    stag = getattr(cfg, "stagnation_config", None)
    reg["neat"] = {
        "weight_mutate_rate": getattr(gc, "weight_mutate_rate", None) if gc else None,
        "weight_mutate_power": getattr(gc, "weight_mutate_power", None) if gc else None,
        "node_add_prob": getattr(gc, "node_add_prob", None) if gc else None,
        "conn_add_prob": getattr(gc, "conn_add_prob", None) if gc else None,
        "survival_threshold": getattr(rep, "survival_threshold", None) if rep else None,
        "max_stagnation": getattr(stag, "max_stagnation", None) if stag else None,
        "pop_size": getattr(cfg, "pop_size", None),
    }
    return reg

def apply_registry(reg: Dict[str, Dict[str, Any]], manager: Any, cars: CarList) -> None:
    common = reg.get("car.common", {})

    # First 4 on every car (if attribute exists)
    for car in cars:
        for k, v in common.items():
            if v is not None and hasattr(car, k):
                setattr(car, k, v)

    # Keep your SetTunables pattern for subclass specifics
    for car in cars:
        if hasattr(car, "SetTunables"):
            extras = []
            if car.__class__.__name__ == "GBFSDetourCar":
                g = reg.get("gbfs", {})
                extras = [
                    g.get("Lookahead_Dist"),
                    g.get("ahead_window"),
                    g.get("clearance_weight"),
                    g.get("detour_alpha"),
                    g.get("max_expansions"),
                    g.get("Align_Angle"),
                    g.get("allow_diag", 0),
                ]
            base = [common.get("max_vel"), common.get("acceleration"),
                    common.get("rotation_vel"), common.get("brake_factor")]
            data = [x for x in base + extras if x is not None]
            car.SetTunables(data)

    # NEAT by explicit attributes
    neat = reg.get("neat", {})
    cfg = manager.config
    gc = getattr(cfg, "genome_config", None)
    rep = getattr(cfg, "reproduction_config", None)
    stag = getattr(cfg, "stagnation_config", None)

    def _set(obj, name, val):
        if obj is not None and val is not None and hasattr(obj, name):
            setattr(obj, name, val)

    _set(gc, "weight_mutate_rate", neat.get("weight_mutate_rate"))
    _set(gc, "weight_mutate_power", neat.get("weight_mutate_power"))
    _set(gc, "node_add_prob", neat.get("node_add_prob"))
    _set(gc, "conn_add_prob", neat.get("conn_add_prob"))
    _set(rep, "survival_threshold", neat.get("survival_threshold"))
    _set(stag, "max_stagnation", neat.get("max_stagnation"))

    prev_pop = getattr(cfg, "pop_size", None)
    new_pop = neat.get("pop_size", prev_pop)
    if new_pop is not None and new_pop != prev_pop:
        cfg.pop_size = new_pop
        if hasattr(manager, "RestartWithNewPopulationSize"):
            manager.RestartWithNewPopulationSize()
