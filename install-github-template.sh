#!/bin/sh
set -eu

# Replace placeholders below after publishing the repository.
ROUTERDASH_PY_URL="https://raw.githubusercontent.com/t4kyofc/RouterDASH---OpenWRT/refs/heads/main/routerdash.py"
ROUTERDASH_INIT_URL="https://raw.githubusercontent.com/t4kyofc/RouterDASH---OpenWRT/refs/heads/main/routerdash.init"
ROUTERDASH_LOCAL_INSTALL_URL="https://raw.githubusercontent.com/t4kyofc/RouterDASH---OpenWRT/refs/heads/main/install.sh"

TMP_DIR="/tmp/routerdash-install.$$"
LANG_CHOICE="${ROUTERDASH_LANG:-}"
trap 'rm -rf "$TMP_DIR"' EXIT INT TERM
mkdir -p "$TMP_DIR"

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
export ROUTERDASH_LANG="$LANG_CODE"

fetch_file() {
  url="$1"
  dst="$2"

  case "$url" in
    __*__)
      echo "Placeholder URL is still set: $url"
      exit 1
      ;;
  esac

  if command -v uclient-fetch >/dev/null 2>&1; then
    uclient-fetch -O "$dst" "$url"
  elif command -v wget >/dev/null 2>&1; then
    wget -O "$dst" "$url"
  elif command -v curl >/dev/null 2>&1; then
    curl -fsSL "$url" -o "$dst"
  else
    echo "No download tool found. Install uclient-fetch, wget, or curl."
    exit 1
  fi
}

echo "[1/3] Downloading RouterDash files..."
fetch_file "$ROUTERDASH_PY_URL" "$TMP_DIR/routerdash.py"
fetch_file "$ROUTERDASH_INIT_URL" "$TMP_DIR/routerdash.init"
fetch_file "$ROUTERDASH_LOCAL_INSTALL_URL" "$TMP_DIR/install.sh"
chmod +x "$TMP_DIR/install.sh"

echo "[2/3] Starting local installer..."
cd "$TMP_DIR"
./install.sh

echo "[3/3] Finished."
