# TopoRisk

[English](README.md) | [简体中文](README_zh-CN.md)

**Dependency-aware verification allocation for agentic workflows**

TopoRisk allocates a limited audit budget across a workflow graph. It estimates
how local errors can reach terminal outputs and recomputes each audit's marginal
value after every selection, avoiding repeated credit for overlapping paths.

This repository is an **artifact-first research preview**. It contains the
implementation, aggregate results, and reproduction utilities. The manuscript
and LaTeX sources are intentionally not included, and the work has not undergone
peer review.

The canonical evaluation artifacts are available on
[Hugging Face](https://huggingface.co/datasets/JosephAA/toporisk-evaluation-artifacts).

## Results snapshot

| Evaluation | Observation |
|---|---|
| Controlled DAGs, 10% audit budget | Corrupted-sink fraction: 0.261 (local risk) vs. 0.147 (TopoRisk) |
| Controlled DAGs, 20% audit budget | Corrupted-sink fraction: 0.172 (local risk) vs. 0.059 (TopoRisk) |
| Fixed-trace allocation stress test | Paired residual-loss differences: -0.526 and -0.544 |
| Online pilot | 39/45 successes in both conditions; no observed end-to-end gain |
| Online verifier cost | Estimated 11.6% total-cost overhead |

The fixed-trace study uses constructed hazards over frozen contexts. It is not
an estimate of natural error frequency or deployment safety. The online pilot's
null result is retained rather than filtered out.

## Install

Python 3.10 or newer is recommended.

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
```

## Quick checks

```bash
make test
make verify
make smoke
```

`make smoke` runs small deterministic instances and does not make network or
model API calls.

## Reproduce the controlled experiments

The full controlled experiment is deterministic but substantially larger than
the smoke test:

```bash
make controlled
make figures
```

Equivalent commands are documented in the `Makefile`. Frozen aggregate outputs
from remote-model experiments are included so that inspecting the reported
values does not require paid API calls.

## Repository layout

```text
src/                         Simulation, allocation, plotting, and checks
tests/                       Unit tests for graph risk and selection behavior
results/controlled/          Reproducible synthetic-DAG tables
results/fixed_trace_summary/ Aggregate heterogeneous-verifier stress test
results/online_summary/      Aggregate paired online-pilot outcomes
figures/                     Figures generated from aggregate results
docs/                        Provenance and scope documentation
```

## Data and privacy

The repository excludes API keys, `.env` files, provider request identifiers,
account data, raw prompts, model responses, conversational traces, the paper
PDF, and LaTeX sources. Task identifiers in aggregate tables are local study
labels.

See [`docs/PROVENANCE_AND_SCOPE.md`](docs/PROVENANCE_AND_SCOPE.md) for details.

## Citation

Until a manuscript identifier is available, cite the artifact release:

```bibtex
@misc{yuan2026toporiskartifacts,
  title        = {TopoRisk Evaluation Artifacts},
  author       = {Yuan, Ye},
  year         = {2026},
  howpublished = {GitHub repository and Hugging Face dataset},
  url          = {https://github.com/YYJoseph/TopoRisk},
  note         = {Artifact-first research preview; manuscript not included}
}
```

## Licenses

- Code under `src/` and `tests/`: Apache License 2.0 (`LICENSE`).
- Aggregate result tables, figures, and documentation: CC BY 4.0
  (`LICENSE-DATA-DOCS`).

No license is granted for excluded upstream benchmark content or for the
unreleased manuscript.
