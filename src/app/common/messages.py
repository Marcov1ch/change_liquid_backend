# noqa: flake8 E501
STATUS_MESSAGES = {
    'no_data': "Нет данных. Рекомендуется произвести замену и внести запись.",
    'critical_book': "🔴 КРИТИЧНО! Превышен регламентированный интервал замены {book_interval} км! Требуется немедленная замена!",
    'critical_user': "🔴 ТРЕБУЕТСЯ ЗАМЕНА! Вы превысили установленный интервал замены {user_interval} км на {exceed} км.",
    'need_replacement': "🔴 ТРЕБУЕТСЯ ЗАМЕНА",
    'urgent_small': "🔴 СРОЧНО! Осталось {km_remaining} км до замены",
    'soon': "🟡 СКОРО ЗАМЕНА! Осталось {km_remaining} км",
    'prepare': "🟡 Рекомендуется подготовиться. Осталось {km_remaining} км",
    'warning_interval': "⚠️ ВНИМАНИЕ! Установленный интервал: {user_interval} км превышает регламентный: {book_interval} км. Замена должна быть через {book_km_remaining} км по мануалу",
    'normal': "🟢 В норме. Замена через {km_remaining} км",
}

ERROR_MESSAGES = {
    'vehicle_not_found': "Автомобиль с ID {vehicle_id} не найден",
    'replacement_not_found': "Замена с ID {replacement_id} не найдена",
    'plate_number_exists': "Автомобиль с госномером {plate_number} уже существует",
    'invalid_km': "Пробег при замене: {km} км не может быть меньше текущего пробега автомобиля: {current_km} км",
    'km_less_than_previous': "Новый пробег: {new_km} км не может быть меньше предыдущей замены: {last_km} км",
    'date_less_than_previous': "Дата замены: {new_date} не может быть раньше предыдущей замены: {last_date}",
}

SUCCESS_MESSAGES = {
    'vehicle_created': "Автомобиль {brand} {model} успешно создан",
    'vehicle_deleted': "Автомобиль {vehicle_id} успешно удален",
    'vehicle_restored': "Автомобиль {vehicle_id} успешно восстановлен",
    'vehicle_hard_deleted': "Автомобиль {vehicle_id} и все его замены полностью удалены",
    'replacement_created': "Замена {liquid_name} для автомобиля {vehicle_id} успешно создана",
    'replacement_deleted': "Замена {replacement_id} успешно удалена",
}

VALIDATION_ERRORS = {
    'negative_km': 'Пробег не может быть отрицательным',
    'future_date': 'Дата не может быть в будущем',
    'km_less_than_previous': 'Пробег ({km}) не может быть меньше предыдущей замены ({previous_km})',
    'date_less_than_previous': 'Дата ({date}) не может быть раньше предыдущей замены ({previous_date})',
    'km_less_than_current': 'Пробег: {km} км не может быть меньше текущего пробега авто: {current_km} км',
}
