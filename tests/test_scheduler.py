from __future__ import annotations

import random
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from run_experiments import (  # noqa: E402
    Graph,
    backward_influence,
    choose,
    expected_terminal_error,
    forward_risk,
    make_graph,
)


class SchedulerTests(unittest.TestCase):
    def test_forward_risk_on_two_node_chain(self) -> None:
        graph = Graph(
            parents=[[], [(0, 0.5)]],
            children=[[(1, 0.5)], []],
            p=[0.2, 0.1],
            sinks=[1],
        )
        risk = forward_risk(graph)
        self.assertAlmostEqual(risk[0], 0.2)
        self.assertAlmostEqual(risk[1], 1.0 - (1.0 - 0.1) * (1.0 - 0.2 * 0.5))

    def test_backward_influence_reaches_terminal(self) -> None:
        graph = Graph(
            parents=[[], [(0, 0.5)]],
            children=[[(1, 0.5)], []],
            p=[0.2, 0.1],
            sinks=[1],
        )
        influence = backward_influence(graph)
        self.assertAlmostEqual(influence[1], 1.0)
        self.assertGreater(influence[0], 0.0)

    def test_toporisk_respects_budget_and_reduces_modeled_loss(self) -> None:
        graph = make_graph("diamond", 20, random.Random(7))
        selected = choose(graph, "toporisk", 4, random.Random(11))
        self.assertEqual(len(selected), 4)
        self.assertLessEqual(
            expected_terminal_error(graph, selected),
            expected_terminal_error(graph, set()),
        )

    def test_selection_is_deterministic_for_nonrandom_method(self) -> None:
        graph = make_graph("random", 24, random.Random(19))
        first = choose(graph, "toporisk", 5, random.Random(1))
        second = choose(graph, "toporisk", 5, random.Random(999))
        self.assertEqual(first, second)


if __name__ == "__main__":
    unittest.main()

