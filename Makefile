# Pacman — 42 project ("Ghosts! More ghosts!")
# All targets go through uv (https://docs.astral.sh/uv/).
# No uv on the review machine? Fallback:
#   python3 -m venv .venv && . .venv/bin/activate
#   pip install pygame flake8 mypy pytest ./mazegenerator-2.0.2-py3-none-any.whl

CONFIG ?= config.json

.PHONY: install run debug clean lint lint-strict test

install:
	uv sync

run:
	uv run python3 pac-man.py $(CONFIG)

debug:
	uv run python3 -m pdb pac-man.py $(CONFIG)

clean:
	find . -type d -name "__pycache__" -exec rm -rf {} +
	rm -rf .mypy_cache .pytest_cache

lint:
	uv run flake8 .
	uv run mypy . --warn-return-any --warn-unused-ignores \
		--ignore-missing-imports --disallow-untyped-defs --check-untyped-defs

lint-strict:
	uv run flake8 .
	uv run mypy . --strict

test:
	uv run pytest
