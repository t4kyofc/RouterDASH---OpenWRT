#!/bin/sh
set -eu
BASE_URL="https://raw.githubusercontent.com/t4kyofc/RouterDASH---OpenWRT/refs/heads/main"
TMP_DIR="/tmp/routerdash-github-install"
mkdir -p "$TMP_DIR"
fetch(){
  url="$1"; out="$2"
  if command -v wget >/dev/null 2>&1; then wget -O "$out" "$url"; elif command -v uclient-fetch >/dev/null 2>&1; then uclient-fetch -O "$out" "$url"; else echo "wget/uclient-fetch not found" >&2; exit 1; fi
}
for f in install.sh routerdash.py routerdash.init blinker.py; do
  echo "Downloading $f"
  fetch "$BASE_URL/$f" "$TMP_DIR/$f"
done
chmod +x "$TMP_DIR/install.sh"
sh "$TMP_DIR/install.sh" "$@"
