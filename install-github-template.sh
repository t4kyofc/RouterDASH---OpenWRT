#!/bin/sh
set -eu

ROUTERDASH_PY_URL="https://raw.githubusercontent.com/t4kyofc/RouterDASH---OpenWRT/refs/heads/main/routerdash.py"
ROUTERDASH_INIT_URL="https://raw.githubusercontent.com/t4kyofc/RouterDASH---OpenWRT/refs/heads/main/routerdash.init"
ROUTERDASH_LOCAL_INSTALL_URL="https://raw.githubusercontent.com/t4kyofc/RouterDASH---OpenWRT/refs/heads/main/install.sh"

TMP_DIR="/tmp/routerdash-install.$$"
APP_DIR=/opt/routerdash
CONF_DIR=/etc/routerdash
INIT_FILE=/etc/init.d/routerdash

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

trap 'rm -rf "$TMP_DIR"' EXIT INT TERM
mkdir -p "$TMP_DIR"
setup_colors

say() {
  key="$1"
  case "${LANG_CODE:-ru}:$key" in
    ru:title) echo "RouterDash мастер установки" ;;
    en:title) echo "RouterDash setup wizard" ;;
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
    ru:not_installed) echo "RouterDash не найден. Запускаю установку." ;;
    en:not_installed) echo "RouterDash not found. Running install." ;;
    ru:download_local) echo "Скачивание локального установщика" ;;
    en:download_local) echo "Downloading local installer" ;;
    ru:download_files) echo "Скачивание файлов RouterDash" ;;
    en:download_files) echo "Downloading RouterDash files" ;;
    ru:run_local) echo "Запуск локального установщика" ;;
    en:run_local) echo "Running local installer" ;;
    ru:done) echo "Готово" ;;
    en:done) echo "Done" ;;
    ru:no_downloader) echo "Не найден загрузчик. Установите uclient-fetch, wget или curl." ;;
    en:no_downloader) echo "No downloader found. Install uclient-fetch, wget or curl." ;;
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

err() {
  printf '%s%s%s\n' "$C_RED" "$1" "$C_RESET" >&2
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
  if ! is_installed; then
    say not_installed >&2
    echo install
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

fetch_file() {
  url="$1"
  dst="$2"
  if command -v uclient-fetch >/dev/null 2>&1; then
    uclient-fetch -O "$dst" "$url"
  elif command -v wget >/dev/null 2>&1; then
    wget -O "$dst" "$url"
  elif command -v curl >/dev/null 2>&1; then
    curl -fsSL "$url" -o "$dst"
  else
    err "$(say no_downloader)"
    exit 1
  fi
}

step 1 4 "$(say download_local)"
fetch_file "$ROUTERDASH_LOCAL_INSTALL_URL" "$TMP_DIR/install.sh"
chmod +x "$TMP_DIR/install.sh"

if [ "$ACTION" = install ] || [ "$ACTION" = reinstall ]; then
  step 2 4 "$(say download_files)"
  fetch_file "$ROUTERDASH_PY_URL" "$TMP_DIR/routerdash.py"
  fetch_file "$ROUTERDASH_INIT_URL" "$TMP_DIR/routerdash.init"
fi

step 3 4 "$(say run_local)"
cd "$TMP_DIR"
./install.sh --action="$ACTION" --lang="$LANG_CODE"

step 4 4 "$(say done)"
ok "$(say done)"
