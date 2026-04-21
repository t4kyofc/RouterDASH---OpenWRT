#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import base64
import csv
import hashlib
import hmac
import io
import json
import os
import re
import secrets
import socket
import subprocess
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
from collections import defaultdict, deque
from copy import deepcopy
from functools import wraps
from typing import Any, Dict, List, Optional, Tuple
import ipaddress

from flask import (
    Flask,
    jsonify,
    redirect,
    render_template_string,
    request,
    session,
    url_for,
)

APP_NAME = "RouterDash"
APP_DIR = os.environ.get("ROUTERDASH_DIR", "/etc/routerdash")
CONFIG_FILE = os.path.join(APP_DIR, "config.json")
STATE_FILE = os.path.join(APP_DIR, "state.json")

DEFAULT_SETTINGS = {
    "bind_host": "0.0.0.0",
    "port": 1999,
    "language": "ru",
    "poll_interval_ms": 1500,
    "offline_grace_sec": 120,
    "activity_total_kbps": 250,
    "local_network_cidr": "192.168.0.0/24",
    "track_ipv6": True,
    "notify_online": True,
    "notify_offline": True,
    "notify_active": False,
    "notify_inactive": False,
    "notification_total_kbps": 500,
    "telegram_enabled": False,
    "telegram_bot_token": "",
    "telegram_chat_id": "",
    "telegram_limit_to_selected_devices": False,
    "telegram_selected_devices": [],
    "telegram_selection_initialized": False,
}

DEFAULT_CONFIG = {
    "version": 1,
    "secret_key": "",
    "admin": {
        "username": "",
        "password_hash": "",
    },
    "settings": deepcopy(DEFAULT_SETTINGS),
}

DEFAULT_STATE = {
    "version": 1,
    "devices": {},
    "events": [],
}


I18N = {
    "ru": {
        "language": "Язык",
        "choose_language": "Выбор языка",
        "language_desc": "Выберите язык интерфейса RouterDash. Он будет сохранён как язык по умолчанию.",
        "russian": "Русский",
        "english": "English",
        "lang_saved": "Язык интерфейса сохранён.",
        "current_default": "Текущий язык по умолчанию",
        "logs": "Логи",
        "logs_caption": "Последние события по сети и уведомлениям",
        "settings": "Настройки",
        "logout": "Выйти",
        "system": "System",
        "tg_monitoring": "Telegram и мониторинг",
        "web_port": "Порт веб‑панели",
        "web_port_note": "После изменения порт будет сохранён, сервис перезапустится и панель откроется на новом порту.",
        "poll_interval_ms": "Интервал опроса, мс",
        "activity_threshold": "Порог активности, кбит/с",
        "notification_threshold": "Порог уведомления, кбит/с",
        "offline_grace": "Задержка до офлайна, сек",
        "local_network_cidr": "Локальная сеть (CIDR)",
        "tg_bot_token": "Токен Telegram‑бота",
        "tg_chat_id": "ID пользователя / chat_id",
        "tg_chat_placeholder": "Например: 123456789",
        "tg_enabled": "Telegram включён",
        "track_ipv6": "Учитывать и показывать IPv6",
        "notify_online": "Сообщать о появлении в сети",
        "notify_offline": "Сообщать об уходе из сети",
        "notify_active": "Сообщать о высокой активности",
        "notify_inactive": "Сообщать о падении активности",
        "selected_only": "Уведомлять только по выбранным устройствам",
        "select_all": "Выбрать все",
        "unselect_all": "Снять все",
        "tg_devices": "Устройства для Telegram‑уведомлений",
        "devices_not_found": "Устройства пока не найдены. Список заполнится после первого обнаружения клиентов.",
        "selected_only_note": "Если режим выбора отключён, уведомления будут приходить по всем устройствам.",
        "save_settings": "Сохранить настройки",
        "send_test_telegram": "Отправить тест в Telegram",
        "admin_account": "Учётная запись администратора",
        "new_username": "Новый логин",
        "current_password": "Текущий пароль",
        "new_password": "Новый пароль",
        "repeat_new_password": "Повтор нового пароля",
        "update_credentials": "Обновить учётные данные",
        "app_subtitle": "Мониторинг устройств OpenWrt: скорость, соединения, активность и Telegram‑уведомления",
        "port_short": "Порт",
        "poll_frequency": "Частота опроса",
        "warnings": "Предупреждения",
        "devices": "Устройства",
        "devices_desc": "Сохраняются в истории, даже если сейчас отключены",
        "connected_now": "Сейчас подключено",
        "connected_desc": "Кабельные клиенты, присутствующие в локальной сети",
        "active": "Активные",
        "active_desc": "Выше заданного порога сетевой активности",
        "idle": "Малоактивные",
        "idle_desc": "В сети, но ниже порога активности",
        "devices_section": "Устройства",
        "devices_caption": "Одна строка на устройство по MAC‑адресу. IPv4 показываются только из локальной сети. {ipv6_sentence} Клик по числу соединений открывает направления с Up/Down.",
        "devices_caption_ipv6": "IPv6 скрыты за кнопкой «...».",
        "th_status": "Статус",
        "th_name": "Имя / хост",
        "th_ipv4": "IPv4",
        "th_ipv6": "IPv6",
        "th_mac": "MAC",
        "th_down": "Скачивание",
        "th_up": "Отдача",
        "th_total": "Суммарно",
        "th_conns": "Соединения",
        "th_last_seen": "Последняя активность",
        "status_online": "Подключен",
        "status_offline": "Отключен",
        "activity_present": "Есть активность",
        "activity_none": "Подключен, но сейчас без активности",
        "no_events": "Событий пока нет.",
        "event_type": "Тип",
        "copied": "Скопировано ✓",
        "no_active_directions": "Нет активных направлений.",
        "no_conntrack_details": "Нет активных направлений или conntrack не дал деталей для этих соединений.",
        "direction": "Направление",
        "zero_speed": "0 Kbit/s",
        "save_settings_failed": "Не удалось сохранить настройки.",
        "settings_saved": "Настройки сохранены.",
        "settings_save_error": "Ошибка сохранения настроек.",
        "username": "Логин",
        "password": "Пароль",
        "repeat_password": "Повторите пароль",
        "setup_intro": "Первичный вход. Создайте логин и пароль администратора панели.",
        "create_admin": "Создать администратора",
        "setup_footer": "После сохранения откроется обычная форма входа.",
        "login_intro": "Вход в веб‑панель мониторинга кабельных устройств.",
        "sign_in": "Войти",
        "admin_created_login_now": "Администратор создан. Теперь выполните вход.",
        "invalid_credentials": "Неверный логин или пароль.",
        "username_min3": "Логин должен быть не короче 3 символов.",
        "password_min6": "Пароль должен быть не короче 6 символов.",
        "passwords_mismatch": "Пароли не совпадают.",
        "new_username_short": "Новый логин слишком короткий.",
        "new_password_min6": "Новый пароль должен быть не короче 6 символов.",
        "new_passwords_mismatch": "Новые пароли не совпадают.",
        "current_password_wrong": "Текущий пароль указан неверно.",
        "creds_updated": "Логин и пароль обновлены.",
        "tg_test_sent": "Тестовое сообщение отправлено.",
        "telegram_error": "Ошибка Telegram: {msg}",
        "tg_token_chat_missing": "Не заполнены token/chat_id",
        "local_network_invalid": "Некорректная локальная сеть IPv4 в формате CIDR.",
        "network_changed_restarting": "Параметр локальной сети изменён. Сервис перезапускается.",
        "network_changed_reload": "Параметр локальной сети изменён. Панель обновится после перезапуска сервиса.",
        "port_range": "Порт должен быть в диапазоне 1-65535.",
        "port_changed_restarting": "Порт изменён на {port}. Сервис перезапускается.",
        "port_changed_reload": "Порт изменён на {port}. Обновите адрес панели после перезапуска сервиса.",
        "settings_updated": "Обновлены настройки уведомлений и порогов",
        "settings_updated_selected": "Обновлены настройки уведомлений. Выбрано устройств для Telegram: {count}",
        "test_message": "✅ {app}: тестовое уведомление\nВремя: {time}",
        "tg_msg_online": "🟢 {name} появился в сети\nIP: {ip}\nMAC: {mac}",
        "tg_msg_offline": "🔴 {name} вышел из сети\nПоследний IP: {ip}\nMAC: {mac}",
        "tg_msg_active": "📈 {name} стал активно использовать сеть\nIP: {ip}\nMAC: {mac}\nТрафик за минуту: {traffic}\nСоединения: {conns}",
        "tg_msg_inactive": "📉 {name} перестал быть активным\nIP: {ip}\nMAC: {mac}",
        "event_online_short": "{name} появился в сети",
        "event_offline_short": "{name} вышел из сети",
        "event_active_short": "{name} стал активным: {traffic}, соединений {conns}",
        "event_inactive_short": "{name} перестал быть активным",
        "event_tg_test_sent": "Отправлено тестовое сообщение в Telegram",
        "event_admin_changed": "Изменены логин/пароль администратора",
        "event_admin_created": "Создан администратор {username}",
        "warning_wifi": "Не удалось получить список Wi‑Fi клиентов через ubus: {details}",
        "warning_nlbw": "nlbw недоступен. Установите и запустите nlbwmon. Детали: {details}",
        "warning_monitor_slow": "Цикл мониторинга замедлен: {spent:.2f}s при интервале {interval:.2f}s",
        "warning_monitor_exception": "Ошибка мониторинга: {error}",
        "just_now": "только что",
        "seconds_ago": "{count} сек назад",
        "minutes_ago": "{count} мин назад",
        "hours_ago": "{count} ч назад",
        "days_ago": "{count} дн назад",
        "panel_open_browser": "Откройте в браузере:",
        "first_visit_hint": "При первом открытии панель предложит создать логин и пароль.",
        "ms": "мс",
    },
    "en": {
        "language": "Language",
        "choose_language": "Choose language",
        "language_desc": "Select the RouterDash interface language. It will be saved as the default language.",
        "russian": "Русский",
        "english": "English",
        "lang_saved": "Interface language saved.",
        "current_default": "Current default language",
        "logs": "Logs",
        "logs_caption": "Latest network and notification events",
        "settings": "Settings",
        "logout": "Log out",
        "system": "System",
        "tg_monitoring": "Telegram and monitoring",
        "web_port": "Web panel port",
        "web_port_note": "After saving, the port will be updated, the service will restart, and the panel will open on the new port.",
        "poll_interval_ms": "Polling interval, ms",
        "activity_threshold": "Activity threshold, Kbit/s",
        "notification_threshold": "Notification threshold, Kbit/s",
        "offline_grace": "Offline grace period, sec",
        "local_network_cidr": "Local network (CIDR)",
        "tg_bot_token": "Telegram bot token",
        "tg_chat_id": "User ID / chat_id",
        "tg_chat_placeholder": "Example: 123456789",
        "tg_enabled": "Enable Telegram",
        "track_ipv6": "Track and show IPv6",
        "notify_online": "Notify when device appears online",
        "notify_offline": "Notify when device goes offline",
        "notify_active": "Notify on high activity",
        "notify_inactive": "Notify when activity drops",
        "selected_only": "Notify only for selected devices",
        "select_all": "Select all",
        "unselect_all": "Clear all",
        "tg_devices": "Devices for Telegram notifications",
        "devices_not_found": "No devices found yet. The list will fill after the first clients are detected.",
        "selected_only_note": "If selection mode is disabled, notifications will be sent for all devices.",
        "save_settings": "Save settings",
        "send_test_telegram": "Send Telegram test",
        "admin_account": "Administrator account",
        "new_username": "New username",
        "current_password": "Current password",
        "new_password": "New password",
        "repeat_new_password": "Repeat new password",
        "update_credentials": "Update credentials",
        "app_subtitle": "OpenWrt device monitoring: speed, connections, activity, and Telegram notifications",
        "port_short": "Port",
        "poll_frequency": "Polling",
        "warnings": "Warnings",
        "devices": "Devices",
        "devices_desc": "Kept in history even when currently offline",
        "connected_now": "Online now",
        "connected_desc": "Wired clients currently present in the local network",
        "active": "Active",
        "active_desc": "Above the configured network activity threshold",
        "idle": "Low activity",
        "idle_desc": "Online, but below the activity threshold",
        "devices_section": "Devices",
        "devices_caption": "One row per device by MAC address. IPv4 addresses are shown only from the local network. {ipv6_sentence} Clicking the connection count opens destinations with Up/Down.",
        "devices_caption_ipv6": "IPv6 addresses are hidden behind the “...” button.",
        "th_status": "Status",
        "th_name": "Name / host",
        "th_ipv4": "IPv4",
        "th_ipv6": "IPv6",
        "th_mac": "MAC",
        "th_down": "Download",
        "th_up": "Upload",
        "th_total": "Total",
        "th_conns": "Connections",
        "th_last_seen": "Last activity",
        "status_online": "Online",
        "status_offline": "Offline",
        "activity_present": "Traffic detected",
        "activity_none": "Online, but currently idle",
        "no_events": "No events yet.",
        "event_type": "Type",
        "copied": "Copied ✓",
        "no_active_directions": "No active destinations.",
        "no_conntrack_details": "No active destinations, or conntrack did not provide details for these connections.",
        "direction": "Destination",
        "zero_speed": "0 Kbit/s",
        "save_settings_failed": "Failed to save settings.",
        "settings_saved": "Settings saved.",
        "settings_save_error": "Failed to save settings.",
        "username": "Username",
        "password": "Password",
        "repeat_password": "Repeat password",
        "setup_intro": "First sign-in. Create the administrator username and password for the panel.",
        "create_admin": "Create administrator",
        "setup_footer": "After saving, the regular sign-in page will open.",
        "login_intro": "Sign in to the device monitoring web panel.",
        "sign_in": "Sign in",
        "admin_created_login_now": "Administrator created. Please sign in now.",
        "invalid_credentials": "Invalid username or password.",
        "username_min3": "Username must be at least 3 characters long.",
        "password_min6": "Password must be at least 6 characters long.",
        "passwords_mismatch": "Passwords do not match.",
        "new_username_short": "New username is too short.",
        "new_password_min6": "New password must be at least 6 characters long.",
        "new_passwords_mismatch": "New passwords do not match.",
        "current_password_wrong": "Current password is incorrect.",
        "creds_updated": "Username and password updated.",
        "tg_test_sent": "Test message sent.",
        "telegram_error": "Telegram error: {msg}",
        "tg_token_chat_missing": "token/chat_id is not set",
        "local_network_invalid": "Invalid local IPv4 network in CIDR format.",
        "network_changed_restarting": "Local network setting changed. The service is restarting.",
        "network_changed_reload": "Local network setting changed. The panel will reload after the service restarts.",
        "port_range": "Port must be in the range 1-65535.",
        "port_changed_restarting": "Port changed to {port}. The service is restarting.",
        "port_changed_reload": "Port changed to {port}. Reload the panel using the new address after the service restarts.",
        "settings_updated": "Notification settings and thresholds updated",
        "settings_updated_selected": "Notification settings updated. Selected Telegram devices: {count}",
        "test_message": "✅ {app}: test notification\nTime: {time}",
        "tg_msg_online": "🟢 {name} is online\nIP: {ip}\nMAC: {mac}",
        "tg_msg_offline": "🔴 {name} went offline\nLast IP: {ip}\nMAC: {mac}",
        "tg_msg_active": "📈 {name} became active\nIP: {ip}\nMAC: {mac}\nTraffic per minute: {traffic}\nConnections: {conns}",
        "tg_msg_inactive": "📉 {name} is no longer active\nIP: {ip}\nMAC: {mac}",
        "event_online_short": "{name} is online",
        "event_offline_short": "{name} went offline",
        "event_active_short": "{name} became active: {traffic}, connections {conns}",
        "event_inactive_short": "{name} is no longer active",
        "event_tg_test_sent": "Telegram test message sent",
        "event_admin_changed": "Administrator username/password changed",
        "event_admin_created": "Administrator {username} created",
        "warning_wifi": "Failed to get Wi‑Fi clients via ubus: {details}",
        "warning_nlbw": "nlbw is unavailable. Install and start nlbwmon. Details: {details}",
        "warning_monitor_slow": "Monitoring loop is slow: {spent:.2f}s at interval {interval:.2f}s",
        "warning_monitor_exception": "Monitoring error: {error}",
        "just_now": "just now",
        "seconds_ago": "{count} sec ago",
        "minutes_ago": "{count} min ago",
        "hours_ago": "{count} h ago",
        "days_ago": "{count} d ago",
        "panel_open_browser": "Open in browser:",
        "first_visit_hint": "On first open, the panel will ask you to create a username and password.",
        "ms": "ms",
    },
}


def normalize_lang(value: Any) -> str:
    value = str(value or "").strip().lower()
    return "en" if value.startswith("en") else "ru"


def get_current_lang(settings: Optional[Dict[str, Any]] = None) -> str:
    if settings is None:
        if 'store' in globals():
            try:
                settings = store.get_settings()
            except Exception:
                settings = DEFAULT_SETTINGS
        else:
            settings = DEFAULT_SETTINGS
    return normalize_lang((settings or {}).get("language", DEFAULT_SETTINGS.get("language", "ru")))


def tr(key: str, lang: Optional[str] = None, **kwargs: Any) -> str:
    lang = normalize_lang(lang or get_current_lang())
    value = I18N.get(lang, {}).get(key) or I18N["ru"].get(key) or key
    if kwargs:
        try:
            return value.format(**kwargs)
        except Exception:
            return value
    return value


def lang_strings(lang: Optional[str] = None) -> Dict[str, str]:
    language = normalize_lang(lang or get_current_lang())
    return dict(I18N.get(language, I18N["ru"]))


HTML_BASE = """
<!doctype html>
<html lang="{{ lang }}">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{{ title }}</title>
  <style>
    :root {
      --bg: #04080d;
      --bg-2: #08101a;
      --shell: rgba(7, 12, 19, 0.98);
      --panel: rgba(10, 16, 25, 0.98);
      --panel-2: rgba(12, 20, 31, 0.96);
      --panel-soft: rgba(17, 26, 40, 0.72);
      --surface: rgba(255,255,255,0.025);
      --surface-2: rgba(255,255,255,0.04);
      --border: rgba(255, 170, 46, 0.14);
      --border-strong: rgba(255, 170, 46, 0.34);
      --text: #eef3fb;
      --muted: #a4b0c3;
      --muted-2: #77849a;
      --accent: #ff9b1f;
      --accent-strong: #ff7a00;
      --mustard: #d6a53c;
      --ok: #2dc973;
      --warn: #dfb23e;
      --bad: #8a93a5;
      --danger: #ff657a;
      --radius-xl: 24px;
      --radius-lg: 18px;
      --radius-md: 14px;
      --radius-sm: 10px;
      --shadow: 0 30px 70px rgba(0,0,0,0.44);
    }
    * { box-sizing: border-box; }
    html, body { min-height: 100%; }
    body {
      margin: 0;
      color: var(--text);
      font-family: "Segoe UI", Inter, Arial, Helvetica, sans-serif;
      background:
        radial-gradient(circle at 12% 14%, rgba(255,145,32,0.14) 0%, rgba(255,145,32,0) 22%),
        radial-gradient(circle at 84% 12%, rgba(255,120,0,0.16) 0%, rgba(255,120,0,0) 24%),
        radial-gradient(circle at 76% 82%, rgba(255,167,61,0.12) 0%, rgba(255,167,61,0) 22%),
        radial-gradient(circle at 22% 78%, rgba(255,110,0,0.12) 0%, rgba(255,110,0,0) 24%),
        linear-gradient(180deg, #03070b 0%, #05090e 38%, #09111b 100%);
      background-attachment: fixed;
      position: relative;
      overflow-x: hidden;
      isolation: isolate;
    }
    body::before {
      content: "";
      position: fixed;
      inset: -12%;
      pointer-events: none;
      z-index: -2;
      background:
        radial-gradient(42rem 24rem at 8% 12%, rgba(255,153,43,0.12) 0%, rgba(255,153,43,0.04) 24%, rgba(255,153,43,0) 62%),
        radial-gradient(36rem 24rem at 88% 10%, rgba(255,112,0,0.16) 0%, rgba(255,112,0,0.05) 26%, rgba(255,112,0,0) 64%),
        radial-gradient(34rem 22rem at 22% 88%, rgba(255,133,0,0.12) 0%, rgba(255,133,0,0.04) 24%, rgba(255,133,0,0) 64%),
        radial-gradient(42rem 28rem at 84% 78%, rgba(255,174,72,0.10) 0%, rgba(255,174,72,0.035) 22%, rgba(255,174,72,0) 60%);
      filter: blur(20px) saturate(112%);
      opacity: .95;
      transform: translateZ(0);
    }
    body::after {
      content: "";
      position: fixed;
      inset: 0;
      pointer-events: none;
      z-index: -1;
      background:
        radial-gradient(30rem 20rem at 14% 26%, rgba(255,145,28,0.10) 0%, rgba(255,145,28,0) 60%),
        radial-gradient(28rem 18rem at 72% 24%, rgba(255,120,0,0.08) 0%, rgba(255,120,0,0) 58%),
        radial-gradient(24rem 18rem at 40% 72%, rgba(255,164,56,0.08) 0%, rgba(255,164,56,0) 56%),
        radial-gradient(34rem 20rem at 88% 86%, rgba(255,127,0,0.10) 0%, rgba(255,127,0,0) 62%);
      mix-blend-mode: screen;
      opacity: .72;
    }
    body.panel-open { overflow: hidden; }
    a { color: var(--accent); text-decoration: none; }
    .wrap { width: min(99vw, 1780px); margin: 0 auto; padding: 18px 14px 22px; }

    .app-shell {
      position: relative;
      background: linear-gradient(180deg, rgba(6,10,16,0.98) 0%, rgba(8,13,21,0.99) 100%);
      border: 1px solid rgba(255,255,255,0.06);
      border-radius: var(--radius-xl);
      box-shadow: var(--shadow), inset 0 0 0 1px rgba(255,255,255,0.015);
      overflow: hidden;
    }
    .app-shell::before {
      content: "";
      position: absolute;
      inset: 0;
      pointer-events: none;
      background:
        radial-gradient(circle at 8% 16%, rgba(255,158,45,0.08) 0%, rgba(255,158,45,0) 24%),
        radial-gradient(circle at 92% 10%, rgba(255,140,0,0.12) 0%, rgba(255,140,0,0) 22%),
        radial-gradient(circle at 80% 86%, rgba(255,167,61,0.06) 0%, rgba(255,167,61,0) 22%),
        linear-gradient(180deg, rgba(255,255,255,0.018), transparent 100px);
      z-index: 0;
    }
    .app-content {
      position: relative;
      z-index: 1;
      padding: 18px;
      border-top: 3px solid var(--accent);
    }

    .browser-bar {
      display: flex;
      align-items: center;
      gap: 12px;
      padding: 14px 18px;
      border-bottom: 1px solid rgba(255,255,255,0.06);
      background: linear-gradient(180deg, rgba(14,18,27,0.95) 0%, rgba(10,15,23,0.94) 100%);
    }
    .traffic-lights { display: flex; gap: 8px; align-items: center; }
    .dot { width: 10px; height: 10px; border-radius: 50%; }
    .dot.red { background: #ff5f57; }
    .dot.yellow { background: #ffbd2f; }
    .dot.green { background: #28c840; }
    .address-bar {
      flex: 1;
      height: 34px;
      border-radius: 999px;
      background: rgba(255,255,255,0.04);
      border: 1px solid rgba(255,255,255,0.04);
      display: flex;
      align-items: center;
      justify-content: center;
      color: var(--muted-2);
      font-size: 12px;
      letter-spacing: .18px;
    }
    .browser-tab {
      width: min(22%, 250px);
      height: 34px;
      border-radius: 999px;
      background: rgba(255,255,255,0.028);
      border: 1px solid rgba(255,255,255,0.035);
    }

    .topbar {
      display: flex;
      gap: 18px;
      align-items: flex-start;
      justify-content: space-between;
      margin-bottom: 16px;
    }
    .brand { font-size: 19px; font-weight: 800; letter-spacing: .28px; text-transform: uppercase; line-height: 1; }
    .brand .accent { color: var(--accent); }
    .brand-sub { margin-top: 6px; color: var(--muted); font-size: 12px; }
    .muted { color: var(--muted); }

    .grid { display: grid; gap: 14px; grid-template-columns: repeat(12, minmax(0, 1fr)); }
    .card {
      grid-column: span 12;
      min-width: 0;
      background: linear-gradient(180deg, rgba(9,15,23,0.97) 0%, rgba(8,13,20,0.99) 100%);
      border: 1px solid rgba(255,255,255,0.06);
      border-radius: var(--radius-lg);
      padding: 16px;
      box-shadow: 0 10px 24px rgba(0,0,0,0.22);
    }
    .tile-card {
      position: relative;
      overflow: hidden;
      min-height: 128px;
      box-shadow: inset 0 0 0 1px rgba(255,255,255,0.012), 0 0 0 1px rgba(255,170,46,0.08), 0 0 18px rgba(255,122,0,0.06);
    }
    .tile-card::before {
      content: "";
      position: absolute;
      left: 0; top: 0; bottom: 0;
      width: 4px;
      background: linear-gradient(180deg, var(--accent-strong) 0%, var(--mustard) 100%);
    }
    .span-3 { grid-column: span 3; }
    .span-4 { grid-column: span 4; }
    .span-6 { grid-column: span 6; }
    .span-12 { grid-column: span 12; }

    .toolbar-group { display: flex; gap: 10px; flex-wrap: wrap; align-items: center; justify-content: flex-end; }
    .pill {
      display: inline-flex;
      align-items: center;
      gap: 8px;
      padding: 9px 13px;
      min-height: 40px;
      border-radius: 999px;
      border: 1px solid rgba(255,255,255,0.06);
      background: rgba(17, 22, 31, 0.96);
      color: #e5ebf4;
      font-size: 13px;
      font-weight: 700;
      white-space: nowrap;
    }
    .pill.ok { color: #cfffdf; border-color: rgba(47,203,118,0.22); background: rgba(22,79,49,0.68); }
    .pill.warn { color: #ffe7ab; border-color: rgba(221,177,61,0.22); background: rgba(93,70,12,0.58); }
    .pill.bad { color: #e6eaf1; border-color: rgba(137,147,166,0.20); background: rgba(58,64,77,0.62); }
    .pill.muted { color: #c8d2e4; }

    label { display: block; font-size: 13px; color: var(--muted); margin-bottom: 6px; }
    input[type=text], input[type=password], input[type=number] {
      width: 100%;
      border-radius: 10px;
      border: 1px solid rgba(255,255,255,0.08);
      background: rgba(7, 13, 20, 0.98);
      color: var(--text);
      padding: 11px 12px;
      outline: none;
      transition: border-color .12s ease, box-shadow .12s ease;
    }
    input[type=text]:focus, input[type=password]:focus, input[type=number]:focus {
      border-color: rgba(255,170,46,0.42);
      box-shadow: 0 0 0 3px rgba(255,155,31,0.10);
    }
    input[type=checkbox] { accent-color: var(--accent-strong); transform: scale(1.05); }
    form.grid-form { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 12px 14px; }
    .checkrow { display: flex; gap: 18px; flex-wrap: wrap; margin-top: 8px; }
    .checkrow label { display: inline-flex; align-items: center; gap: 8px; margin-bottom: 0; color: var(--text); }
    .actions { display: flex; gap: 10px; flex-wrap: wrap; margin-top: 14px; }

    button, .button {
      appearance: none;
      border: 0;
      border-radius: 10px;
      background: linear-gradient(180deg, #ff9b1f 0%, #ff7a00 100%);
      color: #110c06;
      font-weight: 800;
      padding: 11px 16px;
      cursor: pointer;
      transition: transform .12s ease, filter .12s ease, opacity .12s ease;
    }
    button:hover, .button:hover { transform: translateY(-1px); filter: brightness(1.04); }
    button:active, .button:active { transform: translateY(0); }
    button.secondary, .button.secondary {
      background: rgba(20, 26, 36, 0.98);
      color: var(--text);
      border: 1px solid rgba(255,255,255,0.07);
    }
    button.danger, .button.danger {
      background: rgba(110, 27, 43, 0.95);
      color: #ffe7ec;
      border: 1px solid rgba(255,127,152,0.26);
    }
    button.mini, .button.mini { padding: 8px 12px; min-height: 36px; font-size: 13px; }

    .notice {
      border-radius: 12px;
      padding: 12px 14px;
      margin-bottom: 14px;
      border: 1px solid rgba(255,170,46,0.18);
      background: rgba(90, 55, 5, 0.16);
      color: #fff3da;
    }
    .notice.error { background: rgba(132, 31, 55, 0.18); border-color: rgba(255,127,152,0.18); color: #ffdbe4; }
    .notice.success { background: rgba(28, 112, 77, 0.18); border-color: rgba(82,224,164,0.18); color: #deffef; }

    .stat { display: flex; flex-direction: column; gap: 10px; }
    .stat-top { display: flex; justify-content: space-between; gap: 12px; align-items: flex-start; }
    .stat-label {
      color: #e8eef7;
      font-size: 12px;
      text-transform: uppercase;
      letter-spacing: .36px;
      margin-bottom: 2px;
    }
    .stat-icon {
      width: 40px;
      height: 40px;
      display: inline-flex;
      align-items: center;
      justify-content: center;
      opacity: .82;
      color: rgba(255,255,255,0.44);
      flex: 0 0 auto;
    }
    .stat-icon svg {
      width: 36px;
      height: 36px;
      stroke: currentColor;
      fill: none;
      stroke-width: 1.9;
      stroke-linecap: round;
      stroke-linejoin: round;
    }
    .stat .value {
      font-size: 52px;
      line-height: 1;
      font-weight: 800;
      letter-spacing: -1px;
      margin-top: 2px;
    }
    .small { font-size: 12px; color: var(--muted); }
    .mono { font-family: Consolas, Monaco, monospace; }
    .footer-note { margin-top: 10px; color: var(--muted); font-size: 12px; }

    .table-shell {
      border-radius: 18px;
      border: 1px solid rgba(255,255,255,0.05);
      background: linear-gradient(180deg, rgba(7,12,19,0.98) 0%, rgba(8,13,20,0.98) 100%);
      padding: 10px;
      overflow: hidden;
    }
    .table-wrap {
      overflow: auto;
      border-radius: 12px;
      background: rgba(6, 10, 16, 0.92);
      padding: 6px;
      max-width: 100%;
    }
    table {
      width: 100%;
      min-width: 1560px;
      border-collapse: separate;
      border-spacing: 0 8px;
      font-size: 14px;
    }
    th, td {
      text-align: left;
      padding: 8px 8px;
      vertical-align: middle;
      border-bottom: 0;
    }
    th {
      color: #d4dced;
      font-size: 11px;
      letter-spacing: .4px;
      text-transform: uppercase;
      position: sticky;
      top: 0;
      background: rgba(6,10,16,0.98);
      z-index: 2;
    }
    tbody tr {
      background: rgba(255,255,255,0.02);
      box-shadow: inset 0 0 0 1px rgba(255,255,255,0.03);
    }
    tbody tr:hover {
      background: rgba(255,155,31,0.06);
      box-shadow: inset 0 0 0 1px rgba(255,170,46,0.16);
    }
    tbody td:first-child { border-radius: 8px 0 0 8px; }
    tbody td:last-child { border-radius: 0 8px 8px 0; }

    .event-list { display: flex; flex-direction: column; gap: 10px; }
    .event-item {
      border: 1px solid rgba(255,255,255,0.06);
      background: rgba(255,255,255,0.03);
      border-radius: 12px;
      padding: 10px 12px;
    }
    .right { text-align: right; }
    .login-box { max-width: 620px; margin: 7vh auto 0 auto; }

    .icon-btn {
      width: 44px;
      height: 44px;
      border-radius: 12px;
      display: inline-flex;
      align-items: center;
      justify-content: center;
      padding: 0;
      background: rgba(17, 22, 31, 0.98);
      color: var(--text);
      border: 1px solid rgba(255,255,255,0.07);
      font-size: 20px;
      line-height: 1;
      flex: 0 0 auto;
    }
    .icon-btn svg {
      width: 20px;
      height: 20px;
      stroke: currentColor;
      fill: none;
      stroke-width: 1.9;
      stroke-linecap: round;
      stroke-linejoin: round;
    }
    .icon-btn:hover { color: #fff; border-color: rgba(255,170,46,0.24); }

    .overlay-backdrop {
      position: fixed; inset: 0; background: rgba(2, 7, 12, 0.62);
      opacity: 0; pointer-events: none; transition: opacity .18s ease; z-index: 40; backdrop-filter: blur(3px);
    }
    .overlay-backdrop.open { opacity: 1; pointer-events: auto; }
    .overlay-panel {
      position: fixed; top: 18px; bottom: 18px; width: min(480px, calc(100vw - 22px));
      background: linear-gradient(180deg, rgba(9,15,24,0.99) 0%, rgba(7,12,19,0.99) 100%);
      border: 1px solid rgba(255,255,255,0.08); box-shadow: 0 24px 60px rgba(0,0,0,0.34);
      z-index: 55; overflow: auto; opacity: 0; pointer-events: none;
      transition: transform .18s ease, opacity .18s ease; border-radius: 18px;
    }
    .overlay-panel.overlay-right { right: 18px; transform: translateX(34px); }
    .overlay-panel.overlay-left { left: 18px; transform: translateX(-34px); }
    .overlay-panel.open { opacity: 1; pointer-events: auto; }
    .overlay-panel.open.overlay-right, .overlay-panel.open.overlay-left { transform: translateX(0); }
    .panel-head {
      position: sticky; top: 0; z-index: 3; display: flex; align-items: center; justify-content: space-between;
      gap: 12px; padding: 16px 18px; background: rgba(10, 16, 24, 0.98);
      border-bottom: 1px solid rgba(255,255,255,0.06); backdrop-filter: blur(8px);
    }
    .panel-title { font-size: 22px; font-weight: 800; text-transform: uppercase; letter-spacing: 0.35px; }
    .panel-body { padding: 18px; }
    .panel-close {
      width: 38px; height: 38px; min-height: 38px; padding: 0; border-radius: 10px; font-size: 22px;
      background: rgba(255,255,255,0.06); color: var(--text); border: 1px solid rgba(255,255,255,0.08);
    }
    .floating-log-btn {
      position: fixed;
      top: 14px;
      left: 14px;
      z-index: 32;
      box-shadow: 0 10px 28px rgba(0,0,0,0.24);
    }
    .floating-lang-btn {
      position: fixed;
      right: 14px;
      bottom: 14px;
      z-index: 32;
      box-shadow: 0 10px 28px rgba(0,0,0,0.24);
    }
    .lang-grid {
      display: grid;
      grid-template-columns: 1fr;
      gap: 10px;
    }
    .lang-card {
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 14px;
      padding: 14px 16px;
      border-radius: 14px;
      border: 1px solid rgba(255,255,255,0.08);
      background: rgba(255,255,255,0.03);
    }
    .lang-card strong { font-size: 15px; }
    .lang-card .small { margin-top: 4px; }
    .panel-section { padding: 0 0 16px; margin: 0 0 18px; border-bottom: 1px solid rgba(255,255,255,0.06); }
    .panel-section:last-child { border-bottom: 0; margin-bottom: 0; padding-bottom: 0; }
    .section-title { display: flex; align-items: center; justify-content: space-between; gap: 12px; margin-bottom: 12px; }
    .section-title h3 { margin: 0; font-size: 16px; text-transform: uppercase; letter-spacing: .28px; }
    .table-tight td, .table-tight th { white-space: nowrap; }

    .cell-stack { display: flex; flex-wrap: wrap; gap: 8px; align-items: center; justify-content: flex-start; }
    .copy-chip,
    .no-copy-chip {
      display: inline-flex;
      align-items: center;
      justify-content: center;
      max-width: 100%;
      gap: 8px;
      border-radius: 999px;
      padding: 9px 12px;
      min-height: 38px;
      border: 1px solid rgba(255,255,255,0.08);
      background: rgba(17, 22, 31, 0.98);
      color: var(--text);
      line-height: 1.15;
      font-size: 13px;
      text-align: center;
      box-shadow: 0 4px 16px rgba(0,0,0,0.16);
    }
    .copy-chip {
      cursor: pointer;
      transition: transform .12s ease, border-color .12s ease, background .12s ease;
    }
    .copy-chip:hover { transform: translateY(-1px); border-color: rgba(255,170,46,0.36); background: rgba(36, 25, 12, 0.98); }
    .copy-chip:active { transform: translateY(0); }
    .copy-chip.copied { border-color: rgba(82,224,164,0.42); background: rgba(50, 73, 42, 0.96); color: #f5f9d7; }
    .copy-chip.ghost-chip, .no-copy-chip.ghost-chip {
      background: rgba(255,255,255,0.03);
      border-color: rgba(255,255,255,0.06);
      color: #c6b9aa;
      box-shadow: none;
    }
    .copy-chip.status-ok { background: rgba(29, 88, 47, 0.96); border-color: rgba(66,217,123,0.28); color: #d7ffe7; }
    .copy-chip.status-warn { background: rgba(88, 66, 17, 0.96); border-color: rgba(220,167,45,0.30); color: #ffe8a7; }
    .copy-chip.status-bad { background: rgba(53, 55, 63, 0.96); border-color: rgba(138,141,150,0.32); color: #e3e5ea; }
    .copy-chip .chip-text, .no-copy-chip .chip-text { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }

    .sort-btn {
      display: inline-flex; align-items: center; gap: 8px; border: 0; background: transparent; color: inherit;
      font: inherit; font-weight: 700; text-transform: uppercase; letter-spacing: .3px; cursor: pointer; padding: 0;
    }
    .sort-btn:hover { color: #eef3fb; }
    .sort-indicator {
      display: inline-flex; align-items: center; justify-content: center; width: 18px; height: 18px;
      border-radius: 999px; background: rgba(255,255,255,0.05); color: #c9aa79; font-size: 11px; line-height: 1; flex: 0 0 auto;
    }
    .sort-btn.active .sort-indicator { background: rgba(255,155,31,0.18); color: #fff2e1; border: 1px solid rgba(255,155,31,0.22); }

    .device-selector-toolbar {
      display: flex; flex-wrap: wrap; align-items: center; justify-content: space-between; gap: 10px; margin-bottom: 12px;
    }
    .device-selector-toolbar .checkrow { margin-top: 0; }
    .device-selector {
      display: grid; grid-template-columns: 1fr; gap: 8px; max-height: 280px; overflow: auto; padding: 6px;
      border-radius: 12px; background: rgba(5, 16, 25, 0.62); border: 1px solid rgba(255,255,255,0.06);
    }
    .device-option {
      display: flex; align-items: flex-start; gap: 10px; padding: 10px 12px; margin: 0; border-radius: 10px;
      background: rgba(255,255,255,0.03); border: 1px solid rgba(255,255,255,0.04); color: var(--text);
    }
    .device-option:hover { border-color: rgba(255,155,31,0.18); background: rgba(255,155,31,0.06); }
    .device-option input { margin-top: 3px; }
    .device-option-text { display: flex; flex-direction: column; gap: 3px; }

    .panel-heading { display: flex; align-items: flex-start; justify-content: space-between; gap: 14px; flex-wrap: wrap; margin-bottom: 14px; }
    .panel-heading h2 { margin: 0; font-size: 18px; }
    .panel-caption { color: var(--muted); font-size: 12px; margin-top: 6px; }

    .ipv6-disclosure {
      position: relative;
      display: inline-block;
    }
    .ipv6-disclosure > summary {
      list-style: none;
      cursor: pointer;
      border: 1px solid rgba(255,255,255,0.08);
      background: rgba(17, 22, 31, 0.98);
      color: var(--text);
      min-width: 42px;
      justify-content: center;
      user-select: none;
    }
    .ipv6-disclosure > summary::-webkit-details-marker { display: none; }
    .ipv6-disclosure[open] > summary {
      border-color: rgba(255,170,46,0.28);
      background: rgba(36, 25, 12, 0.98);
    }
    .ipv6-popover {
      position: absolute;
      top: calc(100% + 8px);
      right: 0;
      min-width: 280px;
      max-width: min(60vw, 420px);
      padding: 10px;
      border-radius: 14px;
      border: 1px solid rgba(255,255,255,0.08);
      background: rgba(9, 14, 22, 0.99);
      box-shadow: 0 20px 44px rgba(0,0,0,0.38);
      z-index: 15;
    }
    .ipv6-list { display: flex; flex-direction: column; gap: 8px; }
    .ipv6-list .copy-chip { justify-content: flex-start; width: 100%; }
    .inline-switch-note { margin-top: 6px; }

    .table-empty-click { pointer-events: none; }

    .table-tight td { padding-top: 10px; padding-bottom: 10px; vertical-align: middle; }
    .metro-box, .copy-chip, .no-copy-chip {
      min-height: 40px;
      width: auto;
      max-width: 100%;
      justify-content: flex-start;
      padding: 10px 14px;
      border-radius: 999px;
      border: 1px solid rgba(255,255,255,0.07);
      background: linear-gradient(180deg, rgba(16,24,36,0.96) 0%, rgba(10,16,25,0.96) 100%);
      box-shadow: inset 0 1px 0 rgba(255,255,255,0.03);
      font-weight: 600;
      letter-spacing: 0.01em;
    }
    .cell-stack { gap: 8px; flex-wrap: nowrap; }
    .copy-chip { cursor: pointer; }
    .copy-chip:hover, .copy-chip:focus-visible, .table-disclosure[open] > summary, .disclosure-trigger:hover, .disclosure-trigger:focus-visible {
      border-color: rgba(255,170,46,0.30);
      background: linear-gradient(180deg, rgba(28,20,13,0.98) 0%, rgba(16,12,8,0.98) 100%);
      box-shadow: 0 0 0 1px rgba(255,170,46,0.05), 0 8px 26px rgba(0,0,0,0.24);
    }
    .metro-box.metric-box, .no-copy-chip.metric-box, .disclosure-trigger.metric-box { justify-content: center; text-align: center; min-width: 72px; }
    .status-box { user-select: none; cursor: default; justify-content: center; min-width: 110px; }
    .table-tight td.right, .table-tight th.right { text-align: center; }
    .table-tight td.right > *, .table-tight td.right .table-disclosure { margin-left: auto; margin-right: auto; text-align: center; }
    .status-box.status-ok { background: linear-gradient(180deg, rgba(31,104,67,0.86), rgba(20,82,50,0.88)); border-color: rgba(66,220,132,0.28); color: #e7fff1; }
    .status-box.status-warn { background: linear-gradient(180deg, rgba(122,90,18,0.86), rgba(100,73,12,0.88)); border-color: rgba(255,202,69,0.24); color: #fff6d9; }
    .status-box.status-bad { background: linear-gradient(180deg, rgba(112,38,49,0.84), rgba(88,28,38,0.88)); border-color: rgba(255,101,122,0.24); color: #ffe8ec; }
    .table-disclosure { position: relative; display: inline-block; width: auto; max-width: 100%; }
    .table-disclosure > summary { list-style: none; cursor: pointer; }
    .table-disclosure > summary::-webkit-details-marker { display: none; }
    .table-popover {
      position: absolute;
      top: calc(100% + 8px);
      right: 0;
      min-width: 320px;
      max-width: min(78vw, 540px);
      padding: 12px;
      border-radius: 16px;
      border: 1px solid rgba(255,255,255,0.08);
      background: rgba(8, 13, 20, 0.99);
      box-shadow: 0 24px 46px rgba(0,0,0,0.42);
      z-index: 20;
      backdrop-filter: blur(14px);
    }
    .conn-popover { min-width: 360px; }
    .conn-header, .conn-row { display: grid; grid-template-columns: minmax(180px, 1fr) 92px 92px; gap: 10px; align-items: center; }
    .conn-header { margin-bottom: 8px; padding: 0 2px 6px; color: var(--muted); font-size: 11px; text-transform: uppercase; letter-spacing: .05em; border-bottom: 1px solid rgba(255,255,255,0.06); }
    .conn-row { padding: 9px 2px; border-bottom: 1px solid rgba(255,255,255,0.05); }
    .conn-row:last-child { border-bottom: 0; }
    .conn-host { font-weight: 600; color: var(--text); word-break: break-word; }
    .conn-remote { color: var(--muted); font-size: 12px; word-break: break-word; margin-top: 2px; }
    .conn-num { text-align: right; font-variant-numeric: tabular-nums; color: #f6f8fb; }
    .conn-empty { color: var(--muted); padding: 6px 2px 2px; }
    .total-metric {
      display: inline-flex;
      align-items: center;
      justify-content: center;
      gap: 10px;
      flex-wrap: nowrap;
      max-width: 100%;
      margin: 0 auto;
    }
    .total-metric .metric-box { min-width: 96px; }
    .activity-wrap { display: inline-flex; align-items: center; justify-content: center; width: 34px; height: 34px; border-radius: 50%; position: relative; flex: 0 0 auto; }
    .activity-dot { width: 12px; height: 12px; border-radius: 50%; position: relative; }
    .activity-wrap::before, .activity-wrap::after { content: ""; position: absolute; inset: 8px; border-radius: 50%; border: 1px solid transparent; opacity: 0; }
    .activity-wrap.state-active .activity-dot { background: #32d777; box-shadow: 0 0 18px rgba(50,215,119,0.55); }
    .activity-wrap.state-idle .activity-dot { background: #f0be43; box-shadow: 0 0 18px rgba(240,190,67,0.42); }
    .activity-wrap.state-offline .activity-dot { background: #ff657a; box-shadow: 0 0 18px rgba(255,101,122,0.42); }
    .activity-wrap.state-active::before, .activity-wrap.state-active::after { border-color: rgba(50,215,119,0.28); animation: pulseRing 2.2s ease-out infinite; opacity: 1; }
    .activity-wrap.state-idle::before, .activity-wrap.state-idle::after { border-color: rgba(240,190,67,0.26); animation: pulseRing 2.2s ease-out infinite; opacity: 1; }
    .activity-wrap.state-offline::before, .activity-wrap.state-offline::after { border-color: rgba(255,101,122,0.24); animation: pulseRing 2.2s ease-out infinite; opacity: 1; }
    .activity-wrap::after { animation-delay: 1.1s !important; }
    @keyframes pulseRing {
      0% { transform: scale(0.62); opacity: .82; }
      70% { opacity: .12; }
      100% { transform: scale(1.34); opacity: 0; }
    }
    @media (max-width: 760px) {
      .table-popover { right: auto; left: 0; max-width: min(92vw, 540px); }
      .conn-popover { min-width: 300px; }
      .conn-header, .conn-row { grid-template-columns: minmax(120px, 1fr) 76px 76px; gap: 8px; }
    }

    @media (max-width: 1120px) {
      .span-3,.span-4,.span-6,.span-12 { grid-column: span 12; }
      .topbar { flex-direction: column; align-items: flex-start; }
      .toolbar-group { justify-content: flex-start; }
      form.grid-form { grid-template-columns: 1fr; }
    }
    @media (max-width: 820px) {
      .wrap { width: min(100vw, 100%); padding: 64px 10px 14px; }
      .app-content { padding: 12px; }
      .card { padding: 14px; }
      .stat .value { font-size: 42px; }
      .floating-log-btn { top: 10px; left: 10px; }
      .floating-lang-btn { right: 10px; bottom: 10px; }
      .overlay-panel.overlay-left { left: 10px; }
      .overlay-panel.overlay-right { right: 10px; }
      .overlay-panel { top: 10px; bottom: 10px; width: calc(100vw - 20px); }
    }
    @media (max-width: 760px) {
      .table-shell { padding: 0; border: 0; background: transparent; }
      .table-wrap { overflow: visible; padding: 0; background: transparent; }
      table { min-width: 0; border-spacing: 0 12px; }
      thead { display: none; }
      tbody, tr, td { display: block; width: 100%; }
      tbody tr {
        padding: 8px;
        border-radius: 14px;
        background: rgba(255,255,255,0.03);
        box-shadow: inset 0 0 0 1px rgba(255,255,255,0.05);
      }
      tbody td {
        padding: 7px 6px;
        display: flex;
        align-items: center;
        gap: 12px;
        justify-content: space-between;
        border-bottom: 1px solid rgba(255,255,255,0.04);
      }
      tbody td:last-child { border-bottom: 0; }
      tbody td::before {
        content: attr(data-label);
        color: var(--muted);
        font-size: 11px;
        letter-spacing: .3px;
        text-transform: uppercase;
        flex: 0 0 42%;
        max-width: 42%;
      }
      tbody td > * {
        margin-left: auto;
        max-width: 58%;
      }
      .ipv6-popover {
        position: fixed;
        left: 10px;
        right: 10px;
        top: auto;
        bottom: 14px;
        min-width: 0;
        max-width: none;
      }
      .pill { min-height: 36px; padding: 8px 11px; }
      .icon-btn { width: 40px; height: 40px; }
    }
  </style>
</head>
<body>
  {{ body|safe }}
</body>
</html>
"""



SETUP_TEMPLATE = """
<div class="wrap">
  <div class="login-box">
    <div class="app-shell">
      <div class="browser-bar">
        <div class="traffic-lights"><span class="dot red"></span><span class="dot yellow"></span><span class="dot green"></span></div>
        <div class="address-bar">http://router-ip:1999/setup</div>
        <div class="browser-tab"></div>
      </div>
      <div class="app-content">
        <div class="card">
          <div class="brand">ROUTER<span class="accent">DASH</span></div>
          <p class="muted">{{ t('setup_intro') }}</p>
          {% if error %}<div class="notice error">{{ error }}</div>{% endif %}
          <form method="post">
            <label>{{ t('username') }}</label>
            <input type="text" name="username" autocomplete="username" required>
            <div style="height:10px"></div>
            <label>{{ t('password') }}</label>
            <input type="password" name="password" autocomplete="new-password" required>
            <div style="height:10px"></div>
            <label>{{ t('repeat_password') }}</label>
            <input type="password" name="password2" autocomplete="new-password" required>
            <div class="actions">
              <button type="submit">{{ t('create_admin') }}</button>
            </div>
          </form>
          <div class="footer-note">{{ t('setup_footer') }}</div>
        </div>
      </div>
    </div>
  </div>
</div>
"""


LOGIN_TEMPLATE = """
<div class="wrap">
  <div class="login-box">
    <div class="app-shell">
      <div class="browser-bar">
        <div class="traffic-lights"><span class="dot red"></span><span class="dot yellow"></span><span class="dot green"></span></div>
        <div class="address-bar">http://router-ip:1999/login</div>
      </div>
      <div class="app-content">
        <div class="card">
          <div class="brand">ROUTER<span class="accent">DASH</span></div>
          <p class="muted">{{ t('login_intro') }}</p>
          {% if message %}<div class="notice success">{{ message }}</div>{% endif %}
          {% if error %}<div class="notice error">{{ error }}</div>{% endif %}
          <form method="post">
            <label>{{ t('username') }}</label>
            <input type="text" name="username" autocomplete="username" required>
            <div style="height:10px"></div>
            <label>{{ t('password') }}</label>
            <input type="password" name="password" autocomplete="current-password" required>
            <div class="actions">
              <button type="submit">{{ t('sign_in') }}</button>
            </div>
          </form>
        </div>
      </div>
    </div>
  </div>
</div>
"""


DASHBOARD_TEMPLATE = """
<button class="icon-btn floating-log-btn" type="button" onclick="toggleLogsPanel()" title="{{ t('logs') }}">
  <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M8 3h6l5 5v13H5V3h3z"/><path d="M14 3v6h6"/><path d="M9 12h6"/><path d="M9 16h6"/></svg>
</button>
<button class="icon-btn floating-lang-btn" type="button" onclick="toggleLanguagePanel()" title="{{ t('language') }}">
  <svg viewBox="0 0 24 24" aria-hidden="true"><circle cx="12" cy="12" r="9"/><path d="M3 12h18"/><path d="M12 3a15 15 0 0 1 0 18"/><path d="M12 3a15 15 0 0 0 0 18"/></svg>
</button>
<div id="panel-backdrop" class="overlay-backdrop" onclick="closePanels()"></div>

<div id="logs-panel" class="overlay-panel overlay-left">
  <div class="panel-head">
    <div>
      <div class="panel-title">{{ t('logs') }}</div>
      <div class="small">{{ t('logs_caption') }}</div>
    </div>
    <button class="panel-close" type="button" onclick="closePanels()">×</button>
  </div>
  <div class="panel-body">
    <div class="event-list" id="events-list">
      {% for e in events %}
        <div class="event-item">
          <div><strong>{{ e.ts_h }}</strong> — {{ e.message }}</div>
          <div class="small">{{ t('event_type') }}: {{ e.kind }}{% if e.mac %} · {{ e.mac }}{% endif %}</div>
        </div>
      {% endfor %}
      {% if not events %}<div class="small">{{ t('no_events') }}</div>{% endif %}
    </div>
  </div>
</div>

<div id="settings-panel" class="overlay-panel overlay-right">
  <div class="panel-head">
    <div>
      <div class="panel-title">{{ t('settings') }}</div>
    </div>
    <button class="panel-close" type="button" onclick="closePanels()">×</button>
  </div>
  <div class="panel-body">
    <div class="panel-section">
      <div class="section-title">
        <h3>{{ t('tg_monitoring') }}</h3>
        <span class="pill muted">{{ t('system') }}</span>
      </div>
      <form id="settings-form" class="grid-form" method="post" action="{{ url_for('save_settings') }}">
        <div>
          <label>{{ t('web_port') }}</label>
          <input type="number" name="port" min="1" max="65535" value="{{ settings.port }}">
          <div class="footer-note inline-switch-note">{{ t('web_port_note') }}</div>
        </div>
        <div>
          <label>{{ t('poll_interval_ms') }}</label>
          <input type="number" name="poll_interval_ms" min="100" step="50" value="{{ settings.poll_interval_ms }}">
        </div>
        <div>
          <label>{{ t('activity_threshold') }}</label>
          <input type="number" name="activity_total_kbps" min="1" value="{{ settings.activity_total_kbps }}">
        </div>
        <div>
          <label>{{ t('notification_threshold') }}</label>
          <input type="number" name="notification_total_kbps" min="1" value="{{ settings.notification_total_kbps }}">
        </div>
        <div>
          <label>{{ t('offline_grace') }}</label>
          <input type="number" name="offline_grace_sec" min="5" max="600" value="{{ settings.offline_grace_sec }}">
        </div>
        <div>
          <label>{{ t('local_network_cidr') }}</label>
          <input type="text" name="local_network_cidr" value="{{ settings.local_network_cidr }}" placeholder="192.168.0.0/24">
        </div>
        <div>
          <label>{{ t('tg_bot_token') }}</label>
          <input type="text" name="telegram_bot_token" value="{{ settings.telegram_bot_token }}" placeholder="123456:ABC...">
        </div>
        <div>
          <label>{{ t('tg_chat_id') }}</label>
          <input type="text" name="telegram_chat_id" value="{{ settings.telegram_chat_id }}" placeholder="{{ t('tg_chat_placeholder') }}">
        </div>
        <div style="grid-column:1/-1;">
          <div class="checkrow">
            <label><input type="checkbox" name="telegram_enabled" {% if settings.telegram_enabled %}checked{% endif %}> {{ t('tg_enabled') }}</label>
            <label><input type="checkbox" name="track_ipv6" {% if settings.track_ipv6 %}checked{% endif %}> {{ t('track_ipv6') }}</label>
            <label><input type="checkbox" name="notify_online" {% if settings.notify_online %}checked{% endif %}> {{ t('notify_online') }}</label>
            <label><input type="checkbox" name="notify_offline" {% if settings.notify_offline %}checked{% endif %}> {{ t('notify_offline') }}</label>
            <label><input type="checkbox" name="notify_active" {% if settings.notify_active %}checked{% endif %}> {{ t('notify_active') }}</label>
            <label><input type="checkbox" name="notify_inactive" {% if settings.notify_inactive %}checked{% endif %}> {{ t('notify_inactive') }}</label>
          </div>
        </div>
        <div style="grid-column:1/-1;">
          <div class="device-selector-toolbar">
            <div class="checkrow">
              <label><input type="checkbox" name="telegram_limit_to_selected_devices" {% if settings.telegram_limit_to_selected_devices %}checked{% endif %}> {{ t('selected_only') }}</label>
            </div>
            <div class="actions" style="margin-top:0;">
              <button class="secondary mini" type="button" onclick="setAllDeviceSelection(true)">{{ t('select_all') }}</button>
              <button class="secondary mini" type="button" onclick="setAllDeviceSelection(false)">{{ t('unselect_all') }}</button>
            </div>
          </div>
          <label>{{ t('tg_devices') }}</label>
          {% if telegram_devices %}
            <div class="device-selector" id="telegram-device-selector">
              {% for item in telegram_devices %}
                <label class="device-option">
                  <input class="telegram-device-checkbox" type="checkbox" name="telegram_selected_devices" value="{{ item.mac }}" {% if item.selected %}checked{% endif %}>
                  <span class="device-option-text">
                    <strong>{{ item.display_name }}</strong>
                    <span class="small">{{ item.status_h }} · {{ item.mac }}</span>
                  </span>
                </label>
              {% endfor %}
            </div>
          {% else %}
            <div class="device-selector"><div class="small">{{ t('devices_not_found') }}</div></div>
          {% endif %}
          <div class="footer-note">{{ t('selected_only_note') }}</div>
        </div>
        <div style="grid-column:1/-1;" class="actions">
          <button id="settings-submit-btn" type="submit">{{ t('save_settings') }}</button>
          <button class="secondary" type="submit" formaction="{{ url_for('test_telegram') }}" formnovalidate>{{ t('send_test_telegram') }}</button>
        </div>
      </form>
    </div>

    <div class="panel-section">
      <div class="section-title">
        <h3>{{ t('admin_account') }}</h3>
      </div>
      <form class="grid-form" method="post" action="{{ url_for('change_password') }}">
        <div>
          <label>{{ t('new_username') }}</label>
          <input type="text" name="username" value="{{ admin_username }}" required>
        </div>
        <div>
          <label>{{ t('current_password') }}</label>
          <input type="password" name="current_password" required>
        </div>
        <div>
          <label>{{ t('new_password') }}</label>
          <input type="password" name="new_password" required>
        </div>
        <div>
          <label>{{ t('repeat_new_password') }}</label>
          <input type="password" name="new_password2" required>
        </div>
        <div style="grid-column:1/-1;" class="actions">
          <button type="submit">{{ t('update_credentials') }}</button>
        </div>
      </form>
    </div>
  </div>
</div>

<div id="language-panel" class="overlay-panel overlay-right">
  <div class="panel-head">
    <div>
      <div class="panel-title">{{ t('choose_language') }}</div>
      <div class="small">{{ t('language_desc') }}</div>
    </div>
    <button class="panel-close" type="button" onclick="closePanels()">×</button>
  </div>
  <div class="panel-body">
    <div class="lang-grid">
      <form method="post" action="{{ url_for('set_language') }}">
        <input type="hidden" name="language" value="ru">
        <div class="lang-card">
          <div>
            <strong>{{ t('russian') }}</strong>
            <div class="small">{{ t('current_default') if settings.language == 'ru' else '' }}</div>
          </div>
          <button type="submit" class="{{ 'secondary' if settings.language != 'ru' else '' }}">{{ t('russian') }}</button>
        </div>
      </form>
      <form method="post" action="{{ url_for('set_language') }}">
        <input type="hidden" name="language" value="en">
        <div class="lang-card">
          <div>
            <strong>{{ t('english') }}</strong>
            <div class="small">{{ t('current_default') if settings.language == 'en' else '' }}</div>
          </div>
          <button type="submit" class="{{ 'secondary' if settings.language != 'en' else '' }}">{{ t('english') }}</button>
        </div>
      </form>
    </div>
  </div>
</div>

<div class="wrap">
  <div class="app-shell">
    <div class="app-content">
      <div id="dynamic-notice-anchor"></div>

      <div class="topbar">
        <div>
          <div class="brand">ROUTER<span class="accent">DASH</span></div>
          <div class="brand-sub">{{ t('app_subtitle') }}</div>
        </div>
        <div class="toolbar-group">
          <span id="pill-port" class="pill">{{ t('port_short') }}: {{ settings.port }}</span>
          <span class="pill">{{ t('poll_frequency') }}: {{ settings.poll_interval_ms }} {{ t('ms') }}</span>
          <button class="icon-btn" type="button" onclick="toggleSettingsPanel()" title="{{ t('settings') }}">
            <svg viewBox="0 0 24 24" aria-hidden="true"><circle cx="12" cy="12" r="3"/><path d="M19.4 15a1.7 1.7 0 0 0 .34 1.87l.06.06a2 2 0 0 1 0 2.83l-.1.1a2 2 0 0 1-2.83 0l-.06-.06a1.7 1.7 0 0 0-1.87-.34 1.7 1.7 0 0 0-1 1.55V21a2 2 0 0 1-2 2h-.14a2 2 0 0 1-2-2v-.09a1.7 1.7 0 0 0-1.11-1.59 1.7 1.7 0 0 0-1.87.34l-.06.06a2 2 0 0 1-2.83 0l-.1-.1a2 2 0 0 1 0-2.83l.06-.06A1.7 1.7 0 0 0 4.6 15a1.7 1.7 0 0 0-1.55-1H3a2 2 0 0 1-2-2v-.14a2 2 0 0 1 2-2h.09a1.7 1.7 0 0 0 1.59-1.11 1.7 1.7 0 0 0-.34-1.87l-.06-.06a2 2 0 0 1 0-2.83l.1-.1a2 2 0 0 1 2.83 0l.06.06A1.7 1.7 0 0 0 9 4.6a1.7 1.7 0 0 0 1-1.55V3a2 2 0 0 1 2-2h.14a2 2 0 0 1 2 2v.09a1.7 1.7 0 0 0 1.11 1.59 1.7 1.7 0 0 0 1.87-.34l.06-.06a2 2 0 0 1 2.83 0l.1.1a2 2 0 0 1 0 2.83l-.06.06A1.7 1.7 0 0 0 19.4 9c0 .68.4 1.3 1.03 1.58.17.08.35.12.54.12H21a2 2 0 0 1 2 2v.14a2 2 0 0 1-2 2h-.09c-.74 0-1.41.44-1.71 1.12Z"/></svg>
          </button>
          <a class="button secondary" href="{{ url_for('logout') }}">{{ t('logout') }}</a>
        </div>
      </div>

      {% if info %}<div class="notice success">{{ info }}</div>{% endif %}
      {% if error %}<div class="notice error">{{ error }}</div>{% endif %}
      {% if warnings %}
        <div class="notice error">
          <strong>{{ t('warnings') }}:</strong><br>
          {% for w in warnings %}• {{ w }}<br>{% endfor %}
        </div>
      {% endif %}

      <div class="grid">
        <div class="card tile-card span-3 stat">
          <div class="stat-top">
            <div>
              <div class="stat-label">{{ t('devices') }}</div>
              <div class="value" id="sum-total">{{ summary.total }}</div>
            </div>
            <div class="stat-icon">
              <svg viewBox="0 0 24 24" aria-hidden="true"><rect x="3" y="4" width="8" height="6" rx="1.5"/><rect x="13" y="4" width="8" height="16" rx="1.5"/><rect x="3" y="14" width="8" height="6" rx="1.5"/></svg>
            </div>
          </div>
          <div class="small">{{ t('devices_desc') }}</div>
        </div>

        <div class="card tile-card span-3 stat">
          <div class="stat-top">
            <div>
              <div class="stat-label">{{ t('connected_now') }}</div>
              <div class="value" id="sum-online">{{ summary.online }}</div>
            </div>
            <div class="stat-icon">
              <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M22 21v-2a4 4 0 0 0-3-3.87"/><path d="M16 3.13a4 4 0 0 1 0 7.75"/></svg>
            </div>
          </div>
          <div class="small">{{ t('connected_desc') }}</div>
        </div>

        <div class="card tile-card span-3 stat">
          <div class="stat-top">
            <div>
              <div class="stat-label">{{ t('active') }}</div>
              <div class="value" id="sum-active">{{ summary.active }}</div>
            </div>
            <div class="stat-icon">
              <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M3 12h4l2-5 4 10 2-5h6"/></svg>
            </div>
          </div>
          <div class="small">{{ t('active_desc') }}</div>
        </div>

        <div class="card tile-card span-3 stat">
          <div class="stat-top">
            <div>
              <div class="stat-label">{{ t('idle') }}</div>
              <div class="value" id="sum-idle">{{ summary.idle }}</div>
            </div>
            <div class="stat-icon">
              <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M3 9c4-4 14-4 18 0"/><path d="M6 12c3-3 9-3 12 0"/><path d="M9 15c2-2 4-2 6 0"/><path d="m12 19 .01 0"/></svg>
            </div>
          </div>
          <div class="small">{{ t('idle_desc') }}</div>
        </div>

        <div class="card span-12">
          <div class="panel-heading">
            <div>
              <h2>{{ t('devices_section') }}</h2>
              <div class="panel-caption">{{ t('devices_caption', ipv6_sentence=(t('devices_caption_ipv6') if show_ipv6 else '')) }}</div>
            </div>
          </div>

          <div class="table-shell">
            <div class="table-wrap">
              <table class="table-tight">
                <thead>
                  <tr>
                    <th><button type="button" class="sort-btn" data-sort-key="status">{{ t('th_status') }} <span class="sort-indicator">↕</span></button></th>
                    <th><button type="button" class="sort-btn" data-sort-key="name">{{ t('th_name') }} <span class="sort-indicator">↕</span></button></th>
                    <th><button type="button" class="sort-btn" data-sort-key="ipv4">{{ t('th_ipv4') }} <span class="sort-indicator">↕</span></button></th>
                    {% if show_ipv6 %}
                    <th><button type="button" class="sort-btn" data-sort-key="ipv6">{{ t('th_ipv6') }} <span class="sort-indicator">↕</span></button></th>
                    {% endif %}
                    <th><button type="button" class="sort-btn" data-sort-key="mac">{{ t('th_mac') }} <span class="sort-indicator">↕</span></button></th>
                    <th class="right"><button type="button" class="sort-btn" data-sort-key="down">{{ t('th_down') }} <span class="sort-indicator">↕</span></button></th>
                    <th class="right"><button type="button" class="sort-btn" data-sort-key="up">{{ t('th_up') }} <span class="sort-indicator">↕</span></button></th>
                    <th class="right"><button type="button" class="sort-btn" data-sort-key="total">{{ t('th_total') }} <span class="sort-indicator">↕</span></button></th>
                    <th class="right"><button type="button" class="sort-btn" data-sort-key="conns">{{ t('th_conns') }} <span class="sort-indicator">↕</span></button></th>
                    <th><button type="button" class="sort-btn" data-sort-key="last_seen">{{ t('th_last_seen') }} <span class="sort-indicator">↕</span></button></th>
                  </tr>
                </thead>
                <tbody id="devices-body">
                  {% for d in devices %}
                  <tr>
                    <td data-label="{{ t('th_status') }}">{{ d.status_chip|safe }}</td>
                    <td data-label="{{ t('th_name') }}">{{ d.name_chip|safe }}</td>
                    <td data-label="{{ t('th_ipv4') }}">{{ d.ipv4_chip|safe }}</td>
                    {% if show_ipv6 %}
                    <td data-label="{{ t('th_ipv6') }}">{{ d.ipv6_toggle|safe }}</td>
                    {% endif %}
                    <td data-label="{{ t('th_mac') }}">{{ d.mac_chip|safe }}</td>
                    <td class="right" data-label="{{ t('th_down') }}">{{ d.down_chip|safe }}</td>
                    <td class="right" data-label="{{ t('th_up') }}">{{ d.up_chip|safe }}</td>
                    <td class="right" data-label="{{ t('th_total') }}">{{ d.total_chip|safe }}</td>
                    <td class="right" data-label="{{ t('th_conns') }}">{{ d.conns_chip|safe }}</td>
                    <td data-label="{{ t('th_last_seen') }}">{{ d.last_seen_chip|safe }}</td>
                  </tr>
                  {% endfor %}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</div>

<script>
const IPV6_ENABLED = {{ 'true' if show_ipv6 else 'false' }};
const I18N = {{ strings_json|safe }};
function L(key) { return I18N[key] || key; }

function esc(s) {
  return String(s ?? '').replace(/[&<>"']/g, function(m) {
    return ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#039;'})[m];
  });
}
function statusText(status) {
  if (status === 'active') return L('status_online');
  if (status === 'idle') return L('status_online');
  return L('status_offline');
}
function statusChipClass(status) {
  if (status === 'active') return 'status-ok';
  if (status === 'idle') return 'status-warn';
  return 'status-bad';
}
function chip(text, copyText, extraClass = '', feedbackKey = '') {
  const shown = (text === undefined || text === null || text === '') ? '—' : String(text);
  const copied = (copyText === undefined || copyText === null || copyText === '') ? shown : String(copyText);
  const key = String(feedbackKey || copied);
  const isCopied = (copyFeedback.get(key) || 0) > Date.now();
  const label = isCopied ? L('copied') : shown;
  const classes = ['copy-chip'];
  if (extraClass) classes.push(extraClass);
  if (isCopied) classes.push('copied');
  return `<button type="button" class="${classes.join(' ')}" data-copy="${esc(copied)}" data-feedback="${esc(key)}"><span class="chip-text">${esc(label)}</span></button>`;
}
function staticBox(text = '—', extraClass = '') {
  const shown = (text === undefined || text === null || text === '') ? '—' : String(text);
  const classes = ['metro-box'];
  if (extraClass) classes.push(extraClass);
  return `<span class="${classes.join(' ')}"><span class="chip-text">${esc(shown)}</span></span>`;
}
function ghostChip(text = '—') { return staticBox(text, 'ghost-chip table-empty-click'); }
function chipGroup(values, extraClass = '', feedbackPrefix = '') {
  const arr = Array.isArray(values) ? values.filter(v => v !== undefined && v !== null && String(v).trim() !== '') : [];
  if (!arr.length) return `<div class="cell-stack">${ghostChip('—')}</div>`;
  return `<div class="cell-stack">${arr.map((v, idx) => chip(v, v, extraClass, `${feedbackPrefix}:${idx}:${v}`)).join('')}</div>`;
}
function statusBox(status) { return staticBox(statusText(status), `status-box ${statusChipClass(status)}`); }
function metricBox(text, extraClass = '') { return staticBox(text, `metric-box ${extraClass}`.trim()); }
function activityIndicator(status, totalKbps) {
  let state = 'offline';
  let title = L('status_offline');
  if (status === 'active' || status === 'idle') {
    if (Number(totalKbps || 0) > 0) { state = 'active'; title = L('activity_present'); }
    else { state = 'idle'; title = L('activity_none'); }
  }
  return `<span class="activity-wrap state-${state}" title="${esc(title)}"><span class="activity-dot"></span></span>`;
}
function totalMetric(speedText, status, totalKbps) {
  return `<span class="total-metric">${metricBox(speedText || L('zero_speed'))}${activityIndicator(status, totalKbps)}</span>`;
}
function ipv6Toggle(values, feedbackPrefix = '') {
  if (!IPV6_ENABLED) return '';
  const arr = Array.isArray(values) ? values.filter(v => v !== undefined && v !== null && String(v).trim() !== '') : [];
  if (!arr.length) return ghostChip('—');
  const items = arr.map((v, idx) => chip(v, v, '', `${feedbackPrefix}:${idx}:${v}`)).join('');
  return `<details class="table-disclosure ipv6-disclosure"><summary class="metro-box disclosure-trigger">...</summary><div class="table-popover ipv6-popover"><div class="ipv6-list">${items}</div></div></details>`;
}
function renderConnRows(entries) {
  if (!Array.isArray(entries) || !entries.length) return `<div class="conn-empty">${esc(L('no_active_directions'))}</div>`;
  return entries.map((item) => {
    const host = item.host || item.remote || '—';
    const remote = item.remote && item.remote !== host ? `<div class="conn-remote">${esc(item.remote)}</div>` : '';
    return `<div class="conn-row"><div class="conn-dest"><div class="conn-host">${esc(host)}</div>${remote}</div><div class="conn-num">${esc(item.up_h || '0 B')}</div><div class="conn-num">${esc(item.down_h || '0 B')}</div></div>`;
  }).join('');
}
function connToggle(entries, count) {
  const n = Number(count || 0);
  if (!n) return metricBox('0');
  const body = (Array.isArray(entries) && entries.length)
    ? `<div class="conn-header"><div>${esc(L('direction'))}</div><div>Up</div><div>Down</div></div>${renderConnRows(entries)}`
    : `<div class=\"conn-empty\">${esc(L('no_conntrack_details'))}</div>`;
  return `<details class="table-disclosure conn-disclosure"><summary class="metro-box disclosure-trigger metric-box">${esc(String(n))}</summary><div class="table-popover conn-popover">${body}</div></details>`;
}

const copyFeedback = new Map();
let tableInteractionUntil = 0;
let refreshInFlight = false;
let lastPayloadFingerprint = '';

function cleanupCopyFeedback() {
  const now = Date.now();
  for (const [key, until] of copyFeedback.entries()) {
    if (until <= now) copyFeedback.delete(key);
  }
}
async function copyChipValue(btn) {
  const value = btn.getAttribute('data-copy') || btn.innerText || '';
  const feedbackKey = btn.getAttribute('data-feedback') || value;
  try {
    if (navigator.clipboard && window.isSecureContext) {
      await navigator.clipboard.writeText(value);
    } else {
      const area = document.createElement('textarea');
      area.value = value;
      area.style.position = 'fixed';
      area.style.opacity = '0';
      document.body.appendChild(area);
      area.focus();
      area.select();
      document.execCommand('copy');
      area.remove();
    }
    const until = Date.now() + 1900;
    copyFeedback.set(feedbackKey, until);
    tableInteractionUntil = Math.max(tableInteractionUntil, Date.now() + 1400);
    btn.classList.add('copied');
    const textEl = btn.querySelector('.chip-text');
    if (textEl) textEl.textContent = L('copied');
    setTimeout(() => {
      cleanupCopyFeedback();
      if ((copyFeedback.get(feedbackKey) || 0) <= Date.now()) refreshData(true);
    }, 1950);
  } catch (e) {
    console.log('copy error', e);
  }
}
document.addEventListener('pointerdown', function(ev) {
  const btn = ev.target.closest('.copy-chip');
  if (!btn) return;
  ev.preventDefault();
  copyChipValue(btn);
});
document.addEventListener('keydown', function(ev) {
  if (ev.key !== 'Enter' && ev.key !== ' ') return;
  const btn = ev.target.closest('.copy-chip');
  if (!btn) return;
  ev.preventDefault();
  copyChipValue(btn);
});
function hasPinnedTableOverlay() {
  return !!document.querySelector('.table-disclosure[open]');
}
function closeTableDisclosures(exceptNode = null) {
  document.querySelectorAll('.table-disclosure[open]').forEach(item => {
    if (item !== exceptNode) item.removeAttribute('open');
  });
}
document.addEventListener('click', function(ev) {
  const details = ev.target.closest('.table-disclosure');
  closeTableDisclosures(details);
  if (!details) setTimeout(() => refreshData(true), 20);
});
document.addEventListener('toggle', function(ev) {
  const details = ev.target;
  if (!details || !details.classList || !details.classList.contains('table-disclosure')) return;
  if (details.hasAttribute('open')) closeTableDisclosures(details);
  else setTimeout(() => refreshData(true), 20);
}, true);

const deviceSort = { key: null, dir: 'asc' };
function compareText(a, b) { return String(a ?? '').localeCompare(String(b ?? ''), '{{ lang }}', {numeric: true, sensitivity: 'base'}); }
function compareIpText(a, b) { return compareText(a || '', b || ''); }
function getSortValue(d, key) {
  switch (key) {
    case 'status': {
      const order = {active: 0, idle: 1, offline: 2};
      return order[d.status] ?? 9;
    }
    case 'name': return (d.name_values && d.name_values[0]) || d.display_name || '';
    case 'ipv4': return (d.ipv4_list && d.ipv4_list[0]) || '';
    case 'ipv6': return (d.ipv6_list && d.ipv6_list[0]) || '';
    case 'mac': return d.mac || '';
    case 'down': return Number(d.current_down_bps || 0);
    case 'up': return Number(d.current_up_bps || 0);
    case 'total': return Number(d.current_total_kbps || 0);
    case 'conns': return Number(d.conns || 0);
    case 'last_seen': return Number(d.last_seen_ts || 0);
    default: return '';
  }
}
function sortDevices(devices) {
  if (!deviceSort.key) return devices;
  const dir = deviceSort.dir === 'desc' ? -1 : 1;
  return [...devices].sort((a, b) => {
    const av = getSortValue(a, deviceSort.key);
    const bv = getSortValue(b, deviceSort.key);
    let cmp = 0;
    if (['status', 'down', 'up', 'total', 'conns', 'last_seen'].includes(deviceSort.key)) {
      cmp = (Number(av) > Number(bv)) - (Number(av) < Number(bv));
    } else if (deviceSort.key === 'ipv4' || deviceSort.key === 'ipv6') {
      cmp = compareIpText(av, bv);
    } else {
      cmp = compareText(av, bv);
    }
    if (cmp === 0) cmp = compareText(a.display_name || '', b.display_name || '');
    return cmp * dir;
  });
}
function updateSortIndicators() {
  document.querySelectorAll('.sort-btn').forEach(btn => {
    const active = btn.dataset.sortKey === deviceSort.key;
    btn.classList.toggle('active', active);
    const indicator = btn.querySelector('.sort-indicator');
    if (!indicator) return;
    indicator.textContent = active ? (deviceSort.dir === 'asc' ? '↑' : '↓') : '↕';
  });
}
document.addEventListener('click', function(ev) {
  const btn = ev.target.closest('.sort-btn');
  if (!btn) return;
  const key = btn.dataset.sortKey;
  if (!key) return;
  if (deviceSort.key === key) deviceSort.dir = deviceSort.dir === 'asc' ? 'desc' : 'asc';
  else { deviceSort.key = key; deviceSort.dir = 'asc'; }
  updateSortIndicators();
  refreshData(true);
});

function renderTableRows(devices) {
  const tbody = document.getElementById('devices-body');
  tbody.innerHTML = devices.map(d => `
      <tr>
        <td data-label="{{ t('th_status') }}">${statusBox(d.status)}</td>
        <td data-label="{{ t('th_name') }}">${chipGroup(d.name_values, '', `name:${d.mac}`)}</td>
        <td data-label="{{ t('th_ipv4') }}">${chipGroup(d.ipv4_list, 'ipv4-chip', `ipv4:${d.mac}`)}</td>
        ${IPV6_ENABLED ? `<td data-label="{{ t('th_ipv6') }}">${ipv6Toggle(d.ipv6_list, `ipv6:${d.mac}`)}</td>` : ``}
        <td data-label="{{ t('th_mac') }}">${chip(d.mac, d.mac, 'mono', `mac:${d.mac}`)}</td>
        <td class="right" data-label="{{ t('th_down') }}">${metricBox(d.down_h)}</td>
        <td class="right" data-label="{{ t('th_up') }}">${metricBox(d.up_h)}</td>
        <td class="right" data-label="{{ t('th_total') }}">${totalMetric(d.minute_h, d.status, d.current_total_kbps)}</td>
        <td class="right" data-label="{{ t('th_conns') }}">${connToggle(d.conn_directions || [], d.conns)}</td>
        <td data-label="{{ t('th_last_seen') }}">${metricBox(d.last_seen_h)}</td>
      </tr>
    `).join('');
}
function renderEvents(eventsList) {
  const events = document.getElementById('events-list');
  if (!events) return;
  events.innerHTML = eventsList.length ? eventsList.map(e => `
      <div class="event-item">
        <div><strong>${esc(e.ts_h)}</strong> — ${esc(e.message)}</div>
        <div class="small">${esc(L('event_type'))}: ${esc(e.kind)}${e.mac ? ' · ' + esc(e.mac) : ''}</div>
      </div>
    `).join('') : `<div class=\"small\">${esc(L('no_events'))}</div>`;
}

function showInlineNotice(message, kind = 'success') {
  const anchor = document.getElementById('dynamic-notice-anchor');
  if (!anchor || !message) return;
  anchor.innerHTML = `<div class="notice ${kind === 'error' ? 'error' : 'success'}">${esc(message)}</div>`;
}
(function restoreInlineNotice() {
  try {
    const raw = localStorage.getItem('routerdash_notice');
    if (!raw) return;
    localStorage.removeItem('routerdash_notice');
    const payload = JSON.parse(raw);
    if (payload && payload.message) showInlineNotice(payload.message, payload.kind || 'success');
  } catch (e) { console.log(e); }
})();

function closePanels() {
  document.getElementById('settings-panel')?.classList.remove('open');
  document.getElementById('logs-panel')?.classList.remove('open');
  document.getElementById('language-panel')?.classList.remove('open');
  document.getElementById('panel-backdrop')?.classList.remove('open');
  document.body.classList.remove('panel-open');
}
function openPanel(panelId) {
  document.getElementById('settings-panel')?.classList.remove('open');
  document.getElementById('logs-panel')?.classList.remove('open');
  document.getElementById('language-panel')?.classList.remove('open');
  const panel = document.getElementById(panelId);
  if (!panel) return;
  panel.classList.add('open');
  document.getElementById('panel-backdrop')?.classList.add('open');
  document.body.classList.add('panel-open');
}
function toggleSettingsPanel() {
  const panel = document.getElementById('settings-panel');
  if (!panel) return;
  if (panel.classList.contains('open')) { closePanels(); return; }
  openPanel('settings-panel');
}
function toggleLanguagePanel() {
  const panel = document.getElementById('language-panel');
  if (!panel) return;
  if (panel.classList.contains('open')) { closePanels(); return; }
  openPanel('language-panel');
}
function toggleLogsPanel() {
  const panel = document.getElementById('logs-panel');
  if (!panel) return;
  if (panel.classList.contains('open')) { closePanels(); return; }
  openPanel('logs-panel');
}
document.addEventListener('keydown', function(ev) { if (ev.key === 'Escape') closePanels(); });

function setAllDeviceSelection(checked) {
  document.querySelectorAll('.telegram-device-checkbox').forEach(cb => { cb.checked = checked; });
}

async function submitSettingsForm(form) {
  const submitBtn = document.getElementById('settings-submit-btn');
  const formData = new FormData(form);
  if (submitBtn) submitBtn.disabled = true;
  try {
    const r = await fetch(form.action, {
      method: 'POST',
      body: formData,
      headers: {
        'X-Requested-With': 'XMLHttpRequest',
        'Accept': 'application/json'
      },
      credentials: 'same-origin'
    });
    const data = await r.json();
    if (!r.ok || !data.ok) throw new Error(data.error || L('save_settings_failed')); 
    closePanels();
    if (data.restart_required && data.redirect_url) {
      try {
        localStorage.setItem('routerdash_notice', JSON.stringify({
          kind: 'success',
          message: data.message || L('port_changed_restarting').replace('{port}', data.port)
        }));
      } catch (e) {}
      showInlineNotice(data.message || L('port_changed_restarting').replace('{port}', data.port), 'success');
      setTimeout(() => { window.location.href = data.redirect_url; }, data.redirect_delay_ms || 2200);
      return;
    }
    try {
      localStorage.setItem('routerdash_notice', JSON.stringify({kind: 'success', message: data.message || L('settings_saved')}));
    } catch (e) {}
    window.location.href = data.redirect_url || window.location.href;
  } catch (e) {
    showInlineNotice(e.message || L('settings_save_error'), 'error');
  } finally {
    if (submitBtn) submitBtn.disabled = false;
  }
}

document.getElementById('settings-form')?.addEventListener('submit', function(ev) {
  const submitter = ev.submitter;
  if (submitter && submitter.getAttribute('formaction')) return;
  ev.preventDefault();
  submitSettingsForm(ev.currentTarget);
});

async function refreshData(forceTableRender = false) {
  if (refreshInFlight) return;
  refreshInFlight = true;
  try {
    const r = await fetch('{{ url_for("api_status") }}', {cache: 'no-store'});
    if (!r.ok) return;
    const data = await r.json();
    document.getElementById('sum-total').textContent = data.summary.total;
    document.getElementById('sum-online').textContent = data.summary.online;
    document.getElementById('sum-active').textContent = data.summary.active;
    document.getElementById('sum-idle').textContent = data.summary.idle;

    cleanupCopyFeedback();
    const devices = sortDevices(data.devices || []);
    const fingerprint = JSON.stringify(devices.map(d => [d.mac, d.status, d.current_total_kbps, d.current_down_bps, d.current_up_bps, d.conns, d.last_seen_ts, d.ipv4_list, d.ipv6_list, d.name_values, d.conn_directions]));
    const tableOverlayPinned = hasPinnedTableOverlay();
    const canRenderTable = !tableOverlayPinned && (forceTableRender || Date.now() >= tableInteractionUntil);
    if (canRenderTable && (forceTableRender || fingerprint !== lastPayloadFingerprint)) {
      renderTableRows(devices);
      lastPayloadFingerprint = fingerprint;
    }
    renderEvents(data.events || []);
    const pill = document.getElementById('pill-port');
    if (pill && data.port) pill.textContent = `${L('port_short')}: ${data.port}`;
  } catch (e) {
    console.log('refresh error', e);
  } finally {
    refreshInFlight = false;
  }
}
updateSortIndicators();
setInterval(() => refreshData(false), Math.max(100, {{ settings.poll_interval_ms }}));
setTimeout(() => refreshData(true), 50);
</script>
"""





def ensure_dir(path: str) -> None:
    os.makedirs(path, exist_ok=True)


def read_json(path: str, default: Dict[str, Any]) -> Dict[str, Any]:
    if not os.path.exists(path):
        return deepcopy(default)
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
            if isinstance(data, dict):
                return data
    except Exception:
        pass
    return deepcopy(default)


def write_json_atomic(path: str, data: Dict[str, Any]) -> None:
    ensure_dir(os.path.dirname(path))
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2, sort_keys=True)
    os.replace(tmp, path)


def now_ts() -> int:
    return int(time.time())


def normalize_mac(mac: str) -> str:
    mac = (mac or "").strip().lower().replace("-", ":")
    parts = [p.zfill(2) for p in mac.split(":") if p]
    if len(parts) == 6:
        return ":".join(parts)
    return mac


def safe_network(value: str) -> Optional[ipaddress._BaseNetwork]:
    value = (value or '').strip()
    if not value:
        return None
    try:
        return ipaddress.ip_network(value, strict=False)
    except Exception:
        return None


def filter_local_ips(ips: List[str], cidr: str, include_ipv6: bool = True) -> List[str]:
    """Keep all sane device IPs in state.

    The CIDR filter is applied later, only for dashboard presentation. Storing
    raw device IPs prevents losing IPv4 addresses when the local network setting
    changes from one subnet to another.
    """
    _ = cidr
    out: List[str] = []
    seen = set()
    for ip in ips:
        ip = (ip or '').strip()
        if not ip or ip in seen:
            continue
        try:
            addr = ipaddress.ip_address(ip)
        except Exception:
            continue
        if addr.version == 4:
            if addr.is_unspecified or addr.is_loopback or addr.is_multicast:
                continue
        elif addr.version == 6:
            if not include_ipv6:
                continue
            if addr.is_unspecified or addr.is_loopback or addr.is_multicast:
                continue
        else:
            continue
        seen.add(ip)
        out.append(ip)
    return out


def normalize_local_network_cidr(value: str) -> str:
    raw = (value or '').strip() or DEFAULT_SETTINGS["local_network_cidr"]
    net = safe_network(raw)
    if net is None or getattr(net, "version", None) != 4:
        raise ValueError(tr("local_network_invalid"))
    return str(net)


def split_device_ips(ips: List[str], local_ipv4_cidr: str, include_ipv6: bool = True) -> Tuple[List[str], List[str]]:
    ipv4_list: List[str] = []
    ipv6_list: List[str] = []
    seen4 = set()
    seen6 = set()
    net4 = safe_network(local_ipv4_cidr)

    for raw in ips:
        ip = (raw or '').strip()
        if not ip:
            continue
        try:
            addr = ipaddress.ip_address(ip)
        except Exception:
            continue

        if addr.version == 4:
            if net4 is not None and addr not in net4:
                continue
            if ip not in seen4:
                seen4.add(ip)
                ipv4_list.append(ip)
            continue

        if addr.version == 6:
            if not include_ipv6:
                continue
            if addr.is_unspecified or addr.is_loopback or addr.is_multicast:
                continue
            if ip not in seen6:
                seen6.add(ip)
                ipv6_list.append(ip)

    return ipv4_list, ipv6_list


def html_escape(value: Any) -> str:
    return (
        str(value if value is not None else "")
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('\"', "&quot;")
        .replace("'", "&#039;")
    )


def render_chip(text: Any, copy_value: Optional[Any] = None, extra_class: str = "") -> str:
    shown = str(text if text not in (None, "") else "—")
    copied = str(copy_value if copy_value not in (None, "") else shown)
    classes = "copy-chip" + (f" {extra_class.strip()}" if extra_class.strip() else "")
    return (
        f'<button type="button" class="{classes}" data-copy="{html_escape(copied)}">'
        f'<span class="chip-text">{html_escape(shown)}</span>'
        f'</button>'
    )


def render_chip_group(values: List[Any], extra_class: str = "") -> str:
    clean = [v for v in (values or []) if str(v).strip()]
    if not clean:
        return f'<div class="cell-stack">{render_chip("—", "—", (extra_class + " ghost-chip").strip())}</div>'
    return '<div class="cell-stack">' + ''.join(render_chip(v, v, extra_class) for v in clean) + '</div>'


def render_static_chip(text: Any, extra_class: str = "") -> str:
    shown = str(text if text not in (None, "") else "—")
    classes = "no-copy-chip" + (f" {extra_class.strip()}" if extra_class.strip() else "")
    return f'<span class="{classes}"><span class="chip-text">{html_escape(shown)}</span></span>'


def render_ipv6_toggle(values: List[Any]) -> str:
    clean = [str(v).strip() for v in (values or []) if str(v).strip()]
    if not clean:
        return render_static_chip("—", "ghost-chip table-empty-click metro-box")
    items = "".join(render_chip(v, v) for v in clean)
    return (
        '<details class="table-disclosure ipv6-disclosure">'
        '<summary class="metro-box disclosure-trigger">...</summary>'
        f'<div class="table-popover ipv6-popover"><div class="ipv6-list">{items}</div></div>'
        '</details>'
    )


def render_activity_indicator(status: str, total_kbps: float) -> str:
    lang = get_current_lang()
    state = "offline"
    title = tr("status_offline", lang)
    if status in {"active", "idle"}:
        if float(total_kbps or 0.0) > 0.0:
            state = "active"
            title = tr("activity_present", lang)
        else:
            state = "idle"
            title = tr("activity_none", lang)
    return (
        f'<span class="activity-wrap state-{html_escape(state)}" title="{html_escape(title)}">'
        '<span class="activity-dot"></span>'
        '</span>'
    )


def render_total_metric(speed_text: str, status: str, total_kbps: float) -> str:
    lang = get_current_lang()
    speed_chip = render_static_chip(speed_text or tr("zero_speed", lang), "metro-box metric-box")
    return f'<span class="total-metric">{speed_chip}{render_activity_indicator(status, total_kbps)}</span>'


def render_conn_toggle(entries: List[Dict[str, Any]], count: int) -> str:
    lang = get_current_lang()
    count = int(count or 0)
    if count <= 0:
        return render_static_chip("0", "metro-box metric-box table-empty-click")
    if not entries:
        return (
            '<details class="table-disclosure conn-disclosure">'
            f'<summary class="metro-box disclosure-trigger metric-box">{count}</summary>'
            '<div class="table-popover conn-popover">'
            f'<div class="conn-empty">{html_escape(tr("no_conntrack_details", lang))}</div>'
            '</div>'
            '</details>'
        )
    rows = []
    for item in entries or []:
        host = str(item.get("host") or item.get("remote") or "—")
        remote = str(item.get("remote") or "")
        label_extra = f'<div class="conn-remote">{html_escape(remote)}</div>' if remote and remote != host else ''
        rows.append(
            '<div class="conn-row">'
            f'<div class="conn-dest"><div class="conn-host">{html_escape(host)}</div>{label_extra}</div>'
            f'<div class="conn-num">{html_escape(str(item.get("up_h") or "0 B"))}</div>'
            f'<div class="conn-num">{html_escape(str(item.get("down_h") or "0 B"))}</div>'
            '</div>'
        )
    body = ''.join(rows) if rows else f'<div class="conn-empty">{html_escape(tr("no_active_directions", lang))}</div>'
    return (
        '<details class="table-disclosure conn-disclosure">'
        f'<summary class="metro-box disclosure-trigger metric-box">{count}</summary>'
        '<div class="table-popover conn-popover">'
        f'<div class="conn-header"><div>{html_escape(tr("direction", lang))}</div><div>Up</div><div>Down</div></div>'
        f'{body}'
        '</div>'
        '</details>'
    )


def pbkdf2_hash(password: str, salt: Optional[bytes] = None) -> str:
    salt = salt or secrets.token_bytes(16)
    derived = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 200000)
    return "pbkdf2_sha256$200000$%s$%s" % (
        base64.b64encode(salt).decode("ascii"),
        base64.b64encode(derived).decode("ascii"),
    )


def verify_password(password: str, stored: str) -> bool:
    try:
        algo, rounds, salt_b64, hash_b64 = stored.split("$", 3)
        if algo != "pbkdf2_sha256":
            return False
        salt = base64.b64decode(salt_b64.encode("ascii"))
        check = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, int(rounds))
        return hmac.compare_digest(base64.b64encode(check).decode("ascii"), hash_b64)
    except Exception:
        return False


def human_rate(bytes_per_sec: float) -> str:
    if bytes_per_sec is None:
        return "0 B/s"
    value = float(bytes_per_sec)
    units = ["B/s", "KB/s", "MB/s", "GB/s"]
    idx = 0
    while value >= 1024 and idx < len(units) - 1:
        value /= 1024.0
        idx += 1
    if idx == 0:
        return f"{int(value)} {units[idx]}"
    return f"{value:.2f} {units[idx]}"


def human_bytes(num_bytes: float) -> str:
    if num_bytes is None:
        return "0 B"
    value = float(num_bytes)
    units = ["B", "KB", "MB", "GB", "TB"]
    idx = 0
    while value >= 1024 and idx < len(units) - 1:
        value /= 1024.0
        idx += 1
    if idx == 0:
        return f"{int(value)} {units[idx]}"
    return f"{value:.2f} {units[idx]}"


def human_kbits(kbit: float) -> str:
    if kbit is None:
        return "0 Kbit/s"
    if kbit >= 1000:
        return f"{kbit/1000:.2f} Mbit/s"
    return f"{kbit:.0f} Kbit/s"


def relative_time(ts: Optional[int]) -> str:
    if not ts:
        return "—"
    delta = max(0, now_ts() - int(ts))
    lang = get_current_lang()
    if delta < 15:
        return tr("just_now", lang)
    if delta < 60:
        return tr("seconds_ago", lang, count=delta)
    if delta < 3600:
        return tr("minutes_ago", lang, count=delta // 60)
    if delta < 86400:
        return tr("hours_ago", lang, count=delta // 3600)
    return tr("days_ago", lang, count=delta // 86400)


def fmt_ts(ts: int) -> str:
    return time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(ts))


def parse_bool_from_form(name: str) -> bool:
    return request.form.get(name) in {"1", "true", "on", "yes"}


def is_json_request() -> bool:
    accept = (request.headers.get("Accept") or "").lower()
    requested_with = (request.headers.get("X-Requested-With") or "").lower()
    return "application/json" in accept or requested_with == "xmlhttprequest"


def build_redirect_url(port: int, path: str = "/") -> str:
    parsed = urllib.parse.urlsplit(request.host_url)
    hostname = parsed.hostname or "localhost"
    if ":" in hostname and not hostname.startswith("["):
        host_for_netloc = f"[{hostname}]"
    else:
        host_for_netloc = hostname
    default_port = 443 if parsed.scheme == "https" else 80
    netloc = host_for_netloc if int(port) == default_port else f"{host_for_netloc}:{int(port)}"
    base_path = (request.script_root or "").rstrip("/")
    full_path = path if path.startswith("/") else "/" + path
    return urllib.parse.urlunsplit((parsed.scheme, netloc, (base_path + full_path) or "/", "", ""))


def schedule_service_restart(delay_sec: float = 1.0) -> bool:
    service_name = re.sub(r"[^a-zA-Z0-9_.-]", "", os.environ.get("ROUTERDASH_SERVICE", "routerdash")) or "routerdash"
    delay_sec = max(0.2, float(delay_sec))
    script = (
        f"sleep {delay_sec:.2f}; "
        f"if [ -x /etc/init.d/{service_name} ]; then "
        f"/etc/init.d/{service_name} restart; "
        f"elif command -v service >/dev/null 2>&1; then "
        f"service {service_name} restart; "
        f"elif command -v systemctl >/dev/null 2>&1; then "
        f"systemctl restart {service_name}; "
        f"fi >/dev/null 2>&1"
    )
    try:
        subprocess.Popen(
            ["/bin/sh", "-c", script],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            stdin=subprocess.DEVNULL,
            close_fds=True,
            start_new_session=True,
        )
        return True
    except Exception:
        return False


def sync_state_device_ips(settings: Dict[str, Any]) -> None:
    include_ipv6 = bool(settings.get("track_ipv6", True))
    local_network_cidr = str(settings.get("local_network_cidr", DEFAULT_SETTINGS["local_network_cidr"]))
    leases = monitor._get_dhcp_leases()
    neigh = monitor._get_neighbors()
    changed = False
    with store.lock:
        devices = store.state.setdefault("devices", {})
        for mac, dev in devices.items():
            merged_ips = filter_local_ips(
                list(dev.get("ips", []))
                + list(leases.get(mac, {}).get("ips", []))
                + list(neigh.get(mac, {}).get("ips", [])),
                local_network_cidr,
                include_ipv6=include_ipv6,
            )
            if merged_ips != list(dev.get("ips", [])):
                dev["ips"] = merged_ips
                changed = True
            ipv4_list, _ = split_device_ips(merged_ips, local_network_cidr, include_ipv6=include_ipv6)
            new_last_ip = ipv4_list[0] if ipv4_list else ""
            if new_last_ip != str(dev.get("last_ip", "") or ""):
                dev["last_ip"] = new_last_ip
                changed = True
        if changed:
            store.save_state()


def run_cmd(args: List[str], timeout: int = 5) -> Tuple[int, str, str]:
    try:
        proc = subprocess.run(args, capture_output=True, text=True, timeout=timeout)
        return proc.returncode, proc.stdout.strip(), proc.stderr.strip()
    except FileNotFoundError:
        return 127, "", f"command not found: {args[0]}"
    except subprocess.TimeoutExpired:
        return 124, "", f"timeout: {' '.join(args)}"
    except Exception as exc:
        return 1, "", str(exc)


class Store:
    def __init__(self) -> None:
        ensure_dir(APP_DIR)
        self.lock = threading.RLock()
        self.config = read_json(CONFIG_FILE, DEFAULT_CONFIG)
        self.state = read_json(STATE_FILE, DEFAULT_STATE)
        self._merge_defaults()
        self.save_config()
        self.save_state()

    def _merge_defaults(self) -> None:
        changed = False
        for k, v in DEFAULT_CONFIG.items():
            if k not in self.config:
                self.config[k] = deepcopy(v)
                changed = True
        if not self.config.get("secret_key"):
            self.config["secret_key"] = secrets.token_hex(32)
            changed = True
        admin = self.config.setdefault("admin", deepcopy(DEFAULT_CONFIG["admin"]))
        for k, v in DEFAULT_CONFIG["admin"].items():
            if k not in admin:
                admin[k] = v
                changed = True
        settings = self.config.setdefault("settings", deepcopy(DEFAULT_SETTINGS))
        for k, v in DEFAULT_SETTINGS.items():
            if k not in settings:
                settings[k] = deepcopy(v)
                changed = True
        for k, v in DEFAULT_STATE.items():
            if k not in self.state:
                self.state[k] = deepcopy(v)
                changed = True
        if changed:
            self.save_config()
            self.save_state()

    def save_config(self) -> None:
        with self.lock:
            write_json_atomic(CONFIG_FILE, self.config)

    def save_state(self) -> None:
        with self.lock:
            write_json_atomic(STATE_FILE, self.state)

    def admin_exists(self) -> bool:
        with self.lock:
            admin = self.config.get("admin", {})
            return bool(admin.get("username") and admin.get("password_hash"))

    def set_admin(self, username: str, password: str) -> None:
        with self.lock:
            self.config["admin"] = {
                "username": username.strip(),
                "password_hash": pbkdf2_hash(password),
            }
            self.save_config()

    def verify_admin(self, username: str, password: str) -> bool:
        with self.lock:
            admin = self.config.get("admin", {})
            return (
                username.strip() == admin.get("username", "")
                and verify_password(password, admin.get("password_hash", ""))
            )

    def change_admin(self, current_password: str, username: str, new_password: str) -> Tuple[bool, str]:
        with self.lock:
            admin = self.config.get("admin", {})
            if not verify_password(current_password, admin.get("password_hash", "")):
                return False, tr("current_password_wrong")
            self.config["admin"] = {
                "username": username.strip(),
                "password_hash": pbkdf2_hash(new_password),
            }
            self.save_config()
            return True, tr("creds_updated")

    def get_settings(self) -> Dict[str, Any]:
        with self.lock:
            return deepcopy(self.config.get("settings", DEFAULT_SETTINGS))

    def update_settings(self, values: Dict[str, Any]) -> None:
        with self.lock:
            settings = self.config.setdefault("settings", deepcopy(DEFAULT_SETTINGS))
            settings.update(values)
            self.save_config()

    def add_event(self, kind: str, message: str, mac: str = "") -> None:
        with self.lock:
            events = self.state.setdefault("events", [])
            events.insert(0, {
                "ts": now_ts(),
                "kind": kind,
                "message": message,
                "mac": mac,
            })
            del events[200:]
            self.save_state()


class Monitor:
    def __init__(self, store: Store):
        self.store = store
        self.lock = threading.RLock()
        self.stop_event = threading.Event()
        self.thread: Optional[threading.Thread] = None
        self.prev_traffic: Dict[str, Dict[str, Any]] = {}
        self.histories: Dict[str, deque] = defaultdict(lambda: deque(maxlen=32))
        self.runtime: Dict[str, Dict[str, Any]] = {}
        self.last_presence_ts: Dict[str, int] = {}
        self.warnings: List[str] = []
        self.last_warning_keys: set = set()
        self.dns_cache: Dict[str, Dict[str, Any]] = {}
        self.prev_conn_counters: Dict[str, Dict[str, Any]] = {}
        self.bootstrap_completed = False

    def start(self) -> None:
        if self.thread and self.thread.is_alive():
            return
        self.thread = threading.Thread(target=self.loop, name="routerdash-monitor", daemon=True)
        self.thread.start()

    def loop(self) -> None:
        while not self.stop_event.is_set():
            start = time.time()
            try:
                self.collect_once()
            except Exception as exc:
                self._set_warning("monitor_exception", tr("warning_monitor_exception", error=exc))
            settings = self.store.get_settings()
            interval_ms = max(100, min(60000, int(settings.get("poll_interval_ms", DEFAULT_SETTINGS["poll_interval_ms"]))))
            interval = interval_ms / 1000.0
            spent = time.time() - start
            if spent > interval * 3:
                self._set_warning("monitor_slow_loop", tr("warning_monitor_slow", spent=spent, interval=interval))
            else:
                self._clear_warning("monitor_slow_loop")
            wait_for = max(0.05, interval - spent)
            self.stop_event.wait(wait_for)

    def _set_warning(self, key: str, message: str) -> None:
        with self.lock:
            if key not in self.last_warning_keys:
                self.store.add_event("warning", message)
                self.last_warning_keys.add(key)
            warnings = [w for w in self.warnings if not w.startswith(f"[{key}]")]
            warnings.append(f"[{key}] {message}")
            self.warnings = warnings[-20:]

    def _clear_warning(self, key: str) -> None:
        with self.lock:
            self.warnings = [w for w in self.warnings if not w.startswith(f"[{key}]")]
            self.last_warning_keys.discard(key)


    def _build_ip_to_mac_map(
        self,
        leases: Dict[str, Dict[str, Any]],
        neigh: Dict[str, Dict[str, Any]],
    ) -> Dict[str, str]:
        ip_to_mac: Dict[str, str] = {}
        with self.store.lock:
            devices = deepcopy(self.store.state.get("devices", {}))
        for mac, dev in devices.items():
            for ip in dev.get("ips", []):
                ip = (ip or "").strip()
                if ip:
                    ip_to_mac[ip] = mac
        for source in (leases, neigh):
            for mac, row in source.items():
                for ip in row.get("ips", []):
                    ip = (ip or "").strip()
                    if ip:
                        ip_to_mac[ip] = mac
        return ip_to_mac

    def _load_conntrack_lines(self) -> List[str]:
        lines: List[str] = []
        for proc_path in ("/proc/net/nf_conntrack", "/proc/net/ip_conntrack"):
            if os.path.exists(proc_path):
                try:
                    with open(proc_path, "r", encoding="utf-8", errors="ignore") as f:
                        lines = f.readlines()
                    break
                except Exception:
                    lines = []
        if not lines:
            rc, out, _ = run_cmd(["conntrack", "-L"], timeout=8)
            if rc == 0 and out.strip():
                lines = out.splitlines()
        return lines

    def _has_conntrack_proc(self) -> bool:
        return os.path.exists("/proc/net/nf_conntrack") or os.path.exists("/proc/net/ip_conntrack")

    def _reverse_dns_cached(self, ip: str, allow_lookup: bool = True) -> str:
        ip = (ip or "").strip()
        if not ip:
            return ""
        now = time.time()
        cached = self.dns_cache.get(ip)
        if cached and float(cached.get("expires_at", 0.0) or 0.0) > now:
            return str(cached.get("host") or "")
        # Avoid blocking reverse DNS in the hot monitor loop. On OpenWrt this can add
        # multiple seconds per IP and completely break the selected poll interval.
        if not allow_lookup:
            return str(cached.get("host") or "") if cached else ""
        self.dns_cache[ip] = {"host": "", "expires_at": now + 1800}
        return ""

    def _parse_conntrack_details(self, ip_to_mac: Dict[str, str], lookup_budget: int = 8) -> Tuple[Dict[str, int], Dict[str, List[Dict[str, Any]]], Dict[str, Dict[str, int]]]:
        if not ip_to_mac:
            return {}, {}, {}
        counts: Dict[str, int] = defaultdict(int)
        aggregated: Dict[str, Dict[str, Dict[str, Any]]] = defaultdict(dict)
        lines = self._load_conntrack_lines()
        if not lines:
            return {}, {}, {}

        tuple_pattern = re.compile(r'\b(src|dst|sport|dport|packets|bytes)=([^\s]+)')
        tcp_active_states = {"ESTABLISHED", "SYN_SENT", "SYN_RECV", "FIN_WAIT", "FIN_WAIT_1", "FIN_WAIT_2", "CLOSE_WAIT", "LAST_ACK"}
        skip_tokens = {"TIME_WAIT", "CLOSE", "CLOSED"}

        for raw_line in lines:
            line = (raw_line or "").strip()
            if not line:
                continue
            upper = line.upper()
            if any(token in upper for token in skip_tokens):
                continue
            parts = line.split()
            if len(parts) >= 5 and parts[4].isdigit():
                try:
                    if int(parts[4]) <= 0:
                        continue
                except Exception:
                    pass
            is_tcp = " tcp " in f" {line.lower()} "
            if is_tcp and not any(state in upper for state in tcp_active_states):
                continue

            tokens = tuple_pattern.findall(line)
            if not tokens:
                continue
            tuples: List[Dict[str, str]] = []
            current: Dict[str, str] = {}
            seen_src = False
            for key, value in tokens:
                if key == 'src' and seen_src:
                    tuples.append(current)
                    current = {}
                if key == 'src':
                    seen_src = True
                current[key] = value
            if current:
                tuples.append(current)
            if len(tuples) < 2:
                continue
            orig = tuples[0]
            reply = tuples[1]
            orig_src = orig.get('src', '')
            orig_dst = orig.get('dst', '')
            if not orig_src or not orig_dst:
                continue
            orig_bytes = int(orig.get('bytes') or 0)
            reply_bytes = int(reply.get('bytes') or 0)

            endpoint_specs: List[Tuple[str, str, int, int]] = []
            if orig_src in ip_to_mac:
                endpoint_specs.append((orig_src, orig_dst, orig_bytes, reply_bytes))
            if orig_dst in ip_to_mac:
                endpoint_specs.append((orig_dst, orig_src, reply_bytes, orig_bytes))
            if not endpoint_specs:
                continue

            for local_ip, remote_ip, up_bytes, down_bytes in endpoint_specs:
                mac = ip_to_mac.get(local_ip)
                if not mac:
                    continue
                counts[mac] += 1
                bucket = aggregated[mac].setdefault(remote_ip, {'remote': remote_ip, 'up_bytes': 0, 'down_bytes': 0, 'count': 0})
                bucket['up_bytes'] += max(0, int(up_bytes or 0))
                bucket['down_bytes'] += max(0, int(down_bytes or 0))
                bucket['count'] += 1

        details: Dict[str, List[Dict[str, Any]]] = {}
        totals: Dict[str, Dict[str, int]] = {}
        for mac, remote_map in aggregated.items():
            rows: List[Dict[str, Any]] = []
            total_up = 0
            total_down = 0
            for remote_ip, item in remote_map.items():
                host = self._reverse_dns_cached(remote_ip, allow_lookup=False)
                up_bytes = int(item.get('up_bytes', 0) or 0)
                down_bytes = int(item.get('down_bytes', 0) or 0)
                total_up += up_bytes
                total_down += down_bytes
                rows.append({
                    'remote': remote_ip,
                    'host': host,
                    'up_bytes': up_bytes,
                    'down_bytes': down_bytes,
                    'up_h': human_bytes(up_bytes),
                    'down_h': human_bytes(down_bytes),
                    'count': int(item.get('count', 0) or 0),
                })
            rows.sort(key=lambda x: (-(int(x.get('up_bytes', 0)) + int(x.get('down_bytes', 0))), str(x.get('host') or x.get('remote') or '').lower()))
            details[mac] = rows[:32]
            totals[mac] = {'up_bytes': total_up, 'down_bytes': total_down}
        return dict(counts), details, totals

    def collect_once(self) -> None:
        settings = self.store.get_settings()
        ts = now_ts()
        sample_time = time.time()
        poll_interval_sec = max(0.10, min(60.0, float(settings.get("poll_interval_ms", DEFAULT_SETTINGS["poll_interval_ms"])) / 1000.0))
        nlbw_refresh_sec = max(0.20, min(10.0, float(self._get_nlbw_refresh_interval() or 1.0)))
        have_conntrack_proc = self._has_conntrack_proc()
        rate_hold_sec = max(0.20, min(2.00, max(poll_interval_sec * 1.8, min(nlbw_refresh_sec, 1.0) * 1.20)))
        live_hold_sec = max(0.20, min(1.20, poll_interval_sec * 2.2))
        if have_conntrack_proc:
            bootstrap_wait_sec = max(0.12, min(0.45, poll_interval_sec * 1.8))
        else:
            bootstrap_wait_sec = max(0.20, min(1.20, max(poll_interval_sec, min(nlbw_refresh_sec, 1.0) + 0.05)))
        self._clear_warning("wifi")
        wifi_clients = {}
        leases = self._get_dhcp_leases()
        neigh = self._get_neighbors()
        bridge_fdb = self._get_bridge_fdb()
        traffic = self._get_nlbw_stats()
        active_conn_counts, conntrack_details, conntrack_totals = self._parse_conntrack_details(self._build_ip_to_mac_map(leases, neigh))
        bootstrap_traffic = None
        bootstrap_conn_totals = None
        if not self.bootstrap_completed:
            bootstrap_traffic = traffic
            bootstrap_conn_totals = conntrack_totals
            # On platforms with /proc/net/nf_conntrack available we can bootstrap quickly and
            # start showing existing live activity almost immediately. Otherwise wait a bit for nlbwmon.
            if bootstrap_wait_sec > 0:
                time.sleep(bootstrap_wait_sec)
            ts = now_ts()
            sample_time = time.time()
            leases = self._get_dhcp_leases()
            neigh = self._get_neighbors()
            bridge_fdb = self._get_bridge_fdb()
            traffic = self._get_nlbw_stats()
            active_conn_counts, conntrack_details, conntrack_totals = self._parse_conntrack_details(self._build_ip_to_mac_map(leases, neigh))
            self.bootstrap_completed = True

        known_macs = set()
        known_macs.update(wifi_clients.keys())
        known_macs.update(leases.keys())
        known_macs.update(neigh.keys())
        known_macs.update(bridge_fdb.keys())
        known_macs.update(traffic.keys())
        known_macs.update(self.last_presence_ts.keys())
        with self.store.lock:
            known_macs.update(self.store.state.get("devices", {}).keys())

        changed_state = False
        active_neigh_states = {"REACHABLE", "DELAY", "PROBE", "PERMANENT"}
        offline_grace = max(3, int(settings.get("offline_grace_sec", 90)))
        with self.store.lock:
            devices = self.store.state.setdefault("devices", {})
            for mac in sorted(known_macs):
                if not mac or mac == "00:00:00:00:00:00":
                    continue
                dev = devices.setdefault(mac, {
                    "mac": mac,
                    "alias": "",
                    "hostname": "",
                    "last_ip": "",
                    "ips": [],
                    "first_seen_ts": ts,
                    "last_seen_ts": 0,
                    "ever_wifi": False,
                    "notify_enabled": True,
                    "status": "offline",
                    "online": False,
                    "last_notified": {},
                })

                lease = leases.get(mac, {})
                if lease.get("hostname") and lease["hostname"] != dev.get("hostname"):
                    dev["hostname"] = lease["hostname"]
                    changed_state = True
                local_ips = filter_local_ips(
                    list(dev.get("ips", [])) + list(lease.get("ips", [])) + list(neigh.get(mac, {}).get("ips", [])),
                    str(settings.get("local_network_cidr", DEFAULT_SETTINGS["local_network_cidr"])),
                    include_ipv6=bool(settings.get("track_ipv6", True)),
                )
                if local_ips != list(dev.get("ips", [])):
                    dev["ips"] = local_ips
                    changed_state = True
                new_last_ip = local_ips[0] if local_ips else ""
                if new_last_ip != dev.get("last_ip"):
                    dev["last_ip"] = new_last_ip
                    changed_state = True
                if mac in wifi_clients and not dev.get("ever_wifi"):
                    dev["ever_wifi"] = True
                    changed_state = True

                prev_state = self.prev_traffic.get(mac)
                current = dict(traffic.get(mac, {}))
                if not current:
                    current = {
                        "conns": 0,
                        "rx_bytes": int(prev_state.get("rx_bytes", 0)) if prev_state else 0,
                        "tx_bytes": int(prev_state.get("tx_bytes", 0)) if prev_state else 0,
                    }
                else:
                    current.setdefault("conns", 0)
                    current.setdefault("rx_bytes", int(prev_state.get("rx_bytes", 0)) if prev_state else 0)
                    current.setdefault("tx_bytes", int(prev_state.get("tx_bytes", 0)) if prev_state else 0)

                rx_diff = 0
                tx_diff = 0
                down_bps = 0.0
                up_bps = 0.0

                if prev_state is None:
                    boot_current = dict((bootstrap_traffic or {}).get(mac, {})) if bootstrap_traffic else {}
                    boot_rx = int(boot_current.get("rx_bytes", current.get("rx_bytes", 0)) or 0)
                    boot_tx = int(boot_current.get("tx_bytes", current.get("tx_bytes", 0)) or 0)
                    boot_sample_time = max(0.001, sample_time - bootstrap_wait_sec)
                    rx_diff = int(current["rx_bytes"]) - boot_rx
                    tx_diff = int(current["tx_bytes"]) - boot_tx
                    if rx_diff > 0 or tx_diff > 0:
                        dt_boot = max(0.05, sample_time - boot_sample_time)
                        down_bps = max(0.0, rx_diff / dt_boot)
                        up_bps = max(0.0, tx_diff / dt_boot)
                        last_rate_ts = sample_time
                        last_counter_change_ts = sample_time
                    else:
                        rx_diff = 0
                        tx_diff = 0
                        last_rate_ts = 0.0
                        last_counter_change_ts = boot_sample_time
                    prev_state = {
                        "rx_bytes": int(current["rx_bytes"]),
                        "tx_bytes": int(current["tx_bytes"]),
                        "sample_time": sample_time,
                        "last_counter_change_ts": last_counter_change_ts,
                        "last_rate_ts": last_rate_ts,
                        "current_down_bps": down_bps,
                        "current_up_bps": up_bps,
                    }
                    self.prev_traffic[mac] = prev_state
                else:
                    prev_rx = int(prev_state.get("rx_bytes", current["rx_bytes"]))
                    prev_tx = int(prev_state.get("tx_bytes", current["tx_bytes"]))
                    rx_diff = int(current["rx_bytes"]) - prev_rx
                    tx_diff = int(current["tx_bytes"]) - prev_tx

                    if rx_diff < 0 or tx_diff < 0:
                        rx_diff = 0
                        tx_diff = 0
                        prev_state.update({
                            "rx_bytes": int(current["rx_bytes"]),
                            "tx_bytes": int(current["tx_bytes"]),
                            "sample_time": sample_time,
                            "last_counter_change_ts": sample_time,
                            "last_rate_ts": 0.0,
                            "current_down_bps": 0.0,
                            "current_up_bps": 0.0,
                        })
                    elif rx_diff > 0 or tx_diff > 0:
                        anchor_ts = float(prev_state.get("last_counter_change_ts", prev_state.get("sample_time", sample_time)))
                        dt = max(0.05, sample_time - anchor_ts)
                        down_bps = rx_diff / dt
                        up_bps = tx_diff / dt
                        prev_state.update({
                            "rx_bytes": int(current["rx_bytes"]),
                            "tx_bytes": int(current["tx_bytes"]),
                            "sample_time": sample_time,
                            "last_counter_change_ts": sample_time,
                            "last_rate_ts": sample_time,
                            "current_down_bps": down_bps,
                            "current_up_bps": up_bps,
                        })
                    else:
                        last_rate_ts = float(prev_state.get("last_rate_ts", 0.0) or 0.0)
                        rate_age = sample_time - last_rate_ts if last_rate_ts else 10**9
                        if rate_age <= rate_hold_sec:
                            down_bps = float(prev_state.get("current_down_bps", 0.0) or 0.0)
                            up_bps = float(prev_state.get("current_up_bps", 0.0) or 0.0)
                        else:
                            prev_state["current_down_bps"] = 0.0
                            prev_state["current_up_bps"] = 0.0
                            down_bps = 0.0
                            up_bps = 0.0
                        prev_state["sample_time"] = sample_time

                conn_total = conntrack_totals.get(mac, {})
                conn_down_bytes = int(conn_total.get("down_bytes", 0) or 0)
                conn_up_bytes = int(conn_total.get("up_bytes", 0) or 0)
                prev_conn = self.prev_conn_counters.get(mac)
                conn_down_bps = 0.0
                conn_up_bps = 0.0
                if prev_conn is None:
                    boot_conn = dict((bootstrap_conn_totals or {}).get(mac, {})) if bootstrap_conn_totals else {}
                    boot_conn_down = int(boot_conn.get("down_bytes", conn_down_bytes) or 0)
                    boot_conn_up = int(boot_conn.get("up_bytes", conn_up_bytes) or 0)
                    boot_conn_sample_time = max(0.001, sample_time - bootstrap_wait_sec)
                    diff_down = conn_down_bytes - boot_conn_down
                    diff_up = conn_up_bytes - boot_conn_up
                    if diff_down > 0 or diff_up > 0:
                        dt_boot_conn = max(0.05, sample_time - boot_conn_sample_time)
                        conn_down_bps = max(0.0, diff_down / dt_boot_conn)
                        conn_up_bps = max(0.0, diff_up / dt_boot_conn)
                        last_conn_rate_ts = sample_time
                    else:
                        diff_down = 0
                        diff_up = 0
                        last_conn_rate_ts = 0.0
                    self.prev_conn_counters[mac] = {
                        "down_bytes": conn_down_bytes,
                        "up_bytes": conn_up_bytes,
                        "sample_time": sample_time,
                        "last_rate_ts": last_conn_rate_ts,
                        "current_down_bps": conn_down_bps,
                        "current_up_bps": conn_up_bps,
                    }
                    prev_conn = self.prev_conn_counters[mac]
                else:
                    prev_conn_down = int(prev_conn.get("down_bytes", conn_down_bytes) or 0)
                    prev_conn_up = int(prev_conn.get("up_bytes", conn_up_bytes) or 0)
                    diff_down = conn_down_bytes - prev_conn_down
                    diff_up = conn_up_bytes - prev_conn_up
                    if diff_down < 0 or diff_up < 0:
                        diff_down = 0
                        diff_up = 0
                        prev_conn.update({
                            "down_bytes": conn_down_bytes,
                            "up_bytes": conn_up_bytes,
                            "sample_time": sample_time,
                            "last_rate_ts": 0.0,
                            "current_down_bps": 0.0,
                            "current_up_bps": 0.0,
                        })
                    elif diff_down > 0 or diff_up > 0:
                        dt_conn = max(0.05, sample_time - float(prev_conn.get("sample_time", sample_time) or sample_time))
                        conn_down_bps = diff_down / dt_conn
                        conn_up_bps = diff_up / dt_conn
                        prev_conn.update({
                            "down_bytes": conn_down_bytes,
                            "up_bytes": conn_up_bytes,
                            "sample_time": sample_time,
                            "last_rate_ts": sample_time,
                            "current_down_bps": conn_down_bps,
                            "current_up_bps": conn_up_bps,
                        })
                    else:
                        last_conn_rate_ts = float(prev_conn.get("last_rate_ts", 0.0) or 0.0)
                        conn_age = sample_time - last_conn_rate_ts if last_conn_rate_ts else 10**9
                        if conn_age <= live_hold_sec:
                            conn_down_bps = float(prev_conn.get("current_down_bps", 0.0) or 0.0)
                            conn_up_bps = float(prev_conn.get("current_up_bps", 0.0) or 0.0)
                        else:
                            prev_conn["current_down_bps"] = 0.0
                            prev_conn["current_up_bps"] = 0.0
                        prev_conn["sample_time"] = sample_time

                if conn_down_bps > 0.0 or conn_up_bps > 0.0:
                    # Prefer live conntrack byte deltas when they are available.
                    down_bps = max(down_bps, conn_down_bps)
                    up_bps = max(up_bps, conn_up_bps)
                elif int(active_conn_counts.get(mac, 0) or 0) > 0:
                    # Keep the latest live values briefly between polls, but do not suppress fresher nlbw values.
                    down_bps = max(down_bps, float(prev_conn.get("current_down_bps", 0.0) or 0.0))
                    up_bps = max(up_bps, float(prev_conn.get("current_up_bps", 0.0) or 0.0))

                hist = self.histories[mac]
                hist.append({
                    "sample_time": sample_time,
                    "rx_bytes": int(current["rx_bytes"]),
                    "tx_bytes": int(current["tx_bytes"]),
                    "conns": int(current.get("conns", 0)),
                    "down_bps": down_bps,
                    "up_bps": up_bps,
                })
                while len(hist) > 2 and float(hist[0].get("sample_time", sample_time)) < sample_time - 65.0:
                    hist.popleft()
                current_total_kbps = ((down_bps + up_bps) * 8.0) / 1000.0

                neigh_state = str(neigh.get(mac, {}).get("state", "")).upper()
                conn_rows = list(conntrack_details.get(mac, []))
                active_conns = int(active_conn_counts.get(mac, 0) or 0)
                if conn_rows:
                    active_conns = max(active_conns, len(conn_rows))

                current_rate_alive = bool((down_bps > 0.0 or up_bps > 0.0) and current_total_kbps > 0.0)
                presence_now = bool(
                    active_conns > 0
                    or rx_diff > 0
                    or tx_diff > 0
                    or current_rate_alive
                )
                if presence_now:
                    self.last_presence_ts[mac] = ts
                    if ts - int(dev.get("last_seen_ts", 0) or 0) >= 5:
                        dev["last_seen_ts"] = ts
                        changed_state = True
                presence_ts = int(self.last_presence_ts.get(mac, int(dev.get("last_seen_ts", 0) or 0)))

                online = bool(presence_ts and (ts - presence_ts) <= offline_grace and (active_conns > 0 or current_rate_alive or rx_diff > 0 or tx_diff > 0))
                if not online:
                    status = "offline"
                elif current_total_kbps > float(settings.get("activity_total_kbps", 500)):
                    status = "active"
                else:
                    status = "idle"

                if active_conns <= 0 and not online:
                    conn_rows = []
                display_conns = active_conns if online else 0

                prev_online = bool(dev.get("online"))
                prev_status = dev.get("status", "offline")
                if prev_online != online:
                    dev["online"] = online
                    changed_state = True
                if prev_status != status:
                    dev["status"] = status
                    changed_state = True

                wifi = wifi_clients.get(mac, {})
                self.runtime[mac] = {
                    "mac": mac,
                    "ip": dev.get("last_ip", ""),
                    "ips": list(dev.get("ips", [])),
                    "hostname": dev.get("hostname", ""),
                    "alias": dev.get("alias", ""),
                    "online": online,
                    "status": status,
                    "current_conns": display_conns,
                    "current_down_bps": down_bps,
                    "current_up_bps": up_bps,
                    "current_total_kbps": current_total_kbps,
                    "wifi_signal": wifi.get("signal"),
                    "wifi_connected": mac in wifi_clients,
                    "bridge_present": mac in bridge_fdb,
                    "last_seen_ts": presence_ts,
                    "display_name": dev.get("alias") or dev.get("hostname") or mac,
                    "conn_directions": conn_rows,
                }

                self._handle_notifications(dev, prev_online, online, prev_status, status, current_total_kbps, active_conns)

            if changed_state:
                self.store.save_state()

    def _handle_notifications(self, dev: Dict[str, Any], prev_online: bool, online: bool, prev_status: str, status: str, total_kbps: float, conns: int) -> None:
        settings = self.store.get_settings()
        if not settings.get("telegram_enabled"):
            return
        selected_only = bool(settings.get("telegram_limit_to_selected_devices"))
        selected_devices = {normalize_mac(v) for v in settings.get("telegram_selected_devices", []) if v}
        if selected_only and normalize_mac(dev.get("mac", "")) not in selected_devices:
            return
        if not dev.get("notify_enabled", True):
            return
        name = dev.get("alias") or dev.get("hostname") or dev.get("last_ip") or dev.get("mac")
        mac = dev.get("mac", "")
        ip = dev.get("last_ip", "—")
        note_total = float(settings.get("notification_total_kbps", 500))
        last = dev.setdefault("last_notified", {})
        ts = now_ts()
        sample_time = time.time()

        def allowed(event_key: str, cooldown: int = 120) -> bool:
            prev_ts = int(last.get(event_key, 0) or 0)
            if ts - prev_ts < cooldown:
                return False
            last[event_key] = ts
            return True

        if not prev_online and online and settings.get("notify_online") and allowed("online"):
            msg = tr("tg_msg_online", name=name, ip=ip, mac=mac)
            self._send_telegram(msg)
            self.store.add_event("online", tr("event_online_short", name=name), mac)

        if prev_online and not online and settings.get("notify_offline") and allowed("offline"):
            msg = tr("tg_msg_offline", name=name, ip=ip, mac=mac)
            self._send_telegram(msg)
            self.store.add_event("offline", tr("event_offline_short", name=name), mac)

        if prev_status != "active" and status == "active" and settings.get("notify_active") and total_kbps >= note_total and allowed("active", cooldown=180):
            msg = tr("tg_msg_active", name=name, ip=ip, mac=mac, traffic=human_kbits(total_kbps), conns=conns)
            self._send_telegram(msg)
            self.store.add_event("active", tr("event_active_short", name=name, traffic=human_kbits(total_kbps), conns=conns), mac)

        if prev_status == "active" and status != "active" and settings.get("notify_inactive") and allowed("inactive", cooldown=180):
            msg = tr("tg_msg_inactive", name=name, ip=ip, mac=mac)
            self._send_telegram(msg)
            self.store.add_event("inactive", tr("event_inactive_short", name=name), mac)

    def _send_telegram(self, text: str) -> Tuple[bool, str]:
        settings = self.store.get_settings()
        token = (settings.get("telegram_bot_token") or "").strip()
        chat_id = str(settings.get("telegram_chat_id") or "").strip()
        if not token or not chat_id:
            return False, tr("tg_token_chat_missing")
        url = f"https://api.telegram.org/bot{token}/sendMessage"
        payload = urllib.parse.urlencode({
            "chat_id": chat_id,
            "text": text,
        }).encode("utf-8")
        req = urllib.request.Request(url, data=payload, headers={"Content-Type": "application/x-www-form-urlencoded"})
        try:
            with urllib.request.urlopen(req, timeout=10) as resp:
                body = resp.read().decode("utf-8", errors="ignore")
                if '"ok":true' in body:
                    return True, "ok"
                return False, body[:400]
        except urllib.error.HTTPError as exc:
            return False, f"HTTP {exc.code}"
        except Exception as exc:
            return False, str(exc)

    def test_telegram(self) -> Tuple[bool, str]:
        text = tr("test_message", app=APP_NAME, time=fmt_ts(now_ts()))
        ok, msg = self._send_telegram(text)
        if ok:
            self.store.add_event("telegram", tr("event_tg_test_sent"))
        return ok, msg

    def _get_nlbw_refresh_interval(self) -> float:
        rc, out, _ = run_cmd(["uci", "-q", "get", "nlbwmon.@nlbwmon[0].refresh_interval"], timeout=3)
        if rc != 0 or not out:
            return 1.0
        value = out.strip().lower()
        try:
            if value.endswith('ms'):
                return max(0.1, float(value[:-2]) / 1000.0)
            if value.endswith('s'):
                return max(0.1, float(value[:-1]))
            if value.endswith('m'):
                return max(1.0, float(value[:-1]) * 60.0)
            return max(0.1, float(value))
        except Exception:
            return 1.0

    def _get_bridge_fdb(self) -> Dict[str, Dict[str, Any]]:
        commands = [
            ["bridge", "fdb", "show", "br", "br-lan"],
            ["bridge", "fdb", "show"],
        ]
        output = ""
        for cmd in commands:
            rc, out, _ = run_cmd(cmd, timeout=5)
            if rc == 0 and out:
                output = out
                break
        if not output:
            return {}
        result: Dict[str, Dict[str, Any]] = {}
        for line in output.splitlines():
            text = line.strip()
            if not text:
                continue
            if 'self' in text or 'permanent' in text:
                continue
            parts = text.split()
            mac = normalize_mac(parts[0]) if parts else ''
            if not mac or mac == '00:00:00:00:00:00':
                continue
            if 'master' in parts:
                idx = parts.index('master')
                if idx + 1 < len(parts) and parts[idx + 1] != 'br-lan':
                    continue
            if 'dev' in parts:
                idx = parts.index('dev')
                dev_name = parts[idx + 1] if idx + 1 < len(parts) else ''
            else:
                dev_name = ''
            result[mac] = {'dev': dev_name}
        return result

    def _get_wifi_clients(self) -> Dict[str, Dict[str, Any]]:
        rc, out, err = run_cmd(["ubus", "list", "hostapd.*"])
        if rc != 0:
            if rc == 127 or "Not found" in (err or out):
                self._clear_warning("wifi")
                return {}
            self._set_warning("wifi", tr("warning_wifi", details=(err or out or "no data")))
            return {}
        result: Dict[str, Dict[str, Any]] = {}
        objects = [line.strip() for line in out.splitlines() if line.strip().startswith("hostapd.")]
        for obj in objects:
            rc2, out2, err2 = run_cmd(["ubus", "call", obj, "get_clients"])
            if rc2 != 0 or not out2:
                continue
            try:
                data = json.loads(out2)
                clients = data.get("clients") if isinstance(data, dict) and isinstance(data.get("clients"), dict) else data
                if isinstance(clients, dict):
                    for mac, info in clients.items():
                        nmac = normalize_mac(mac)
                        result[nmac] = {
                            "signal": info.get("signal") if isinstance(info, dict) else None,
                            "noise": info.get("noise") if isinstance(info, dict) else None,
                            "object": obj,
                        }
                self._clear_warning("wifi")
            except Exception:
                continue
        return result

    def _get_dhcp_leases(self) -> Dict[str, Dict[str, Any]]:
        leases_path = "/tmp/dhcp.leases"
        result: Dict[str, Dict[str, Any]] = {}
        if not os.path.exists(leases_path):
            return result
        try:
            with open(leases_path, "r", encoding="utf-8", errors="ignore") as f:
                for line in f:
                    parts = line.strip().split()
                    if len(parts) < 4:
                        continue
                    expiry, mac, ip, hostname = parts[:4]
                    mac = normalize_mac(mac)
                    row = result.setdefault(mac, {"expiry": expiry, "ips": [], "hostname": ""})
                    row["expiry"] = expiry
                    if ip and ip not in row["ips"]:
                        row["ips"].append(ip)
                    if hostname != "*":
                        row["hostname"] = hostname
        except Exception:
            pass
        return result

    def _get_neighbors(self) -> Dict[str, Dict[str, Any]]:
        result: Dict[str, Dict[str, Any]] = {}
        outputs: List[str] = []
        for family in ("-4", "-6"):
            rc, out, _ = run_cmd(["ip", family, "neigh", "show"])
            if rc == 0 and out:
                outputs.append(out)
        if not outputs:
            rc, out, _ = run_cmd(["ip", "neigh", "show"])
            if rc != 0:
                return {}
            outputs.append(out)

        for chunk in outputs:
            for line in chunk.splitlines():
                parts = line.split()
                if len(parts) < 3:
                    continue
                ip = parts[0]
                lladdr = None
                state = parts[-1]
                if "lladdr" in parts:
                    idx = parts.index("lladdr")
                    if idx + 1 < len(parts):
                        lladdr = normalize_mac(parts[idx + 1])
                if lladdr:
                    row = result.setdefault(lladdr, {"ips": [], "state": state})
                    row["state"] = state
                    if ip and ip not in row["ips"]:
                        row["ips"].append(ip)
        return result

    def _get_nlbw_stats(self) -> Dict[str, Dict[str, int]]:
        rc, out, err = run_cmd(["nlbw", "-c", "csv", "-g", "mac", "-o", "mac", "-q", "-n"], timeout=10)
        if rc != 0:
            self._set_warning("nlbw", tr("warning_nlbw", details=(err or out or "unknown")))
            return {}
        self._clear_warning("nlbw")
        text = out.strip()
        if not text:
            return {}
        reader = csv.DictReader(io.StringIO(text), delimiter='\t')
        rows = list(reader)
        if not rows and ',' in text:
            reader = csv.DictReader(io.StringIO(text))
            rows = list(reader)
        result: Dict[str, Dict[str, int]] = {}
        for row in rows:
            mac = normalize_mac((row.get("mac") or "").strip())
            if not mac or mac == "00:00:00:00:00:00":
                continue
            try:
                result[mac] = {
                    "conns": int(row.get("conns") or 0),
                    "rx_bytes": int(row.get("rx_bytes") or 0),
                    "tx_bytes": int(row.get("tx_bytes") or 0),
                }
            except ValueError:
                continue
        return result

    def get_dashboard_payload(self) -> Dict[str, Any]:
        with self.store.lock, self.lock:
            devices_out: List[Dict[str, Any]] = []
            devices_meta = self.store.state.get("devices", {})
            current_settings = self.store.get_settings()
            include_ipv6 = bool(current_settings.get("track_ipv6", True))
            local_network_cidr = str(current_settings.get("local_network_cidr", DEFAULT_SETTINGS["local_network_cidr"]))
            for mac, meta in devices_meta.items():
                rt = self.runtime.get(mac, {})
                status = rt.get("status", meta.get("status", "offline"))
                ipv4_list, ipv6_list = split_device_ips(
                    list(meta.get("ips", [])),
                    local_network_cidr,
                    include_ipv6=include_ipv6,
                )
                name = meta.get("alias") or meta.get("hostname") or (ipv4_list[0] if ipv4_list else meta.get("last_ip")) or mac
                hostname = meta.get("hostname", "")
                name_values = [name]
                if hostname and hostname != name:
                    name_values.append(hostname)
                devices_out.append({
                    "mac": mac,
                    "display_name": name,
                    "hostname": hostname,
                    "name_values": name_values,
                    "ip": ", ".join(ipv4_list),
                    "ipv6": ", ".join(ipv6_list),
                    "ipv4_list": ipv4_list,
                    "ipv6_list": ipv6_list,
                    "status": status,
                    "conns": int(rt.get("current_conns", 0)),
                    "conn_directions": list(rt.get("conn_directions", [])),
                    "down_h": human_rate(rt.get("current_down_bps", 0.0)),
                    "up_h": human_rate(rt.get("current_up_bps", 0.0)),
                    "minute_h": human_kbits(float(rt.get("current_total_kbps", 0.0))),
                    "last_seen_h": relative_time(int(rt.get("last_seen_ts", meta.get("last_seen_ts", 0)) or 0)),
                    "last_seen_ts": int(rt.get("last_seen_ts", meta.get("last_seen_ts", 0)) or 0),
                    "online": bool(rt.get("online", meta.get("online", False))),
                    "wifi_connected": bool(rt.get("wifi_connected", False)),
                    "current_down_bps": float(rt.get("current_down_bps", 0.0)),
                    "current_up_bps": float(rt.get("current_up_bps", 0.0)),
                    "current_total_kbps": float(rt.get("current_total_kbps", 0.0)),
                    "notify_enabled": bool(meta.get("notify_enabled", True)),
                    "has_ipv6": bool(ipv6_list),
                })

            sort_weight = {"active": 0, "idle": 1, "offline": 2}
            devices_out.sort(key=lambda d: (sort_weight.get(d["status"], 9), d["display_name"].lower()))
            summary = {
                "total": len(devices_out),
                "online": sum(1 for d in devices_out if d["status"] in {"active", "idle"}),
                "active": sum(1 for d in devices_out if d["status"] == "active"),
                "idle": sum(1 for d in devices_out if d["status"] == "idle"),
            }
            events = []
            for event in self.store.state.get("events", [])[:30]:
                e = deepcopy(event)
                e["ts_h"] = fmt_ts(int(e.get("ts", 0) or 0)) if e.get("ts") else "—"
                events.append(e)
            warnings = [w.split('] ', 1)[1] if '] ' in w else w for w in self.warnings]
            return {
                "devices": devices_out,
                "summary": summary,
                "events": events,
                "warnings": warnings,
                "port": int(current_settings.get("port", 1999)),
            }


store = Store()
app = Flask(__name__)
app.secret_key = store.config.get("secret_key")
monitor = Monitor(store)
monitor.start()


def render_page(title: str, body: str, **ctx: Any) -> str:
    lang = normalize_lang(ctx.pop("lang", get_current_lang()))
    ctx.setdefault("lang", lang)
    ctx.setdefault("t", lambda key, **kwargs: tr(key, lang, **kwargs))
    ctx.setdefault("strings_json", json.dumps(lang_strings(lang), ensure_ascii=False))
    inner = render_template_string(body, **ctx)
    return render_template_string(HTML_BASE, title=title, body=inner, lang=lang)


def login_required(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        if not store.admin_exists():
            return redirect(url_for("setup"))
        if not session.get("auth"):
            return redirect(url_for("login"))
        return func(*args, **kwargs)
    return wrapper


@app.route("/")
def index():
    if not store.admin_exists():
        return redirect(url_for("setup"))
    if not session.get("auth"):
        return redirect(url_for("login"))
    payload = monitor.get_dashboard_payload()
    settings = store.get_settings()
    lang = get_current_lang(settings)
    show_ipv6 = bool(settings.get("track_ipv6", True))
    selected_macs = {normalize_mac(v) for v in settings.get("telegram_selected_devices", []) if v}
    selected_only = bool(settings.get("telegram_limit_to_selected_devices"))
    selection_initialized = bool(settings.get("telegram_selection_initialized", False))
    devices = []
    telegram_devices = []
    for d in payload["devices"]:
        badge_cls = "bad"
        badge_text = tr("status_offline", lang)
        if d["status"] == "active":
            badge_cls, badge_text = "ok", tr("status_online", lang)
        elif d["status"] == "idle":
            badge_cls, badge_text = "warn", tr("status_online", lang)
        d = dict(d)
        status_copy_class = {
            "ok": "status-ok",
            "warn": "status-warn",
            "bad": "status-bad",
        }.get(badge_cls, "")
        d["status_text"] = badge_text
        d["status_copy_class"] = status_copy_class
        d["status_chip"] = render_static_chip(badge_text, f"metro-box status-box {status_copy_class}")
        d["name_chip"] = render_chip_group(d.get("name_values") or [d.get("display_name") or d.get("hostname") or d.get("mac")])
        d["ipv4_chip"] = render_chip_group(d.get("ipv4_list", []), "ipv4-chip")
        d["ipv6_chip"] = render_chip_group(d.get("ipv6_list", []), "ipv6-chip")
        d["ipv6_toggle"] = render_ipv6_toggle(d.get("ipv6_list", [])) if show_ipv6 else ""
        d["mac_chip"] = render_chip(d.get("mac", ""), d.get("mac", ""), "mono")
        d["down_chip"] = render_static_chip(d.get("down_h", ""), "metro-box metric-box")
        d["up_chip"] = render_static_chip(d.get("up_h", ""), "metro-box metric-box")
        d["total_chip"] = render_total_metric(d.get("minute_h", tr("zero_speed", lang)), d.get("status", "offline"), d.get("current_total_kbps", 0.0))
        d["conns_chip"] = render_conn_toggle(d.get("conn_directions", []), d.get("conns", 0))
        d["last_seen_chip"] = render_static_chip(d.get("last_seen_h", ""), "metro-box metric-box")
        devices.append(d)
        telegram_devices.append({
            "mac": d.get("mac", ""),
            "display_name": d.get("display_name") or d.get("hostname") or d.get("mac"),
            "status_h": badge_text,
            "selected": (d.get("mac", "") in selected_macs) if selection_initialized else True,
        })
    return render_page(
        APP_NAME,
        DASHBOARD_TEMPLATE,
        app_name=APP_NAME,
        settings=settings,
        devices=devices,
        summary=payload["summary"],
        events=payload["events"],
        warnings=payload["warnings"],
        info=session.pop("flash_info", None),
        error=session.pop("flash_error", None),
        admin_username=store.config.get("admin", {}).get("username", ""),
        telegram_devices=telegram_devices,
        show_ipv6=show_ipv6,
        lang=lang,
    )


@app.route("/setup", methods=["GET", "POST"])
def setup():
    if store.admin_exists():
        return redirect(url_for("login"))
    error = None
    if request.method == "POST":
        username = (request.form.get("username") or "").strip()
        password = request.form.get("password") or ""
        password2 = request.form.get("password2") or ""
        if len(username) < 3:
            error = tr("username_min3")
        elif len(password) < 6:
            error = tr("password_min6")
        elif password != password2:
            error = tr("passwords_mismatch")
        else:
            store.set_admin(username, password)
            store.add_event("setup", tr("event_admin_created", username=username))
            session["flash_info"] = tr("admin_created_login_now")
            return redirect(url_for("login"))
    return render_page(APP_NAME, SETUP_TEMPLATE, app_name=APP_NAME, error=error, lang=get_current_lang())


@app.route("/login", methods=["GET", "POST"])
def login():
    if not store.admin_exists():
        return redirect(url_for("setup"))
    error = None
    if request.method == "POST":
        username = (request.form.get("username") or "").strip()
        password = request.form.get("password") or ""
        if store.verify_admin(username, password):
            session["auth"] = True
            session["user"] = username
            return redirect(url_for("index"))
        error = tr("invalid_credentials")
    return render_page(APP_NAME, LOGIN_TEMPLATE, app_name=APP_NAME, error=error, message=session.pop("flash_info", None), lang=get_current_lang())


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


@app.route("/settings/save", methods=["POST"])
@login_required
def save_settings():
    try:
        current_settings = store.get_settings()
        selected_devices_raw = request.form.getlist("telegram_selected_devices")
        selected_devices = []
        seen = set()
        for value in selected_devices_raw:
            mac = normalize_mac(value)
            if not mac or mac in seen:
                continue
            seen.add(mac)
            selected_devices.append(mac)

        new_port = int(request.form.get("port") or current_settings.get("port", 1999))
        if new_port < 1 or new_port > 65535:
            raise ValueError(tr("port_range"))

        normalized_local_network = normalize_local_network_cidr(
            (request.form.get("local_network_cidr") or DEFAULT_SETTINGS["local_network_cidr"]).strip()
            or DEFAULT_SETTINGS["local_network_cidr"]
        )
        current_local_network = normalize_local_network_cidr(
            str(current_settings.get("local_network_cidr", DEFAULT_SETTINGS["local_network_cidr"]))
        )

        updated = {
            "port": new_port,
            "telegram_bot_token": (request.form.get("telegram_bot_token") or "").strip(),
            "telegram_chat_id": (request.form.get("telegram_chat_id") or "").strip(),
            "activity_total_kbps": max(1, int(request.form.get("activity_total_kbps") or DEFAULT_SETTINGS["activity_total_kbps"])),
            "notification_total_kbps": max(1, int(request.form.get("notification_total_kbps") or DEFAULT_SETTINGS["notification_total_kbps"])),
            "poll_interval_ms": min(60000, max(250, int(request.form.get("poll_interval_ms") or DEFAULT_SETTINGS["poll_interval_ms"]))),
            "offline_grace_sec": min(600, max(10, int(request.form.get("offline_grace_sec") or DEFAULT_SETTINGS["offline_grace_sec"]))),
            "local_network_cidr": normalized_local_network,
            "track_ipv6": parse_bool_from_form("track_ipv6"),
            "telegram_enabled": parse_bool_from_form("telegram_enabled"),
            "notify_online": parse_bool_from_form("notify_online"),
            "notify_offline": parse_bool_from_form("notify_offline"),
            "notify_active": parse_bool_from_form("notify_active"),
            "notify_inactive": parse_bool_from_form("notify_inactive"),
            "telegram_limit_to_selected_devices": parse_bool_from_form("telegram_limit_to_selected_devices"),
            "telegram_selected_devices": selected_devices,
            "telegram_selection_initialized": True,
        }
        store.update_settings(updated)
        sync_state_device_ips(updated)

        if updated["telegram_limit_to_selected_devices"]:
            store.add_event("settings", tr("settings_updated_selected", count=len(selected_devices)))
        else:
            store.add_event("settings", tr("settings_updated"))

        port_changed = int(current_settings.get("port", 1999)) != int(updated["port"])
        network_changed = current_local_network != updated["local_network_cidr"]
        restart_required = port_changed or network_changed
        redirect_url = build_redirect_url(updated["port"], url_for("index"))
        message = tr("settings_saved")
        if port_changed:
            message = tr("port_changed_restarting", port=updated["port"])
        elif network_changed:
            message = tr("network_changed_restarting")

        if is_json_request():
            if restart_required:
                restarted = schedule_service_restart(delay_sec=0.8)
                return jsonify({
                    "ok": True,
                    "restart_required": True,
                    "restart_scheduled": restarted,
                    "redirect_url": redirect_url,
                    "redirect_delay_ms": 2200,
                    "port": updated["port"],
                    "message": message,
                })
            return jsonify({
                "ok": True,
                "restart_required": False,
                "redirect_url": redirect_url,
                "port": updated["port"],
                "message": message,
            })

        if restart_required:
            schedule_service_restart(delay_sec=0.8)
            if port_changed:
                session["flash_info"] = tr("port_changed_reload", port=updated["port"])
            elif network_changed:
                session["flash_info"] = tr("network_changed_reload")
            else:
                session["flash_info"] = message
        else:
            session["flash_info"] = message
    except Exception as exc:
        if is_json_request():
            return jsonify({"ok": False, "error": f"{tr('save_settings_failed')}: {exc}"}), 400
        session["flash_error"] = f"{tr('save_settings_failed')}: {exc}"
    return redirect(url_for("index"))



@app.route("/settings/test_telegram", methods=["POST"])
@login_required
def test_telegram():
    ok, msg = monitor.test_telegram()
    if ok:
        session["flash_info"] = tr("tg_test_sent")
    else:
        session["flash_error"] = tr("telegram_error", msg=msg)
    return redirect(url_for("index"))


@app.route("/settings/change_password", methods=["POST"])
@login_required
def change_password():
    username = (request.form.get("username") or "").strip()
    current_password = request.form.get("current_password") or ""
    new_password = request.form.get("new_password") or ""
    new_password2 = request.form.get("new_password2") or ""
    if len(username) < 3:
        session["flash_error"] = tr("new_username_short")
    elif len(new_password) < 6:
        session["flash_error"] = tr("new_password_min6")
    elif new_password != new_password2:
        session["flash_error"] = tr("new_passwords_mismatch")
    else:
        ok, msg = store.change_admin(current_password, username, new_password)
        if ok:
            store.add_event("admin", tr("event_admin_changed"))
            session["flash_info"] = msg
        else:
            session["flash_error"] = msg
    return redirect(url_for("index"))


@app.route("/settings/language", methods=["POST"])
@login_required
def set_language():
    language = normalize_lang(request.form.get("language"))
    store.update_settings({"language": language})
    session["flash_info"] = tr("lang_saved", language)
    return redirect(url_for("index"))


@app.route("/api/status")
@login_required
def api_status():
    return jsonify(monitor.get_dashboard_payload())


def main() -> None:
    settings = store.get_settings()
    host = settings.get("bind_host", "0.0.0.0")
    port = int(settings.get("port", 1999))
    app.run(host=host, port=port, debug=False, use_reloader=False, threaded=True)


if __name__ == "__main__":
    main()
