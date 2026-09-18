.PHONY: test interop matrix benchmark probe all

test:
	python -m unittest discover -s tests -v

interop:
	python scripts/run_all.py

matrix:
	python scripts/profile_matrix.py

benchmark:
	python scripts/benchmark.py

probe:
	python scripts/mutation_probe.py

all: test interop matrix benchmark probe
