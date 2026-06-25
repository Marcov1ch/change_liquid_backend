.PHONY: help install run test lint format type-check clean shell

help:
	@echo "Доступные команды:"
	@echo "  make install     - установка зависимостей через poetry"
	@echo "  make run         - запуск приложения"
	echo "  make lint        - проверка стиля (flake8)"
	@echo "  make mypy  - проверка типов (mypy)"

install:
	poetry install

run:
	poetry run python src/app/main.py

lint:
	poetry run flake8 src

mypy:
	poetry run mypy src

test:
	PYTHONPATH=src poetry run pytest src/tests -v

ruff:
	poetry run ruff check src