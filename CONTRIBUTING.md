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
    ``
    Linux
    ```shell script
    source /path/to/your/venv/bin/activate
    ```
    Windows
    ```shell script
    . "/path/to/your/venv/bin/activate"
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

### Собрать образ
```shell script
docker-compose build --no-cache
```
### Запустить контейнер
```shell script
docker-compose up -d
```
### Посмотреть логи контейнера
```shell script
docker-compose logs -f
```
### Остановить контейнер
```shell script
docker-compose down
```
### Удалить пользователя
```shell script
poetry run python script/delete_user.py
```