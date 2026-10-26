.PHONY: help install run test lint mypy ruff radon check clean

help:
	@echo "Доступные команды:"
	@echo "  make install     - установка зависимостей через poetry"
	@echo "  make run         - запуск приложения"
	@echo "  make test        - запуск тестов (pytest)"
	@echo "  make lint        - проверка стиля (flake8)"
	@echo "  make mypy        - проверка типов (mypy)"
	@echo "  make ruff        - проверка ruff (локально, в CI нет)"
	@echo "  make radon       - анализ сложности кода (блоки C-F + средняя, radon)"
	@echo "  make check       - lint + mypy + test (перед коммитом)"
	@echo "  make clean       - очистка кэшей"

install:
	poetry install

run:
	PYTHONPATH=src poetry run python src/app/main.py

test:
	PYTHONPATH=src poetry run pytest src/tests -v

lint:
	poetry run flake8 src

mypy:
	poetry run mypy src

ruff:
	poetry run ruff check src

radon:
	poetry run radon cc src -s --total-average -n C

check: lint mypy test

clean:
	find . -type d -name __pycache__ -prune -exec rm -rf {} +
	rm -rf .pytest_cache .mypy_cache .ruff_cache
