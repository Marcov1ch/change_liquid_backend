# AGENTS.md - backend

## Команды разработки

### Основные
- `poetry install` — установка зависимостей
- `make run` — запуск dev-сервера (`poetry run python src/app/main.py`). Приложение доступно на http://localhost:8000, Swagger — на http://localhost:8000/docs
- `make test` — запуск тестов (`PYTHONPATH=src poetry run pytest src/tests -v`). При прямом запуске pytest всегда задавайте `PYTHONPATH=src`
- `make lint` — проверка стиля (flake8, лимит 110 символов, см. setup.cfg)
- `make mypy` — проверка типов (mypy)
- `make ruff` — проверка через ruff (`poetry run ruff check src`)

### Важные нюансы
- В CI используются те же команды: lint, typecheck (mypy), test — запускаются параллельно. Деплой в master возможен только при успешном прохождении всех трёх.
- Тесты лежат в `src/tests/` (мн.ч.). В `setup.cfg` есть `exclude = src/test` (ед.ч.) — это не ошибка, просто особенность конфига.
- Конфиг flake8 содержит `per-file-ignores` для файлов с длинными строками.
- Для mypy включён `disallow_untyped_defs` и `check_untyped_defs` — при правках следуйте существующему стилю типизации.
- В `src/tests/conftest.py` принудительно задаётся `SECRET_KEY` для тестов.

## Архитектура

### Точки входа
- `src/app/main.py` — точка входа FastAPI. При старте: загружает `.env`, настраивает логирование, запускает миграции, инициализирует БД (сидирование), монтирует роутеры, стартует планировщик уведомлений.
- `src/app/api/routes.py` — регистрация v1-роутов (`/api/v1/*`).
- `app.auth.handler.router` монтируется напрямую в `main.py`.

### База данных
- SQLAlchemy 2 + SQLite. Путь к БД берётся из `DB_PATH` (по умолчанию `data/app.db`). `engine` использует `connect_args={"check_same_thread": False}`.
- Миграции Alembic: `alembic/`, `alembic.ini`. `alembic/env.py` добавляет `src` в `sys.path` и использует `app.db.models.Base.metadata`.
- Кастомный механизм миграций: `src/app/db/migrate.py`. Если БД пустая (нет таблиц) — `Base.metadata.create_all()` + `alembic stamp head`. Если есть таблицы — `alembic upgrade head`. Не меняйте это поведение без понимания.
- Инициализация/сидирование: `src/app/db/database.init_db()` вызывает `seed_brands()`. Схема управляется миграциями.
- Модели: `src/app/db/models.py` (User, Vehicle с интервалами/флагами уведомлений по компонентам, VehicleSize, Replacement с флагами уведомлений, Brand, Model).

### Прочее
- Сервисный слой: `src/app/services/` (включая планировщик `scheduler.py` и уведомления по email).
- Репозитории: `src/app/repository/`.
- Общие утилиты/конфиги: `src/app/common/`.

## Конфигурация и окружение

- Переменные окружения берутся из `.env` (см. `.env.example`). Обязательные: `SECRET_KEY`. Опциональные: `DB_PATH`, `SMTP_HOST/PORT/USER/PASSWORD/FROM`, `FRONTEND_URL`.
- Email-уведомления и планировщик (APScheduler) стартуют при запуске приложения.

## Советы при работе

- Всегда используйте `PYTHONPATH=src` при запуске pytest из корня репозитория.
- При изменении схемы БД обновляйте именно Alembic-миграции, а не только модели.
- Учитывайте side-эффекты при импорте `src/app/main.py` (миграции, сидирование, старт планировщика) — это важно при тестировании/импорте.
- При проверке кода перед коммитом ориентируйтесь на Makefile/CI: `make lint && make mypy && make test`.
- Не добавляйте комментарии в код без явного запроса.
