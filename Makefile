.PHONY: install run test lint typecheck check seed

install:
	python3 -m venv .venv
	.venv/bin/pip install -e '.[dev]'

run:
	.venv/bin/uvicorn mobility_guard.main:app --reload --host 0.0.0.0 --port 8000

test:
	.venv/bin/pytest

lint:
	.venv/bin/ruff check src tests scripts migrations

typecheck:
	.venv/bin/mypy

check: lint typecheck test

dashboard-check:
	cd dashboard && npm run lint && npm run typecheck && npm run build

seed:
	.venv/bin/python scripts/seed_demo.py
