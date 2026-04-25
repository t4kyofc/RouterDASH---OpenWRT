#!/bin/sh
set -u

APP_DIR="/opt/routerdash"
CONF_DIR="/etc/routerdash"
INIT_FILE="/etc/init.d/routerdash"
PID_FILE="/var/run/routerdash.pid"
SCRIPT_DIR="$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)"

LANG_CHOICE=""
ACTION_CHOICE=""

is_interactive() {
  [ -t 0 ] || { [ -r /dev/tty ] && [ -w /dev/tty ]; }
}

prompt_value() {
  prompt="$1"
  answer=""
  if [ -t 0 ]; then
    printf '%s' "$prompt"
    IFS= read -r answer || answer=""
  elif [ -r /dev/tty ] && [ -w /dev/tty ]; then
    printf '%s' "$prompt" >/dev/tty
    IFS= read -r answer </dev/tty || answer=""
  else
    answer=""
  fi
  printf '%s' "$answer"
}

lower_trim() {
  printf '%s' "$1" | tr '[:upper:]' '[:lower:]' | sed 's/^[[:space:]]*//;s/[[:space:]]*$//'
}

normalize_lang() {
  case "$(lower_trim "$1")" in
    2|en|eng|english) echo en ;;
    *) echo ru ;;
  esac
}

normalize_action() {
  case "$(lower_trim "$1")" in
    2|remove|delete|uninstall|--remove|--uninstall|--action=uninstall|--action=remove) echo uninstall ;;
    3|reinstall|clean|clean-reinstall|--reinstall|--clean-reinstall|--action=reinstall) echo reinstall ;;
    *) echo install ;;
  esac
}

for arg in "$@"; do
  case "$arg" in
    --lang=*) LANG_CHOICE="$(normalize_lang "${arg#--lang=}")" ;;
    --action=*) ACTION_CHOICE="$(normalize_action "$arg")" ;;
    en|english|ru|russian|1|2)
      [ -z "$LANG_CHOICE" ] && LANG_CHOICE="$(normalize_lang "$arg")"
      ;;
    install|update|uninstall|remove|delete|reinstall|clean|clean-reinstall|3)
      ACTION_CHOICE="$(normalize_action "$arg")"
      ;;
  esac
done

choose_lang() {
  [ -n "$LANG_CHOICE" ] && return 0
  if is_interactive; then
    echo "Select installation language / Выберите язык установки"
    echo "  1) Русский"
    echo "  2) English"
    LANG_CHOICE="$(normalize_lang "$(prompt_value 'Choice [1/2, default 1]: ')")"
    echo ""
  else
    LANG_CHOICE="ru"
  fi
}

choose_action() {
  [ -n "$ACTION_CHOICE" ] && return 0
  if is_interactive; then
    if [ "$LANG_CHOICE" = "en" ]; then
      echo "Choose action"
      echo "  1) Install / update        - keep existing settings"
      echo "  2) Remove RouterDash       - remove app and config"
      echo "  3) Clean reinstall         - remove app/config and install again"
    else
      echo "Выберите действие"
      echo "  1) Установить / обновить   - сохранить текущие настройки"
      echo "  2) Удалить RouterDash      - удалить приложение и конфиг"
      echo "  3) Переустановить начисто  - удалить всё и установить заново"
    fi
    ACTION_CHOICE="$(normalize_action "$(prompt_value 'Choice [1/2/3, default 1]: ')")"
    echo ""
  else
    ACTION_CHOICE="install"
  fi
}

choose_lang
choose_action

say() {
  key="$1"
  case "$LANG_CHOICE:$key" in
    ru:need_apk) echo "Требуется OpenWrt 25.12+ с apk." ;;
    en:need_apk) echo "OpenWrt 25.12+ with apk is required." ;;
    ru:apk_locked) echo "База apk занята другим процессом." ;;
    en:apk_locked) echo "The apk database is locked by another process." ;;
    ru:step_check) echo "Проверка файлов и окружения" ;;
    en:step_check) echo "Checking files and environment" ;;
    ru:step_pkg) echo "Установка и проверка зависимостей" ;;
    en:step_pkg) echo "Installing and checking dependencies" ;;
    ru:step_copy) echo "Копирование файлов" ;;
    en:step_copy) echo "Copying files" ;;
    ru:step_cfg) echo "Подготовка конфигурации" ;;
    en:step_cfg) echo "Preparing configuration" ;;
    ru:step_nlbw) echo "Настройка nlbwmon" ;;
    en:step_nlbw) echo "Configuring nlbwmon" ;;
    ru:step_start) echo "Запуск сервиса" ;;
    en:step_start) echo "Starting service" ;;
    ru:step_done) echo "Готово" ;;
    en:step_done) echo "Done" ;;
    ru:step_stop) echo "Остановка сервиса" ;;
    en:step_stop) echo "Stopping service" ;;
    ru:step_disable) echo "Отключение автозапуска" ;;
    en:step_disable) echo "Disabling autostart" ;;
    ru:step_clean) echo "Очистка процессов и PID" ;;
    en:step_clean) echo "Cleaning processes and PID" ;;
    ru:step_remove) echo "Удаление файлов" ;;
    en:step_remove) echo "Removing files" ;;
    ru:removed) echo "RouterDash удалён полностью" ;;
    en:removed) echo "RouterDash removed completely" ;;
    ru:missing_file) echo "Не найден обязательный файл" ;;
    en:missing_file) echo "Required file not found" ;;
    ru:open) echo "Откройте в браузере" ;;
    en:open) echo "Open in browser" ;;
    ru:first) echo "При первом открытии панель предложит создать логин и пароль." ;;
    en:first) echo "On first open, the panel will ask you to create username and password." ;;
    ru:service_fail) echo "Сервис не запущен. Проверьте логи: logread -e routerdash" ;;
    en:service_fail) echo "Service is not running. Check logs: logread -e routerdash" ;;
    *) echo "$key" ;;
  esac
}

step() {
  idx="$1"
  total="$2"
  msg="$3"
  printf '[%s/%s] %s\n' "$idx" "$total" "$msg"
}

die() {
  echo "ERROR: $*" >&2
  exit 1
}

warn() {
  echo "WARNING: $*" >&2
}

require_file() {
  f="$1"
  [ -f "$f" ] || die "$(say missing_file): $f"
}

copy_with_mode() {
  mode="$1"
  src="$2"
  dst="$3"
  tmp="$dst.tmp.$$"
  require_file "$src"
  mkdir -p "$(dirname -- "$dst")" || die "mkdir failed: $(dirname -- "$dst")"
  cp "$src" "$tmp" || die "copy failed: $src -> $dst"
  chmod "$mode" "$tmp" || die "chmod failed: $tmp"
  mv "$tmp" "$dst" || die "move failed: $tmp -> $dst"
}

apk_processes() {
  ps w 2>/dev/null | grep -E '[ /](apk|opkg)( |$)' | grep -v grep || true
}

apk_run() {
  label="$1"
  shift
  tmp="/tmp/routerdash-apk.$$.log"
  tries=0
  max_tries=30
  while [ "$tries" -lt "$max_tries" ]; do
    if "$@" >"$tmp" 2>&1; then
      cat "$tmp"
      rm -f "$tmp"
      return 0
    fi
    if grep -qiE 'lock database|temporarily unavailable|Failed to open apk database' "$tmp" 2>/dev/null; then
      if [ "$tries" -eq 0 ]; then
        echo "$(say apk_locked) Жду освобождения lock: $label" >&2
        apk_processes >&2
      fi
      sleep 2
      tries=$((tries + 1))
      continue
    fi
    cat "$tmp" >&2
    rm -f "$tmp"
    return 1
  done
  cat "$tmp" >&2
  rm -f "$tmp"
  echo "ERROR: $(say apk_locked)" >&2
  echo "Fix:" >&2
  echo "  jobs -l" >&2
  echo "  kill %1" >&2
  echo "  ps w | grep apk" >&2
  echo "  kill <PID>" >&2
  return 1
}

check_files() {
  require_file "$SCRIPT_DIR/routerdash.py"
  require_file "$SCRIPT_DIR/routerdash.init"
  require_file "$SCRIPT_DIR/blinker.py"
}

install_packages() {
  command -v apk >/dev/null 2>&1 || die "$(say need_apk)"
  apk_run "apk update" apk update || die "apk update failed"
  apk_run "required packages" apk add python3 python3-flask ca-bundle nlbwmon iwinfo || die "apk add required packages failed"
  apk_run "optional network tools" apk add ip-full bridge-utils >/dev/null 2>&1 || true

  command -v python3 >/dev/null 2>&1 || die "python3 not found after install"
  python3 - <<'PY' || exit 1
import flask
PY
  [ $? -eq 0 ] || die "python3-flask is not importable"

  [ -x /etc/init.d/nlbwmon ] || die "nlbwmon init script not found"
  command -v iwinfo >/dev/null 2>&1 || warn "iwinfo command not found; Wi-Fi client detection can be limited"
  command -v ip >/dev/null 2>&1 || die "ip command not found"
  command -v ping >/dev/null 2>&1 || die "ping command not found"
  command -v ubus >/dev/null 2>&1 || warn "ubus command not found; Wi-Fi detection can be limited"
}

write_default_config() {
  LANG_CODE="$LANG_CHOICE" CONF_DIR="$CONF_DIR" python3 - <<'PY'
import json
import os
import secrets
import subprocess
import ipaddress

conf_dir = os.environ["CONF_DIR"]
lang = os.environ.get("LANG_CODE", "ru").strip().lower()
if lang not in {"ru", "en"}:
    lang = "ru"
config_path = os.path.join(conf_dir, "config.json")

def run_cmd(args):
    try:
        p = subprocess.run(args, capture_output=True, text=True, timeout=4)
        return p.returncode, (p.stdout or "").strip()
    except Exception:
        return 1, ""

def detect_system_local_network_cidr():
    fallback = "192.168.0.0/24"
    rc, out = run_cmd(["uci", "-q", "get", "network.lan.ipaddr"])
    ipaddr = out if rc == 0 else ""
    rc, out = run_cmd(["uci", "-q", "get", "network.lan.netmask"])
    netmask = out if rc == 0 else ""
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
        rc, out = run_cmd(["ip", "-4", "addr", "show", "dev", dev])
        if rc != 0 or not out:
            continue
        for line in out.splitlines():
            line = line.strip()
            if line.startswith("inet "):
                token = line.split()[1]
                try:
                    return str(ipaddress.ip_interface(token).network)
                except Exception:
                    pass
    return fallback

def load_config(path):
    if not os.path.exists(path):
        return {}
    try:
        with open(path, "r", encoding="utf-8") as fh:
            data = json.load(fh)
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}

system_net = detect_system_local_network_cidr()
data = load_config(config_path)
data.setdefault("version", 2)
data.setdefault("secret_key", secrets.token_hex(32))
data.setdefault("admin", {"username": "", "password_hash": ""})
settings = data.setdefault("settings", {})
defaults = {
    "bind_host": "0.0.0.0",
    "port": 1999,
    "language": lang,
    "poll_interval_ms": 1500,
    "offline_grace_sec": 120,
    "presence_probe_cooldown_sec": 20,
    "activity_total_kbps": 250,
    "local_network_cidr": system_net,
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
for key, value in defaults.items():
    settings.setdefault(key, value)
settings["language"] = lang
if str(settings.get("local_network_cidr", "")).strip() in {"", "192.168.0.0/24"}:
    settings["local_network_cidr"] = system_net
os.makedirs(conf_dir, exist_ok=True)
with open(config_path, "w", encoding="utf-8") as fh:
    json.dump(data, fh, ensure_ascii=False, indent=2, sort_keys=True)
PY
}

configure_nlbwmon() {
  if command -v uci >/dev/null 2>&1; then
    if ! uci -q get nlbwmon.@nlbwmon[0] >/dev/null 2>&1; then
      uci add nlbwmon nlbwmon >/dev/null 2>&1 || true
    fi
    uci -q del_list nlbwmon.@nlbwmon[0].local_network='lan' >/dev/null 2>&1 || true
    uci add_list nlbwmon.@nlbwmon[0].local_network='lan' >/dev/null 2>&1 || true
    uci set nlbwmon.@nlbwmon[0].refresh_interval='30s' >/dev/null 2>&1 || true
    uci set nlbwmon.@nlbwmon[0].database_directory='/var/lib/nlbwmon' >/dev/null 2>&1 || true
    uci commit nlbwmon >/dev/null 2>&1 || true
  fi
  /etc/init.d/nlbwmon enable >/dev/null 2>&1 || true
  /etc/init.d/nlbwmon restart >/dev/null 2>&1 || true
}

service_running() {
  if [ -x "$INIT_FILE" ] && "$INIT_FILE" status 2>/dev/null | grep -qi running; then
    return 0
  fi
  ps w 2>/dev/null | grep -F '/opt/routerdash/routerdash.py' | grep -v grep >/dev/null 2>&1
}

start_routerdash_service() {
  [ -x "$INIT_FILE" ] || return 1
  "$INIT_FILE" enable >/dev/null 2>&1 || true
  "$INIT_FILE" stop >/dev/null 2>&1 || true
  rm -f "$PID_FILE"
  "$INIT_FILE" start >/dev/null 2>&1 || true
  i=0
  while [ "$i" -lt 8 ]; do
    service_running && return 0
    sleep 1
    i=$((i + 1))
  done
  return 1
}

remove_routerdash() {
  step 1 4 "$(say step_stop)"
  [ -x "$INIT_FILE" ] && "$INIT_FILE" stop >/dev/null 2>&1 || true
  step 2 4 "$(say step_disable)"
  [ -x "$INIT_FILE" ] && "$INIT_FILE" disable >/dev/null 2>&1 || true
  step 3 4 "$(say step_clean)"
  if command -v pkill >/dev/null 2>&1; then
    pkill -f '/opt/routerdash/routerdash.py' >/dev/null 2>&1 || true
  fi
  rm -f "$PID_FILE"
  step 4 4 "$(say step_remove)"
  rm -f "$INIT_FILE"
  rm -rf "$APP_DIR" "$CONF_DIR"
  echo "$(say removed)"
}

do_install() {
  step 1 6 "$(say step_check)"
  check_files
  step 2 6 "$(say step_pkg)"
  install_packages
  step 3 6 "$(say step_copy)"
  mkdir -p "$APP_DIR" "$CONF_DIR" || die "mkdir failed"
  copy_with_mode 0755 "$SCRIPT_DIR/routerdash.py" "$APP_DIR/routerdash.py"
  copy_with_mode 0644 "$SCRIPT_DIR/blinker.py" "$APP_DIR/blinker.py"
  copy_with_mode 0755 "$SCRIPT_DIR/routerdash.init" "$INIT_FILE"
  step 4 6 "$(say step_cfg)"
  write_default_config || die "config preparation failed"
  step 5 6 "$(say step_nlbw) / $(say step_start)"
  configure_nlbwmon
  start_routerdash_service || die "$(say service_fail)"
  step 6 6 "$(say step_done)"
  LAN_IP="$(uci -q get network.lan.ipaddr 2>/dev/null || echo 192.168.1.1)"
  LAN_IP="${LAN_IP%%/*}"
  echo "$(say open): http://$LAN_IP:1999"
  echo "$(say first)"
}

case "$ACTION_CHOICE" in
  uninstall)
    remove_routerdash
    ;;
  reinstall)
    remove_routerdash
    do_install
    ;;
  *)
    do_install
    ;;
esac
