#!/bin/sh
set -eu

REPO_BASE="https://raw.githubusercontent.com/t4kyofc/RouterDASH---OpenWRT/refs/heads/main"
FILES="install.sh routerdash.py routerdash.init blinker.py routerdash_patch.py README.md README_ru.md"
STAGE_DIR="/opt/routerdash-installer"

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

say() {
  key="$1"
  case "${LANG_CHOICE:-ru}:$key" in
    ru:title) echo "RouterDash GitHub установщик" ;;
    en:title) echo "RouterDash GitHub installer" ;;
    ru:lang_title) echo "Выберите язык установки" ;;
    en:lang_title) echo "Select installation language" ;;
    ru:lang_ru) echo "  1) Русский" ;;
    en:lang_ru) echo "  1) Russian" ;;
    ru:lang_en) echo "  2) English" ;;
    en:lang_en) echo "  2) English" ;;
    ru:action_title) echo "Выберите действие" ;;
    en:action_title) echo "Choose action" ;;
    ru:action_install) echo "  1) Установить / обновить" ;;
    en:action_install) echo "  1) Install / update" ;;
    ru:action_remove) echo "  2) Удалить RouterDash" ;;
    en:action_remove) echo "  2) Remove RouterDash" ;;
    ru:step_stage) echo "Подготовка каталога /opt/routerdash-installer" ;;
    en:step_stage) echo "Preparing /opt/routerdash-installer directory" ;;
    ru:step_download) echo "Скачивание файлов проекта в /opt/routerdash-installer" ;;
    en:step_download) echo "Downloading project files into /opt/routerdash-installer" ;;
    ru:step_chmod) echo "Применение прав доступа" ;;
    en:step_chmod) echo "Applying file permissions" ;;
    ru:step_run) echo "Запуск локального установщика" ;;
    en:step_run) echo "Running local installer" ;;
    ru:no_downloader) echo "Не найден загрузчик. Установите uclient-fetch, wget или curl." ;;
    en:no_downloader) echo "No downloader found. Install uclient-fetch, wget or curl." ;;
    *) echo "$key" ;;
  esac
}

step() {
  idx="$1"
  total="$2"
  msg="$3"
  printf '[%s/%s] %s\n' "$idx" "$total" "$msg"
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
    echo "$(say no_downloader)" >&2
    exit 1
  fi
  if [ ! -s "$dst" ]; then
    echo "Downloaded file is empty: $dst" >&2
    exit 1
  fi
}

choose_lang() {
  if [ -n "$LANG_CHOICE" ]; then
    return
  fi
  if has_tty; then
    echo "$(say lang_title)" >/dev/tty
    echo "$(say lang_ru)" >/dev/tty
    echo "$(say lang_en)" >/dev/tty
    LANG_CHOICE="$(normalize_lang "$(prompt_value 'Choice [1/2, default 1]: ')")"
  else
    LANG_CHOICE=ru
  fi
}

choose_action() {
  if [ -n "$ACTION_CHOICE" ]; then
    return
  fi
  if has_tty; then
    echo "$(say action_title)" >/dev/tty
    echo "$(say action_install)" >/dev/tty
    echo "$(say action_remove)" >/dev/tty
    ACTION_CHOICE="$(normalize_action "$(prompt_value 'Choice [1/2, default 1]: ')")"
  else
    ACTION_CHOICE=install
  fi
}

for arg in "$@"; do
  case "$arg" in
    --lang=*) LANG_CHOICE="$(normalize_lang "${arg#--lang=}")" ;;
    --action=*) ACTION_CHOICE="$(normalize_action "${arg#--action=}")" ;;
  esac
done

choose_lang
choose_action

step 1 4 "$(say step_stage)"
mkdir -p "$STAGE_DIR"

step 2 4 "$(say step_download)"
for file in $FILES; do
  fetch_file "$REPO_BASE/$file" "$STAGE_DIR/$file"
done

step 3 4 "$(say step_chmod)"
chmod 0755 "$STAGE_DIR/install.sh" "$STAGE_DIR/routerdash.py" "$STAGE_DIR/routerdash.init"
chmod 0644 "$STAGE_DIR/blinker.py" "$STAGE_DIR/routerdash_patch.py" "$STAGE_DIR/README.md" "$STAGE_DIR/README_ru.md"

step 4 4 "$(say step_run)"
cd "$STAGE_DIR"
exec ./install.sh --lang="$LANG_CHOICE" --action="$ACTION_CHOICE"
