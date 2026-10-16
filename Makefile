.PHONY: install test lint typecheck check
install:
	python -m pip install -e ".[dev]"
test:
	python -m pytest -m "not integration"
lint:
	ruff check .
typecheck:
	mypy
check: lint typecheck test
