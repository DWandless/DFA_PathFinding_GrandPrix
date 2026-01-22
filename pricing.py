
# pricing.py

from typing import Dict, Any
import math

Currency = float

def clamp(x, lo, hi): return max(lo, min(hi, x))

def lin(value, base, lo, hi, k=1.0):
    v = clamp(value, lo, hi)
    return base * k * (v - lo) / max(1e-9, (hi - lo))

def smooth(value, base, lo, hi, steep=2.0):
    v = clamp(value, lo, hi)
    t = (v - lo) / max(1e-9, (hi - lo))
    return base * (t ** steep)

def superlinear(value, base, lo, hi, power=1.5):
    v = clamp(value, lo, hi)
    t = (v - lo) / max(1e-9, (hi - lo))
    return base * (t ** power)

def inverse(value, base, lo, hi):
    v = clamp(value, lo, hi)
    t = (v - lo) / max(1e-9, (hi - lo))
    return base * (1.0 - t)

MODEL_BASE_PRICE = {
    "Player": 0.0,
    "Computer": 1000.0,
    "GBFS": 5000.0,
    "Dijkstra": 8000.0,
    "NEAT": 15000.0,
}

# Map to your levels for now
TRACK_MULT = {
    "level1": 1.0,
    "level2": 1.2,
}

RANGE = {
    "car.common": {
        "max_vel":        (1.5, 8.0),
        "acceleration":   (0.05, 0.40),
        "rotation_vel":   (1.0, 8.0),
        "brake_factor":   (0.2, 0.95),
    },
    "gbfs": {
        "Lookahead_Dist":  (8, 128),
        "ahead_window":    (10, 120),
        "clearance_weight":(0.0, 1.0),
        "detour_alpha":    (0.0, 1.0),
        "max_expansions":  (1000, 100000),
        "Align_Angle":     (10, 60),
        "allow_diag":      (0, 1),
    },
    "dijkstra": {
        "GRID_SIZE":        (2, 16),
        "WAYPOINT_REACH":   (5, 40),
        "CHECKPOINT_RADIUS":(10, 60),
    },
    "neat": {
        "pop_size":           (10, 300),
        "weight_mutate_rate": (0.0, 1.0),
        "weight_mutate_power":(0.05, 3.0),
        "node_add_prob":      (0.0, 0.5),
        "conn_add_prob":      (0.0, 0.5),
        "survival_threshold": (0.1, 0.6),
        "max_stagnation":     (2, 30),
    }
}

def _lo_hi(rng):
    lo, hi = rng
    return dict(lo=lo, hi=hi)

def price_car_common(common: Dict[str, Any]) -> Currency:
    r = RANGE["car.common"]
    p  = smooth(common["max_vel"],      base=4000,  **_lo_hi(r["max_vel"]),     steep=2.2)
    p += smooth(common["acceleration"], base=3500,  **_lo_hi(r["acceleration"]), steep=2.0)
    p += smooth(common["rotation_vel"], base=2000,  **_lo_hi(r["rotation_vel"]), steep=1.6)
    p += smooth(common["brake_factor"], base=1000,  **_lo_hi(r["brake_factor"]), steep=1.5)
    return p

def price_gbfs(g: Dict[str, Any]) -> Currency:
    r = RANGE["gbfs"]
    p  = smooth(g["Lookahead_Dist"],  base=2500, **_lo_hi(r["Lookahead_Dist"]),  steep=1.4)
    p += smooth(g["ahead_window"],    base=1200, **_lo_hi(r["ahead_window"]),    steep=1.2)
    p += smooth(g["clearance_weight"],base=2200, **_lo_hi(r["clearance_weight"]),steep=1.5)
    p += smooth(g["detour_alpha"],    base=2200, **_lo_hi(r["detour_alpha"]),    steep=1.5)
    p += superlinear(g["max_expansions"], base=3500, **_lo_hi(r["max_expansions"]), power=1.3)
    p += inverse(g["Align_Angle"],    base=900,  **_lo_hi(r["Align_Angle"]))
    if int(g.get("allow_diag", 0)) == 1:
        p += 400
    return p

def price_dijkstra(d: Dict[str, Any]) -> Currency:
    r = RANGE["dijkstra"]
    lo, hi = r["GRID_SIZE"]
    gs = clamp(d["GRID_SIZE"], lo, hi)
    t = 1.0 - (gs - lo) / (hi - lo + 1e-9)
    p  = 3000 * (t ** 1.8)
    p += inverse(d["WAYPOINT_REACH"], base=1200, **_lo_hi(r["WAYPOINT_REACH"]))
    p += inverse(d["CHECKPOINT_RADIUS"], base=600, **_lo_hi(r["CHECKPOINT_RADIUS"]))
    return p

def price_neat(n: Dict[str, Any]) -> Currency:
    r = RANGE["neat"]
    p  = superlinear(n["pop_size"], base=16000, **_lo_hi(r["pop_size"]), power=1.7)
    p += smooth(n["weight_mutate_rate"],  base=4500, **_lo_hi(r["weight_mutate_rate"]), steep=1.4)
    p += smooth(n["weight_mutate_power"], base=3000, **_lo_hi(r["weight_mutate_power"]), steep=1.2)
    p += lin(n["node_add_prob"],  base=800, **_lo_hi(r["node_add_prob"]), k=1.0)
    p += lin(n["conn_add_prob"],  base=800, **_lo_hi(r["conn_add_prob"]), k=1.0)
    p += smooth(n["survival_threshold"], base=1200, **_lo_hi(r["survival_threshold"]), steep=1.1)
    p += lin(n["max_stagnation"], base=600, **_lo_hi(r["max_stagnation"]), k=0.8)
    return p

def price_build(model_name: str, track_key: str, reg: Dict[str, Dict[str, Any]]) -> Currency:
    model_base = MODEL_BASE_PRICE.get(model_name, 0.0)
    track_mult = TRACK_MULT.get(track_key, 1.0)

    total = model_base
    total += price_car_common(reg["car.common"])

    if model_name == "GBFS":
        total += price_gbfs(reg.get("gbfs", {}))
    elif model_name == "Dijkstra":
        total += price_dijkstra(reg.get("dijkstra", {}))
    elif model_name == "NEAT":
        total += price_neat(reg.get("neat", {}))
    # Player/Computer: no extras

    return total * track_mult
