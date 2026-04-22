#!/bin/sh
set -eu

APP_DIR=/opt/routerdash
CONF_DIR=/etc/routerdash
INIT_FILE=/etc/init.d/routerdash
PID_FILE=/var/run/routerdash.pid
SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)

LANG_CHOICE=""
ACTION_CHOICE=""

has_tty() {
  [ -t 1 ] && [ -r /dev/tty ] && [ -w /dev/tty ]
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

normalize_text() {
  printf '%s' "$1" | tr '[:upper:]' '[:lower:]' | sed 's/^[[:space:]]*//;s/[[:space:]]*$//'
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
    *) echo install ;;
  esac
}

for arg in "$@"; do
  case "$arg" in
    --lang=*) LANG_CHOICE="$(normalize_lang "${arg#--lang=}")" ;;
    --action=*) ACTION_CHOICE="$(normalize_action "${arg#--action=}")" ;;
  esac
done

choose_lang() {
  if [ -n "$LANG_CHOICE" ]; then
    return
  fi
  if has_tty; then
    echo "Select installation language / Выберите язык установки" >/dev/tty
    echo "  1) Русский" >/dev/tty
    echo "  2) English" >/dev/tty
    LANG_CHOICE="$(normalize_lang "$(prompt_value 'Choice [1/2, default 1]: ')")"
  else
    LANG_CHOICE=ru
  fi
}

say() {
  key="$1"
  case "${LANG_CHOICE:-ru}:$key" in
    ru:title) echo "RouterDash локальный установщик" ;;
    en:title) echo "RouterDash local installer" ;;
    ru:menu_action) echo "Выберите действие" ;;
    en:menu_action) echo "Choose action" ;;
    ru:menu_install) echo "  1) Установить / обновить" ;;
    en:menu_install) echo "  1) Install / update" ;;
    ru:menu_remove) echo "  2) Удалить RouterDash" ;;
    en:menu_remove) echo "  2) Remove RouterDash" ;;
    ru:need_apk) echo "Требуется OpenWrt 25.12+ с apk." ;;
    en:need_apk) echo "OpenWrt 25.12+ with apk is required." ;;
    ru:step_pkg) echo "Установка пакетов" ;;
    en:step_pkg) echo "Installing packages" ;;
    ru:step_dirs) echo "Создание каталогов" ;;
    en:step_dirs) echo "Creating directories" ;;
    ru:step_patch) echo "Применение патча RouterDash" ;;
    en:step_patch) echo "Applying RouterDash patch" ;;
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
    ru:missing_patch) echo "Не найден routerdash_patch.py рядом с install.sh" ;;
    en:missing_patch) echo "routerdash_patch.py was not found next to install.sh" ;;
    *) echo "$key" ;;
  esac
}

choose_lang

choose_action() {
  if [ -n "$ACTION_CHOICE" ]; then
    return
  fi
  if has_tty; then
    echo "$(say menu_action)" >/dev/tty
    echo "$(say menu_install)" >/dev/tty
    echo "$(say menu_remove)" >/dev/tty
    ACTION_CHOICE="$(normalize_action "$(prompt_value 'Choice [1/2, default 1]: ')")"
  else
    ACTION_CHOICE=install
  fi
}

choose_action

step() {
  idx="$1"
  total="$2"
  msg="$3"
  printf '[%s/%s] %s\n' "$idx" "$total" "$msg"
}

ensure_apk() {
  if ! command -v apk >/dev/null 2>&1; then
    echo "$(say need_apk)" >&2
    exit 1
  fi
}

copy_with_mode() {
  mode="$1"
  src="$2"
  dst="$3"
  [ -f "$src" ] || {
    echo "Source file not found: $src" >&2
    exit 1
  }
  mkdir -p "$(dirname -- "$dst")"
  cp "$src" "$dst"
  chmod "$mode" "$dst"
}

write_default_config() {
  LANG_CODE="$LANG_CHOICE" CONF_DIR="$CONF_DIR" python3 - <<'PY'
import json, os, subprocess, ipaddress
from copy import deepcopy

conf_dir = os.environ['CONF_DIR']
lang = os.environ.get('LANG_CODE', 'ru').strip().lower()
if lang not in {'ru', 'en'}:
    lang = 'ru'
config_path = os.path.join(conf_dir, 'config.json')

def run_cmd(args):
    try:
        p = subprocess.run(args, capture_output=True, text=True, timeout=4)
        return p.returncode, (p.stdout or '').strip()
    except Exception:
        return 1, ''

def normalize_net(value):
    try:
        net = ipaddress.ip_network(str(value).strip(), strict=False)
        if net.version == 4:
            return str(net)
    except Exception:
        pass
    return None

def detect_system_local_network_cidr():
    fallback = '192.168.0.0/24'
    rc, out = run_cmd(['uci', '-q', 'get', 'network.lan.ipaddr'])
    ipaddr = out if rc == 0 else ''
    rc, out = run_cmd(['uci', '-q', 'get', 'network.lan.netmask'])
    netmask = out if rc == 0 else ''
    try:
        if ipaddr:
            if '/' in ipaddr:
                return str(ipaddress.ip_interface(ipaddr).network)
            if netmask:
                return str(ipaddress.ip_network(f'{ipaddr}/{netmask}', strict=False))
            return str(ipaddress.ip_network(f'{ipaddr}/24', strict=False))
    except Exception:
        pass
    for dev in ('br-lan', 'lan'):
        rc, out = run_cmd(['ip', '-4', 'addr', 'show', 'dev', dev])
        if rc != 0 or not out:
            continue
        for line in out.splitlines():
            line = line.strip()
            if line.startswith('inet '):
                token = line.split()[1]
                try:
                    return str(ipaddress.ip_interface(token).network)
                except Exception:
                    pass
    return fallback

system_net = detect_system_local_network_cidr()
defaults = {
    'version': 1,
    'secret_key': '',
    'admin': {'username': '', 'password_hash': ''},
    'settings': {
        'bind_host': '0.0.0.0',
        'port': 1999,
        'language': lang,
        'poll_interval_ms': 1500,
        'offline_grace_sec': 120,
        'activity_total_kbps': 250,
        'local_network_cidr': system_net,
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
    settings.setdefault(key, deepcopy(value))
legacy = {'', '192.168.0.0/24'}
normalized_existing = normalize_net(settings.get('local_network_cidr', ''))
if normalized_existing is None or str(settings.get('local_network_cidr', '')).strip() in legacy:
    settings['local_network_cidr'] = system_net
else:
    settings['local_network_cidr'] = normalized_existing
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
  ensure_apk
  step 1 10 "$(say step_pkg)"
  apk update
  apk add python3 python3-flask ca-bundle nlbwmon iwinfo

  step 2 10 "$(say step_dirs)"
  mkdir -p "$APP_DIR" "$CONF_DIR"

  step 3 10 "$(say step_patch)"
  [ -f "$SCRIPT_DIR/routerdash.py" ] || { echo "$(say missing_py)" >&2; exit 1; }
  [ -f "$SCRIPT_DIR/routerdash_patch.py" ] || { echo "$(say missing_patch)" >&2; exit 1; }
  python3 "$SCRIPT_DIR/routerdash_patch.py" "$SCRIPT_DIR/routerdash.py"

  step 4 10 "$(say step_copy)"
  [ -f "$SCRIPT_DIR/routerdash.init" ] || { echo "$(say missing_init)" >&2; exit 1; }
  [ -f "$SCRIPT_DIR/blinker.py" ] || { echo "$(say missing_blinker)" >&2; exit 1; }
  copy_with_mode 0755 "$SCRIPT_DIR/routerdash.py" "$APP_DIR/routerdash.py"
  copy_with_mode 0644 "$SCRIPT_DIR/blinker.py" "$APP_DIR/blinker.py"
  copy_with_mode 0755 "$SCRIPT_DIR/routerdash.init" "$INIT_FILE"

  step 5 10 "$(say step_cfg)"
  write_default_config

  step 6 10 "$(say step_nlbw)"
  configure_nlbwmon

  step 7 10 "$(say step_enable)"
  /etc/init.d/routerdash enable >/dev/null 2>&1 || true

  step 8 10 "$(say step_start)"
  start_service_with_retry || true

  step 9 10 "$(say step_check)"
  /etc/init.d/routerdash status || true

  step 10 10 "$(say step_done)"
  LAN_IP="$(uci -q get network.lan.ipaddr || echo 192.168.1.1)"
  LAN_IP="${LAN_IP%%/*}"
  if service_running; then
    echo "$(say service_ok)"
  else
    echo "$(say service_fail)"
  fi
  printf '%s http://%s:1999\n' "$(say open)" "$LAN_IP"
  printf '%s\n' "$(say first)"
}

uninstall_routerdash() {
  if [ ! -f "$APP_DIR/routerdash.py" ] && [ ! -x "$INIT_FILE" ] && [ ! -d "$CONF_DIR" ]; then
    echo "$(say remove_missing)"
    return 0
  fi
  step 1 4 "$(say step_stop)"
  [ -x "$INIT_FILE" ] && /etc/init.d/routerdash stop >/dev/null 2>&1 || true
  step 2 4 "$(say step_disable)"
  [ -x "$INIT_FILE" ] && /etc/init.d/routerdash disable >/dev/null 2>&1 || true
  step 3 4 "$(say step_kill)"
  pkill -f '/opt/routerdash/routerdash.py' >/dev/null 2>&1 || true
  rm -f "$PID_FILE"
  step 4 4 "$(say step_rm)"
  rm -f "$INIT_FILE"
  rm -rf "$APP_DIR" "$CONF_DIR"
  echo "$(say step_removed)"
}

case "$ACTION_CHOICE" in
  uninstall) uninstall_routerdash ;;
  *) install_routerdash ;;
esac
