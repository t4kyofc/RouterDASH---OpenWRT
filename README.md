<p align="center">
  <b>English documentation</b> · <a href="./README_ru.md"><b>Русская документация</b></a>
</p>

# RouterDash for OpenWrt

Adapted installer bundle for `t4kyofc/RouterDASH---OpenWRT`.

## What changed

- the GitHub launcher now **downloads files to `/opt/routerdash-installer` first**
- after download it applies the required `chmod`
- then it starts the local `install.sh`
- the local installer **asks for language first**, then shows the action menu in that language
- a local `blinker.py` fallback was added so RouterDash can run on OpenWrt builds where `python3-blinker` is not available

## Included files

- `install-github-template.sh`
- `install.sh`
- `blinker.py`
- `routerdash.init`
- `README.md`
- `README_ru.md`

## Quick install from GitHub

```sh
wget -O /tmp/routerdash-installer.sh https://raw.githubusercontent.com/t4kyofc/RouterDASH---OpenWRT/refs/heads/main/install-github-template.sh && sh /tmp/routerdash-installer.sh
```

What happens:

1. `/opt/routerdash-installer` is created
2. `install.sh`, `routerdash.py`, `routerdash.init`, and `blinker.py` are downloaded there
3. `chmod 0755` is applied to `install.sh`, `routerdash.py`, and `routerdash.init`
4. the local `install.sh` is started
5. the local installer asks for language
6. the selected-language action menu is shown

## Local install

If the files are already present in `/opt/routerdash-installer` or another directory:

```sh
cd /opt/routerdash-installer
sh ./install.sh
```

## Non-interactive usage

```sh
sh ./install.sh --lang=en --action=install
sh ./install.sh --lang=en --action=uninstall
sh ./install.sh --lang=en --action=reinstall
sh ./install.sh --lang=en --action=status
```

## Installed paths

- application: `/opt/routerdash/routerdash.py`
- local Flask signals fallback: `/opt/routerdash/blinker.py`
- config: `/etc/routerdash/config.json`
- service: `/etc/init.d/routerdash`

## Packages

The installer installs:

- `python3`
- `python3-flask`
- `ca-bundle`
- `nlbwmon`
- `iwinfo`

The `python3-blinker` package is **not required**, because the project uses the local `blinker.py` fallback.

## Repository replacement

Replace at least these files in the repository:

- `install-github-template.sh`
- `install.sh`
- add the new `blinker.py`
- optionally update `README.md` and `README_ru.md`
