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

## Features / Возможности

- RU/EN interface;
- guided installer with action menu;
- install, remove, reinstall, and status modes;
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

## One-command launch / Запуск одной командой

```sh
wget -O /tmp/routerdash-installer.sh https://raw.githubusercontent.com/t4kyofc/RouterDASH---OpenWRT/refs/heads/main/install-github-template.sh && sh /tmp/routerdash-installer.sh
```

После запуска мастер покажет меню:

1. Установить / обновить
2. Удалить RouterDash
3. Переустановить RouterDash
4. Показать статус

Installer flow is structured with numbered stages and clear status output for each action.

## Non-interactive usage / Неинтерактивный режим

```sh
sh /tmp/routerdash-installer.sh --lang=ru --action=install
sh /tmp/routerdash-installer.sh --lang=ru --action=uninstall
sh /tmp/routerdash-installer.sh --lang=en --action=reinstall
sh /tmp/routerdash-installer.sh --lang=en --action=status
```

## Service management / Управление сервисом

```sh
/etc/init.d/routerdash status
/etc/init.d/routerdash restart
/etc/init.d/routerdash stop
/etc/init.d/routerdash start
```

## Defaults / Значения по умолчанию

- host: `0.0.0.0`
- port: `1999`
- polling interval: `1500 ms`
- offline grace: `120 sec`
- activity threshold: `250 Kbit/s`
- local network: `192.168.0.0/24`

## License

MIT
