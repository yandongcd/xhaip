"""Force-directed graph layout engine.

Algorithm: Coulomb repulsion + Hooke attraction + center gravity + overlap repair.
"""

from __future__ import annotations

import math
import random
from typing import TypedDict


class NodeDict(TypedDict, total=False):
    id: str
    x: float
    y: float
    w: float
    h: float


class EdgeDict(TypedDict):
    source: str
    target: str


class LayoutNode(TypedDict):
    id: str
    x: float
    y: float


def compute_layout(
    nodes: list[NodeDict],
    edges: list[EdgeDict],
    *,
    width: int = 1200,
    height: int = 800,
    repulsion: float = 80000,
    attraction: float = 0.005,
    gravity: float = 0.0002,
    damping: float = 0.85,
    iterations: int = 400,
    seed: int | None = 42,
) -> list[LayoutNode]:
    """Compute force-directed layout coordinates for a graph.

    Args:
        nodes: [{id, w=32, h=18}] — width/height are optional node dimensions.
        edges: [{source, target}] — directed edges.
        width, height: Canvas dimensions in pixels.
        repulsion, attraction, gravity, damping: Force parameters.
        iterations: Number of simulation steps.
        seed: Random seed for deterministic output.

    Returns:
        [{id, x, y}] — sorted by ID for deterministic output.
    """
    if not nodes:
        return []

    rng = random.Random(seed)
    _ = len(nodes)  # node count reserved for future adaptive params

    # Init positions
    positions: dict[str, list[float]] = {}
    cx, cy = width / 2, height / 2
    for node in nodes:
        pid = node["id"]
        angle = rng.random() * 2 * math.pi
        r = rng.random() * min(width, height) * 0.3
        positions[pid] = [cx + r * math.cos(angle), cy + r * math.sin(angle)]

    # Init velocities
    velocities: dict[str, list[float]] = {pid: [0.0, 0.0] for pid in positions}

    # Node sizes (default 32x18)
    sizes: dict[str, tuple[float, float]] = {
        node["id"]: (float(node.get("w", 32)), float(node.get("h", 18))) for node in nodes
    }

    # Edge adjacency
    adjacency: dict[str, list[str]] = {pid: [] for pid in positions}
    for edge in edges:
        s, t = edge.get("source", ""), edge.get("target", "")
        if s in adjacency and t in adjacency:
            adjacency[s].append(t)
            adjacency[t].append(s)

    def _dist(pid1: str, pid2: str) -> float:
        x1, y1 = positions[pid1]
        x2, y2 = positions[pid2]
        return max(math.hypot(x2 - x1, y2 - y1), 1.0)

    # Collision distance
    COLL_DIST = 60.0
    COLL_FORCE = 200.0

    for _ in range(iterations):
        forces: dict[str, list[float]] = {pid: [0.0, 0.0] for pid in positions}

        # Repulsion (all pairs — n², acceptable for < 100 nodes)
        for i, pid1 in enumerate(positions):
            for j, pid2 in enumerate(positions):
                if j <= i:
                    continue
                d = _dist(pid1, pid2)
                if d < 1:
                    d = 1
                fx = (positions[pid1][0] - positions[pid2][0]) / d
                fy = (positions[pid1][1] - positions[pid2][1]) / d
                f = repulsion / (d * d)
                forces[pid1][0] += fx * f
                forces[pid1][1] += fy * f
                forces[pid2][0] -= fx * f
                forces[pid2][1] -= fy * f

        # Attraction (edges)
        for pid, neighbors in adjacency.items():
            for nb in neighbors:
                d = _dist(pid, nb)
                if d < 1:
                    d = 1
                fx = (positions[nb][0] - positions[pid][0]) / d
                fy = (positions[nb][1] - positions[pid][1]) / d
                f = attraction * d
                forces[pid][0] += fx * f
                forces[pid][1] += fy * f

        # Center gravity
        for pid in positions:
            forces[pid][0] += (cx - positions[pid][0]) * gravity
            forces[pid][1] += (cy - positions[pid][1]) * gravity

        # Collision
        for pid1 in positions:
            for pid2 in positions:
                if pid2 <= pid1:
                    continue
                d = _dist(pid1, pid2)
                if d < COLL_DIST and d > 0:
                    fx = (positions[pid1][0] - positions[pid2][0]) / d
                    fy = (positions[pid1][1] - positions[pid2][1]) / d
                    f = COLL_FORCE * (COLL_DIST - d) / COLL_DIST
                    forces[pid1][0] += fx * f
                    forces[pid1][1] += fy * f
                    forces[pid2][0] -= fx * f
                    forces[pid2][1] -= fy * f

        # Bounds
        for pid in positions:
            w, h = sizes[pid]
            positions[pid][0] = max(w / 2, min(width - w / 2, positions[pid][0]))
            positions[pid][1] = max(h / 2, min(height - h / 2, positions[pid][1]))

        # Velocity
        for pid in positions:
            velocities[pid][0] = (velocities[pid][0] + forces[pid][0]) * damping
            velocities[pid][1] = (velocities[pid][1] + forces[pid][1]) * damping
            positions[pid][0] += velocities[pid][0]
            positions[pid][1] += velocities[pid][1]

    # Overlap repair (2 passes)
    for _ in range(2):
        for pid1 in positions:
            for pid2 in positions:
                if pid2 <= pid1:
                    continue
                d = _dist(pid1, pid2)
                if d < COLL_DIST * 0.8 and d > 0:
                    fx = (positions[pid1][0] - positions[pid2][0]) / d * 0.5
                    fy = (positions[pid1][1] - positions[pid2][1]) / d * 0.5
                    positions[pid1][0] += fx * COLL_DIST
                    positions[pid1][1] += fy * COLL_DIST
                    positions[pid2][0] -= fx * COLL_DIST
                    positions[pid2][1] -= fy * COLL_DIST

    return [
        {"id": pid, "x": round(pos[0], 1), "y": round(pos[1], 1)}
        for pid, pos in sorted(positions.items())
    ]


def layout_graph(nodes: list[dict], edges: list[dict]) -> list[dict]:
    """Layout a graph with sensible defaults.

    Args:
        nodes: [{id, x?, y?, w?, h?}] — node data dicts.
        edges: [{source, target}] — edge data dicts.

    Returns:
        [{id, x, y}] — nodes with computed positions, sorted by ID.
    """
    return compute_layout(nodes, edges)
