.PHONY: install lint format typecheck test bench clean

install:
	pip install -e ".[dev]"

lint:
	ruff check .

format:
	ruff format .

typecheck:
	mypy src

test:
	pytest

bench:
	pytest benchmarks/ --benchmark-only

clean:
	rm -rf build dist .pytest_cache .mypy_cache .ruff_cache htmlcov
