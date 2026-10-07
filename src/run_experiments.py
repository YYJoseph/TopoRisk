#!/usr/bin/env python3
"""Controlled Monte Carlo study for TopoRisk.

The simulator models an agent workflow as a DAG. A node can fail intrinsically;
an erroneous parent can corrupt a child with an edge-specific probability.
Verifying a selected node occurs after that node executes and before its output
is consumed, and repairs a detected error with configurable sensitivity.
"""
from __future__ import annotations

import argparse
import csv
import math
import random
from dataclasses import dataclass
from pathlib import Path
from statistics import mean, stdev


@dataclass
class Graph:
    parents: list[list[tuple[int, float]]]
    children: list[list[tuple[int, float]]]
    p: list[float]
    sinks: list[int]


def make_graph(kind: str, n: int, rng: random.Random) -> Graph:
    edges: set[tuple[int, int]] = set()
    if kind == "chain":
        edges.update((i, i + 1) for i in range(n - 1))
    elif kind == "tree":
        edges.update(((i - 1) // 2, i) for i in range(1, n))
    elif kind == "diamond":
        width = 5
        layers = [list(range(i, min(i + width, n))) for i in range(0, n, width)]
        for a, b in zip(layers, layers[1:]):
            for u in a:
                for v in b:
                    if rng.random() < 0.48:
                        edges.add((u, v))
            for v in b:
                if not any(y == v for _, y in edges):
                    edges.add((rng.choice(a), v))
    elif kind == "random":
        for v in range(1, n):
            candidates = list(range(max(0, v - 10), v))
            rng.shuffle(candidates)
            for u in candidates[: rng.randint(1, min(3, len(candidates)))]:
                edges.add((u, v))
    else:
        raise ValueError(kind)
    parents = [[] for _ in range(n)]
    children = [[] for _ in range(n)]
    for u, v in sorted(edges):
        q = rng.uniform(0.42, 0.88)
        children[u].append((v, q))
        parents[v].append((u, q))
    # Most steps are reliable; a minority are difficult.
    p = [min(0.32, max(0.015, rng.betavariate(1.7, 14.0))) for _ in range(n)]
    sinks = [i for i, ch in enumerate(children) if not ch]
    return Graph(parents, children, p, sinks)


def forward_risk(g: Graph) -> list[float]:
    r = []
    for i in range(len(g.p)):
        survive = 1.0 - g.p[i]
        for u, q in g.parents[i]:
            survive *= 1.0 - r[u] * q
        r.append(1.0 - survive)
    return r


def backward_influence(g: Graph) -> list[float]:
    # Expected weighted terminal exposure under an independence approximation.
    d = [0.0] * len(g.p)
    sink_set = set(g.sinks)
    for i in reversed(range(len(g.p))):
        base = 1.0 if i in sink_set else 0.0
        d[i] = base + sum(q * d[v] for v, q in g.children[i])
    return d


def expected_terminal_error(g: Graph, selected: set[int], sensitivity: float = 0.90) -> float:
    """Noisy-OR mean-field estimate used by the scheduler, not the evaluator."""
    r: list[float] = []
    for i in range(len(g.p)):
        survive = 1.0 - g.p[i]
        for u, q in g.parents[i]:
            survive *= 1.0 - r[u] * q
        value = 1.0 - survive
        if i in selected:
            value *= 1.0 - sensitivity
        r.append(value)
    return sum(r[s] for s in g.sinks) / len(g.sinks)


def choose(g: Graph, method: str, k: int, rng: random.Random) -> set[int]:
    r = forward_risk(g)
    inf = backward_influence(g)
    descendants = [0] * len(g.p)
    for i in reversed(range(len(g.p))):
        descendants[i] = len(g.children[i]) + sum(descendants[v] for v, _ in g.children[i])
    if method == "random":
        return set(rng.sample(range(len(g.p)), k))
    if method == "local-risk":
        score = r
    elif method == "uncertainty":
        score = [x * (1 - x) for x in r]
    elif method == "centrality":
        score = descendants
    elif method == "risk-x-count":
        score = [r[i] * (1 + descendants[i]) for i in range(len(r))]
    elif method == "risk-x-influence":
        # Static structure-aware baseline. Unlike descendant count, influence
        # weights paths by edge transmission and terminal exposure, but does
        # not recompute after selections and can double-count reconvergence.
        score = [r[i] * inf[i] for i in range(len(r))]
    elif method == "toporisk":
        # Greedy marginal terminal-risk reduction. Recompute after each choice so
        # overlapping downstream paths exhibit diminishing returns.
        selected: set[int] = set()
        remaining = set(range(len(g.p)))
        base = expected_terminal_error(g, selected)
        for _ in range(k):
            best = min(remaining)
            best_loss = base
            for i in sorted(remaining):
                loss = expected_terminal_error(g, selected | {i})
                if loss < best_loss - 1e-15:
                    best, best_loss = i, loss
            selected.add(best); remaining.remove(best); base = best_loss
        return selected
    else:
        raise ValueError(method)
    return set(sorted(range(len(score)), key=lambda i: (-score[i], i))[:k])


def episode(g: Graph, selected: set[int], sensitivity: float, rng: random.Random) -> tuple[float, bool]:
    wrong: list[bool] = []
    for i in range(len(g.p)):
        bad = rng.random() < g.p[i]
        if not bad:
            for u, q in g.parents[i]:
                if wrong[u] and rng.random() < q:
                    bad = True
                    break
        if bad and i in selected and rng.random() < sensitivity:
            bad = False
        wrong.append(bad)
    frac = sum(wrong[s] for s in g.sinks) / len(g.sinks)
    return frac, frac == 0.0


def ci(values: list[float]) -> tuple[float, float]:
    m = mean(values)
    return m, 1.96 * stdev(values) / math.sqrt(len(values))


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", type=Path, default=Path("results"))
    ap.add_argument("--graphs", type=int, default=240)
    ap.add_argument("--episodes", type=int, default=400)
    ap.add_argument("--seed", type=int, default=7)
    args = ap.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)
    kinds = ["chain", "tree", "diamond", "random"]
    methods = ["random", "local-risk", "uncertainty", "centrality", "risk-x-count",
               "risk-x-influence", "toporisk"]
    budgets = [0.10, 0.20]
    rows = []
    master = random.Random(args.seed)
    graphs = [(kind, make_graph(kind, 40, random.Random(master.randrange(2**63))))
              for kind in kinds for _ in range(args.graphs // len(kinds))]
    for budget in budgets:
        per = {(kind, m): [] for kind in kinds for m in methods}
        success = {(kind, m): [] for kind in kinds for m in methods}
        for gi, (kind, g) in enumerate(graphs):
            k = max(1, round(len(g.p) * budget))
            for mi, method in enumerate(methods):
                sel_rng = random.Random(args.seed * 10_000 + gi * 100 + mi)
                selected = choose(g, method, k, sel_rng)
                vals, oks = [], []
                for ep in range(args.episodes):
                    # Common seed across methods reduces comparison variance.
                    erng = random.Random(args.seed * 10**8 + gi * 10_000 + ep)
                    frac, ok = episode(g, selected, 0.90, erng)
                    vals.append(frac)
                    oks.append(float(ok))
                per[(kind, method)].append(mean(vals))
                success[(kind, method)].append(mean(oks))
        for kind in kinds:
            for method in methods:
                m, h = ci(per[(kind, method)])
                sm, sh = ci(success[(kind, method)])
                rows.append({"budget": budget, "graph": kind, "method": method,
                             "terminal_error": m, "terminal_error_ci95": h,
                             "workflow_success": sm, "workflow_success_ci95": sh})
    with (args.out / "main_results.csv").open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=rows[0].keys()); w.writeheader(); w.writerows(rows)

    # Robustness: planner uses perturbed risk/propagation estimates, evaluation uses the true graph.
    robust = []
    for noise in [0.0, 0.25, 0.50, 0.75]:
        vals = {m: [] for m in ["local-risk", "risk-x-count", "risk-x-influence", "toporisk"]}
        for gi, (_, g) in enumerate(graphs):
            nrng = random.Random(args.seed + 99_000 + gi)
            est = Graph(g.parents, [[] for _ in g.children], [], g.sinks)
            est.p = [min(.49, max(.005, p * math.exp(nrng.gauss(0, noise)))) for p in g.p]
            est.parents = [[] for _ in g.parents]
            for u, ch in enumerate(g.children):
                for v, q in ch:
                    qh = min(.98, max(.05, q * math.exp(nrng.gauss(0, noise))))
                    est.children[u].append((v, qh)); est.parents[v].append((u, qh))
            for mi, method in enumerate(vals):
                selected = choose(est, method, 4, random.Random(gi + mi))
                ev = []
                for ep in range(args.episodes):
                    frac, _ = episode(g, selected, .90, random.Random(args.seed * 10**8 + gi * 10_000 + ep))
                    ev.append(frac)
                vals[method].append(mean(ev))
        for method, x in vals.items():
            m, h = ci(x); robust.append({"noise": noise, "method": method, "terminal_error": m, "ci95": h})
    with (args.out / "robustness.csv").open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=robust[0].keys()); w.writeheader(); w.writerows(robust)

    print(f"wrote {args.out / 'main_results.csv'} and {args.out / 'robustness.csv'}")


if __name__ == "__main__":
    main()
