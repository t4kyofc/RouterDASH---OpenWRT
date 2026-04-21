#!/bin/sh
set -eu

APP_DIR=/opt/routerdash
CONF_DIR=/etc/routerdash
INIT_FILE=/etc/init.d/routerdash
PID_FILE=/var/run/routerdash.pid
SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)

LANG_CHOICE="${ROUTERDASH_LANG:-}"
ACTION_CHOICE="${ROUTERDASH_ACTION:-}"

for arg in "$@"; do
  case "$arg" in
    ru|RU|en|EN|eng|ENG|english|English|1|2)
      if [ -z "$LANG_CHOICE" ]; then
        LANG_CHOICE="$arg"
      fi
      ;;
    install|INSTALL|update|UPDATE|remove|REMOVE|delete|DELETE|uninstall|UNINSTALL|reinstall|REINSTALL|status|STATUS|3)
      if [ -z "$ACTION_CHOICE" ]; then
        ACTION_CHOICE="$arg"
      fi
      ;;
    --lang=*)
      LANG_CHOICE="${arg#--lang=}"
      ;;
    --action=*)
      ACTION_CHOICE="${arg#--action=}"
      ;;
  esac
done

has_tty() {
  [ -r /dev/tty ] && [ -w /dev/tty ]
}

prompt_value() {
  prompt="$1"
  if has_tty; then
    printf '%s' "$prompt" >/dev/tty
    IFS= read -r answer </dev/tty || true
    printf '%s' "$answer"
  else
    printf ''
  fi
}

normalize_lang() {
  case "$(printf '%s' "$1" | tr '[:upper:]' '[:lower:]')" in
    2|en|eng|english) echo "en" ;;
    *) echo "ru" ;;
  esac
}

normalize_action() {
  case "$(printf '%s' "$1" | tr '[:upper:]' '[:lower:]')" in
    2|remove|delete|uninstall) echo "uninstall" ;;
    3|reinstall) echo "reinstall" ;;
    status) echo "status" ;;
    * ) echo "install" ;;
  esac
}

is_installed() {
  [ -f "$APP_DIR/routerdash.py" ] || [ -x "$INIT_FILE" ] || [ -d "$CONF_DIR" ]
}

choose_lang() {
  if [ -n "$LANG_CHOICE" ]; then
    normalize_lang "$LANG_CHOICE"
    return
  fi

  if has_tty; then
    echo "==========================================" >/dev/tty
    echo "Select installation language / Выберите язык установки" >/dev/tty
    echo "  1) Русский" >/dev/tty
    echo "  2) English" >/dev/tty
    answer="$(prompt_value 'Choice [1/2, default 1]: ')"
    normalize_lang "$answer"
    return
  fi

  echo "No TTY detected. Default language: Russian (ru)." >&2
  echo "Tip: set ROUTERDASH_LANG=en for English." >&2
  echo "ru"
}

LANG_CODE="$(choose_lang)"
export ROUTERDASH_LANG="$LANG_CODE"

say() {
  key="$1"
  case "$LANG_CODE:$key" in
    ru:need_apk) echo "Требуется OpenWrt 25.12+ с apk." ;;
    en:need_apk) echo "OpenWrt 25.12+ with apk is required." ;;
    ru:menu_action) echo "Выберите действие" ;;
    en:menu_action) echo "Choose action" ;;
    ru:menu_install) echo "  1) Установить / обновить" ;;
    en:menu_install) echo "  1) Install / update" ;;
    ru:menu_remove) echo "  2) Удалить RouterDash" ;;
    en:menu_remove) echo "  2) Remove RouterDash" ;;
    ru:menu_reinstall) echo "  3) Переустановить RouterDash" ;;
    en:menu_reinstall) echo "  3) Reinstall RouterDash" ;;
    ru:default_install) echo "По умолчанию: установка." ;;
    en:default_install) echo "Default action: install." ;;
    ru:not_installed_install) echo "RouterDash не найден. Будет выполнена установка." ;;
    en:not_installed_install) echo "RouterDash not found. Installation will be performed." ;;
    ru:already_installed) echo "RouterDash уже установлен." ;;
    en:already_installed) echo "RouterDash is already installed." ;;

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

    ru:remove1) echo "[1/4] Остановка RouterDash..." ;;
    en:remove1) echo "[1/4] Stopping RouterDash..." ;;
    ru:remove2) echo "[2/4] Отключение автозапуска..." ;;
    en:remove2) echo "[2/4] Disabling autostart..." ;;
    ru:remove3) echo "[3/4] Удаление файлов..." ;;
    en:remove3) echo "[3/4] Removing files..." ;;
    ru:remove4) echo "[4/4] RouterDash удалён." ;;
    en:remove4) echo "[4/4] RouterDash removed." ;;
    ru:remove_note) echo "Пакеты python3, flask и nlbwmon сохранены." ;;
    en:remove_note) echo "The python3, flask, and nlbwmon packages were kept." ;;
    ru:remove_missing) echo "RouterDash не найден. Удалять нечего." ;;
    en:remove_missing) echo "RouterDash not found. Nothing to remove." ;;

    ru:open) echo "Откройте в браузере:" ;;
    en:open) echo "Open in browser:" ;;
    ru:first) echo "При первом открытии панель предложит создать логин и пароль." ;;
    en:first) echo "On first open, the panel will ask you to create a username and password." ;;
    ru:status_title) echo "Текущий статус RouterDash:" ;;
    en:status_title) echo "Current RouterDash status:" ;;
    *) echo "$key" ;;
  esac
}

choose_action() {
  if [ -n "$ACTION_CHOICE" ]; then
    normalize_action "$ACTION_CHOICE"
    return
  fi

  if ! is_installed; then
    say not_installed_install >&2
    echo "install"
    return
  fi

  if has_tty; then
    echo "==========================================" >/dev/tty
    say already_installed >/dev/tty
    say menu_action >/dev/tty
    say menu_install >/dev/tty
    say menu_remove >/dev/tty
    say menu_reinstall >/dev/tty
    answer="$(prompt_value 'Choice [1/2/3, default 1]: ')"
    normalize_action "$answer"
    return
  fi

  say default_install >&2
  echo "install"
}

ACTION="$(choose_action)"
export ROUTERDASH_ACTION="$ACTION"

ensure_apk() {
  if ! command -v apk >/dev/null 2>&1; then
    say need_apk
    exit 1
  fi
}

write_default_config() {
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
}

configure_nlbwmon() {
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
}

install_routerdash() {
  ensure_apk

  say step1
  apk update
  apk add python3 python3-flask ca-bundle nlbwmon iwinfo

  say step2
  mkdir -p "$APP_DIR" "$CONF_DIR"

  say step3
  [ -f "$SCRIPT_DIR/routerdash.py" ] || { echo "routerdash.py not found in $SCRIPT_DIR"; exit 1; }
  [ -f "$SCRIPT_DIR/routerdash.init" ] || { echo "routerdash.init not found in $SCRIPT_DIR"; exit 1; }
  cp "$SCRIPT_DIR/routerdash.py" "$APP_DIR/routerdash.py"
  chmod +x "$APP_DIR/routerdash.py"
  cp "$SCRIPT_DIR/routerdash.init" "$INIT_FILE"
  chmod +x "$INIT_FILE"

  say step4
  write_default_config

  say step5
  configure_nlbwmon

  say step6
  if [ -x "$INIT_FILE" ]; then
    /etc/init.d/routerdash enable >/dev/null 2>&1 || true
    /etc/init.d/routerdash restart >/dev/null 2>&1 || /etc/init.d/routerdash start >/dev/null 2>&1 || true
  fi

  say step7
  sleep 2
  /etc/init.d/routerdash status || true

  LAN_IP="$(uci -q get network.lan.ipaddr || echo 192.168.1.1)"
  LAN_IP="${LAN_IP%%/*}"
  say step8
  printf '%s http://%s:1999\n' "$(say open)" "$LAN_IP"
  say first
}

uninstall_routerdash() {
  if ! is_installed; then
    say remove_missing
    exit 0
  fi

  say remove1
  if [ -x "$INIT_FILE" ]; then
    /etc/init.d/routerdash stop >/dev/null 2>&1 || true
  fi

  say remove2
  if [ -x "$INIT_FILE" ]; then
    /etc/init.d/routerdash disable >/dev/null 2>&1 || true
  fi

  say remove3
  rm -f "$INIT_FILE" "$PID_FILE"
  rm -rf "$APP_DIR" "$CONF_DIR"

  say remove4
  say remove_note
}

show_status() {
  say status_title
  if [ -x "$INIT_FILE" ]; then
    /etc/init.d/routerdash status || true
  else
    say remove_missing
  fi
}

case "$ACTION" in
  install)
    install_routerdash
    ;;
  reinstall)
    uninstall_routerdash || true
    install_routerdash
    ;;
  uninstall)
    uninstall_routerdash
    ;;
  status)
    show_status
    ;;
  *)
    install_routerdash
    ;;
esac
