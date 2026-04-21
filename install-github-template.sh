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

for arg in "$@"; do
  case "$arg" in
    ru|RU|en|EN|eng|ENG|english|English|1|2)
      if [ -z "$LANG_CHOICE" ]; then
        LANG_CHOICE="$arg"
      fi
      ;;
    install|INSTALL|update|UPDATE|remove|REMOVE|delete|DELETE|uninstall|UNINSTALL|reinstall|REINSTALL|status|STATUS|1|2|3|4)
      if [ -z "$ACTION_CHOICE" ]; then
        ACTION_CHOICE="$arg"
      fi
      ;;
    --lang=*) LANG_CHOICE="${arg#--lang=}" ;;
    --action=*) ACTION_CHOICE="${arg#--action=}" ;;
  esac
done

trap 'rm -rf "$TMP_DIR"' EXIT INT TERM
mkdir -p "$TMP_DIR"

has_tty() {
  [ -r /dev/tty ] && [ -w /dev/tty ]
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
    2|en|eng|english) echo "en" ;;
    *) echo "ru" ;;
  esac
}

normalize_action() {
  case "$(normalize_text "$1")" in
    2|remove|delete|uninstall) echo "uninstall" ;;
    3|reinstall) echo "reinstall" ;;
    4|status) echo "status" ;;
    *) echo "install" ;;
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
    ru:title) echo "RouterDash мастер установки" ;;
    en:title) echo "RouterDash setup wizard" ;;
    ru:menu_action) echo "Выберите действие" ;;
    en:menu_action) echo "Choose action" ;;
    ru:menu_install) echo "  1) Установить / обновить" ;;
    en:menu_install) echo "  1) Install / update" ;;
    ru:menu_remove) echo "  2) Удалить RouterDash" ;;
    en:menu_remove) echo "  2) Remove RouterDash" ;;
    ru:menu_reinstall) echo "  3) Переустановить RouterDash" ;;
    en:menu_reinstall) echo "  3) Reinstall RouterDash" ;;
    ru:menu_status) echo "  4) Показать статус" ;;
    en:menu_status) echo "  4) Show status" ;;
    ru:already_installed) echo "RouterDash уже установлен." ;;
    en:already_installed) echo "RouterDash is already installed." ;;
    ru:default_install) echo "По умолчанию: установка." ;;
    en:default_install) echo "Default action: install." ;;
    ru:not_installed_install) echo "RouterDash не найден. Будет выполнена установка." ;;
    en:not_installed_install) echo "RouterDash not found. Installation will be performed." ;;
    ru:step1) echo "[1/4] Скачивание установщика..." ;;
    en:step1) echo "[1/4] Downloading local installer..." ;;
    ru:step2) echo "[2/4] Скачивание файлов RouterDash..." ;;
    en:step2) echo "[2/4] Downloading RouterDash files..." ;;
    ru:step3) echo "[3/4] Запуск установщика..." ;;
    en:step3) echo "[3/4] Running installer..." ;;
    ru:step4) echo "[4/4] Готово." ;;
    en:step4) echo "[4/4] Done." ;;
    ru:no_downloader) echo "Не найден загрузчик. Установите uclient-fetch, wget или curl." ;;
    en:no_downloader) echo "No downloader found. Install uclient-fetch, wget, or curl." ;;
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
    say title >/dev/tty
    say already_installed >/dev/tty
    say menu_action >/dev/tty
    say menu_install >/dev/tty
    say menu_remove >/dev/tty
    say menu_reinstall >/dev/tty
    say menu_status >/dev/tty
    answer="$(prompt_value 'Choice [1/2/3/4, default 1]: ')"
    normalize_action "$answer"
    return
  fi

  say default_install >&2
  echo "install"
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
    say no_downloader
    exit 1
  fi
}

say step1
fetch_file "$ROUTERDASH_LOCAL_INSTALL_URL" "$TMP_DIR/install.sh"
chmod +x "$TMP_DIR/install.sh"

if [ "$ACTION" = "install" ] || [ "$ACTION" = "reinstall" ]; then
  say step2
  fetch_file "$ROUTERDASH_PY_URL" "$TMP_DIR/routerdash.py"
  fetch_file "$ROUTERDASH_INIT_URL" "$TMP_DIR/routerdash.init"
fi

say step3
cd "$TMP_DIR"
./install.sh --action="$ACTION" --lang="$LANG_CODE"

say step4
