#!/usr/bin/env python3
"""Evaluate multi-check allocation on DAGs recovered from frozen tau3 traces."""

from __future__ import annotations

import argparse
import csv
import hashlib
import itertools
import json
import math
import random
import re
from collections import Counter, defaultdict
from pathlib import Path


WRITE_PREFIXES = (
    "book_", "cancel_", "create_", "delete_", "disable_", "enable_",
    "exchange_", "make_", "modify_", "refuel_", "resume_", "return_",
    "send_", "suspend_", "transfer_", "update_",
)
TOKEN = re.compile(r"[A-Za-z][A-Za-z0-9_#-]{3,}|\d{5,}")
STOP = {"true", "false", "none", "null", "success", "error", "assistant", "user"}


def normalize_call(raw):
    fn = raw.get("function", raw)
    args = fn.get("arguments", {})
    if isinstance(args, str):
        try:
            args = json.loads(args)
        except json.JSONDecodeError:
            args = {"raw": args}
    return {"name": fn.get("name", ""), "arguments": args}


def tokens(value):
    text = json.dumps(value, sort_keys=True, ensure_ascii=False)
    return {x for x in TOKEN.findall(text) if x.lower() not in STOP and not x.isalpha()}


def extract_trace(sim):
    calls, results = [], {}
    for message in sim.get("messages", []):
        if message.get("role") == "tool":
            results[message.get("tool_call_id")] = message.get("content")
        if message.get("role") != "assistant":
            continue
        for raw in message.get("tool_calls") or []:
            call = normalize_call(raw)
            calls.append({
                "name": call["name"],
                "arguments": call["arguments"],
                "call_id": raw.get("id"),
            })
    for call in calls:
        call["input_tokens"] = tokens(call["arguments"])
        call["output_tokens"] = tokens(results.get(call["call_id"], ""))
    return calls


def graph_from_calls(calls):
    edges = set()
    for i, source in enumerate(calls):
        produced = source["input_tokens"] | source["output_tokens"]
        for j in range(i + 1, len(calls)):
            shared = produced & calls[j]["input_tokens"]
            if shared:
                edges.add((i, j, tuple(sorted(shared))))
    terminals = [i for i, call in enumerate(calls) if call["name"].startswith(WRITE_PREFIXES)]
    return sorted(edges), terminals


def terminal_reach(n, edges, terminals):
    children = defaultdict(list)
    for a, b, _ in edges:
        children[a].append(b)
    terminal_set = set(terminals)
    reach = {}
    for node in range(n):
        seen, stack = set(), list(children[node])
        while stack:
            current = stack.pop()
            if current in seen:
                continue
            seen.add(current)
            stack.extend(children[current])
        reach[node] = seen & terminal_set
        if node in terminal_set:
            reach[node].add(node)
    return reach


def forward_loss(p, edges, terminals, weights, verified=frozenset(), eta=0.9):
    """Noisy-OR modeled loss with the same repair semantics as Eq. (3).

    Verification acts after intrinsic and propagated errors reach a node.  A
    selected check therefore scales the node's complete pre-verification risk,
    rather than removing only its intrinsic failure probability.
    """
    parents = defaultdict(list)
    for a, b, _, q in edges:
        parents[b].append((a, q))
    risk = {}
    for node in range(len(p)):
        survive = 1.0 - p[node]
        for parent, q in parents[node]:
            survive *= 1.0 - risk[parent] * q
        value = 1.0 - survive
        if node in verified:
            value *= 1.0 - eta
        risk[node] = value
    return sum(weights[t] * risk[t] for t in terminals) / sum(weights[t] for t in terminals)


def static_influence(n, edges, terminals, weights):
    children = defaultdict(list)
    for a, b, _, q in edges:
        children[a].append((b, q))
    influence = {}
    for node in range(n - 1, -1, -1):
        influence[node] = (weights[node] if node in terminals else 0.0) + sum(
            q * influence[child] for child, q in children[node]
        )
    return influence


def select(p, edges, terminals, weights, budget, method, seed_key):
    n = len(p)
    base = forward_loss(p, edges, terminals, weights)
    single = {i: base - forward_loss(p, edges, terminals, weights, {i}) for i in range(n)}
    influence = static_influence(n, edges, terminals, weights)
    tie = lambda i: hashlib.sha256(f"{seed_key}:{method}:{i}".encode()).hexdigest()
    if method == "dynamic":
        chosen = set()
        for _ in range(budget):
            current = forward_loss(p, edges, terminals, weights, chosen)
            values = {i: current - forward_loss(p, edges, terminals, weights, chosen | {i})
                      for i in range(n) if i not in chosen}
            chosen.add(max(values, key=lambda i: (values[i], tie(i))))
        return chosen
    if method == "static_marginal":
        score = single
    elif method == "risk_influence":
        score = {i: p[i] * influence[i] for i in range(n)}
    elif method == "local_risk":
        score = {i: p[i] for i in range(n)}
    elif method == "random":
        score = {i: int(tie(i), 16) for i in range(n)}
    else:
        raise ValueError(method)
    return set(sorted(score, key=lambda i: (score[i], tie(i)), reverse=True)[:budget])


def bootstrap(values, samples=20000, seed=20261008):
    rng = random.Random(seed)
    draws = sorted(sum(rng.choice(values) for _ in values) / len(values) for _ in range(samples))
    return [draws[int(.025 * samples)], draws[int(.975 * samples)]]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path("../../work/tau3-bench/data/simulations"))
    parser.add_argument("--out", type=Path, default=Path("results"))
    args = parser.parse_args()
    names = [
        "natural_error_harvest_10_29", "natural_error_stress_30_39_t07",
        "qwen_agent_probe_40_44", "expand50_noverify", "multitrial30_noverify",
        "toporisk_pilot10_none", "toporisk_stage4_tasks45_49_baseline",
        "toporisk_airline_main_baseline", "toporisk_glm53_airline_main_noverify",
    ]
    raw, seen, counts = [], set(), Counter()
    for name in names:
        path = args.root / name / "results.json"
        if not path.exists():
            counts["missing_source"] += 1
            continue
        data = json.loads(path.read_text())
        domain = data.get("info", {}).get("environment_info", {}).get("domain_name", "unknown")
        for sim in data.get("simulations", []):
            calls = extract_trace(sim)
            signature = json.dumps([(x["name"], x["arguments"]) for x in calls], sort_keys=True)
            digest = hashlib.sha256(signature.encode()).hexdigest()
            if digest in seen:
                counts["duplicate"] += 1
                continue
            seen.add(digest)
            edges0, terminals = graph_from_calls(calls)
            reach = terminal_reach(len(calls), edges0, terminals)
            overlap = any(reach[i] & reach[j] for i in range(len(calls)) for j in range(i + 1, len(calls)))
            if len(calls) < 6:
                counts["fewer_than_6_calls"] += 1; continue
            if len(terminals) < 2:
                counts["fewer_than_2_write_terminals"] += 1; continue
            if not overlap:
                counts["no_overlapping_terminal_reach"] += 1; continue
            raw.append((name, domain, sim, calls, edges0, terminals))

    methods = ("random", "local_risk", "risk_influence", "static_marginal", "dynamic")
    rows = []
    for index, (source, domain, sim, calls, edges0, terminals) in enumerate(raw):
        rng = random.Random(20261008 + index)
        p = [rng.uniform(.04, .28) for _ in calls]
        weights = {i: rng.uniform(.8, 2.4) for i in range(len(calls))}
        edges = [(a, b, shared, rng.uniform(.45, .90)) for a, b, shared in edges0]
        empty = forward_loss(p, edges, terminals, weights)
        for budget in (2, 3):
            if budget >= len(calls):
                continue
            optimum = min(
                (forward_loss(p, edges, terminals, weights, set(choice)), set(choice))
                for choice in itertools.combinations(range(len(calls)), budget)
            )[0]
            for method in methods:
                chosen = select(p, edges, terminals, weights, budget, method, sim["id"])
                loss = forward_loss(p, edges, terminals, weights, chosen)
                fraction = (empty - loss) / (empty - optimum) if empty > optimum else 1.0
                rows.append({
                    "graph": index, "source": source, "domain": domain,
                    "task_id": sim.get("task_id"), "nodes": len(calls),
                    "edges": len(edges), "terminals": len(terminals), "budget": budget,
                    "method": method, "loss": loss, "fraction_optimal_gain": fraction,
                    "exact_optimal": math.isclose(loss, optimum, abs_tol=1e-12),
                    "selected": ";".join(map(str, sorted(chosen))),
                })
    args.out.mkdir(parents=True, exist_ok=True)
    with (args.out / "per_graph.csv").open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=rows[0].keys()); writer.writeheader(); writer.writerows(rows)
    summary = {"graphs": len(raw), "exclusions": dict(counts), "budgets": {}}
    for budget in (2, 3):
        block = [r for r in rows if r["budget"] == budget]
        by_method = {}
        for method in methods:
            mr = [r for r in block if r["method"] == method]
            by_method[method] = {
                "mean_loss": sum(r["loss"] for r in mr) / len(mr),
                "mean_fraction_optimal_gain": sum(r["fraction_optimal_gain"] for r in mr) / len(mr),
                "exact_optimal_graphs": sum(r["exact_optimal"] for r in mr),
            }
        dyn = {r["graph"]: r for r in block if r["method"] == "dynamic"}
        comparisons = {}
        for baseline in ("static_marginal", "risk_influence"):
            sta = {r["graph"]: r for r in block if r["method"] == baseline}
            diff = [dyn[g]["loss"] - sta[g]["loss"] for g in dyn]
            comparisons[baseline] = {
                "dynamic_minus_baseline_mean": sum(diff) / len(diff),
                "bootstrap_95_ci": bootstrap(diff),
                "wins_losses_ties": [sum(x < -1e-12 for x in diff), sum(x > 1e-12 for x in diff), sum(abs(x) <= 1e-12 for x in diff)],
            }
        summary["budgets"][str(budget)] = {
            "methods": by_method,
            "paired_comparisons": comparisons,
        }
    (args.out / "summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
