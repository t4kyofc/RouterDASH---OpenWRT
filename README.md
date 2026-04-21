<p align="center">
  <img src="./docs/preview.png" alt="RouterDash preview" width="100%">
</p>

<p align="center">
  <b>Open-source dashboard for OpenWrt</b><br>
  Мониторинг устройств, скорости, соединений, активности и Telegram-уведомления.<br>
  Device monitoring, live speed, connections, activity, and Telegram notifications.
</p>

<p align="center">
  <img alt="OpenWrt" src="https://img.shields.io/badge/OpenWrt-25.12+-00B5E2?style=for-the-badge">
  <img alt="Python" src="https://img.shields.io/badge/Python-3-orange?style=for-the-badge">
  <img alt="Flask" src="https://img.shields.io/badge/Flask-Web_UI-black?style=for-the-badge">
  <img alt="License" src="https://img.shields.io/badge/License-MIT-success?style=for-the-badge">
</p>

## RouterDash

**RouterDash** is a lightweight OpenWrt web dashboard that shows devices in the network, live speed, active connections, online history, and Telegram notifications.

**RouterDash** — лёгкая веб-панель для OpenWrt, которая показывает устройства в сети, текущую скорость, активные соединения, историю присутствия и Telegram-уведомления.

The project runs directly on the router and uses standard OpenWrt components: `nlbwmon`, `ubus`, DHCP leases, and `ip neigh`.

## Features / Возможности

- RU/EN interface with a language selector in the bottom-right corner;
- safe default settings for low-power devices;
- default local network: `192.168.0.0/24`;
- per-device live download/upload speed;
- active connection counters and destination details;
- online / idle / offline detection;
- history log overlay;
- Telegram notifications for selected devices;
- first-run admin setup from the web UI.

## Requirements / Требования

- **OpenWrt 25.12+**
- **apk** package manager
- SSH access to the router
- internet access for GitHub-based installation

## Quick install / Быстрая установка

Recommended one-liner:

```sh
wget -O /tmp/routerdash-installer.sh https://raw.githubusercontent.com/t4kyofc/RouterDASH---OpenWRT/refs/heads/main/install-github-template.sh && sh /tmp/routerdash-installer.sh
```

Alternative for systems with `uclient-fetch`:

```sh
uclient-fetch -O /tmp/routerdash-installer.sh https://raw.githubusercontent.com/t4kyofc/RouterDASH---OpenWRT/refs/heads/main/install-github-template.sh && sh /tmp/routerdash-installer.sh
```

What the installer does:

1. asks for language first: **Русский** or **English**;
2. if RouterDash is already installed, offers **install/update**, **remove**, or **reinstall**;
3. downloads the required files from GitHub;
4. installs packages and enables the service;
5. saves the chosen interface language as the default in RouterDash.

> Do not use `sh <(wget -O - ...)` as the primary README command. On many systems stdin gets occupied by the script body, which breaks interactive prompts. The new installer is compatible with direct file execution and is safer for OpenWrt.

## Manual local install / Локальная установка

```sh
scp install.sh routerdash.py routerdash.init root@192.168.1.1:/tmp/routerdash/
ssh root@192.168.1.1
cd /tmp/routerdash
chmod +x install.sh
./install.sh
```

You can also pass arguments:

```sh
./install.sh install en
./install.sh uninstall ru
./install.sh reinstall en
./install.sh status
```

## Remove RouterDash / Удаление

Remote uninstall from GitHub installer:

```sh
wget -O /tmp/routerdash-installer.sh https://raw.githubusercontent.com/t4kyofc/RouterDASH---OpenWRT/refs/heads/main/install-github-template.sh && sh /tmp/routerdash-installer.sh uninstall
```

Or locally:

```sh
./install.sh uninstall
```

Removal deletes:

- `/opt/routerdash`
- `/etc/routerdash`
- `/etc/init.d/routerdash`

Installed packages such as `python3`, `python3-flask`, and `nlbwmon` are kept.

## Service management / Управление сервисом

```sh
/etc/init.d/routerdash status
/etc/init.d/routerdash restart
/etc/init.d/routerdash stop
/etc/init.d/routerdash start
```

## Defaults / Значения по умолчанию

- port: `1999`
- polling interval: `1500 ms`
- offline grace: `120 sec`
- activity threshold: `250 Kbit/s`
- local network: `192.168.0.0/24`
- interface language: selected during installation

## License

MIT
