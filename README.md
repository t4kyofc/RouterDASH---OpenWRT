<p align="center">
  <img src="./docs/preview.png" alt="RouterDash preview" width="100%">
</p>

<p align="center">
  <b>English documentation (main)</b> · <a href="./README_ru.md"><b>Русская документация</b></a>
</p>

## RouterDash

RouterDash is a lightweight OpenWrt dashboard for device visibility, live speed, activity state tracking, and Telegram alerts.

## Requirements

- OpenWrt 25.12+
- `apk` package manager
- SSH access to the router
- internet access to GitHub for one-line install

## One-line launcher

```sh
wget -O /tmp/routerdash-installer.sh https://raw.githubusercontent.com/t4kyofc/RouterDASH---OpenWRT/refs/heads/main/install-github-template.sh && sh /tmp/routerdash-installer.sh
```

This launcher opens an interactive wizard with clear menu options:

1. Install / update
2. Remove RouterDash
3. Reinstall RouterDash
4. Show status

The installer has color highlights and explicit numbered phases.

## Non-interactive mode

```sh
sh /tmp/routerdash-installer.sh --lang=en --action=install
sh /tmp/routerdash-installer.sh --lang=en --action=uninstall
sh /tmp/routerdash-installer.sh --lang=en --action=reinstall
sh /tmp/routerdash-installer.sh --lang=en --action=status
```

## Service commands

```sh
/etc/init.d/routerdash status
/etc/init.d/routerdash restart
/etc/init.d/routerdash stop
/etc/init.d/routerdash start
```

## Defaults

- host: `0.0.0.0`
- port: `1999`
- polling interval: `1500 ms`
- offline grace: `120 sec`
- activity threshold: `250 Kbit/s`
- local network: `192.168.0.0/24`

## License

MIT
