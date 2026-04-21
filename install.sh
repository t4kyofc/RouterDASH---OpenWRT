#!/bin/sh
set -eu

APP_DIR=/opt/routerdash
CONF_DIR=/etc/routerdash
INIT_FILE=/etc/init.d/routerdash
PID_FILE=/var/run/routerdash.pid
SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)

LANG_CHOICE="${ROUTERDASH_LANG:-}"
ACTION_CHOICE="${ROUTERDASH_ACTION:-}"

has_tty() {
  [ -t 1 ] && [ -r /dev/tty ] && [ -w /dev/tty ]
}

setup_colors() {
  if has_tty; then
    C_RESET="$(printf '\033[0m')"
    C_RED="$(printf '\033[31m')"
    C_GREEN="$(printf '\033[32m')"
    C_YELLOW="$(printf '\033[33m')"
    C_BLUE="$(printf '\033[34m')"
    C_CYAN="$(printf '\033[36m')"
    C_BOLD="$(printf '\033[1m')"
  else
    C_RESET=''
    C_RED=''
    C_GREEN=''
    C_YELLOW=''
    C_BLUE=''
    C_CYAN=''
    C_BOLD=''
  fi
}

normalize_text() {
  printf '%s' "$1" | tr '[:upper:]' '[:lower:]' | sed 's/^[[:space:]]*//;s/[[:space:]]*$//'
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
  case "$(normalize_text "$1")" in
    2|en|eng|english) echo en ;;
    *) echo ru ;;
  esac
}

normalize_action() {
  case "$(normalize_text "$1")" in
    2|remove|delete|uninstall) echo uninstall ;;
    3|reinstall) echo reinstall ;;
    4|status) echo status ;;
    *) echo install ;;
  esac
}

for arg in "$@"; do
  case "$arg" in
    ru|RU|en|EN|eng|ENG|english|English|1|2)
      [ -n "$LANG_CHOICE" ] || LANG_CHOICE="$arg"
      ;;
    install|INSTALL|update|UPDATE|remove|REMOVE|delete|DELETE|uninstall|UNINSTALL|reinstall|REINSTALL|status|STATUS|1|2|3|4)
      [ -n "$ACTION_CHOICE" ] || ACTION_CHOICE="$arg"
      ;;
    --lang=*) LANG_CHOICE="${arg#--lang=}" ;;
    --action=*) ACTION_CHOICE="${arg#--action=}" ;;
  esac
done

say() {
  key="$1"
  case "${LANG_CODE:-ru}:$key" in
    ru:title) echo "RouterDash локальный установщик" ;;
    en:title) echo "RouterDash local installer" ;;
    ru:need_apk) echo "Требуется OpenWrt 25.12+ с apk." ;;
    en:need_apk) echo "OpenWrt 25.12+ with apk is required." ;;
    ru:menu_lang) echo "Select installation language / Выберите язык установки" ;;
    en:menu_lang) echo "Select installation language / Choose installation language" ;;
    ru:menu_action) echo "Выберите действие:" ;;
    en:menu_action) echo "Choose action:" ;;
    ru:menu_install) echo "  1) Установить / обновить" ;;
    en:menu_install) echo "  1) Install / update" ;;
    ru:menu_remove) echo "  2) Удалить RouterDash" ;;
    en:menu_remove) echo "  2) Remove RouterDash" ;;
    ru:menu_reinstall) echo "  3) Переустановить RouterDash" ;;
    en:menu_reinstall) echo "  3) Reinstall RouterDash" ;;
    ru:menu_status) echo "  4) Показать статус" ;;
    en:menu_status) echo "  4) Show status" ;;
    ru:step_pkg) echo "Установка пакетов" ;;
    en:step_pkg) echo "Installing packages" ;;
    ru:step_dirs) echo "Создание каталогов" ;;
    en:step_dirs) echo "Creating directories" ;;
    ru:step_copy) echo "Копирование файлов" ;;
    en:step_copy) echo "Copying files" ;;
    ru:step_cfg) echo "Подготовка конфигурации" ;;
    en:step_cfg) echo "Preparing configuration" ;;
    ru:step_nlbw) echo "Настройка nlbwmon" ;;
    en:step_nlbw) echo "Configuring nlbwmon" ;;
    ru:step_enable) echo "Включение автозапуска" ;;
    en:step_enable) echo "Enabling autostart" ;;
    ru:step_start) echo "Запуск сервиса" ;;
    en:step_start) echo "Starting service" ;;
    ru:step_check) echo "Проверка статуса" ;;
    en:step_check) echo "Checking status" ;;
    ru:step_done) echo "Установка завершена" ;;
    en:step_done) echo "Install completed" ;;
    ru:step_stop) echo "Остановка сервиса" ;;
    en:step_stop) echo "Stopping service" ;;
    ru:step_disable) echo "Отключение автозапуска" ;;
    en:step_disable) echo "Disabling autostart" ;;
    ru:step_kill) echo "Очистка процессов и PID" ;;
    en:step_kill) echo "Cleaning processes and PID" ;;
    ru:step_rm) echo "Удаление файлов" ;;
    en:step_rm) echo "Removing files" ;;
    ru:step_removed) echo "RouterDash удалён" ;;
    en:step_removed) echo "RouterDash removed" ;;
    ru:remove_missing) echo "RouterDash не найден. Удалять нечего." ;;
    en:remove_missing) echo "RouterDash not found. Nothing to remove." ;;
    ru:status_title) echo "Текущий статус RouterDash:" ;;
    en:status_title) echo "Current RouterDash status:" ;;
    ru:service_ok) echo "Сервис запущен" ;;
    en:service_ok) echo "Service is running" ;;
    ru:service_fail) echo "Сервис не запущен. Проверьте логи: logread -e routerdash" ;;
    en:service_fail) echo "Service is not running. Check logs: logread -e routerdash" ;;
    ru:open) echo "Откройте в браузере:" ;;
    en:open) echo "Open in browser:" ;;
    ru:first) echo "При первом открытии панель предложит создать логин и пароль." ;;
    en:first) echo "On first open, the panel will ask you to create username and password." ;;
    ru:missing_py) echo "Не найден routerdash.py рядом с install.sh" ;;
    en:missing_py) echo "routerdash.py was not found next to install.sh" ;;
    ru:missing_init) echo "Не найден routerdash.init рядом с install.sh" ;;
    en:missing_init) echo "routerdash.init was not found next to install.sh" ;;
    ru:missing_blinker) echo "Не найден blinker.py рядом с install.sh" ;;
    en:missing_blinker) echo "blinker.py was not found next to install.sh" ;;
    ru:source_dir) echo "Источник файлов" ;;
    en:source_dir) echo "Source directory" ;;
    *) echo "$key" ;;
  esac
}

print_banner() {
  printf '%s%s==========================================%s\n' "$C_BLUE" "$C_BOLD" "$C_RESET"
  printf '%s%s%s\n' "$C_CYAN" "$(say title)" "$C_RESET"
  printf '%s%s==========================================%s\n' "$C_BLUE" "$C_BOLD" "$C_RESET"
}

step() {
  idx="$1"
  total="$2"
  msg="$3"
  printf '%s[%s/%s]%s %s\n' "$C_BLUE" "$idx" "$total" "$C_RESET" "$msg"
}

ok() {
  printf '%s%s%s\n' "$C_GREEN" "$1" "$C_RESET"
}

warn() {
  printf '%s%s%s\n' "$C_YELLOW" "$1" "$C_RESET"
}

err() {
  printf '%s%s%s\n' "$C_RED" "$1" "$C_RESET" >&2
}

setup_colors

is_installed() {
  [ -f "$APP_DIR/routerdash.py" ] || [ -x "$INIT_FILE" ] || [ -d "$CONF_DIR" ]
}

choose_lang() {
  if [ -n "$LANG_CHOICE" ]; then
    normalize_lang "$LANG_CHOICE"
    return
  fi
  if has_tty; then
    echo "Select installation language / Выберите язык установки" >/dev/tty
    echo "  1) Русский" >/dev/tty
    echo "  2) English" >/dev/tty
    answer="$(prompt_value 'Choice [1/2, default 1]: ')"
    normalize_lang "$answer"
    return
  fi
  echo ru
}

LANG_CODE="$(choose_lang)"
export ROUTERDASH_LANG="$LANG_CODE"

choose_action() {
  if [ -n "$ACTION_CHOICE" ]; then
    normalize_action "$ACTION_CHOICE"
    return
  fi
  if has_tty; then
    print_banner >/dev/tty
    say menu_action >/dev/tty
    say menu_install >/dev/tty
    say menu_remove >/dev/tty
    say menu_reinstall >/dev/tty
    say menu_status >/dev/tty
    answer="$(prompt_value 'Choice [1/2/3/4, default 1]: ')"
    normalize_action "$answer"
    return
  fi
  echo install
}

ACTION="$(choose_action)"
export ROUTERDASH_ACTION="$ACTION"

ensure_apk() {
  if ! command -v apk >/dev/null 2>&1; then
    err "$(say need_apk)"
    exit 1
  fi
}

copy_with_mode() {
  mode="$1"
  src="$2"
  dst="$3"
  [ -f "$src" ] || {
    err "Source file not found: $src"
    exit 1
  }
  dst_dir=$(dirname -- "$dst")
  mkdir -p "$dst_dir"
  cp "$src" "$dst"
  chmod "$mode" "$dst"
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
        'telegram_selection_initialized': False,
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

for key, value in defaults['settings'].items():
    if key not in settings:
        settings[key] = deepcopy(value)

settings['language'] = lang

with open(config_path, 'w', encoding='utf-8') as fh:
    json.dump(config, fh, ensure_ascii=False, indent=2, sort_keys=True)
PY
}

configure_nlbwmon() {
  if ! uci -q get nlbwmon.@nlbwmon[0] >/dev/null 2>&1; then
    uci add nlbwmon nlbwmon >/dev/null 2>&1 || true
  fi
  uci -q del_list nlbwmon.@nlbwmon[0].local_network='lan' >/dev/null 2>&1 || true
  uci add_list nlbwmon.@nlbwmon[0].local_network='lan' >/dev/null 2>&1 || true
  uci set nlbwmon.@nlbwmon[0].refresh_interval='30s' >/dev/null 2>&1 || true
  uci set nlbwmon.@nlbwmon[0].database_directory='/var/lib/nlbwmon' >/dev/null 2>&1 || true
  uci commit nlbwmon >/dev/null 2>&1 || true
  /etc/init.d/nlbwmon enable >/dev/null 2>&1 || true
  /etc/init.d/nlbwmon restart >/dev/null 2>&1 || true
}

service_running() {
  /etc/init.d/routerdash status 2>/dev/null | grep -qi running
}

start_service_with_retry() {
  /etc/init.d/routerdash stop >/dev/null 2>&1 || true
  rm -f "$PID_FILE"
  /etc/init.d/routerdash start >/dev/null 2>&1 || true
  i=0
  while [ "$i" -lt 6 ]; do
    if service_running; then
      return 0
    fi
    sleep 1
    i=$((i + 1))
  done
  return 1
}

install_routerdash() {
  print_banner
  ensure_apk

  step 1 9 "$(say step_pkg)"
  apk update
  apk add python3 python3-flask ca-bundle nlbwmon iwinfo

  step 2 9 "$(say step_dirs)"
  mkdir -p "$APP_DIR" "$CONF_DIR"

  step 3 9 "$(say step_copy)"
  [ -f "$SCRIPT_DIR/routerdash.py" ] || { err "$(say missing_py)"; exit 1; }
  [ -f "$SCRIPT_DIR/routerdash.init" ] || { err "$(say missing_init)"; exit 1; }
  [ -f "$SCRIPT_DIR/blinker.py" ] || { err "$(say missing_blinker)"; exit 1; }
  copy_with_mode 0755 "$SCRIPT_DIR/routerdash.py" "$APP_DIR/routerdash.py"
  copy_with_mode 0644 "$SCRIPT_DIR/blinker.py" "$APP_DIR/blinker.py"
  copy_with_mode 0755 "$SCRIPT_DIR/routerdash.init" "$INIT_FILE"

  step 4 9 "$(say step_cfg)"
  write_default_config

  step 5 9 "$(say step_nlbw)"
  configure_nlbwmon

  step 6 9 "$(say step_enable)"
  /etc/init.d/routerdash enable >/dev/null 2>&1 || true

  step 7 9 "$(say step_start)"
  if ! start_service_with_retry; then
    warn "$(say service_fail)"
  fi

  step 8 9 "$(say step_check)"
  /etc/init.d/routerdash status || true

  LAN_IP="$(uci -q get network.lan.ipaddr || echo 192.168.1.1)"
  LAN_IP="${LAN_IP%%/*}"

  step 9 9 "$(say step_done)"
  if service_running; then
    ok "$(say service_ok)"
  else
    warn "$(say service_fail)"
  fi
  printf '%s http://%s:1999\n' "$(say open)" "$LAN_IP"
  printf '%s\n' "$(say first)"
}

uninstall_routerdash() {
  print_banner
  if ! is_installed; then
    warn "$(say remove_missing)"
    return 0
  fi

  step 1 5 "$(say step_stop)"
  [ -x "$INIT_FILE" ] && /etc/init.d/routerdash stop >/dev/null 2>&1 || true

  step 2 5 "$(say step_disable)"
  [ -x "$INIT_FILE" ] && /etc/init.d/routerdash disable >/dev/null 2>&1 || true

  step 3 5 "$(say step_kill)"
  pkill -f '/opt/routerdash/routerdash.py' >/dev/null 2>&1 || true
  rm -f "$PID_FILE"

  step 4 5 "$(say step_rm)"
  rm -f "$INIT_FILE"
  rm -rf "$APP_DIR" "$CONF_DIR"

  step 5 5 "$(say step_removed)"
  ok "$(say step_removed)"
}

show_status() {
  print_banner
  printf '%s\n' "$(say status_title)"
  printf '%s: %s\n' "$(say source_dir)" "$SCRIPT_DIR"
  if [ -x "$INIT_FILE" ]; then
    /etc/init.d/routerdash status || true
    if service_running; then
      ok "$(say service_ok)"
    else
      warn "$(say service_fail)"
    fi
  else
    warn "$(say remove_missing)"
  fi
}

case "$ACTION" in
  install)
    install_routerdash
    ;;
  reinstall)
    uninstall_routerdash
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
