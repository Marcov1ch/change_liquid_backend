# Доменная модель и бизнес-логика

Справочник по предметной области: статусы, компоненты, интервалы, уведомления и правила создания замен.
Источник правды — код; здесь собраны правила, которые неочевидны из имён полей.

## Статусы замен

Перечисление `StatusEnum` (`src/app/common/enums.py`): `good`, `warning`, `critical`, `overdue`, `replaced`, `unknown`.

### Расчёт по пробегу

`StatusCalculator.calculate_status` (`src/app/common/utils/calculator.py`):

```
next_replacement_km = km_at_replacement + interval_km
km_remaining        = next_replacement_km - current_km
```

| Условие (`km_remaining`) | Статус |
|---|---|
| `< 0` | `overdue` |
| `0 … 250` | `critical` |
| `251 … 500` | `warning` |
| `> 500` | `good` |

Пороги заданы константами `_CRITICAL_KM = 250`, `_WARNING_KM = 500` в `calculator.py`.
Важно: `km_remaining == 0` — это `critical`, а не `overdue` (просрочка строго `< 0`).

### Расчёт по дате

`StatusCalculator.calculate_date_status` — используется для шин и date-based компонентов:

| Условие (`days_remaining = next_change_date - today`) | Статус |
|---|---|
| `next_change_date is None` | `unknown` |
| `< 0` | `overdue` |
| `0 … DATE_WARNING_DAYS` (5) | `warning` |
| `> 5` | `good` |

`DATE_WARNING_DAYS = 5` (`src/app/common/constants.py`).

### `replaced`

Проставляется **не** калькулятором, а хэндлером (`src/app/api/replacement/handler.py`, `_to_response`).
Для каждого компонента «живой» статус (`good/warning/critical/overdue`) имеет только **последняя** замена
(`get_latest_replacement_ids`). Все более старые записи того же компонента возвращаются со статусом `replaced`.

### Общий статус автомобиля

`StatusCalculator.get_vehicle_status` — берётся **худший** статус среди последних замен по каждому типу:

1. Нет замен вообще → `unknown`.
2. Для шин (`tire_change`) статус считается по дате, для остальных — по пробегу (интервал из настроек авто).
3. Приоритет: `overdue` > `critical` > `warning` > `good`.
4. Если у компонента не задан интервал — компонент пропускается.
5. Если ни один компонент не `overdue/critical`, но есть `warning` → статус авто `warning`, иначе `good`.

## Компоненты и интервалы

Список и значения по умолчанию — `COMPONENTS_CONFIG` (`src/app/common/component_config.py`),
доступен из API: `GET /api/v1/enums/component-configs`.

| Тип (`component_type`) | Название | Интервал, км | Интервал, мес |
|---|---|---|---|
| `engine_oil` | Моторное масло | 7000 | 12 |
| `transmission_oil` | Масло АКПП | 60000 | 60 |
| `brake_fluid` | Тормозная жидкость | 40000 | 24 |
| `coolant` | Антифриз | 60000 | 24 |
| `power_steering_fluid` | Жидкость ГУР | 40000 | 60 |
| `differential_oil` | Масло в редукторе | 50000 | 60 |
| `cabin_filter` | Фильтр салона | 15000 | 12 |
| `spark_plugs` | Свечи зажигания | 45000 | 24 |
| `air_filter` | Воздушный фильтр | 10000 | 12 |
| `fuel_filter` | Топливный фильтр | 50000 | 24 |
| `tire_change` | Замена шин | — | — (только по дате) |

- У **всех** компонентов, кроме `tire_change`, есть **оба** интервала: по пробегу и по месяцам.
- `tire_change` — особый тип: его нет в `COMPONENTS_CONFIG`, у него нет интервалов по км/мес. Дата следующей замены (`next_change_date`) задаётся вручную при создании записи, статус считается только по дате.
- Интервал по пробегу влияет на статус (`good/warning/...`), интервал по месяцам — на `next_change_date` / `days_remaining`.
- Интервалы хранятся у автомобиля (колонки `*_interval_km` / `*_interval_months`). Если значение не задано — подставляется дефолт из `COMPONENTS_CONFIG` (см. `VehicleRepository._intervals_and_flags`).
- Флаги уведомлений также хранятся у автомобиля (`*_notify_enabled`, плюс `tire_notify_enabled`) и переключаются через `PATCH /api/v1/vehicles/{id}/notify`.

## Уведомления

Уведомления делятся на два независимых механизма.

### 1. По дате (по месяцам) — планировщик

`src/app/services/scheduler.py`, APScheduler `BackgroundScheduler`, cron **ежедневно в 09:00** (`hour=9, minute=0`).

Алгоритм `_check_date_notifications`:
1. Берёт все активные автомобили, для каждого — настраиваемые компоненты + `tire_change`.
2. Пропускает компонент, если его уведомления выключены (`notify_flags`).
3. Ищет последнюю замену и вычисляет `next_change_date`:
   - шины — сохранённая дата `next_change_date`;
   - остальные — `replacement_date + interval_months` (функция `add_months` с учётом переполнения дней, напр. 31.01 + 1 мес → 28.02).
4. `days_remaining = next_change_date - today`:
   - `<= 0` → `overdue`, но только если ещё не слали (`date_overdue_notified`);
   - `<= 5` → `warning`, только если не слали (`date_warning_notified`);
   - `> 5` → флаги сбрасываются (уведомление «перевзводится» на следующий цикл).
5. Отправляет письмо (`send_date_notification_email`) и фиксирует флаг отправки.

Это единственный механизм, который шлёт письма **автоматически по расписанию**.

### 2. По пробегу — по событию

`src/app/services/notification_service.py`, вызывается через `BackgroundTasks` после:
- создания/обновления замен,
- обновления пробега авто (`PATCH /vehicles/{id}/km`, `PATCH /vehicles/{id}`).

`check_vehicle_notifications` группирует все «тревожные» компоненты авто в **одно** письмо (`send_grouped_notification_email`).

Логика по статусу компонента:
- `good` → флаги сбрасываются;
- `warning` → письмо один раз (флаг `warning_notified`);
- `critical` → письмо один раз (флаг `critical_notified`);
- `overdue` → повторное уведомление каждые `RE_NOTIFY_KM = 500` км (порог = последний уведомлённый пробег либо `next_replacement_km`, плюс 500; хранится в `overdue_notified_at_km`).

Флаги — колонки `ReplacementDB`: `warning_notified`, `critical_notified`, `overdue_notified_at_km`, `date_warning_notified`, `date_overdue_notified`.

## Создание замен и проверка хронологии

`src/app/services/replacement_service.py`, метод `create`.

Валидация для **не**-шинных компонентов:
- `km_at_replacement >= 0`, `replacement_date <= сегодня`;
- **хронология** — пробег и дата новой замены не меньше, чем у предыдущей замены того же компонента (`_validate_sequence`, `get_last_replacement`);
- **нет дубликата** — для этого компонента ещё нет замены с таким же `km_at_replacement`;
- если новый пробег больше текущего пробега авто — `current_km` авто обновляется.

Для `tire_change` эти проверки пропускаются (можно задавать `next_change_date` вручную).

При **обновлении** (`update`) те же проверки выполняются с `exclude_id` и поиском соседей (`find_neighbors`): значение не должно быть меньше предыдущей и больше следующей замены. При изменении даты не-шинной замены пересчитывается `next_change_date` и сбрасываются date-флаги.

### Массовое создание (ТО)

`POST /api/v1/vehicles/{id}/replacements/bulk` (`ReplacementsBulkRequest`), `1…10` замен за раз.
- Все замены создаются в одной транзакции (`commit=False`, затем один `db.commit()`).
- Любая ошибка валидации (`ValueError`) → `db.rollback()` и HTTP 400 (атомарно: либо всё, либо ничего).
- После успешного коммита запускается проверка уведомлений по пробегу.

## `Vehicle` и `VehicleSize`

- **`Vehicle`** (`VehicleDB`) — основной автомобиль: марка/модель (ссылки на `brands`/`models`), госномер, год, `current_km`, интервалы и флаги уведомлений по компонентам. Справочные данные марки/модели сидируются (`seed_brands`).
- **`VehicleSize`** (`VehicleSizeDB`) — **справочник допустимых дисков и шин** для авто (появился в 2026.18.0). Это «что подходит машине», а не история фактических замен.
  - `kind = 'rim'`: `diameter`, `pcd`, `et_from`/`et_to`, `width_from`/`width_to`.
  - `kind = 'tire'`: `size`, `label`.
  - Связан с авто через `vehicle_id` (`ondelete CASCADE`); обновляется целиком через `PATCH /api/v1/vehicles/{id}/sizes` (`replace_sizes` — полная замена списков).
- **Фактическая** замена шин — это запись `Replacement` с `component_type = tire_change` и `next_change_date`. Не путать со справочником `VehicleSize`.
