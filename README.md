# RouterDash for OpenWrt

Fixed installer bundle.

## What changed

- the GitHub installer now works in a strict sequence:
  1. choose language
  2. on that language choose action: install or remove
  3. run the selected action
- files are downloaded into `/opt/routerdash-installer`
- permissions are applied before launch
- the downloaded `routerdash.py` is patched before install
- local `blinker.py` is included for OpenWrt builds without `python3-blinker`
- IPv4 display is fixed with a private-IPv4 fallback when network filtering would otherwise hide all addresses
- if config still contains the old `192.168.0.0/24` while the real LAN is different, the detected LAN network is used automatically

## Install

```sh
wget -O /tmp/routerdash-installer.sh https://raw.githubusercontent.com/t4kyofc/RouterDASH---OpenWRT/refs/heads/main/install-github-template.sh && sh /tmp/routerdash-installer.sh
```

## Recommended after applying these changes

Remove and install again through the new launcher.
