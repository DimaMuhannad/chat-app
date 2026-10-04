"""Тесты изоляции учетных данных и скоупов в веб-студии chat-app (ISO-03).

Проверяют:
1. Отсутствие учетных данных и полей LMS в Settings бэкенда chat-app.
2. Отсутствие переменных окружения PRO_GUAP_* и LMS_* в процессе chat-app.
3. Отсутствие LMS-эндпоинтов в зарегистрированных HTTP-маршрутах приложения.
"""

from __future__ import annotations

import os
from app.core.config import Settings, settings
from app.main import app


def test_settings_has_no_lms_credentials():
    """Settings chat-app не содержит полей или настроек для личного кабинета LMS."""
    field_names = [f.lower() for f in Settings.model_fields.keys()]

    # Проверяем поля модели Settings
    for field in field_names:
        assert not field.startswith("pro_guap_"), f"Обнаружено LMS-поле {field} в Settings!"
        assert not field.startswith("lms_"), f"Обнаружено LMS-поле {field} в Settings!"
        assert "guap" not in field, f"Обнаружено поле с упоминанием guap: {field} в Settings!"
        assert "lms" not in field, f"Обнаружено поле с упоминанием lms: {field} в Settings!"

    # Проверяем атрибуты экземпляра settings
    for attr in dir(settings):
        if attr.startswith("_"):
            continue
        attr_lower = attr.lower()
        assert not attr_lower.startswith("pro_guap_"), f"Атрибут {attr} содержит LMS-префикс!"
        assert not attr_lower.startswith("lms_"), f"Атрибут {attr} содержит LMS-префикс!"


def test_environ_has_no_lms_credentials_in_chatapp():
    """Переменные окружения процесса chat-app не содержат паролей или токенов LMS."""
    for key in os.environ.keys():
        key_upper = key.upper()
        assert not key_upper.startswith("PRO_GUAP_"), f"Секрет {key} экспортирован в окружение chat-app!"
        assert not key_upper.startswith("LMS_"), f"Секрет {key} экспортирован в окружение chat-app!"
        assert "GUAP_PASSWORD" not in key_upper, f"Пароль LMS {key} в окружении chat-app!"
        assert "GUAP_LK_PASSWORD" not in key_upper, f"Пароль ЛК {key} в окружении chat-app!"


def test_routes_do_not_expose_lms_endpoints():
    """Веб-роутер chat-app не публикует эндпоинты управления или доступа к LMS."""
    paths = [route.path.lower() for route in app.routes if hasattr(route, "path")]

    for path in paths:
        assert "/lms" not in path, f"Обнаружен маршрут LMS {path} в API chat-app!"
        assert "/guap" not in path, f"Обнаружен маршрут GUAP {path} в API chat-app!"
