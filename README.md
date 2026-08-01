# Сервис учета замены технических жидкостей авто

Backend-сервис для учёта замены технических жидкостей и расходников автомобиля (моторное масло, антифриз, фильтры, свечи, шины и др.) с отслеживанием статусов замен и email-уведомлениями.

## Возможности

- Учёт автомобилей (марка/модель из справочника, госномер РФ/РБ, пробег)
- Записи о заменах по компонентам, массовое создание (ТО), проверка хронологии
- Статусы замен: `good` / `warning` / `critical` / `overdue` / `replaced`
- Email-уведомления о приближении/просрочке замен (ежедневный scheduler в 09:00)
- Регистрация и JWT-авторизация (access/refresh), смена пароля и email, восстановление пароля

## Стек

Python 3.12 · FastAPI · SQLAlchemy 2 · Alembic · SQLite · JWT (python-jose) · bcrypt · APScheduler · Poetry · Docker Compose + Caddy

## Структура проекта

```
src/app/
├── api/          # handlers и схемы (vehicle, replacement, enums, routes)
├── auth/         # регистрация, JWT, пароли
├── common/       # enums, конфигурация компонентов, middleware, утилиты
├── db/           # модели, миграции, сидирование справочников
├── repository/   # доступ к БД
└── services/     # бизнес-логика, уведомления, scheduler
```

## Быстрый старт

### Локальный запуск

```shell
poetry install
cp .env.example .env   # подставьте свои значения
make run               # или: python src/app/main.py
```

Документация API (Swagger): http://localhost:8000/docs

### Docker (dev)

```shell
docker compose -f docker-compose.yml -f docker-compose.dev.yml up -d
```

## Конфигурация

Все переменные задаются в `.env` (см. `.env.example`).

| Переменная | Обязательна | По умолчанию | Описание |
|---|---|---|---|
| `SECRET_KEY` | да | — | Ключ подписи JWT |
| `DB_PATH` | нет | `data/app.db` | Путь к файлу SQLite |
| `SMTP_HOST` | нет | `smtp.mail.ru` | SMTP-сервер |
| `SMTP_PORT` | нет | `465` | Порт SMTP |
| `SMTP_USER` | нет | — | Логин SMTP |
| `SMTP_PASSWORD` | нет | — | Пароль SMTP |
| `SMTP_FROM` | нет | `SMTP_USER` | Отправитель писем |
| `FRONTEND_URL` | нет | `http://localhost:5173` | Адрес фронтенда для ссылок в письмах |

## API

Основные группы эндпоинтов (префикс `/api/v1`):

- `/auth/*` — регистрация, логин, refresh, профиль, смена пароля/email, восстановление пароля
- `/vehicles` — создание, получение, обновление, мягкое/полное удаление, восстановление, пробег, интервалы, уведомления
- `/replacements` — создание (в т.ч. bulk), получение, обновление, удаление замен
- `/enums/*` — справочники марок, моделей, компонентов и их конфигураций

## Тесты и качество

```shell
make test     # pytest
make lint     # flake8
make mypy     # проверка типов
make ruff     # ruff
```

## Деплой

Production-сборка через `docker compose` (backend + frontend + Caddy). Автодеплой выполняется CI при пуше в `master`. Подробнее об окружении — в [CONTRIBUTING.md](CONTRIBUTING.md).
