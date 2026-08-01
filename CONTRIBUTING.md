# Разработка сервиса

## Рабочее окружение
Для разработки необходимо настроить окружение. Нам понадобятся следующие системные зависимости:
- python версии 3.12 или выше (чистый, не anaconda)
- менеджер зависимости poetry версии 2.1.4 или выше

Настройка окружения:
1. Настроить репозиторий
    ```shell script
    git clone <ссылка>
    ```
2. Установить зависимости
    ```shell scrip
    poetry install 
    ```
3. Активировать окружение 
    ```shell script
    eval $(poetry env activate)
    ```
    Или вручную:
    ```shell script
    poetry env activate
    ```
    Linux
    ```shell script
    source /path/to/your/venv/bin/activate
    ```
    Windows
    ```shell script
    . "/path/to/your/venv/bin/activate"
    ```
4. Деактивировать виртуальное окружение
    ```shell script
    exit
    ```


### Быстрая установка всех зависимостей
Если вы пользуетесь утилитой `make` для установки зависимостей, то можно выполнить
```shell script
make install
```
Команда запустит установку всех зависимостей poetry.

## Локальный запуск сервиса
Из корневой директории выполнить:
```shell script
python src/app/main.py
```
Или
```shell script
make run
```

## База данных и миграции

Схема БД управляется через Alembic. При старте сервиса автоматически выполняется `run_migrations()`:
- **пустая БД** — схема создаётся из моделей SQLAlchemy и помечается как `head`;
- **существующая БД** — применяются только новые миграции (`upgrade head`), данные не перезаписываются.

Правило при изменении схемы (например, добавлении колонки):

1. Внести изменение в модель в `src/app/db/models.py`.
2. Сгенерировать миграцию из корня проекта:
   ```shell
   alembic revision --autogenerate -m "add <что> to <таблица>"
   ```
3. Проверить сгенерированную миграцию (ожидаем `op.add_column` / `op.drop_column`, без пересоздания таблиц).
4. Применить: `alembic upgrade head`. На проде колонка добавится через `ALTER TABLE ... ADD COLUMN`, данные сохранятся.

Запрещено: редактировать схему БД вручную и использовать `create_all` в рантайме.

### Собрать образ
```shell script
docker compose -f docker-compose.yml -f docker-compose.dev.yml build
```
### Запустить контейнер
```shell script
docker compose -f docker-compose.yml -f docker-compose.dev.yml up -d
```
### Посмотреть логи контейнера
```shell script
docker compose logs -f
```
### Остановить контейнер
```shell script
docker compose down
```
