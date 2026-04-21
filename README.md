<p align="center">
  <img src="./docs/preview.png" alt="RouterDash preview" width="100%">
</p>

<p align="center">
  <b>English documentation</b> · <a href="./README_ru.md"><b>Русская документация</b></a>
</p>

# RouterDash for OpenWrt

RouterDash is a lightweight web dashboard for OpenWrt that shows devices on the local network, current speed, activity state, active connections, presence history, and Telegram alerts.

## What the project includes

- `routerdash.py` — main web application
- `routerdash.init` — OpenWrt init script (`/etc/init.d/routerdash`)
- `install.sh` — local installer/remover for files already downloaded
- `install-github-template.sh` — GitHub bootstrap launcher that downloads the required files and runs `install.sh`

## Requirements

- OpenWrt 25.12 or newer
- `apk` package manager
- SSH access to the router
- Internet access to GitHub for the bootstrap installer

## Quick install from GitHub

```sh
wget -O /tmp/routerdash-installer.sh https://raw.githubusercontent.com/t4kyofc/RouterDASH---OpenWRT/refs/heads/main/install-github-template.sh && sh /tmp/routerdash-installer.sh
```

What happens next:

1. The launcher asks for the installation language
2. Downloads `install.sh`, `routerdash.py`, and `routerdash.init`
3. Runs the local installer
4. Enables and starts the `routerdash` service

The installer is now compatible with BusyBox-based OpenWrt systems and does not require the external `install` utility.

## Local install from downloaded files

If you already downloaded or unpacked the project files on the router, run:

```sh
cd /path/to/RouterDASH---OpenWRT
sh ./install.sh --lang=en --action=install
```

Required files in the same directory:

- `install.sh`
- `routerdash.py`
- `routerdash.init`

## Quick remove

Using the GitHub launcher:

```sh
wget -O /tmp/routerdash-installer.sh https://raw.githubusercontent.com/t4kyofc/RouterDASH---OpenWRT/refs/heads/main/install-github-template.sh && sh /tmp/routerdash-installer.sh --lang=en --action=uninstall
```

Using local files:

```sh
cd /path/to/RouterDASH---OpenWRT
sh ./install.sh --lang=en --action=uninstall
```

## Other actions

```sh
sh ./install.sh --lang=en --action=reinstall
sh ./install.sh --lang=en --action=status
```

The interactive launcher also supports these menu actions:

1. Install / update
2. Remove RouterDash
3. Reinstall RouterDash
4. Show status

## Installed paths

After installation the project uses these paths:

- application: `/opt/routerdash/routerdash.py`
- config: `/etc/routerdash/config.json`
- service: `/etc/init.d/routerdash`

## Default settings

- bind host: `0.0.0.0`
- port: `1999`
- language: selected during install
- polling interval: `1500 ms`
- offline grace: `120 sec`
- activity threshold: `250 Kbit/s`
- local network: `192.168.0.0/24`

## Service management

```sh
/etc/init.d/routerdash status
/etc/init.d/routerdash restart
/etc/init.d/routerdash stop
/etc/init.d/routerdash start
logread -e routerdash
```

## Notes

- The installer also configures and restarts `nlbwmon`
- On first web login RouterDash asks you to create the admin username and password
- The panel is opened in a browser at `http://LAN_IP:1999`

## License

MIT
