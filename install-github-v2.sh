#!/bin/sh
set -eu

BASE_URL="${ROUTERDASH_BASE_URL:-https://raw.githubusercontent.com/t4kyofc/RouterDASH---OpenWRT/refs/heads/main}"
TMP_DIR="/tmp/routerdash-github-install-v2"
FILES="install-v2.sh routerdash.py routerdash.init blinker.py"

rm -rf "$TMP_DIR"
mkdir -p "$TMP_DIR"

fetch() {
  url="$1"
  out="$2"
  tmp="$out.tmp.$$"
  echo "Downloading $(basename "$out")"
  if command -v wget >/dev/null 2>&1; then
    wget --no-cache -O "$tmp" "$url"
  elif command -v uclient-fetch >/dev/null 2>&1; then
    uclient-fetch -O "$tmp" "$url"
  else
    echo "ERROR: wget/uclient-fetch not found" >&2
    exit 1
  fi
  [ -s "$tmp" ] || { echo "ERROR: downloaded file is empty: $url" >&2; rm -f "$tmp"; exit 1; }
  mv "$tmp" "$out"
}

for f in $FILES; do
  fetch "$BASE_URL/$f?v=$(date +%s)" "$TMP_DIR/$f"
done

chmod +x "$TMP_DIR/install-v2.sh"
sh "$TMP_DIR/install-v2.sh" "$@"
