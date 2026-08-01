from unittest.mock import patch

from app.services.email_service import (
    _html,
    _header,
    ComponentNotificationItem,
    send_date_notification_email,
    send_grouped_notification_email,
)


def test_html_escapes_special_characters() -> None:
    assert _html('<script>alert("x")</script>') == '&lt;script&gt;alert(&quot;x&quot;)&lt;/script&gt;'


def test_header_strips_crlf() -> None:
    assert _header('Mobil 1\r\nBcc: attacker@evil.com') == 'Mobil 1  Bcc: attacker@evil.com'


def test_send_date_notification_email_escapes_user_data() -> None:
    with patch('app.services.email_service._send_email') as mock_send:
        send_date_notification_email(
            to_email='user@example.com',
            username='<b>User</b>',
            brand='Toyota',
            model='Camry',
            plate_number='A123AA178',
            component_name='</strong><img src=x onerror=alert(1)>',
            next_change_date='2026-11-01',
            days_remaining=5,
            is_overdue=False,
        )

    mock_send.assert_called_once()
    subject, body = mock_send.call_args.args[1], mock_send.call_args.args[2]
    assert '</strong><img src=x' not in body
    assert '&lt;/strong&gt;' in body
    assert '<b>User</b>' not in body
    assert '&lt;b&gt;User&lt;/b&gt;' in body
    assert '\r' not in subject and '\n' not in subject


def test_send_grouped_notification_email_escapes_user_data() -> None:
    items = [
        ComponentNotificationItem(
            component_name='Oil\r\nInjected',
            component_name_genitive='<script>oil</script>',
            km_remaining=-100,
            status='overdue',
        ),
    ]
    with patch('app.services.email_service._send_email') as mock_send:
        send_grouped_notification_email(
            to_email='user@example.com',
            username='User',
            brand='Toyota',
            model='Camry',
            plate_number='A123AA178',
            items=items,
        )

    mock_send.assert_called_once()
    subject, body = mock_send.call_args.args[1], mock_send.call_args.args[2]
    assert '<script>' not in body
    assert '&lt;script&gt;' in body
    assert '\r' not in subject and '\n' not in subject
