#!/usr/bin/env python3
"""Budget, recomputation, and exact-optimum studies for TopoRisk.

The script is local and deterministic. It reuses the simulator in
``run_experiments.py`` and makes no model or network calls.
"""

from __future__ import annotations

import argparse
import csv
import itertools
import math
import random
from pathlib import Path
from statistics import mean, stdev

from run_experiments import Graph, choose, episode, expected_terminal_error, make_graph


def ci95(values: list[float]) -> float:
    return 1.96 * stdev(values) / math.sqrt(len(values))


def static_toporisk(g: Graph, k: int) -> set[int]:
    base = expected_terminal_error(g, set())
    gains = [base - expected_terminal_error(g, {i}) for i in range(len(g.p))]
    return set(sorted(range(len(g.p)), key=lambda i: (-gains[i], i))[:k])


def exact_optimum(g: Graph, k: int) -> tuple[set[int], float]:
    best_set: set[int] | None = None
    best_loss = float("inf")
    for items in itertools.combinations(range(len(g.p)), k):
        selected = set(items)
        loss = expected_terminal_error(g, selected)
        if loss < best_loss - 1e-15:
            best_set, best_loss = selected, loss
    assert best_set is not None
    return best_set, best_loss


def write_csv(path: Path, rows: list[dict]) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", type=Path, default=Path("results/ablations"))
    parser.add_argument("--graphs", type=int, default=240)
    parser.add_argument("--episodes", type=int, default=400)
    parser.add_argument("--seed", type=int, default=7)
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)

    kinds = ["chain", "tree", "diamond", "random"]
    master = random.Random(args.seed)
    graphs = [
        (kind, make_graph(kind, 40, random.Random(master.randrange(2**63))))
        for kind in kinds
        for _ in range(args.graphs // len(kinds))
    ]

    budget_rows: list[dict] = []
    methods = ["local-risk", "risk-x-count", "risk-x-influence", "static-toporisk", "toporisk"]
    for budget in [0.025, 0.05, 0.10, 0.15, 0.20, 0.30]:
        per_method = {method: [] for method in methods}
        success_method = {method: [] for method in methods}
        for graph_id, (_, graph) in enumerate(graphs):
            k = max(1, round(len(graph.p) * budget))
            for method_id, method in enumerate(methods):
                if method == "static-toporisk":
                    selected = static_toporisk(graph, k)
                else:
                    selected = choose(
                        graph, method, k,
                        random.Random(args.seed * 10_000 + graph_id * 100 + method_id),
                    )
                losses, successes = [], []
                for ep in range(args.episodes):
                    value, success = episode(
                        graph,
                        selected,
                        0.90,
                        random.Random(args.seed * 10**8 + graph_id * 10_000 + ep),
                    )
                    losses.append(value)
                    successes.append(float(success))
                per_method[method].append(mean(losses))
                success_method[method].append(mean(successes))
        for method in methods:
            budget_rows.append({
                "budget": budget,
                "method": method,
                "terminal_error": mean(per_method[method]),
                "terminal_error_ci95": ci95(per_method[method]),
                "workflow_success": mean(success_method[method]),
                "workflow_success_ci95": ci95(success_method[method]),
            })
    write_csv(args.out / "budget_curve.csv", budget_rows)

    # Exact comparison is feasible on twelve-node graphs with three checks.
    small_master = random.Random(args.seed + 331_007)
    optimality_rows: list[dict] = []
    for kind in kinds:
        for graph_index in range(50):
            graph = make_graph(kind, 12, random.Random(small_master.randrange(2**63)))
            k = 3
            optimum, optimum_loss = exact_optimum(graph, k)
            greedy = choose(graph, "toporisk", k, random.Random(0))
            static = static_toporisk(graph, k)
            greedy_loss = expected_terminal_error(graph, greedy)
            static_loss = expected_terminal_error(graph, static)
            no_audit = expected_terminal_error(graph, set())
            denom = max(1e-12, no_audit - optimum_loss)
            optimality_rows.append({
                "graph": kind,
                "graph_index": graph_index,
                "budget_nodes": k,
                "no_audit_loss": no_audit,
                "optimal_loss": optimum_loss,
                "greedy_loss": greedy_loss,
                "static_loss": static_loss,
                "greedy_excess_loss": greedy_loss - optimum_loss,
                "static_excess_loss": static_loss - optimum_loss,
                "greedy_fraction_of_optimal_gain": (no_audit - greedy_loss) / denom,
                "static_fraction_of_optimal_gain": (no_audit - static_loss) / denom,
                "greedy_exact_match": int(greedy == optimum),
                "static_exact_match": int(static == optimum),
            })
    write_csv(args.out / "exact_optimality.csv", optimality_rows)

    print(f"wrote {args.out / 'budget_curve.csv'}")
    print(f"wrote {args.out / 'exact_optimality.csv'}")


if __name__ == "__main__":
    main()
