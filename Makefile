PYTHON ?= python3
MPLCONFIGDIR ?= /tmp/toporisk-mpl

.PHONY: test verify smoke controlled figures clean

test:
	PYTHONPYCACHEPREFIX=/tmp/toporisk-pycache $(PYTHON) -m unittest discover -s tests -v

verify:
	$(PYTHON) src/verify_release.py

smoke:
	mkdir -p /tmp/toporisk-smoke
	$(PYTHON) src/run_experiments.py --graphs 8 --episodes 8 --out /tmp/toporisk-smoke/main
	$(PYTHON) src/run_allocation_ablations.py --graphs 8 --episodes 8 --out /tmp/toporisk-smoke/ablations
	$(PYTHON) src/run_structure_sensitivity.py --graphs 8 --episodes 8 --out /tmp/toporisk-smoke/structure

controlled:
	$(PYTHON) src/run_experiments.py --out results/controlled
	$(PYTHON) src/run_allocation_ablations.py --out results/controlled/ablations
	$(PYTHON) src/run_structure_sensitivity.py --out results/controlled/structure_sensitivity

figures:
	MPLCONFIGDIR=$(MPLCONFIGDIR) $(PYTHON) src/make_figures.py
	MPLCONFIGDIR=$(MPLCONFIGDIR) $(PYTHON) src/make_ablation_figures.py

clean:
	find . -type d -name __pycache__ -prune -exec rm -rf {} +

