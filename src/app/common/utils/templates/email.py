"""HTML-шаблоны писем."""

LIQUID_LABELS: dict[str, str] = {
    'engine_oil': 'Моторное масло',
    'transmission_oil': 'Масло АКПП',
    'brake_fluid': 'Тормозная жидкость',
    'coolant': 'Антифриз',
    'power_steering_fluid': 'Жидкость ГУР',
    'differential_oil': 'Масло в редукторе',
}


def render_reset_password_body(reset_link: str) -> str:
    return f"""
    <h2>Восстановление пароля</h2>
    <p>Вы запросили восстановление пароля. Перейдите по ссылке ниже, чтобы задать новый пароль:</p>
    <p><a href="{reset_link}">{reset_link}</a></p>
    <p>Ссылка действительна в течение 15 минут.</p>
    <p>Если вы не запрашивали восстановление пароля, просто проигнорируйте это письмо.</p>
    """


def render_replacement_notification_body(
    frontend_url: str,
    vehicle_info: str,
    plate_number: str,
    current_km: int,
    due_items: list[dict],
) -> str:
    """Собрать HTML-тело письма о замене жидкостей."""
    overdue_rows = ""
    critical_rows = ""
    for item in due_items:
        label = LIQUID_LABELS.get(item['liquid_type'], item['liquid_type'])
        km_at = item['km_at_replacement']
        next_km = item['next_replacement_km']
        exceed = current_km - next_km

        row = f"""
        <tr>
            <td style="padding:8px;border-bottom:1px solid #ddd;">{label}</td>
            <td style="padding:8px;border-bottom:1px solid #ddd;text-align:center;">{km_at} км</td>
            <td style="padding:8px;border-bottom:1px solid #ddd;text-align:center;">{next_km} км</td>
            <td style="padding:8px;border-bottom:1px solid #ddd;text-align:center;">{exceed} км</td>
        </tr>"""

        if item['level'] == 'overdue':
            overdue_rows += row
        else:
            critical_rows += row

    overdue_section = ""
    if overdue_rows:
        overdue_section = f"""
        <h3 style="color:#d32f2f;">🔴 Требуется немедленная замена</h3>
        <table style="width:100%;border-collapse:collapse;margin-bottom:20px;">
            <tr style="background:#ffebee;">
                <th style="padding:8px;text-align:left;border-bottom:2px solid #d32f2f;">Жидкость</th>
                <th style="padding:8px;text-align:center;border-bottom:2px solid #d32f2f;">Заменено при</th>
                <th style="padding:8px;text-align:center;border-bottom:2px solid #d32f2f;">Требовалось при</th>
                <th style="padding:8px;text-align:center;border-bottom:2px solid #d32f2f;">Превышение</th>
            </tr>
            {overdue_rows}
        </table>"""

    critical_section = ""
    if critical_rows:
        critical_section = f"""
        <h3 style="color:#e65100;">🟠 Скоро потребуется замена</h3>
        <table style="width:100%;border-collapse:collapse;margin-bottom:20px;">
            <tr style="background:#fff3e0;">
                <th style="padding:8px;text-align:left;border-bottom:2px solid #e65100;">Жидкость</th>
                <th style="padding:8px;text-align:center;border-bottom:2px solid #e65100;">Заменено при</th>
                <th style="padding:8px;text-align:center;border-bottom:2px solid #e65100;">Требуется при</th>
                <th style="padding:8px;text-align:center;border-bottom:2px solid #e65100;">Осталось</th>
            </tr>
            {critical_rows}
        </table>"""

    return f"""
    <html>
    <body style="font-family:Arial,sans-serif;color:#222;max-width:600px;margin:0 auto;padding:20px;">
        <h2 style="color:#1976d2;">Car Liquid Tracker</h2>
        <p style="font-size:16px;color:#555;">
            Автомобиль: <strong>{vehicle_info}</strong> ({plate_number})
        </p>
        <p style="font-size:16px;color:#555;">
            Текущий пробег: <strong>{current_km} км</strong>
        </p>
        {overdue_section}
        {critical_section}
        <p style="margin-top:20px;font-size:14px;color:#999;">
            <a href="{frontend_url}" style="color:#1976d2;">Открыть приложение</a>
        </p>
        <p style="font-size:12px;color:#aaa;border-top:1px solid #eee;padding-top:10px;">
            Данное уведомление можно отключить в настройках автомобиля в приложении.
        </p>
    </body>
    </html>
    """
