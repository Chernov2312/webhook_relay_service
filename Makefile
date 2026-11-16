.PHONY: install test lint run

install:
	python -m pip install -e '.[dev]'

test:
	pytest

lint:
	ruff check .

run:
	docker compose up --build
