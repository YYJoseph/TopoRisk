#!/usr/bin/env python3
"""Check public headline values using only packaged aggregate artifacts."""

from __future__ import annotations

import csv
import json
import math
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent


def close(value: float, expected: float, tolerance: float = 5e-4) -> None:
    if not math.isclose(value, expected, abs_tol=tolerance, rel_tol=0.0):
        raise AssertionError(f"expected {expected}, found {value}")


def rows(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


controlled = rows(ROOT / "results" / "controlled" / "main_results.csv")
for budget, local_expected, topo_expected in [
    (0.10, 0.261, 0.147),
    (0.20, 0.172, 0.059),
]:
    subset = [r for r in controlled if float(r["budget"]) == budget]
    for method, expected in [("local-risk", local_expected), ("toporisk", topo_expected)]:
        values = [float(r["terminal_error"]) for r in subset if r["method"] == method]
        close(sum(values) / len(values), expected)

fixed = json.loads((ROOT / "results" / "fixed_trace_summary" / "summary.json").read_text())
assert fixed["workflows"] == 18
close(fixed["deepseek_scores_qwen_verifier"]["paired_difference"], -0.526)
close(fixed["qwen_scores_deepseek_verifier"]["paired_difference"], -0.544)

online = json.loads((ROOT / "results" / "online_summary" / "combined_summary.json").read_text())
assert online["paired_runs"] == 45
assert online["baseline_success"] == online["verified_success"] == 39
assert online["paired_wins"] == online["paired_losses"] == 2
close(online["relative_total_cost_overhead_percent"], 11.6, tolerance=0.05)

glm = json.loads((ROOT / "results" / "online_summary" / "glm_airline_summary.json").read_text())
assert glm["paired_runs"] == 45
assert glm["baseline_success"] == 40
assert glm["verified_success"] == 39
assert glm["baseline_database_match"] == glm["verified_database_match"] == 42
assert (glm["paired_wins"], glm["paired_losses"], glm["paired_ties"]) == (2, 3, 40)
close(glm["success_difference_percentage_points"], -2.2222222222)
assert glm["task_cluster_bootstrap_95_ci_percentage_points"] == [
    -11.1111111111,
    6.6666666667,
]

real_topology = json.loads(
    (ROOT / "results" / "real_topology_summary" / "summary.json").read_text()
)
assert real_topology["graphs"] == 44
assert real_topology["budget_2"]["dynamic_toporisk_exact_optimal_graphs"] == 44
assert real_topology["budget_2"]["static_marginal_exact_optimal_graphs"] == 38
assert real_topology["budget_2"]["wins_losses_ties"] == [6, 0, 38]
close(real_topology["budget_2"]["dynamic_toporisk_mean_loss"], 0.136080)
close(real_topology["budget_2"]["static_marginal_mean_loss"], 0.140501)
close(real_topology["budget_3"]["dynamic_toporisk_mean_loss"], 0.056320)
close(real_topology["budget_3"]["static_marginal_mean_loss"], 0.060765)

print("PASS: packaged aggregate artifacts match the public headline values.")
