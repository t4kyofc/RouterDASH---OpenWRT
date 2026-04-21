#!/bin/sh
set -eu

REPO_BASE="https://raw.githubusercontent.com/t4kyofc/RouterDASH---OpenWRT/refs/heads/main"
ROUTERDASH_PY_URL="$REPO_BASE/routerdash.py"
ROUTERDASH_INIT_URL="$REPO_BASE/routerdash.init"
ROUTERDASH_LOCAL_INSTALL_URL="$REPO_BASE/install.sh"
ROUTERDASH_BLINKER_URL="$REPO_BASE/blinker.py"

STAGE_DIR=/opt/routerdash-installer

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

say() {
  key="$1"
  case "$key" in
    title) echo "RouterDash GitHub installer" ;;
    stage) echo "Preparing /opt staging directory" ;;
    download) echo "Downloading RouterDash files to /opt" ;;
    chmod) echo "Applying execute permissions" ;;
    run) echo "Starting local installer" ;;
    done) echo "Done" ;;
    no_downloader) echo "No downloader found. Install uclient-fetch, wget or curl." ;;
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
exec ./install.sh "$@"
