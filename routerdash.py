#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
RouterDash for OpenWrt.

This build focuses on reliable home-presence detection for Telegram alerts:
- DHCP leases are used only as identity/address hints, not as online proof.
- A device is online only after a strong signal: active conntrack flow, traffic delta,
  Wi-Fi association, active ARP/ND neighbour state, or a successful verification probe.
- When activity disappears for offline_grace_sec, RouterDash verifies the last IP(s)
  with ARP/ND + ping before sending an offline alert.
"""

import base64
import csv
import hashlib
import hmac
import io
import ipaddress
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

from flask import Flask, jsonify, redirect, render_template_string, request, session, url_for

APP_NAME = "RouterDash"
APP_DIR = os.environ.get("ROUTERDASH_DIR", "/etc/routerdash")
CONFIG_FILE = os.path.join(APP_DIR, "config.json")
STATE_FILE = os.path.join(APP_DIR, "state.json")
LEGACY_DEFAULT_LOCAL_NETWORK_CIDR = "192.168.0.0/24"

DEFAULT_SETTINGS = {
    "bind_host": "0.0.0.0",
    "port": 1999,
    "language": "ru",
    "poll_interval_ms": 1500,
    "offline_grace_sec": 120,
    "presence_probe_cooldown_sec": 20,
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
    "version": 2,
    "secret_key": "",
    "admin": {"username": "", "password_hash": ""},
    "settings": deepcopy(DEFAULT_SETTINGS),
}

DEFAULT_STATE = {"version": 2, "devices": {}, "events": []}

I18N = {
    "ru": {
        "language": "Язык", "choose_language": "Выбор языка", "language_desc": "Выберите язык интерфейса RouterDash.",
        "russian": "Русский", "english": "English", "lang_saved": "Язык интерфейса сохранён.",
        "current_default": "Текущий язык по умолчанию", "logs": "Логи", "settings": "Настройки", "logout": "Выйти",
        "system": "Система", "tg_monitoring": "Telegram и мониторинг", "web_port": "Порт веб‑панели",
        "poll_interval_ms": "Интервал опроса, мс", "activity_threshold": "Порог активности, кбит/с",
        "notification_threshold": "Порог уведомления, кбит/с", "offline_grace": "Idle/задержка ухода, сек",
        "presence_probe_cooldown": "Повтор проверки ухода, сек", "local_network_cidr": "Локальная сеть (CIDR)",
        "tg_bot_token": "Токен Telegram‑бота", "tg_chat_id": "ID пользователя / chat_id", "tg_enabled": "Telegram включён",
        "track_ipv6": "Учитывать IPv6", "notify_online": "Сообщать о появлении", "notify_offline": "Сообщать об уходе",
        "notify_active": "Сообщать о высокой активности", "notify_inactive": "Сообщать о падении активности",
        "selected_only": "Уведомлять только по выбранным устройствам", "tg_devices": "Устройства для уведомлений",
        "save_settings": "Сохранить настройки", "send_test_telegram": "Отправить тест", "admin_account": "Администратор",
        "new_username": "Новый логин", "current_password": "Текущий пароль", "new_password": "Новый пароль",
        "repeat_new_password": "Повтор нового пароля", "update_credentials": "Обновить", "app_subtitle": "Мониторинг присутствия устройств OpenWrt",
        "port_short": "Порт", "poll_frequency": "Опрос", "warnings": "Предупреждения", "devices": "Устройства",
        "devices_desc": "История по MAC", "connected_now": "Дома сейчас", "connected_desc": "Подтверждены активностью или проверкой",
        "active": "Активные", "active_desc": "Трафик выше порога", "idle": "Idle/дома", "idle_desc": "Дома, но без активного трафика",
        "devices_section": "Устройства", "th_status": "Статус", "th_name": "Имя / хост", "th_ipv4": "IPv4", "th_mac": "MAC",
        "th_down": "Down", "th_up": "Up", "th_total": "Всего", "th_conns": "Conn", "th_last_seen": "Последняя активность",
        "status_active": "Активен", "status_idle": "Дома / idle", "status_offline": "Вне зоны",
        "activity_present": "Есть активность", "activity_none": "В сети, но без активности", "no_events": "Событий пока нет.",
        "event_type": "Тип", "copied": "Скопировано ✓", "zero_speed": "0 Kbit/s", "settings_saved": "Настройки сохранены.",
        "save_settings_failed": "Не удалось сохранить настройки", "username": "Логин", "password": "Пароль", "repeat_password": "Повтор пароля",
        "setup_intro": "Первичный вход. Создайте логин и пароль администратора.", "create_admin": "Создать администратора",
        "setup_footer": "После сохранения откроется форма входа.", "login_intro": "Вход в RouterDash.", "sign_in": "Войти",
        "admin_created_login_now": "Администратор создан. Теперь выполните вход.", "invalid_credentials": "Неверный логин или пароль.",
        "username_min3": "Логин должен быть не короче 3 символов.", "password_min6": "Пароль должен быть не короче 6 символов.",
        "passwords_mismatch": "Пароли не совпадают.", "current_password_wrong": "Текущий пароль указан неверно.", "creds_updated": "Логин и пароль обновлены.",
        "tg_test_sent": "Тестовое сообщение отправлено.", "telegram_error": "Ошибка Telegram: {msg}", "tg_token_chat_missing": "Не заполнены token/chat_id",
        "local_network_invalid": "Некорректная IPv4 сеть в CIDR.", "port_range": "Порт должен быть 1-65535.",
        "settings_updated": "Настройки обновлены", "settings_updated_selected": "Настройки обновлены. Выбрано устройств: {count}",
        "test_message": "✅ {app}: тестовое уведомление\nВремя: {time}",
        "tg_msg_online": "🟢 {name} появился в сети\nIP: {ip}\nMAC: {mac}",
        "tg_msg_offline": "🔴 {name} вышел из сети\nПоследний IP: {ip}\nMAC: {mac}",
        "tg_msg_active": "📈 {name} стал активным\nIP: {ip}\nMAC: {mac}\nТрафик: {traffic}\nСоединения: {conns}",
        "tg_msg_inactive": "📉 {name} перестал быть активным\nIP: {ip}\nMAC: {mac}",
        "event_online_short": "{name} появился в сети", "event_offline_short": "{name} вышел из сети",
        "event_active_short": "{name} стал активным: {traffic}, соединений {conns}", "event_inactive_short": "{name} перестал быть активным",
        "event_tg_test_sent": "Отправлено тестовое сообщение", "event_admin_created": "Создан администратор {username}", "event_admin_changed": "Изменён администратор",
        "warning_monitor_exception": "Ошибка мониторинга: {error}", "warning_monitor_slow": "Цикл мониторинга замедлен: {spent:.2f}s при интервале {interval:.2f}s",
        "warning_nlbw": "nlbw недоступен. Детали: {details}", "just_now": "только что", "seconds_ago": "{count} сек назад",
        "minutes_ago": "{count} мин назад", "hours_ago": "{count} ч назад", "days_ago": "{count} дн назад", "ms": "мс",
    },
    "en": {
        "language": "Language", "choose_language": "Choose language", "language_desc": "Choose RouterDash language.",
        "russian": "Русский", "english": "English", "lang_saved": "Language saved.", "current_default": "Current default",
        "logs": "Logs", "settings": "Settings", "logout": "Log out", "system": "System", "tg_monitoring": "Telegram and monitoring",
        "web_port": "Web panel port", "poll_interval_ms": "Polling interval, ms", "activity_threshold": "Activity threshold, Kbit/s",
        "notification_threshold": "Notification threshold, Kbit/s", "offline_grace": "Idle/offline grace, sec", "presence_probe_cooldown": "Offline recheck interval, sec",
        "local_network_cidr": "Local network (CIDR)", "tg_bot_token": "Telegram bot token", "tg_chat_id": "chat_id", "tg_enabled": "Enable Telegram",
        "track_ipv6": "Track IPv6", "notify_online": "Notify online", "notify_offline": "Notify offline", "notify_active": "Notify high activity",
        "notify_inactive": "Notify activity drop", "selected_only": "Selected devices only", "tg_devices": "Notification devices",
        "save_settings": "Save settings", "send_test_telegram": "Send test", "admin_account": "Administrator", "new_username": "New username",
        "current_password": "Current password", "new_password": "New password", "repeat_new_password": "Repeat new password", "update_credentials": "Update",
        "app_subtitle": "OpenWrt device presence monitor", "port_short": "Port", "poll_frequency": "Polling", "warnings": "Warnings", "devices": "Devices",
        "devices_desc": "History by MAC", "connected_now": "Home now", "connected_desc": "Confirmed by activity or probe", "active": "Active", "active_desc": "Above threshold",
        "idle": "Idle/home", "idle_desc": "Home, no active traffic", "devices_section": "Devices", "th_status": "Status", "th_name": "Name / host", "th_ipv4": "IPv4",
        "th_mac": "MAC", "th_down": "Down", "th_up": "Up", "th_total": "Total", "th_conns": "Conn", "th_last_seen": "Last activity",
        "status_active": "Active", "status_idle": "Home / idle", "status_offline": "Away", "activity_present": "Traffic detected", "activity_none": "Online but idle",
        "no_events": "No events yet.", "event_type": "Type", "copied": "Copied ✓", "zero_speed": "0 Kbit/s", "settings_saved": "Settings saved.",
        "save_settings_failed": "Failed to save settings", "username": "Username", "password": "Password", "repeat_password": "Repeat password",
        "setup_intro": "First sign-in. Create administrator credentials.", "create_admin": "Create administrator", "setup_footer": "After saving, sign in.",
        "login_intro": "Sign in to RouterDash.", "sign_in": "Sign in", "admin_created_login_now": "Administrator created. Please sign in.",
        "invalid_credentials": "Invalid username or password.", "username_min3": "Username must be at least 3 chars.", "password_min6": "Password must be at least 6 chars.",
        "passwords_mismatch": "Passwords do not match.", "current_password_wrong": "Current password is incorrect.", "creds_updated": "Credentials updated.",
        "tg_test_sent": "Test message sent.", "telegram_error": "Telegram error: {msg}", "tg_token_chat_missing": "token/chat_id is missing", "local_network_invalid": "Invalid IPv4 CIDR.",
        "port_range": "Port must be 1-65535.", "settings_updated": "Settings updated", "settings_updated_selected": "Settings updated. Selected devices: {count}",
        "test_message": "✅ {app}: test notification\nTime: {time}", "tg_msg_online": "🟢 {name} is online\nIP: {ip}\nMAC: {mac}",
        "tg_msg_offline": "🔴 {name} went offline\nLast IP: {ip}\nMAC: {mac}", "tg_msg_active": "📈 {name} became active\nIP: {ip}\nMAC: {mac}\nTraffic: {traffic}\nConnections: {conns}",
        "tg_msg_inactive": "📉 {name} is no longer active\nIP: {ip}\nMAC: {mac}", "event_online_short": "{name} is online", "event_offline_short": "{name} went offline",
        "event_active_short": "{name} became active: {traffic}, connections {conns}", "event_inactive_short": "{name} is no longer active",
        "event_tg_test_sent": "Telegram test sent", "event_admin_created": "Administrator {username} created", "event_admin_changed": "Administrator changed",
        "warning_monitor_exception": "Monitoring error: {error}", "warning_monitor_slow": "Monitoring loop is slow: {spent:.2f}s at interval {interval:.2f}s",
        "warning_nlbw": "nlbw unavailable. Details: {details}", "just_now": "just now", "seconds_ago": "{count} sec ago", "minutes_ago": "{count} min ago", "hours_ago": "{count} h ago", "days_ago": "{count} d ago", "ms": "ms",
    },
}


def normalize_lang(value: Any) -> str:
    return "en" if str(value or "").lower().startswith("en") else "ru"


def tr(key: str, lang: Optional[str] = None, **kwargs: Any) -> str:
    lang = normalize_lang(lang or (store.get_settings().get("language") if 'store' in globals() else 'ru'))
    value = I18N.get(lang, I18N["ru"]).get(key) or I18N["ru"].get(key) or key
    try:
        return value.format(**kwargs) if kwargs else value
    except Exception:
        return value


def ensure_dir(path: str) -> None:
    os.makedirs(path, exist_ok=True)


def read_json(path: str, default: Dict[str, Any]) -> Dict[str, Any]:
    if not os.path.exists(path):
        return deepcopy(default)
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, dict) else deepcopy(default)
    except Exception:
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
    return ":".join(parts) if len(parts) == 6 else mac


def safe_network(value: str) -> Optional[ipaddress._BaseNetwork]:
    try:
        return ipaddress.ip_network(str(value or "").strip(), strict=False)
    except Exception:
        return None


def run_cmd(args: List[str], timeout: int = 5) -> Tuple[int, str, str]:
    try:
        p = subprocess.run(args, capture_output=True, text=True, timeout=timeout)
        return p.returncode, (p.stdout or "").strip(), (p.stderr or "").strip()
    except FileNotFoundError:
        return 127, "", f"command not found: {args[0]}"
    except subprocess.TimeoutExpired:
        return 124, "", "timeout"
    except Exception as exc:
        return 1, "", str(exc)


def detect_system_local_network_cidr() -> str:
    fallback = LEGACY_DEFAULT_LOCAL_NETWORK_CIDR
    rc, ipaddr, _ = run_cmd(["uci", "-q", "get", "network.lan.ipaddr"], timeout=3)
    if rc != 0:
        ipaddr = ""
    rc, netmask, _ = run_cmd(["uci", "-q", "get", "network.lan.netmask"], timeout=3)
    if rc != 0:
        netmask = ""
    try:
        if ipaddr:
            if "/" in ipaddr:
                return str(ipaddress.ip_interface(ipaddr).network)
            if netmask:
                return str(ipaddress.ip_network(f"{ipaddr}/{netmask}", strict=False))
            return str(ipaddress.ip_network(f"{ipaddr}/24", strict=False))
    except Exception:
        pass
    for dev in ("br-lan", "lan"):
        rc, out, _ = run_cmd(["ip", "-4", "addr", "show", "dev", dev], timeout=3)
        if rc == 0:
            for line in out.splitlines():
                line = line.strip()
                if line.startswith("inet "):
                    try:
                        return str(ipaddress.ip_interface(line.split()[1]).network)
                    except Exception:
                        pass
    return fallback


def normalize_local_network_cidr(value: str) -> str:
    raw = (value or "").strip()
    if not raw or raw.lower() == "auto":
        return detect_system_local_network_cidr()
    net = safe_network(raw)
    if net is None or getattr(net, "version", None) != 4:
        raise ValueError(tr("local_network_invalid"))
    return str(net)


def filter_device_ips(ips: List[str], include_ipv6: bool = True) -> List[str]:
    out: List[str] = []
    seen = set()
    for raw in ips:
        ip = str(raw or "").strip()
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
            if not include_ipv6 or addr.is_unspecified or addr.is_loopback or addr.is_multicast:
                continue
        seen.add(ip)
        out.append(ip)
    return out


def split_device_ips(ips: List[str], cidr: str, include_ipv6: bool = True) -> Tuple[List[str], List[str]]:
    net4 = safe_network(cidr)
    v4: List[str] = []
    v6: List[str] = []
    for ip in filter_device_ips(ips, include_ipv6=include_ipv6):
        addr = ipaddress.ip_address(ip)
        if addr.version == 4:
            if net4 is None or addr in net4:
                v4.append(ip)
        elif include_ipv6:
            v6.append(ip)
    return v4, v6


def html_escape(value: Any) -> str:
    return str(value if value is not None else "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;").replace("'", "&#39;")


def human_rate(bps: float) -> str:
    value = float(bps or 0.0)
    units = ["B/s", "KB/s", "MB/s", "GB/s"]
    idx = 0
    while value >= 1024 and idx < len(units) - 1:
        value /= 1024.0
        idx += 1
    return f"{int(value)} {units[idx]}" if idx == 0 else f"{value:.2f} {units[idx]}"


def human_kbits(kbit: float) -> str:
    return f"{kbit/1000:.2f} Mbit/s" if float(kbit or 0) >= 1000 else f"{float(kbit or 0):.0f} Kbit/s"


def human_bytes(num: float) -> str:
    value = float(num or 0)
    units = ["B", "KB", "MB", "GB", "TB"]
    idx = 0
    while value >= 1024 and idx < len(units) - 1:
        value /= 1024.0
        idx += 1
    return f"{int(value)} {units[idx]}" if idx == 0 else f"{value:.2f} {units[idx]}"


def relative_time(ts: Optional[int]) -> str:
    if not ts:
        return "—"
    delta = max(0, now_ts() - int(ts))
    if delta < 15:
        return tr("just_now")
    if delta < 60:
        return tr("seconds_ago", count=delta)
    if delta < 3600:
        return tr("minutes_ago", count=delta // 60)
    if delta < 86400:
        return tr("hours_ago", count=delta // 3600)
    return tr("days_ago", count=delta // 86400)


def fmt_ts(ts: int) -> str:
    return time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(ts))


def pbkdf2_hash(password: str, salt: Optional[bytes] = None) -> str:
    salt = salt or secrets.token_bytes(16)
    derived = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, 200000)
    return "pbkdf2_sha256$200000$%s$%s" % (base64.b64encode(salt).decode(), base64.b64encode(derived).decode())


def verify_password(password: str, stored: str) -> bool:
    try:
        algo, rounds, salt_b64, hash_b64 = stored.split("$", 3)
        if algo != "pbkdf2_sha256":
            return False
        salt = base64.b64decode(salt_b64.encode())
        check = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, int(rounds))
        return hmac.compare_digest(base64.b64encode(check).decode(), hash_b64)
    except Exception:
        return False


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
        self.config.setdefault("version", DEFAULT_CONFIG["version"])
        self.config.setdefault("secret_key", secrets.token_hex(32))
        if not self.config.get("secret_key"):
            self.config["secret_key"] = secrets.token_hex(32)
        self.config.setdefault("admin", deepcopy(DEFAULT_CONFIG["admin"]))
        settings = self.config.setdefault("settings", {})
        for k, v in DEFAULT_SETTINGS.items():
            settings.setdefault(k, deepcopy(v))
        cur = str(settings.get("local_network_cidr") or "").strip()
        if not safe_network(cur) or cur in {"", LEGACY_DEFAULT_LOCAL_NETWORK_CIDR}:
            settings["local_network_cidr"] = detect_system_local_network_cidr()
        else:
            settings["local_network_cidr"] = normalize_local_network_cidr(cur)
        self.state.setdefault("version", DEFAULT_STATE["version"])
        self.state.setdefault("devices", {})
        self.state.setdefault("events", [])

    def save_config(self) -> None:
        with self.lock:
            write_json_atomic(CONFIG_FILE, self.config)

    def save_state(self) -> None:
        with self.lock:
            write_json_atomic(STATE_FILE, self.state)

    def get_settings(self) -> Dict[str, Any]:
        with self.lock:
            return deepcopy(self.config.get("settings", DEFAULT_SETTINGS))

    def update_settings(self, values: Dict[str, Any]) -> None:
        with self.lock:
            self.config.setdefault("settings", {}).update(values)
            self.save_config()

    def admin_exists(self) -> bool:
        with self.lock:
            admin = self.config.get("admin", {})
            return bool(admin.get("username") and admin.get("password_hash"))

    def set_admin(self, username: str, password: str) -> None:
        with self.lock:
            self.config["admin"] = {"username": username.strip(), "password_hash": pbkdf2_hash(password)}
            self.save_config()

    def verify_admin(self, username: str, password: str) -> bool:
        with self.lock:
            admin = self.config.get("admin", {})
            return username.strip() == admin.get("username", "") and verify_password(password, admin.get("password_hash", ""))

    def change_admin(self, current_password: str, username: str, new_password: str) -> Tuple[bool, str]:
        with self.lock:
            admin = self.config.get("admin", {})
            if not verify_password(current_password, admin.get("password_hash", "")):
                return False, tr("current_password_wrong")
            self.config["admin"] = {"username": username.strip(), "password_hash": pbkdf2_hash(new_password)}
            self.save_config()
            return True, tr("creds_updated")

    def add_event(self, kind: str, message: str, mac: str = "") -> None:
        with self.lock:
            events = self.state.setdefault("events", [])
            events.insert(0, {"ts": now_ts(), "kind": kind, "message": message, "mac": mac})
            del events[200:]
            self.save_state()


class Monitor:
    ACTIVE_NEIGH_STATES = {"REACHABLE", "DELAY", "PROBE", "PERMANENT"}
    DEAD_NEIGH_STATES = {"FAILED", "INCOMPLETE"}

    def __init__(self, store: Store) -> None:
        self.store = store
        self.lock = threading.RLock()
        self.stop_event = threading.Event()
        self.thread: Optional[threading.Thread] = None
        self.prev_traffic: Dict[str, Dict[str, Any]] = {}
        self.prev_conn_counters: Dict[str, Dict[str, Any]] = {}
        self.last_presence_ts: Dict[str, int] = {}
        self.last_probe_ts: Dict[str, int] = {}
        self.probe_fail_count: Dict[str, int] = defaultdict(int)
        self.runtime: Dict[str, Dict[str, Any]] = {}
        self.warnings: List[str] = []

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
                self._set_warning("monitor", tr("warning_monitor_exception", error=exc))
            settings = self.store.get_settings()
            interval = max(0.1, min(60.0, int(settings.get("poll_interval_ms", 1500)) / 1000.0))
            spent = time.time() - start
            if spent > interval * 3:
                self._set_warning("slow", tr("warning_monitor_slow", spent=spent, interval=interval))
            self.stop_event.wait(max(0.05, interval - spent))

    def _set_warning(self, key: str, message: str) -> None:
        with self.lock:
            self.warnings = [w for w in self.warnings if not w.startswith(f"[{key}]")]
            self.warnings.append(f"[{key}] {message}")
            self.warnings = self.warnings[-20:]

    def _clear_warning(self, key: str) -> None:
        with self.lock:
            self.warnings = [w for w in self.warnings if not w.startswith(f"[{key}]")]

    def _get_dhcp_leases(self) -> Dict[str, Dict[str, Any]]:
        result: Dict[str, Dict[str, Any]] = {}
        path = "/tmp/dhcp.leases"
        if not os.path.exists(path):
            return result
        try:
            with open(path, "r", encoding="utf-8", errors="ignore") as f:
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
                    if hostname and hostname != "*":
                        row["hostname"] = hostname
        except Exception:
            pass
        return result

    def _get_neighbors(self) -> Dict[str, Dict[str, Any]]:
        result: Dict[str, Dict[str, Any]] = {}
        outputs = []
        for fam in ("-4", "-6"):
            rc, out, _ = run_cmd(["ip", fam, "neigh", "show"], timeout=4)
            if rc == 0 and out:
                outputs.append(out)
        if not outputs:
            rc, out, _ = run_cmd(["ip", "neigh", "show"], timeout=4)
            if rc == 0 and out:
                outputs.append(out)
        for chunk in outputs:
            for line in chunk.splitlines():
                parts = line.split()
                if len(parts) < 3:
                    continue
                ip = parts[0]
                state = parts[-1].upper()
                if "lladdr" not in parts:
                    continue
                idx = parts.index("lladdr")
                if idx + 1 >= len(parts):
                    continue
                mac = normalize_mac(parts[idx + 1])
                row = result.setdefault(mac, {"ips": [], "states": {}})
                if ip not in row["ips"]:
                    row["ips"].append(ip)
                row["states"][ip] = state
        return result

    def _get_wifi_clients(self) -> Dict[str, Dict[str, Any]]:
        rc, out, _ = run_cmd(["ubus", "list", "hostapd.*"], timeout=4)
        if rc != 0 or not out:
            return {}
        result: Dict[str, Dict[str, Any]] = {}
        for obj in [x.strip() for x in out.splitlines() if x.strip().startswith("hostapd.")]:
            rc2, out2, _ = run_cmd(["ubus", "call", obj, "get_clients"], timeout=4)
            if rc2 != 0 or not out2:
                continue
            try:
                data = json.loads(out2)
                clients = data.get("clients") if isinstance(data, dict) else {}
                if isinstance(clients, dict):
                    for mac, info in clients.items():
                        nmac = normalize_mac(mac)
                        result[nmac] = {"object": obj, "signal": info.get("signal") if isinstance(info, dict) else None}
            except Exception:
                continue
        return result

    def _get_bridge_fdb(self) -> Dict[str, Dict[str, Any]]:
        for cmd in (["bridge", "fdb", "show", "br", "br-lan"], ["bridge", "fdb", "show"]):
            rc, out, _ = run_cmd(cmd, timeout=4)
            if rc == 0 and out:
                break
        else:
            return {}
        result: Dict[str, Dict[str, Any]] = {}
        for line in out.splitlines():
            text = line.strip()
            if not text or "permanent" in text or "self" in text:
                continue
            parts = text.split()
            mac = normalize_mac(parts[0]) if parts else ""
            if mac and mac != "00:00:00:00:00:00":
                result[mac] = {"raw": text}
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
        reader = csv.DictReader(io.StringIO(text), delimiter="\t")
        rows = list(reader)
        if not rows and "," in text:
            rows = list(csv.DictReader(io.StringIO(text)))
        result: Dict[str, Dict[str, int]] = {}
        for row in rows:
            mac = normalize_mac((row.get("mac") or "").strip())
            if not mac or mac == "00:00:00:00:00:00":
                continue
            try:
                result[mac] = {"conns": int(row.get("conns") or 0), "rx_bytes": int(row.get("rx_bytes") or 0), "tx_bytes": int(row.get("tx_bytes") or 0)}
            except Exception:
                continue
        return result

    def _load_conntrack_lines(self) -> List[str]:
        for proc_path in ("/proc/net/nf_conntrack", "/proc/net/ip_conntrack"):
            if os.path.exists(proc_path):
                try:
                    with open(proc_path, "r", encoding="utf-8", errors="ignore") as f:
                        return f.readlines()
                except Exception:
                    pass
        rc, out, _ = run_cmd(["conntrack", "-L"], timeout=8)
        return out.splitlines() if rc == 0 and out else []

    def _build_ip_to_mac_map(self, leases: Dict[str, Any], neigh: Dict[str, Any]) -> Dict[str, str]:
        m: Dict[str, str] = {}
        with self.store.lock:
            for mac, dev in self.store.state.get("devices", {}).items():
                for ip in dev.get("ips", []):
                    if ip:
                        m[ip] = mac
        for source in (leases, neigh):
            for mac, row in source.items():
                for ip in row.get("ips", []):
                    if ip:
                        m[ip] = mac
        return m

    def _parse_conntrack_details(self, ip_to_mac: Dict[str, str]) -> Tuple[Dict[str, int], Dict[str, List[Dict[str, Any]]], Dict[str, Dict[str, int]]]:
        if not ip_to_mac:
            return {}, {}, {}
        counts: Dict[str, int] = defaultdict(int)
        aggregated: Dict[str, Dict[str, Dict[str, Any]]] = defaultdict(dict)
        tuple_pattern = re.compile(r"\b(src|dst|sport|dport|packets|bytes)=([^\s]+)")
        skip_tokens = {"TIME_WAIT", "CLOSE", "CLOSED"}
        tcp_active_states = {"ESTABLISHED", "SYN_SENT", "SYN_RECV", "FIN_WAIT", "FIN_WAIT_1", "FIN_WAIT_2", "CLOSE_WAIT", "LAST_ACK"}
        for raw in self._load_conntrack_lines():
            line = raw.strip()
            if not line:
                continue
            upper = line.upper()
            if any(tok in upper for tok in skip_tokens):
                continue
            if " tcp " in f" {line.lower()} " and not any(st in upper for st in tcp_active_states):
                continue
            tokens = tuple_pattern.findall(line)
            if not tokens:
                continue
            tuples: List[Dict[str, str]] = []
            current: Dict[str, str] = {}
            seen_src = False
            for k, v in tokens:
                if k == "src" and seen_src:
                    tuples.append(current)
                    current = {}
                if k == "src":
                    seen_src = True
                current[k] = v
            if current:
                tuples.append(current)
            if len(tuples) < 2:
                continue
            orig, reply = tuples[0], tuples[1]
            orig_src, orig_dst = orig.get("src", ""), orig.get("dst", "")
            if not orig_src or not orig_dst:
                continue
            specs: List[Tuple[str, str, int, int]] = []
            if orig_src in ip_to_mac:
                specs.append((orig_src, orig_dst, int(orig.get("bytes") or 0), int(reply.get("bytes") or 0)))
            if orig_dst in ip_to_mac:
                specs.append((orig_dst, orig_src, int(reply.get("bytes") or 0), int(orig.get("bytes") or 0)))
            for local_ip, remote_ip, up_bytes, down_bytes in specs:
                mac = ip_to_mac.get(local_ip)
                if not mac:
                    continue
                counts[mac] += 1
                bucket = aggregated[mac].setdefault(remote_ip, {"remote": remote_ip, "up_bytes": 0, "down_bytes": 0, "count": 0})
                bucket["up_bytes"] += max(0, up_bytes)
                bucket["down_bytes"] += max(0, down_bytes)
                bucket["count"] += 1
        details: Dict[str, List[Dict[str, Any]]] = {}
        totals: Dict[str, Dict[str, int]] = {}
        for mac, remote_map in aggregated.items():
            rows = []
            total_up = total_down = 0
            for remote, item in remote_map.items():
                up = int(item["up_bytes"])
                down = int(item["down_bytes"])
                total_up += up
                total_down += down
                rows.append({"remote": remote, "host": remote, "up_h": human_bytes(up), "down_h": human_bytes(down), "up_bytes": up, "down_bytes": down, "count": int(item["count"])})
            rows.sort(key=lambda x: -(int(x["up_bytes"]) + int(x["down_bytes"])))
            details[mac] = rows[:32]
            totals[mac] = {"up_bytes": total_up, "down_bytes": total_down}
        return dict(counts), details, totals

    def _neigh_state_for_mac(self, mac: str, neigh: Dict[str, Any]) -> str:
        states = neigh.get(mac, {}).get("states", {}) if neigh.get(mac) else {}
        if any(str(s).upper() in self.ACTIVE_NEIGH_STATES for s in states.values()):
            return "active"
        if any(str(s).upper() in self.DEAD_NEIGH_STATES for s in states.values()):
            return "dead"
        return "unknown"

    def _probe_device_present(self, mac: str, ips: List[str], local_network_cidr: str) -> bool:
        ipv4, ipv6 = split_device_ips(ips, local_network_cidr, include_ipv6=True)
        candidates = ipv4[:2] + ipv6[:1]
        if not candidates:
            return False
        for ip in candidates:
            try:
                addr = ipaddress.ip_address(ip)
            except Exception:
                continue
            # First read current neighbour cache.
            rc, out, _ = run_cmd(["ip", "neigh", "show", ip], timeout=2)
            if rc == 0 and out and mac in out.lower() and any(st in out.upper() for st in self.ACTIVE_NEIGH_STATES):
                return True
            # Ping primarily to trigger ARP/ND; devices may ignore ICMP, so check neighbour again afterwards.
            if addr.version == 4:
                run_cmd(["ping", "-c", "1", "-W", "1", ip], timeout=2)
            else:
                run_cmd(["ping", "-6", "-c", "1", "-W", "1", ip], timeout=3)
            rc, out, _ = run_cmd(["ip", "neigh", "show", ip], timeout=2)
            if rc == 0 and out and mac in out.lower() and any(st in out.upper() for st in self.ACTIVE_NEIGH_STATES):
                return True
        return False

    def collect_once(self) -> None:
        settings = self.store.get_settings()
        ts = now_ts()
        sample_time = time.time()
        local_network = normalize_local_network_cidr(str(settings.get("local_network_cidr", "")))
        include_ipv6 = bool(settings.get("track_ipv6", True))
        offline_grace = max(10, int(settings.get("offline_grace_sec", 120)))
        probe_cooldown = max(5, int(settings.get("presence_probe_cooldown_sec", 20)))
        threshold = float(settings.get("activity_total_kbps", 250))

        wifi = self._get_wifi_clients()
        leases = self._get_dhcp_leases()
        neigh = self._get_neighbors()
        fdb = self._get_bridge_fdb()
        traffic = self._get_nlbw_stats()
        active_conn_counts, conn_details, conn_totals = self._parse_conntrack_details(self._build_ip_to_mac_map(leases, neigh))

        known = set(leases) | set(neigh) | set(fdb) | set(wifi) | set(traffic) | set(active_conn_counts) | set(self.last_presence_ts)
        with self.store.lock:
            known |= set(self.store.state.get("devices", {}))

        changed = False
        with self.store.lock:
            devices = self.store.state.setdefault("devices", {})
            for mac in sorted(known):
                if not mac or mac == "00:00:00:00:00:00":
                    continue
                dev = devices.setdefault(mac, {
                    "mac": mac, "alias": "", "hostname": "", "last_ip": "", "ips": [], "first_seen_ts": ts,
                    "last_seen_ts": 0, "status": "offline", "online": False, "notify_enabled": True, "last_notified": {},
                })
                lease = leases.get(mac, {})
                if lease.get("hostname") and lease.get("hostname") != dev.get("hostname"):
                    dev["hostname"] = lease["hostname"]
                    changed = True
                merged_ips = filter_device_ips(list(dev.get("ips", [])) + list(lease.get("ips", [])) + list(neigh.get(mac, {}).get("ips", [])), include_ipv6=include_ipv6)
                if merged_ips != list(dev.get("ips", [])):
                    dev["ips"] = merged_ips
                    changed = True
                ipv4_list, _ = split_device_ips(merged_ips, local_network, include_ipv6=include_ipv6)
                if ipv4_list and ipv4_list[0] != dev.get("last_ip"):
                    dev["last_ip"] = ipv4_list[0]
                    changed = True

                current = dict(traffic.get(mac, {}))
                prev = self.prev_traffic.get(mac)
                if not current:
                    current = {"conns": 0, "rx_bytes": int(prev.get("rx_bytes", 0)) if prev else 0, "tx_bytes": int(prev.get("tx_bytes", 0)) if prev else 0}
                rx_diff = tx_diff = 0
                down_bps = up_bps = 0.0
                if prev is not None:
                    dt = max(0.05, sample_time - float(prev.get("sample_time", sample_time)))
                    rx_diff = max(0, int(current.get("rx_bytes", 0)) - int(prev.get("rx_bytes", 0)))
                    tx_diff = max(0, int(current.get("tx_bytes", 0)) - int(prev.get("tx_bytes", 0)))
                    if rx_diff or tx_diff:
                        down_bps = rx_diff / dt
                        up_bps = tx_diff / dt
                self.prev_traffic[mac] = {"rx_bytes": int(current.get("rx_bytes", 0)), "tx_bytes": int(current.get("tx_bytes", 0)), "sample_time": sample_time}

                # Conntrack byte deltas give more responsive live speeds than nlbwmon alone.
                total_conn = conn_totals.get(mac, {})
                cdown = int(total_conn.get("down_bytes", 0) or 0)
                cup = int(total_conn.get("up_bytes", 0) or 0)
                pc = self.prev_conn_counters.get(mac)
                if pc is not None:
                    dtc = max(0.05, sample_time - float(pc.get("sample_time", sample_time)))
                    dd = max(0, cdown - int(pc.get("down_bytes", 0)))
                    du = max(0, cup - int(pc.get("up_bytes", 0)))
                    if dd or du:
                        down_bps = max(down_bps, dd / dtc)
                        up_bps = max(up_bps, du / dtc)
                self.prev_conn_counters[mac] = {"down_bytes": cdown, "up_bytes": cup, "sample_time": sample_time}

                active_conns = int(active_conn_counts.get(mac, 0) or 0)
                total_kbps = ((down_bps + up_bps) * 8.0) / 1000.0
                neigh_state = self._neigh_state_for_mac(mac, neigh)
                strong_present = bool(active_conns > 0 or rx_diff > 0 or tx_diff > 0 or total_kbps > 0 or mac in wifi or neigh_state == "active")

                if strong_present:
                    self.last_presence_ts[mac] = ts
                    self.probe_fail_count[mac] = 0
                    if ts - int(dev.get("last_seen_ts", 0) or 0) >= 3:
                        dev["last_seen_ts"] = ts
                        changed = True

                presence_ts = int(self.last_presence_ts.get(mac, int(dev.get("last_seen_ts", 0) or 0)))
                absent_for = ts - presence_ts if presence_ts else 10**9
                prev_online = bool(dev.get("online"))
                online = bool(presence_ts and absent_for <= offline_grace)

                # After idle/offline grace, verify with ARP/ND + ping before marking offline.
                if not strong_present and prev_online and absent_for > offline_grace:
                    if ts - int(self.last_probe_ts.get(mac, 0) or 0) >= probe_cooldown:
                        self.last_probe_ts[mac] = ts
                        verified = self._probe_device_present(mac, merged_ips, local_network)
                        if verified:
                            self.last_presence_ts[mac] = ts
                            self.probe_fail_count[mac] = 0
                            dev["last_seen_ts"] = ts
                            changed = True
                            online = True
                            presence_ts = ts
                        else:
                            self.probe_fail_count[mac] += 1
                    # Two failed confirmations, or one failed confirmation after long absence, makes it offline.
                    online = self.probe_fail_count.get(mac, 0) < 2 and absent_for <= (offline_grace + probe_cooldown)

                if not online:
                    status = "offline"
                    display_conns = 0
                    conn_rows = []
                elif total_kbps >= threshold or active_conns > 0:
                    status = "active"
                    display_conns = active_conns
                    conn_rows = conn_details.get(mac, [])
                else:
                    status = "idle"
                    display_conns = active_conns
                    conn_rows = conn_details.get(mac, [])

                prev_status = str(dev.get("status", "offline"))
                if dev.get("online") != online:
                    dev["online"] = online
                    changed = True
                if dev.get("status") != status:
                    dev["status"] = status
                    changed = True

                self.runtime[mac] = {
                    "mac": mac, "ip": dev.get("last_ip", ""), "ips": list(dev.get("ips", [])), "hostname": dev.get("hostname", ""), "alias": dev.get("alias", ""),
                    "online": online, "status": status, "current_conns": display_conns, "current_down_bps": down_bps, "current_up_bps": up_bps,
                    "current_total_kbps": total_kbps, "last_seen_ts": presence_ts, "display_name": dev.get("alias") or dev.get("hostname") or dev.get("last_ip") or mac,
                    "conn_directions": conn_rows, "wifi_connected": mac in wifi, "bridge_present": mac in fdb, "neigh_state": neigh_state,
                }
                self._handle_notifications(dev, prev_online, online, prev_status, status, total_kbps, active_conns)
            if changed:
                self.store.save_state()

    def _handle_notifications(self, dev: Dict[str, Any], prev_online: bool, online: bool, prev_status: str, status: str, total_kbps: float, conns: int) -> None:
        settings = self.store.get_settings()
        if not settings.get("telegram_enabled") or not dev.get("notify_enabled", True):
            return
        mac = normalize_mac(dev.get("mac", ""))
        selected_only = bool(settings.get("telegram_limit_to_selected_devices"))
        selected = {normalize_mac(x) for x in settings.get("telegram_selected_devices", []) if x}
        if selected_only and mac not in selected:
            return
        name = dev.get("alias") or dev.get("hostname") or dev.get("last_ip") or mac
        ip = dev.get("last_ip") or "—"
        last = dev.setdefault("last_notified", {})
        ts = now_ts()

        def allowed(key: str, cooldown: int = 120) -> bool:
            if ts - int(last.get(key, 0) or 0) < cooldown:
                return False
            last[key] = ts
            return True

        if not prev_online and online and settings.get("notify_online") and allowed("online"):
            self._send_telegram(tr("tg_msg_online", name=name, ip=ip, mac=mac))
            self.store.add_event("online", tr("event_online_short", name=name), mac)
        if prev_online and not online and settings.get("notify_offline") and allowed("offline"):
            self._send_telegram(tr("tg_msg_offline", name=name, ip=ip, mac=mac))
            self.store.add_event("offline", tr("event_offline_short", name=name), mac)
        if prev_status != "active" and status == "active" and settings.get("notify_active") and total_kbps >= float(settings.get("notification_total_kbps", 500)) and allowed("active", 180):
            self._send_telegram(tr("tg_msg_active", name=name, ip=ip, mac=mac, traffic=human_kbits(total_kbps), conns=conns))
            self.store.add_event("active", tr("event_active_short", name=name, traffic=human_kbits(total_kbps), conns=conns), mac)
        if prev_status == "active" and status != "active" and settings.get("notify_inactive") and allowed("inactive", 180):
            self._send_telegram(tr("tg_msg_inactive", name=name, ip=ip, mac=mac))
            self.store.add_event("inactive", tr("event_inactive_short", name=name), mac)

    def _send_telegram(self, text: str) -> Tuple[bool, str]:
        settings = self.store.get_settings()
        token = str(settings.get("telegram_bot_token") or "").strip()
        chat_id = str(settings.get("telegram_chat_id") or "").strip()
        if not token or not chat_id:
            return False, tr("tg_token_chat_missing")
        url = f"https://api.telegram.org/bot{token}/sendMessage"
        payload = urllib.parse.urlencode({"chat_id": chat_id, "text": text}).encode("utf-8")
        req = urllib.request.Request(url, data=payload, headers={"Content-Type": "application/x-www-form-urlencoded"})
        try:
            with urllib.request.urlopen(req, timeout=10) as resp:
                body = resp.read().decode("utf-8", errors="ignore")
                return ('"ok":true' in body), body[:400]
        except urllib.error.HTTPError as exc:
            return False, f"HTTP {exc.code}"
        except Exception as exc:
            return False, str(exc)

    def test_telegram(self) -> Tuple[bool, str]:
        ok, msg = self._send_telegram(tr("test_message", app=APP_NAME, time=fmt_ts(now_ts())))
        if ok:
            self.store.add_event("telegram", tr("event_tg_test_sent"))
        return ok, msg

    def get_dashboard_payload(self) -> Dict[str, Any]:
        with self.store.lock, self.lock:
            settings = self.store.get_settings()
            include_ipv6 = bool(settings.get("track_ipv6", True))
            local_network = normalize_local_network_cidr(str(settings.get("local_network_cidr", "")))
            devices_out = []
            for mac, meta in self.store.state.get("devices", {}).items():
                rt = self.runtime.get(mac, {})
                status = rt.get("status", meta.get("status", "offline"))
                ipv4, ipv6 = split_device_ips(list(meta.get("ips", [])), local_network, include_ipv6=include_ipv6)
                display_name = meta.get("alias") or meta.get("hostname") or (ipv4[0] if ipv4 else meta.get("last_ip")) or mac
                devices_out.append({
                    "mac": mac, "display_name": display_name, "hostname": meta.get("hostname", ""), "ipv4_list": ipv4, "ipv6_list": ipv6,
                    "status": status, "online": bool(rt.get("online", meta.get("online", False))), "conns": int(rt.get("current_conns", 0)),
                    "conn_directions": list(rt.get("conn_directions", [])), "down_h": human_rate(rt.get("current_down_bps", 0.0)),
                    "up_h": human_rate(rt.get("current_up_bps", 0.0)), "minute_h": human_kbits(float(rt.get("current_total_kbps", 0.0))),
                    "current_total_kbps": float(rt.get("current_total_kbps", 0.0)), "last_seen_h": relative_time(int(rt.get("last_seen_ts", meta.get("last_seen_ts", 0)) or 0)),
                    "last_seen_ts": int(rt.get("last_seen_ts", meta.get("last_seen_ts", 0)) or 0), "wifi_connected": bool(rt.get("wifi_connected", False)),
                })
            weights = {"active": 0, "idle": 1, "offline": 2}
            devices_out.sort(key=lambda d: (weights.get(d["status"], 9), d["display_name"].lower()))
            summary = {"total": len(devices_out), "online": sum(1 for d in devices_out if d["status"] in {"active", "idle"}), "active": sum(1 for d in devices_out if d["status"] == "active"), "idle": sum(1 for d in devices_out if d["status"] == "idle")}
            events = []
            for event in self.store.state.get("events", [])[:30]:
                e = deepcopy(event)
                e["ts_h"] = fmt_ts(int(e.get("ts", 0) or 0)) if e.get("ts") else "—"
                events.append(e)
            warnings = [w.split("] ", 1)[1] if "] " in w else w for w in self.warnings]
            return {"devices": devices_out, "summary": summary, "events": events, "warnings": warnings, "port": int(settings.get("port", 1999))}


def render_chip(value: Any, cls: str = "") -> str:
    text = html_escape(value if value not in (None, "") else "—")
    return f'<span class="chip {cls}" data-copy="{text}">{text}</span>'


def render_static(value: Any, cls: str = "") -> str:
    return f'<span class="chip no-copy {cls}">{html_escape(value if value not in (None, "") else "—")}</span>'


def render_conn_details(rows: List[Dict[str, Any]], count: int) -> str:
    if count <= 0:
        return render_static("0", "metric")
    body = "".join(f'<div class="conn-row"><span>{html_escape(r.get("host") or r.get("remote") or "—")}</span><b>↑ {html_escape(r.get("up_h", "0 B"))}</b><b>↓ {html_escape(r.get("down_h", "0 B"))}</b></div>' for r in rows[:20])
    return f'<details class="conn"><summary>{count}</summary><div class="conn-pop">{body or "Нет деталей"}</div></details>'


HTML_BASE = """
<!doctype html>
<html lang="{{ lang }}">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{{ title }}</title>
  <style>
    :root {
      --bg: #05080d;
      --panel: rgba(10,17,29,.94);
      --panel2: rgba(16,26,42,.96);
      --text: #eef3fb;
      --muted: #9fb0c7;
      --muted2: #7d8ea7;
      --orange: #ff9b1f;
      --orange2: #ff7a00;
      --blue: #2f8cff;
      --green: #22c55e;
      --yellow: #eab308;
      --red: #ef4444;
      --border: #1d2e47;
      --shadow: 0 34px 90px rgba(0,0,0,.48);
    }
    * { box-sizing: border-box; }
    html, body { min-height: 100%; }
    body {
      margin: 0;
      font-family: "Segoe UI", Inter, Arial, sans-serif;
      color: var(--text);
      background:
        radial-gradient(circle at 12% 10%, rgba(255,155,31,.22), transparent 27%),
        radial-gradient(circle at 86% 14%, rgba(47,140,255,.18), transparent 28%),
        radial-gradient(circle at 78% 86%, rgba(34,197,94,.12), transparent 25%),
        linear-gradient(180deg, #05080d 0%, #08101a 100%);
      background-attachment: fixed;
    }
    body.modal-open { overflow: hidden; }
    a { color: inherit; text-decoration: none; }
    .wrap { width: min(100%, 1400px); margin: 0 auto; padding: 18px; }

    .app-shell {
      background: linear-gradient(180deg, rgba(11,18,32,.98), rgba(6,10,17,.98));
      border: 1px solid var(--border);
      border-radius: 30px;
      overflow: hidden;
      box-shadow: var(--shadow);
    }
    .shell-accent { height: 7px; background: linear-gradient(90deg, var(--orange), #ffc266 22%, var(--blue) 72%, #56d67b); }
    .shell-inner { padding: 28px; }

    .hero { display: flex; align-items: flex-start; justify-content: space-between; gap: 20px; margin-bottom: 20px; }
    .brand { display: flex; flex-direction: column; gap: 8px; min-width: 0; }
    .brand-line { display: flex; align-items: center; gap: 14px; flex-wrap: wrap; }
    .brand h1 { margin: 0; font-size: clamp(28px, 4vw, 42px); font-weight: 800; letter-spacing: -.03em; }
    .brand p { margin: 0; color: var(--muted); line-height: 1.5; max-width: 820px; }
    .build-badge {
      display: inline-flex; align-items: center; gap: 10px; padding: 10px 16px;
      border-radius: 999px; background: rgba(14,23,38,.88); border: 1px solid #263854;
      color: #cfe4d7; font-size: 14px; white-space: nowrap;
    }
    .build-badge::before { content: ""; width: 10px; height: 10px; border-radius: 50%; background: var(--green); box-shadow: 0 0 0 8px rgba(34,197,94,.12); }
    .actions { display: flex; gap: 10px; flex-wrap: wrap; justify-content: flex-end; }

    .btn, button {
      appearance: none; border: 0; border-radius: 16px; padding: 11px 16px;
      font-weight: 700; font-size: 14px; cursor: pointer; color: #1e1200;
      background: linear-gradient(180deg, #ffb443, #ff7a00); box-shadow: 0 10px 24px rgba(255,122,0,.18);
      display: inline-flex; align-items: center; justify-content: center; gap: 8px;
    }
    .btn.secondary, button.secondary {
      color: var(--text); background: rgba(255,255,255,.045); border: 1px solid rgba(255,255,255,.08); box-shadow: none;
    }

    .banner-stack { display: grid; gap: 12px; margin-bottom: 18px; }
    .banner, .panel, .card {
      background: var(--panel); border: 1px solid var(--border); border-radius: 24px; box-shadow: 0 14px 34px rgba(0,0,0,.20);
    }
    .banner { padding: 14px 16px; display: flex; align-items: center; flex-wrap: wrap; gap: 10px; }
    .banner.warning { border-color: rgba(239,68,68,.30); }

    .stats-grid { display: grid; grid-template-columns: repeat(4, minmax(170px, 1fr)); gap: 14px; margin-bottom: 20px; }
    .card { position: relative; overflow: hidden; padding: 18px 20px; background: linear-gradient(180deg, rgba(16,26,42,.96), rgba(10,17,29,.96)); }
    .card::after { content: ""; position: absolute; right: -10px; top: -10px; width: 90px; height: 90px; border-radius: 50%; background: rgba(255,255,255,.035); }
    .card .label { color: var(--muted); font-size: 14px; margin-bottom: 10px; }
    .card .value { font-size: clamp(32px, 4vw, 48px); font-weight: 800; line-height: 1; margin-bottom: 10px; }
    .card .desc { color: var(--muted2); font-size: 13px; line-height: 1.45; max-width: 28ch; }
    .card.online { background-image: linear-gradient(180deg, rgba(16,26,42,.96), rgba(10,17,29,.96)), radial-gradient(circle at 80% 25%, rgba(34,197,94,.18), transparent 36%); }
    .card.active { background-image: linear-gradient(180deg, rgba(16,26,42,.96), rgba(10,17,29,.96)), radial-gradient(circle at 80% 25%, rgba(255,155,31,.18), transparent 36%); }
    .card.alerts { background-image: linear-gradient(180deg, rgba(16,26,42,.96), rgba(10,17,29,.96)), radial-gradient(circle at 80% 25%, rgba(47,140,255,.18), transparent 36%); }

    .panel { padding: 20px; }
    .section-head { display: flex; align-items: flex-start; justify-content: space-between; gap: 12px; margin-bottom: 16px; }
    .section-head h2 { margin: 0; font-size: 22px; }
    .section-head p { margin: 6px 0 0; color: var(--muted); line-height: 1.5; }
    .table-wrap { overflow-x: auto; border-radius: 20px; background: rgba(7,16,27,.55); border: 1px solid rgba(255,255,255,.035); }
    table { width: 100%; border-collapse: separate; border-spacing: 0; min-width: 980px; }
    thead th {
      text-align: left; font-size: 13px; font-weight: 600; color: #8090a8; padding: 16px 14px;
      border-bottom: 1px solid var(--border); background: rgba(7,16,27,.88);
    }
    tbody td { padding: 14px; border-bottom: 1px solid rgba(29,46,71,.72); vertical-align: middle; background: rgba(7,16,27,.35); }
    tbody tr:hover td { background: rgba(11,18,32,.72); }
    tbody tr:last-child td { border-bottom: 0; }

    .chip {
      display: inline-flex; align-items: center; gap: 8px; padding: 8px 11px; min-height: 36px; border-radius: 999px;
      background: rgba(255,255,255,.05); border: 1px solid rgba(255,255,255,.08); white-space: nowrap; font-size: 14px; line-height: 1.2;
    }
    .metric { min-width: 94px; justify-content: center; }
    .ok { color: #d8fee7; border-color: rgba(34,197,94,.30); background: rgba(34,197,94,.08); }
    .warn { color: #ffe7a8; border-color: rgba(234,179,8,.30); background: rgba(234,179,8,.08); }
    .bad { color: #ffc9cf; border-color: rgba(239,68,68,.28); background: rgba(239,68,68,.08); }
    .status-dot { width: 12px; height: 12px; border-radius: 50%; display: inline-block; box-shadow: 0 0 0 0 currentColor; animation: pulse 1.8s infinite; flex: 0 0 auto; }
    .ok .status-dot { background: var(--green); color: rgba(34,197,94,.36); }
    .warn .status-dot { background: var(--yellow); color: rgba(234,179,8,.36); }
    .bad .status-dot { background: var(--red); color: rgba(239,68,68,.30); animation: none; }
    @keyframes pulse { 70% { box-shadow: 0 0 0 14px transparent; } 100% { box-shadow: 0 0 0 0 transparent; } }

    .muted { color: var(--muted); }
    .auth-wrap { min-height: calc(100vh - 36px); display: grid; place-items: center; padding: 16px 0; }
    .auth-card { width: min(100%, 520px); padding: 28px; background: linear-gradient(180deg, rgba(11,18,32,.96), rgba(6,10,17,.98)); border: 1px solid var(--border); border-radius: 28px; box-shadow: var(--shadow); }
    .auth-card h1 { margin: 0 0 8px; font-size: 34px; }
    .auth-card .subtitle { color: var(--muted); line-height: 1.55; margin-bottom: 18px; }

    .modal { display: none; position: fixed; inset: 0; background: rgba(3,7,12,.72); backdrop-filter: blur(8px); z-index: 30; padding: 24px; overflow: auto; }
    .modal.open { display: block; }
    .modal .box { width: min(100%, 980px); margin: 24px auto; background: linear-gradient(180deg, rgba(11,18,32,.98), rgba(6,10,17,.98)); border: 1px solid var(--border); border-radius: 28px; box-shadow: var(--shadow); padding: 24px; }
    .modal-head { display: flex; align-items: flex-start; justify-content: space-between; gap: 12px; margin-bottom: 18px; }
    .modal-head h2 { margin: 0; font-size: 24px; }
    .modal-close { width: 40px; height: 40px; border-radius: 12px; padding: 0; font-size: 20px; background: rgba(255,255,255,.05); color: var(--text); border: 1px solid rgba(255,255,255,.08); box-shadow: none; }

    .grid { display: grid; grid-template-columns: repeat(2, minmax(220px, 1fr)); gap: 14px; }
    .field { background: rgba(255,255,255,.03); border: 1px solid rgba(255,255,255,.05); border-radius: 18px; padding: 12px; }
    label { display: block; color: var(--muted); font-size: 13px; margin: 0 0 8px; }
    input { width: 100%; background: rgba(7,16,27,.95); border: 1px solid rgba(255,255,255,.08); border-radius: 12px; color: var(--text); padding: 11px 12px; outline: none; }
    input:focus { border-color: rgba(47,140,255,.48); box-shadow: 0 0 0 3px rgba(47,140,255,.15); }
    .checks { display: grid; grid-template-columns: repeat(2, minmax(220px, 1fr)); gap: 10px; margin-top: 10px; }
    .checks label { display: flex; align-items: center; gap: 10px; margin: 0; padding: 12px 14px; border-radius: 16px; background: rgba(255,255,255,.04); border: 1px solid rgba(255,255,255,.05); color: var(--text); cursor: pointer; }
    .checks input { width: 18px; height: 18px; padding: 0; accent-color: var(--orange); box-shadow: none; }
    .form-actions { display: flex; gap: 10px; flex-wrap: wrap; margin-top: 16px; }
    .events { display: grid; gap: 10px; }
    .event { background: rgba(255,255,255,.03); border: 1px solid rgba(255,255,255,.05); border-radius: 16px; padding: 14px; line-height: 1.5; }
    .event .meta { color: var(--muted); font-size: 13px; margin-top: 6px; }

    .conn { position: relative; }
    .conn summary { list-style: none; cursor: pointer; display: inline-flex; align-items: center; }
    .conn summary::-webkit-details-marker { display: none; }
    .conn-pop { position: absolute; right: 0; top: calc(100% + 8px); z-index: 4; background: #07101b; border: 1px solid var(--border); border-radius: 18px; padding: 12px; min-width: 360px; box-shadow: 0 24px 60px rgba(0,0,0,.50); }
    .conn-row { display: grid; grid-template-columns: 1fr auto auto; gap: 10px; align-items: center; padding: 9px 0; border-bottom: 1px solid rgba(255,255,255,.06); }
    .conn-row:last-child { border-bottom: 0; }

    .toast { position: fixed; right: 18px; bottom: 18px; z-index: 60; background: rgba(10,17,29,.96); border: 1px solid rgba(255,155,31,.22); border-radius: 16px; padding: 12px 14px; display: none; box-shadow: 0 18px 40px rgba(0,0,0,.34); }

    @media (max-width: 1080px) { .stats-grid { grid-template-columns: repeat(2, minmax(200px, 1fr)); } .hero { flex-direction: column; } .actions { justify-content: flex-start; } .grid, .checks { grid-template-columns: 1fr; } .shell-inner { padding: 22px; } }
    @media (max-width: 720px) { .wrap { padding: 10px; } .shell-inner { padding: 16px; } .stats-grid { grid-template-columns: 1fr; } .panel, .card { border-radius: 20px; } .auth-card { padding: 22px; } .modal { padding: 12px; } .modal .box { padding: 18px; border-radius: 22px; } .conn-pop { left: 0; right: auto; min-width: 280px; max-width: calc(100vw - 36px); } }
  </style>
</head>
<body>
  <div class="wrap">{{ body|safe }}</div>
  <div id="toast" class="toast">{{ copied }}</div>
  <script>
    function setModalState(){document.body.classList.toggle('modal-open', !!document.querySelector('.modal.open'))}
    document.addEventListener('click', function(e){
      const chip=e.target.closest('.chip:not(.no-copy)');
      if(chip){
        if(navigator.clipboard&&navigator.clipboard.writeText){navigator.clipboard.writeText(chip.dataset.copy||chip.innerText||'')}
        const t=document.getElementById('toast'); t.style.display='block'; clearTimeout(window.__toast); window.__toast=setTimeout(function(){t.style.display='none'},1800)
      }
      if(e.target.classList.contains('modal')){e.target.classList.remove('open');setModalState()}
    });
    function openModal(id){const el=document.getElementById(id);if(el){el.classList.add('open');setModalState()}}
    function closeModal(id){const el=document.getElementById(id);if(el){el.classList.remove('open');setModalState()}}
    document.addEventListener('keydown',function(e){if(e.key==='Escape'){document.querySelectorAll('.modal.open').forEach(function(el){el.classList.remove('open')});setModalState()}});
  </script>
</body>
</html>
"""

SETUP_TEMPLATE = """
<div class="auth-wrap">
  <div class="auth-card">
    <div class="brand-line" style="margin-bottom:10px"><h1>RouterDash</h1><span class="build-badge">Presence-fixed build</span></div>
    <p class="subtitle">{{ t('setup_intro') }}</p>
    {% if error %}<div class="banner warning"><strong>⚠</strong><span>{{ error }}</span></div>{% endif %}
    <form method="post">
      <div class="grid">
        <div class="field"><label>{{ t('username') }}</label><input name="username" required></div>
        <div class="field"><label>{{ t('password') }}</label><input type="password" name="password" required></div>
        <div class="field" style="grid-column:1 / -1"><label>{{ t('repeat_password') }}</label><input type="password" name="password2" required></div>
      </div>
      <div class="form-actions"><button>{{ t('create_admin') }}</button></div>
    </form>
    <p class="muted" style="margin-top:14px">{{ t('setup_footer') }}</p>
  </div>
</div>
"""

LOGIN_TEMPLATE = """
<div class="auth-wrap">
  <div class="auth-card">
    <div class="brand-line" style="margin-bottom:10px"><h1>RouterDash</h1><span class="build-badge">Presence-fixed build</span></div>
    <p class="subtitle">{{ t('login_intro') }}</p>
    {% if message %}<div class="banner"><strong>✓</strong><span>{{ message }}</span></div>{% endif %}
    {% if error %}<div class="banner warning"><strong>⚠</strong><span>{{ error }}</span></div>{% endif %}
    <form method="post">
      <div class="grid">
        <div class="field"><label>{{ t('username') }}</label><input name="username" required></div>
        <div class="field"><label>{{ t('password') }}</label><input type="password" name="password" required></div>
      </div>
      <div class="form-actions"><button>{{ t('sign_in') }}</button></div>
    </form>
  </div>
</div>
"""

DASHBOARD_TEMPLATE = """
<div class="app-shell">
  <div class="shell-accent"></div>
  <div class="shell-inner">
    <div class="hero">
      <div class="brand">
        <div class="brand-line"><h1>RouterDash</h1><span class="build-badge">Presence-fixed build</span></div>
        <p>{{ t('app_subtitle') }}</p>
        <p class="muted">{{ t('port_short') }}: {{ settings.port }} · {{ t('poll_frequency') }}: {{ settings.poll_interval_ms }} {{ t('ms') }}</p>
      </div>
      <div class="actions">
        <button onclick="openModal('settings')">⚙ {{ t('settings') }}</button>
        <button class="secondary" onclick="openModal('logs')">📋 {{ t('logs') }}</button>
        <a class="btn secondary" href="{{ url_for('logout') }}">↪ {{ t('logout') }}</a>
      </div>
    </div>

    {% if info or error or warnings %}
    <div class="banner-stack">
      {% if info %}<div class="banner"><strong>ℹ</strong><span>{{ info }}</span></div>{% endif %}
      {% if error %}<div class="banner warning"><strong>⚠</strong><span>{{ error }}</span></div>{% endif %}
      {% if warnings %}<div class="banner warning"><strong>{{ t('warnings') }}:</strong>{% for w in warnings %}<span class="chip no-copy bad">{{ w }}</span>{% endfor %}</div>{% endif %}
    </div>
    {% endif %}

    <div class="stats-grid">
      <div class="card"><div class="label">{{ t('devices') }}</div><div class="value">{{ summary.total }}</div><div class="desc">{{ t('devices_desc') }}</div></div>
      <div class="card online"><div class="label">{{ t('connected_now') }}</div><div class="value">{{ summary.online }}</div><div class="desc">{{ t('connected_desc') }}</div></div>
      <div class="card active"><div class="label">{{ t('active') }}</div><div class="value">{{ summary.active }}</div><div class="desc">{{ t('active_desc') }}</div></div>
      <div class="card alerts"><div class="label">{{ t('idle') }}</div><div class="value">{{ summary.idle }}</div><div class="desc">{{ t('idle_desc') }}</div></div>
    </div>

    <div class="panel">
      <div class="section-head"><div><h2>{{ t('devices_section') }}</h2><p>{{ t('devices_caption') }}</p></div></div>
      <div class="table-wrap">
        <table>
          <thead><tr><th>{{ t('th_status') }}</th><th>{{ t('th_name') }}</th><th>{{ t('th_ipv4') }}</th><th>{{ t('th_mac') }}</th><th>{{ t('th_down') }}</th><th>{{ t('th_up') }}</th><th>{{ t('th_total') }}</th><th>{{ t('th_conns') }}</th><th>{{ t('th_last_seen') }}</th></tr></thead>
          <tbody>{% for d in devices %}<tr><td>{{ d.status_chip|safe }}</td><td>{{ d.name_chip|safe }}</td><td>{{ d.ipv4_chip|safe }}</td><td>{{ d.mac_chip|safe }}</td><td>{{ d.down_chip|safe }}</td><td>{{ d.up_chip|safe }}</td><td>{{ d.total_chip|safe }}</td><td>{{ d.conns_chip|safe }}</td><td>{{ d.last_seen_chip|safe }}</td></tr>{% endfor %}</tbody>
        </table>
      </div>
    </div>
  </div>
</div>

<div id="logs" class="modal"><div class="box">
  <div class="modal-head"><div><h2>{{ t('logs') }}</h2><p class="muted">{{ t('event_type') }}</p></div><button class="modal-close" type="button" onclick="closeModal('logs')">×</button></div>
  <div class="events">{% for e in events %}<div class="event"><strong>{{ e.ts_h }}</strong> — {{ e.message }}<div class="meta">{{ t('event_type') }}: {{ e.kind }}{% if e.mac %} · {{ e.mac }}{% endif %}</div></div>{% endfor %}{% if not events %}<p>{{ t('no_events') }}</p>{% endif %}</div>
</div></div>

<div id="settings" class="modal"><div class="box">
  <div class="modal-head"><div><h2>{{ t('settings') }}</h2><p class="muted">RouterDash · OpenWrt · Presence monitoring</p></div><button class="modal-close" type="button" onclick="closeModal('settings')">×</button></div>
  <form method="post" action="{{ url_for('save_settings') }}">
    <h3>{{ t('system') }}</h3>
    <div class="grid">
      <div class="field"><label>{{ t('web_port') }}</label><input name="port" value="{{ settings.port }}"></div>
      <div class="field"><label>{{ t('poll_interval_ms') }}</label><input name="poll_interval_ms" value="{{ settings.poll_interval_ms }}"></div>
      <div class="field"><label>{{ t('offline_grace') }}</label><input name="offline_grace_sec" value="{{ settings.offline_grace_sec }}"></div>
      <div class="field"><label>{{ t('presence_probe_cooldown') }}</label><input name="presence_probe_cooldown_sec" value="{{ settings.presence_probe_cooldown_sec }}"></div>
      <div class="field"><label>{{ t('activity_threshold') }}</label><input name="activity_total_kbps" value="{{ settings.activity_total_kbps }}"></div>
      <div class="field"><label>{{ t('local_network_cidr') }}</label><input name="local_network_cidr" value="{{ settings.local_network_cidr }}"></div>
    </div>
    <h3>{{ t('tg_monitoring') }}</h3>
    <div class="grid">
      <div class="field"><label>{{ t('tg_bot_token') }}</label><input name="telegram_bot_token" value="{{ settings.telegram_bot_token }}"></div>
      <div class="field"><label>{{ t('tg_chat_id') }}</label><input name="telegram_chat_id" value="{{ settings.telegram_chat_id }}"></div>
      <div class="field"><label>{{ t('notification_threshold') }}</label><input name="notification_total_kbps" value="{{ settings.notification_total_kbps }}"></div>
    </div>
    <div class="checks">{% for name,label in checks %}<label><input type="checkbox" name="{{ name }}" {% if settings.get(name) %}checked{% endif %}> {{ label }}</label>{% endfor %}</div>
    <h3>{{ t('tg_devices') }}</h3>
    <div class="checks">{% for item in telegram_devices %}<label><input type="checkbox" name="telegram_selected_devices" value="{{ item.mac }}" {% if item.selected %}checked{% endif %}> {{ item.display_name }} · {{ item.mac }}</label>{% endfor %}</div>
    <div class="form-actions"><button>{{ t('save_settings') }}</button></div>
  </form>
  <form method="post" action="{{ url_for('test_telegram') }}"><div class="form-actions"><button class="secondary" type="submit">{{ t('send_test_telegram') }}</button></div></form>
  <h3>{{ t('admin_account') }}</h3>
  <form method="post" action="{{ url_for('change_password') }}">
    <div class="grid">
      <div class="field"><label>{{ t('new_username') }}</label><input name="username" value="{{ admin_username }}"></div>
      <div class="field"><label>{{ t('current_password') }}</label><input type="password" name="current_password"></div>
      <div class="field"><label>{{ t('new_password') }}</label><input type="password" name="new_password"></div>
      <div class="field"><label>{{ t('repeat_new_password') }}</label><input type="password" name="new_password2"></div>
    </div>
    <div class="form-actions"><button type="submit">{{ t('update_credentials') }}</button></div>
  </form>
  <form method="post" action="{{ url_for('set_language') }}">
    <h3>{{ t('choose_language') }}</h3>
    <div class="form-actions"><button name="language" value="ru" class="secondary" type="submit">{{ t('russian') }}</button><button name="language" value="en" class="secondary" type="submit">{{ t('english') }}</button></div>
  </form>
</div></div>
"""

store = Store()
app = Flask(__name__)
app.secret_key = store.config.get("secret_key")
monitor = Monitor(store)
monitor.start()


def render_page(title: str, template: str, **ctx: Any) -> str:
    lang = normalize_lang(ctx.pop("lang", store.get_settings().get("language", "ru")))
    ctx.setdefault("t", lambda key, **kwargs: tr(key, lang, **kwargs))
    body = render_template_string(template, **ctx)
    return render_template_string(HTML_BASE, title=title, body=body, lang=lang, copied=tr("copied", lang))


def login_required(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        if not store.admin_exists():
            return redirect(url_for("setup"))
        if not session.get("auth"):
            return redirect(url_for("login"))
        return fn(*args, **kwargs)
    return wrapper


@app.route("/")
def index():
    if not store.admin_exists():
        return redirect(url_for("setup"))
    if not session.get("auth"):
        return redirect(url_for("login"))
    payload = monitor.get_dashboard_payload()
    settings = store.get_settings()
    devices = []
    telegram_devices = []
    selected = {normalize_mac(v) for v in settings.get("telegram_selected_devices", []) if v}
    selection_initialized = bool(settings.get("telegram_selection_initialized", False))
    for d in payload["devices"]:
        cls = "bad"; text = tr("status_offline")
        if d["status"] == "active":
            cls, text = "ok", tr("status_active")
        elif d["status"] == "idle":
            cls, text = "warn", tr("status_idle")
        item = dict(d)
        item["status_chip"] = f'<span class="chip no-copy {cls}"><span class="status-dot"></span> {html_escape(text)}</span>'
        item["name_chip"] = render_chip(item.get("display_name"))
        item["ipv4_chip"] = "".join(render_chip(x) for x in item.get("ipv4_list", [])) or render_static("—")
        item["mac_chip"] = render_chip(item.get("mac"), "mono")
        item["down_chip"] = render_static(item.get("down_h"), "metric")
        item["up_chip"] = render_static(item.get("up_h"), "metric")
        item["total_chip"] = render_static(item.get("minute_h"), "metric")
        item["conns_chip"] = render_conn_details(item.get("conn_directions", []), item.get("conns", 0))
        item["last_seen_chip"] = render_static(item.get("last_seen_h"), "metric")
        devices.append(item)
        telegram_devices.append({"mac": item["mac"], "display_name": item["display_name"], "selected": (item["mac"] in selected) if selection_initialized else True})
    checks = [
        ("telegram_enabled", tr("tg_enabled")), ("track_ipv6", tr("track_ipv6")), ("notify_online", tr("notify_online")),
        ("notify_offline", tr("notify_offline")), ("notify_active", tr("notify_active")), ("notify_inactive", tr("notify_inactive")),
        ("telegram_limit_to_selected_devices", tr("selected_only")),
    ]
    return render_page(APP_NAME, DASHBOARD_TEMPLATE, settings=settings, devices=devices, summary=payload["summary"], events=payload["events"], warnings=payload["warnings"], info=session.pop("flash_info", None), error=session.pop("flash_error", None), telegram_devices=telegram_devices, checks=checks, admin_username=store.config.get("admin", {}).get("username", ""), lang=settings.get("language"))


@app.route("/setup", methods=["GET", "POST"])
def setup():
    if store.admin_exists():
        return redirect(url_for("login"))
    error = None
    if request.method == "POST":
        username = (request.form.get("username") or "").strip()
        p1 = request.form.get("password") or ""
        p2 = request.form.get("password2") or ""
        if len(username) < 3:
            error = tr("username_min3")
        elif len(p1) < 6:
            error = tr("password_min6")
        elif p1 != p2:
            error = tr("passwords_mismatch")
        else:
            store.set_admin(username, p1)
            store.add_event("setup", tr("event_admin_created", username=username))
            session["flash_info"] = tr("admin_created_login_now")
            return redirect(url_for("login"))
    return render_page(APP_NAME, SETUP_TEMPLATE, error=error)


@app.route("/login", methods=["GET", "POST"])
def login():
    if not store.admin_exists():
        return redirect(url_for("setup"))
    error = None
    if request.method == "POST":
        if store.verify_admin(request.form.get("username") or "", request.form.get("password") or ""):
            session["auth"] = True
            return redirect(url_for("index"))
        error = tr("invalid_credentials")
    return render_page(APP_NAME, LOGIN_TEMPLATE, error=error, message=session.pop("flash_info", None))


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


def parse_bool(name: str) -> bool:
    return request.form.get(name) in {"1", "true", "on", "yes"}


@app.route("/settings/save", methods=["POST"])
@login_required
def save_settings():
    try:
        current = store.get_settings()
        selected = []
        seen = set()
        for raw in request.form.getlist("telegram_selected_devices"):
            mac = normalize_mac(raw)
            if mac and mac not in seen:
                seen.add(mac); selected.append(mac)
        port = int(request.form.get("port") or current.get("port", 1999))
        if port < 1 or port > 65535:
            raise ValueError(tr("port_range"))
        updated = {
            "port": port,
            "poll_interval_ms": max(100, min(60000, int(request.form.get("poll_interval_ms") or 1500))),
            "offline_grace_sec": max(10, min(3600, int(request.form.get("offline_grace_sec") or 120))),
            "presence_probe_cooldown_sec": max(5, min(600, int(request.form.get("presence_probe_cooldown_sec") or 20))),
            "activity_total_kbps": max(1, int(request.form.get("activity_total_kbps") or 250)),
            "notification_total_kbps": max(1, int(request.form.get("notification_total_kbps") or 500)),
            "local_network_cidr": normalize_local_network_cidr(request.form.get("local_network_cidr") or ""),
            "telegram_bot_token": (request.form.get("telegram_bot_token") or "").strip(),
            "telegram_chat_id": (request.form.get("telegram_chat_id") or "").strip(),
            "telegram_enabled": parse_bool("telegram_enabled"), "track_ipv6": parse_bool("track_ipv6"), "notify_online": parse_bool("notify_online"),
            "notify_offline": parse_bool("notify_offline"), "notify_active": parse_bool("notify_active"), "notify_inactive": parse_bool("notify_inactive"),
            "telegram_limit_to_selected_devices": parse_bool("telegram_limit_to_selected_devices"), "telegram_selected_devices": selected, "telegram_selection_initialized": True,
        }
        store.update_settings(updated)
        store.add_event("settings", tr("settings_updated_selected", count=len(selected)) if updated["telegram_limit_to_selected_devices"] else tr("settings_updated"))
        session["flash_info"] = tr("settings_saved")
    except Exception as exc:
        session["flash_error"] = f"{tr('save_settings_failed')}: {exc}"
    return redirect(url_for("index"))


@app.route("/settings/test_telegram", methods=["POST"])
@login_required
def test_telegram():
    ok, msg = monitor.test_telegram()
    session["flash_info" if ok else "flash_error"] = tr("tg_test_sent") if ok else tr("telegram_error", msg=msg)
    return redirect(url_for("index"))


@app.route("/settings/change_password", methods=["POST"])
@login_required
def change_password():
    username = (request.form.get("username") or "").strip()
    p0 = request.form.get("current_password") or ""
    p1 = request.form.get("new_password") or ""
    p2 = request.form.get("new_password2") or ""
    if len(username) < 3:
        session["flash_error"] = tr("username_min3")
    elif len(p1) < 6:
        session["flash_error"] = tr("password_min6")
    elif p1 != p2:
        session["flash_error"] = tr("passwords_mismatch")
    else:
        ok, msg = store.change_admin(p0, username, p1)
        store.add_event("admin", tr("event_admin_changed")) if ok else None
        session["flash_info" if ok else "flash_error"] = msg
    return redirect(url_for("index"))


@app.route("/settings/language", methods=["POST"])
@login_required
def set_language():
    lang = normalize_lang(request.form.get("language"))
    store.update_settings({"language": lang})
    session["flash_info"] = tr("lang_saved", lang)
    return redirect(url_for("index"))


@app.route("/api/status")
@login_required
def api_status():
    return jsonify(monitor.get_dashboard_payload())


def main() -> None:
    settings = store.get_settings()
    app.run(host=settings.get("bind_host", "0.0.0.0"), port=int(settings.get("port", 1999)), debug=False, use_reloader=False, threaded=True)


if __name__ == "__main__":
    main()
