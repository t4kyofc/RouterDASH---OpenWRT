#!/bin/sh
set -eu

APP_DIR=/opt/routerdash
CONF_DIR=/etc/routerdash
INIT_FILE=/etc/init.d/routerdash
LANG_CHOICE="${ROUTERDASH_LANG:-}"

normalize_lang() {
  case "$(printf '%s' "$1" | tr '[:upper:]' '[:lower:]')" in
    2|en|eng|english) echo "en" ;;
    *) echo "ru" ;;
  esac
}

choose_lang() {
  if [ -n "$LANG_CHOICE" ]; then
    normalize_lang "$LANG_CHOICE"
    return
  fi
  echo "=========================================="
  echo "Select installation language / Выберите язык установки"
  echo "  1) Русский"
  echo "  2) English"
  printf "Choice [1/2, default 1]: "
  read -r answer || true
  normalize_lang "$answer"
}

LANG_CODE="$(choose_lang)"

say() {
  key="$1"
  case "$LANG_CODE:$key" in
    ru:need_apk) echo "Требуется OpenWrt 25.12+ с apk." ;;
    en:need_apk) echo "OpenWrt 25.12+ with apk is required." ;;
    ru:step1) echo "[1/8] Установка пакетов..." ;;
    en:step1) echo "[1/8] Installing packages..." ;;
    ru:step2) echo "[2/8] Создание каталогов..." ;;
    en:step2) echo "[2/8] Creating directories..." ;;
    ru:step3) echo "[3/8] Установка файлов приложения..." ;;
    en:step3) echo "[3/8] Installing app files..." ;;
    ru:step4) echo "[4/8] Подготовка конфигурации по умолчанию..." ;;
    en:step4) echo "[4/8] Preparing default configuration..." ;;
    ru:step5) echo "[5/8] Настройка nlbwmon..." ;;
    en:step5) echo "[5/8] Configuring nlbwmon..." ;;
    ru:step6) echo "[6/8] Включение RouterDash..." ;;
    en:step6) echo "[6/8] Enabling RouterDash..." ;;
    ru:step7) echo "[7/8] Проверка сервиса..." ;;
    en:step7) echo "[7/8] Checking service..." ;;
    ru:step8) echo "[8/8] Готово." ;;
    en:step8) echo "[8/8] Done." ;;
    ru:open) echo "Откройте в браузере:" ;;
    en:open) echo "Open in browser:" ;;
    ru:first) echo "При первом открытии панель предложит создать логин и пароль." ;;
    en:first) echo "On first open, the panel will ask you to create a username and password." ;;
    *) echo "$key" ;;
  esac
}

if ! command -v apk >/dev/null 2>&1; then
  say need_apk
  exit 1
fi

say step1
apk update
apk add python3 python3-flask ca-bundle nlbwmon iwinfo

say step2
mkdir -p "$APP_DIR" "$CONF_DIR"

say step3
cp ./routerdash.py "$APP_DIR/routerdash.py"
chmod +x "$APP_DIR/routerdash.py"
cp ./routerdash.init "$INIT_FILE"
chmod +x "$INIT_FILE"

say step4
LANG_CODE="$LANG_CODE" CONF_DIR="$CONF_DIR" python3 - <<'PY'
import json
import os
from copy import deepcopy

conf_dir = os.environ['CONF_DIR']
lang = os.environ.get('LANG_CODE', 'ru').strip().lower()
if lang not in {'ru', 'en'}:
    lang = 'ru'
config_path = os.path.join(conf_dir, 'config.json')

defaults = {
    'version': 1,
    'secret_key': '',
    'admin': {
        'username': '',
        'password_hash': '',
    },
    'settings': {
        'bind_host': '0.0.0.0',
        'port': 1999,
        'language': lang,
        'poll_interval_ms': 1500,
        'offline_grace_sec': 120,
        'activity_total_kbps': 250,
        'local_network_cidr': '192.168.0.0/24',
        'track_ipv6': True,
        'notify_online': True,
        'notify_offline': True,
        'notify_active': False,
        'notify_inactive': False,
        'notification_total_kbps': 500,
        'telegram_enabled': False,
        'telegram_bot_token': '',
        'telegram_chat_id': '',
        'telegram_limit_to_selected_devices': False,
        'telegram_selected_devices': [],
    },
}

if os.path.exists(config_path):
    try:
        with open(config_path, 'r', encoding='utf-8') as fh:
            config = json.load(fh)
        if not isinstance(config, dict):
            config = {}
    except Exception:
        config = {}
else:
    config = {}

config.setdefault('version', defaults['version'])
config.setdefault('secret_key', defaults['secret_key'])
config.setdefault('admin', deepcopy(defaults['admin']))
settings = config.setdefault('settings', deepcopy(defaults['settings']))

legacy_defaults = {
    'poll_interval_ms': {100, 250},
    'offline_grace_sec': {90},
    'activity_total_kbps': {500},
    'local_network_cidr': {'172.20.0.0/16', ''},
}

for key, value in defaults['settings'].items():
    if key not in settings:
        settings[key] = deepcopy(value)

for key, old_values in legacy_defaults.items():
    if settings.get(key) in old_values:
        settings[key] = deepcopy(defaults['settings'][key])

settings['language'] = lang

with open(config_path, 'w', encoding='utf-8') as fh:
    json.dump(config, fh, ensure_ascii=False, indent=2, sort_keys=True)
PY

say step5
uci -q show nlbwmon >/dev/null 2>&1 || true
if ! uci -q get nlbwmon.@nlbwmon[0] >/dev/null 2>&1; then
  uci add nlbwmon nlbwmon >/dev/null
fi
uci -q del_list nlbwmon.@nlbwmon[0].local_network='lan' >/dev/null 2>&1 || true
uci add_list nlbwmon.@nlbwmon[0].local_network='lan'
uci set nlbwmon.@nlbwmon[0].refresh_interval='30s'
uci set nlbwmon.@nlbwmon[0].database_directory='/var/lib/nlbwmon'
uci commit nlbwmon
/etc/init.d/nlbwmon enable
/etc/init.d/nlbwmon restart

say step6
/etc/init.d/routerdash enable
/etc/init.d/routerdash restart

say step7
sleep 2
/etc/init.d/routerdash status || true

LAN_IP="$(uci -q get network.lan.ipaddr || echo 192.168.1.1)"
say step8
printf '%s http://%s:1999\n' "$(say open)" "$LAN_IP"
say first
