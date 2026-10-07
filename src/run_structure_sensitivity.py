#!/usr/bin/env python3
"""Stress tests for graph misspecification, workflow size, and verifier quality."""

from __future__ import annotations

import argparse
import csv
import math
import random
from pathlib import Path
from statistics import mean, stdev

from run_experiments import Graph, choose, episode, make_graph


KINDS = ["chain", "tree", "diamond", "random"]


def ci95(values: list[float]) -> float:
    return 1.96 * stdev(values) / math.sqrt(len(values))


def write_csv(path: Path, rows: list[dict]) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def perturb_edges(graph: Graph, drop_rate: float, add_rate: float, rng: random.Random) -> Graph:
    n = len(graph.p)
    true_edges = {(u, v): q for u, children in enumerate(graph.children) for v, q in children}
    kept = {(u, v): q for (u, v), q in true_edges.items() if rng.random() >= drop_rate}
    target_additions = round(len(true_edges) * add_rate)
    candidates = [(u, v) for u in range(n) for v in range(u + 1, n)
                  if (u, v) not in true_edges]
    rng.shuffle(candidates)
    for u, v in candidates[:target_additions]:
        kept[(u, v)] = rng.uniform(0.42, 0.88)
    parents = [[] for _ in range(n)]
    children = [[] for _ in range(n)]
    for (u, v), q in sorted(kept.items()):
        children[u].append((v, q))
        parents[v].append((u, q))
    # Terminal outputs are part of the workflow specification and remain known;
    # only dependency edges are perturbed.
    return Graph(parents=parents, children=children, p=list(graph.p), sinks=list(graph.sinks))


def evaluate(graph: Graph, selected: set[int], sensitivity: float,
             episodes: int, seed_base: int) -> float:
    return mean([
        episode(graph, selected, sensitivity, random.Random(seed_base + ep))[0]
        for ep in range(episodes)
    ])


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", type=Path, default=Path("results/structure_sensitivity"))
    parser.add_argument("--graphs", type=int, default=240)
    parser.add_argument("--episodes", type=int, default=400)
    parser.add_argument("--seed", type=int, default=7)
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)

    master = random.Random(args.seed)
    graphs = [(kind, make_graph(kind, 40, random.Random(master.randrange(2**63))))
              for kind in KINDS for _ in range(args.graphs // len(KINDS))]

    topology_rows: list[dict] = []
    conditions = [
        ("exact", 0.0, 0.0),
        ("drop", 0.1, 0.0), ("drop", 0.2, 0.0), ("drop", 0.3, 0.0), ("drop", 0.5, 0.0),
        ("add", 0.0, 0.1), ("add", 0.0, 0.2), ("add", 0.0, 0.3), ("add", 0.0, 0.5),
        ("mixed", 0.1, 0.1), ("mixed", 0.2, 0.2), ("mixed", 0.3, 0.3),
    ]
    for label, drop, add in conditions:
        values = {"local-risk": [], "toporisk": []}
        for graph_id, (_, graph) in enumerate(graphs):
            estimated = perturb_edges(
                graph, drop, add,
                random.Random(args.seed * 1_000_003 + graph_id * 101 + int(drop * 100) * 3 + int(add * 100)),
            )
            for method_id, method in enumerate(values):
                selected = choose(estimated, method, 4, random.Random(graph_id + method_id))
                values[method].append(evaluate(
                    graph, selected, .90, args.episodes,
                    args.seed * 10**8 + graph_id * 10_000,
                ))
        for method, observed in values.items():
            topology_rows.append({
                "condition": label,
                "drop_rate": drop,
                "add_rate": add,
                "method": method,
                "terminal_error": mean(observed),
                "terminal_error_ci95": ci95(observed),
            })
    write_csv(args.out / "topology_misspecification.csv", topology_rows)

    sensitivity_rows: list[dict] = []
    for sensitivity in [.50, .70, .90, 1.00]:
        values = {"local-risk": [], "toporisk": []}
        for graph_id, (_, graph) in enumerate(graphs):
            for method_id, method in enumerate(values):
                selected = choose(graph, method, 4, random.Random(graph_id + method_id))
                values[method].append(evaluate(
                    graph, selected, sensitivity, args.episodes,
                    args.seed * 10**8 + graph_id * 10_000,
                ))
        for method, observed in values.items():
            sensitivity_rows.append({
                "sensitivity": sensitivity,
                "method": method,
                "terminal_error": mean(observed),
                "terminal_error_ci95": ci95(observed),
            })
    write_csv(args.out / "verifier_sensitivity.csv", sensitivity_rows)

    size_rows: list[dict] = []
    size_master = random.Random(args.seed + 884_221)
    for n in [20, 40, 80, 160]:
        size_graphs = [(kind, make_graph(kind, n, random.Random(size_master.randrange(2**63))))
                       for kind in KINDS for _ in range(30)]
        values = {"local-risk": [], "toporisk": []}
        for graph_id, (_, graph) in enumerate(size_graphs):
            k = max(1, round(.10 * n))
            for method_id, method in enumerate(values):
                selected = choose(graph, method, k, random.Random(graph_id + method_id))
                values[method].append(evaluate(
                    graph, selected, .90, 200,
                    args.seed * 10**8 + n * 1_000_000 + graph_id * 1_000,
                ))
        for method, observed in values.items():
            size_rows.append({
                "nodes": n,
                "graphs": len(size_graphs),
                "episodes_per_graph": 200,
                "method": method,
                "terminal_error": mean(observed),
                "terminal_error_ci95": ci95(observed),
            })
    write_csv(args.out / "workflow_size.csv", size_rows)

    print(f"wrote three stress-test tables to {args.out}")


if __name__ == "__main__":
    main()
