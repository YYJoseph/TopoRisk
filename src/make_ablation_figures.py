#!/usr/bin/env python3
"""Create vector figures for the method overview and allocation ablations."""

from __future__ import annotations

import csv
from pathlib import Path

import matplotlib.pyplot as plt
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch, Circle


ROOT = Path(__file__).resolve().parent.parent
RESULTS = ROOT / "results" / "controlled" / "ablations"
FIGURES = ROOT / "figures"
BLUE = "#0072B2"
GREEN = "#009E73"
ORANGE = "#E69F00"
PURPLE = "#CC79A7"
GRAY = "#777777"
RED = "#D55E00"


def paper_style() -> None:
    plt.rcParams.update({
        "font.family": "DejaVu Sans",
        "font.size": 8,
        "axes.titlesize": 9,
        "axes.labelsize": 8,
        "xtick.labelsize": 7,
        "ytick.labelsize": 7,
        "legend.fontsize": 7,
        "axes.spines.top": False,
        "axes.spines.right": False,
        "pdf.fonttype": 42,
        "ps.fonttype": 42,
    })


def overview() -> None:
    paper_style()
    fig, ax = plt.subplots(figsize=(7.1, 2.35))
    ax.set_xlim(0, 12)
    ax.set_ylim(0, 4)
    ax.axis("off")

    nodes = {
        "retrieve": (0.8, 2.0),
        "plan A": (2.2, 3.0),
        "plan B": (2.2, 1.0),
        "merge": (3.8, 2.0),
        "write": (5.2, 2.0),
    }
    edges = [("retrieve", "plan A"), ("retrieve", "plan B"),
             ("plan A", "merge"), ("plan B", "merge"), ("merge", "write")]
    for left, right in edges:
        x1, y1 = nodes[left]
        x2, y2 = nodes[right]
        ax.add_patch(FancyArrowPatch((x1 + .25, y1), (x2 - .25, y2),
                                     arrowstyle="-|>", mutation_scale=8,
                                     linewidth=1.15, color="#5B6573"))
    for label, (x, y) in nodes.items():
        selected = label == "retrieve"
        terminal = label == "write"
        face = "#DDF3EA" if selected else ("#FCE8DF" if terminal else "white")
        edge = GREEN if selected else (RED if terminal else "#5B6573")
        ax.add_patch(Circle((x, y), .31, facecolor=face, edgecolor=edge, linewidth=1.6))
        ax.text(x, y, label.replace(" ", "\n"), ha="center", va="center", fontsize=7.2)
    ax.text(2.9, 3.64, "Dependency graph", ha="center", fontsize=9.2, fontweight="bold")
    ax.text(.8, 1.54, "$p=.22$", ha="center", fontsize=6.8, color=GREEN)
    ax.text(5.2, 1.54, "terminal", ha="center", fontsize=6.8, color=RED)
    ax.text(2.9, .20, "Two paths reconverge at one terminal",
            ha="center", fontsize=7.2, color="#3D4652")

    boxes = [
        (6.15, 2.70, 1.50, .76, "1  Propagate risk\nto terminals", BLUE),
        (7.95, 2.70, 1.70, .76, "2  Score marginal\nloss reduction", ORANGE),
        (9.95, 2.70, 1.35, .76, "3  Select within\nbudget", PURPLE),
        (8.02, 1.13, 1.60, .76, "4  Verify and\nupdate graph", GREEN),
    ]
    for x, y, w, h, text, color in boxes:
        ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.05",
                                    facecolor="white", edgecolor=color, linewidth=1.4))
        ax.text(x + w / 2, y + h / 2, text, ha="center", va="center", fontsize=7.25)
    for p1, p2 in [((7.66, 3.08), (7.93, 3.08)), ((9.66, 3.08), (9.93, 3.08)),
                   ((10.62, 2.68), (8.84, 1.92)), ((8.02, 1.51), (5.92, 2.0))]:
        ax.add_patch(FancyArrowPatch(p1, p2, arrowstyle="-|>", mutation_scale=8,
                                     linewidth=1.0, color="#555555",
                                     connectionstyle="arc3,rad=0.0"))
    ax.text(8.82, .28,
            "Recompute after every selected check",
            ha="center", fontsize=7.3, color="#3D4652")
    ax.text(.15, 3.72, "(a)", fontsize=9, fontweight="bold")
    ax.text(6.0, 3.72, "(b)", fontsize=9, fontweight="bold")
    fig.tight_layout(pad=.15)
    fig.savefig(FIGURES / "figures_method_overview.pdf", bbox_inches="tight")
    fig.savefig(FIGURES / "figures_method_overview.png", dpi=240, bbox_inches="tight")
    plt.close(fig)


def allocation_evidence() -> None:
    paper_style()
    budget = list(csv.DictReader((RESULTS / "budget_curve.csv").open()))
    optimality = list(csv.DictReader((RESULTS / "exact_optimality.csv").open()))
    fig, axes = plt.subplots(1, 2, figsize=(7.0, 2.55))

    specs = [
        ("local-risk", "Local risk", BLUE, "o"),
        ("risk-x-influence", "Risk × influence", RED, "s"),
        ("static-toporisk", "Static TopoRisk", ORANGE, "D"),
        ("toporisk", "TopoRisk", GREEN, "^"),
    ]
    for method, label, color, marker in specs:
        rows = [r for r in budget if r["method"] == method]
        x = [100 * float(r["budget"]) for r in rows]
        y = [float(r["terminal_error"]) for r in rows]
        e = [float(r["terminal_error_ci95"]) for r in rows]
        axes[0].errorbar(x, y, yerr=e, label=label, color=color, marker=marker,
                         linewidth=1.4, markersize=4, capsize=2)
    axes[0].set_xlabel("Verification budget (% of nodes)")
    axes[0].set_ylabel("Corrupted-sink fraction ↓")
    axes[0].grid(alpha=.25, linewidth=.5)
    axes[0].legend(frameon=False, fontsize=6.7, ncol=2, columnspacing=.8,
                   handlelength=1.8, loc="upper right")
    axes[0].set_title("Budget sweep on 240 forty-node DAGs", fontsize=9)

    kinds = ["chain", "tree", "diamond", "random"]
    x = list(range(len(kinds)))
    greedy = []
    static = []
    for kind in kinds:
        rows = [r for r in optimality if r["graph"] == kind]
        greedy.append(100 * sum(float(r["greedy_fraction_of_optimal_gain"]) for r in rows) / len(rows))
        static.append(100 * sum(float(r["static_fraction_of_optimal_gain"]) for r in rows) / len(rows))
    width = .34
    axes[1].bar([v - width / 2 for v in x], static, width, label="Static TopoRisk",
                color=ORANGE, edgecolor="black", linewidth=.4)
    axes[1].bar([v + width / 2 for v in x], greedy, width, label="TopoRisk",
                color=GREEN, edgecolor="black", linewidth=.4)
    axes[1].set_xticks(x, [k.capitalize() for k in kinds], rotation=15)
    axes[1].set_ylim(80, 101)
    axes[1].set_ylabel("Fraction of optimal gain (%) ↑")
    axes[1].set_title("Exact optimum on 200 twelve-node DAGs", fontsize=9)
    axes[1].grid(axis="y", alpha=.25, linewidth=.5)
    axes[1].legend(frameon=False, fontsize=7, loc="lower left")

    fig.tight_layout(pad=.5, w_pad=1.0)
    fig.savefig(FIGURES / "figures_allocation_evidence.pdf", bbox_inches="tight")
    fig.savefig(FIGURES / "figures_allocation_evidence.png", dpi=240, bbox_inches="tight")
    plt.close(fig)


if __name__ == "__main__":
    overview()
    allocation_evidence()
