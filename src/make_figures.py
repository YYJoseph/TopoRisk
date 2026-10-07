#!/usr/bin/env python3
"""Render paper figures with one color-blind-safe visual system."""

from __future__ import annotations

import csv
from pathlib import Path

import matplotlib.pyplot as plt


ROOT = Path(__file__).resolve().parent.parent
RESULTS = ROOT / "results" / "controlled"
FIGURES = ROOT / "figures"
BLUE = "#0072B2"
GREEN = "#009E73"
ORANGE = "#E69F00"
PURPLE = "#CC79A7"
RED = "#D55E00"
GRAY = "#7A7A7A"


def style() -> None:
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
        "axes.axisbelow": True,
        "pdf.fonttype": 42,
        "ps.fonttype": 42,
    })


def read(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def main_bars() -> None:
    rows = read(RESULTS / "main_results.csv")
    methods = ["random", "local-risk", "centrality", "risk-x-count",
               "risk-x-influence", "toporisk"]
    labels = ["Random", "Local risk", "Centrality", "Risk × count",
              "Risk × influence", "TopoRisk"]
    colors = [GRAY, BLUE, ORANGE, PURPLE, RED, GREEN]
    fig, axes = plt.subplots(1, 2, figsize=(7.1, 2.65), sharey=True)
    for ax, budget in zip(axes, ["0.1", "0.2"]):
        data = {
            method: [float(r["terminal_error"]) for r in rows
                     if r["budget"] == budget and r["method"] == method]
            for method in methods
        }
        means = [sum(data[m]) / len(data[m]) for m in methods]
        ax.bar(range(len(methods)), means, color=colors,
               edgecolor="#333333", linewidth=.45)
        ax.set_title(f"Audit budget: {int(float(budget) * 100)}%")
        ax.set_xticks(range(len(methods)), labels, rotation=27, ha="right")
        ax.grid(axis="y", color="#D7DCE2", linewidth=.55)
    axes[0].set_ylabel("Corrupted-sink fraction ↓")
    fig.tight_layout(pad=.55, w_pad=.9)
    fig.savefig(FIGURES / "figures_main.pdf", bbox_inches="tight")
    fig.savefig(FIGURES / "figures_main.png", dpi=240, bbox_inches="tight")
    plt.close(fig)


def robustness() -> None:
    rows = read(RESULTS / "robustness.csv")
    specs = [
        ("local-risk", "Local risk", BLUE, "o"),
        ("risk-x-influence", "Risk × influence", RED, "s"),
        ("toporisk", "TopoRisk", GREEN, "^"),
    ]
    fig, ax = plt.subplots(figsize=(3.6, 2.65))
    for method, label, color, marker in specs:
        selected = [r for r in rows if r["method"] == method]
        ax.errorbar(
            [float(r["noise"]) for r in selected],
            [float(r["terminal_error"]) for r in selected],
            yerr=[float(r["ci95"]) for r in selected],
            label=label, color=color, marker=marker, linewidth=1.4,
            markersize=4, capsize=2,
        )
    ax.set_xlabel("Log-normal parameter noise $\\sigma$")
    ax.set_ylabel("Corrupted-sink fraction ↓")
    ax.grid(color="#D7DCE2", linewidth=.55)
    ax.legend(frameon=False, loc="best")
    fig.tight_layout(pad=.55)
    fig.savefig(FIGURES / "figures_robustness.pdf", bbox_inches="tight")
    fig.savefig(FIGURES / "figures_robustness.png", dpi=240, bbox_inches="tight")
    plt.close(fig)


def robust_extension() -> None:
    rows = read(RESULTS / "robust_extension" / "robust_extension_test.csv")
    specs = [
        ("local-risk", "Local risk", BLUE, "o"),
        ("toporisk", "TopoRisk", GREEN, "^"),
        ("robust-toporisk", "Robust-TopoRisk", RED, "D"),
    ]
    fig, ax = plt.subplots(figsize=(3.6, 2.65))
    for method, label, color, marker in specs:
        selected = [r for r in rows if r["method"] == method]
        ax.errorbar(
            [float(r["noise"]) for r in selected],
            [float(r["weighted_terminal_loss"]) for r in selected],
            yerr=[float(r["ci95"]) for r in selected],
            label=label, color=color, marker=marker, linewidth=1.4,
            markersize=4, capsize=2,
        )
    ax.set_xlabel("Log-normal parameter noise $\\sigma$")
    ax.set_ylabel("Weighted terminal loss ↓")
    ax.grid(color="#D7DCE2", linewidth=.55)
    ax.legend(frameon=False, loc="best")
    fig.tight_layout(pad=.55)
    fig.savefig(FIGURES / "figures_robust_extension.pdf", bbox_inches="tight")
    fig.savefig(FIGURES / "figures_robust_extension.png", dpi=240, bbox_inches="tight")
    plt.close(fig)


if __name__ == "__main__":
    style()
    main_bars()
    robustness()
    robust_extension()
