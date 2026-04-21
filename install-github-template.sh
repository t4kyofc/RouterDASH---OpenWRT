#!/bin/sh
set -eu

REPO_BASE="https://raw.githubusercontent.com/t4kyofc/RouterDASH---OpenWRT/refs/heads/main"
ROUTERDASH_PY_URL="$REPO_BASE/routerdash.py"
ROUTERDASH_INIT_URL="$REPO_BASE/routerdash.init"
ROUTERDASH_LOCAL_INSTALL_URL="$REPO_BASE/install.sh"
ROUTERDASH_BLINKER_URL="$REPO_BASE/blinker.py"

STAGE_DIR=/opt/routerdash-installer
LANG_CHOICE="${ROUTERDASH_LANG:-}"
ACTION_CHOICE="${ROUTERDASH_ACTION:-install}"

has_tty() {
  [ -t 1 ] && [ -r /dev/tty ] && [ -w /dev/tty ]
}

setup_colors() {
  if has_tty; then
    C_RESET="$(printf '\033[0m')"
    C_RED="$(printf '\033[31m')"
    C_GREEN="$(printf '\033[32m')"
    C_BLUE="$(printf '\033[34m')"
    C_CYAN="$(printf '\033[36m')"
    C_BOLD="$(printf '\033[1m')"
  else
    C_RESET=''
    C_RED=''
    C_GREEN=''
    C_BLUE=''
    C_CYAN=''
    C_BOLD=''
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
    3|reinstall) echo reinstall ;;
    4|status) echo status ;;
    *) echo install ;;
  esac
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

for arg in "$@"; do
  case "$arg" in
    ru|RU|en|EN|eng|ENG|english|English|1|2)
      [ -n "$LANG_CHOICE" ] || LANG_CHOICE="$arg"
      ;;
    install|INSTALL|update|UPDATE|remove|REMOVE|delete|DELETE|uninstall|UNINSTALL|reinstall|REINSTALL|status|STATUS)
      ACTION_CHOICE="$arg"
      ;;
    --lang=*) LANG_CHOICE="${arg#--lang=}" ;;
    --action=*) ACTION_CHOICE="${arg#--action=}" ;;
  esac
done

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
ACTION="$(normalize_action "$ACTION_CHOICE")"
export ROUTERDASH_LANG="$LANG_CODE"
export ROUTERDASH_ACTION="$ACTION"

say() {
  key="$1"
  case "${LANG_CODE}:$key" in
    ru:title) echo "RouterDash GitHub-установщик" ;;
    en:title) echo "RouterDash GitHub installer" ;;
    ru:stage) echo "Подготовка каталога /opt для скачивания" ;;
    en:stage) echo "Preparing /opt staging directory" ;;
    ru:download) echo "Скачивание файлов RouterDash в /opt" ;;
    en:download) echo "Downloading RouterDash files to /opt" ;;
    ru:chmod) echo "Применение прав доступа" ;;
    en:chmod) echo "Applying file permissions" ;;
    ru:run) echo "Запуск локального установщика" ;;
    en:run) echo "Starting local installer" ;;
    ru:no_downloader) echo "Не найден загрузчик. Установите uclient-fetch, wget или curl." ;;
    en:no_downloader) echo "No downloader found. Install uclient-fetch, wget or curl." ;;
    ru:done) echo "Готово" ;;
    en:done) echo "Done" ;;
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

err() {
  printf '%s%s%s\n' "$C_RED" "$1" "$C_RESET" >&2
}

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

  if [ ! -s "$dst" ]; then
    err "Downloaded file is empty: $dst"
    exit 1
  fi
}

setup_colors
print_banner

step 1 4 "$(say stage)"
rm -rf "$STAGE_DIR"
mkdir -p "$STAGE_DIR"

step 2 4 "$(say download)"
fetch_file "$ROUTERDASH_LOCAL_INSTALL_URL" "$STAGE_DIR/install.sh"
fetch_file "$ROUTERDASH_PY_URL" "$STAGE_DIR/routerdash.py"
fetch_file "$ROUTERDASH_INIT_URL" "$STAGE_DIR/routerdash.init"
fetch_file "$ROUTERDASH_BLINKER_URL" "$STAGE_DIR/blinker.py"

step 3 4 "$(say chmod)"
chmod 0755 "$STAGE_DIR/install.sh" "$STAGE_DIR/routerdash.py" "$STAGE_DIR/routerdash.init"
chmod 0644 "$STAGE_DIR/blinker.py"

step 4 4 "$(say run)"
cd "$STAGE_DIR"
exec ./install.sh --lang="$LANG_CODE" --action="$ACTION"
