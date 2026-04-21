<p align="center">
  <img src="./docs/preview.png" alt="RouterDash preview" width="100%">
</p>

<p align="center">
  <a href="./README.md"><b>English documentation</b></a> · <b>Русская документация (основная для RU)</b>
</p>

## RouterDash

RouterDash — лёгкая панель для OpenWrt: мониторинг устройств, скорости, активности и Telegram-уведомления.

## Требования

- OpenWrt 25.12+
- менеджер пакетов `apk`
- SSH-доступ к роутеру
- доступ в интернет к GitHub для установки одной командой

## Запуск одной командой

```sh
wget -O /tmp/routerdash-installer.sh https://raw.githubusercontent.com/t4kyofc/RouterDASH---OpenWRT/refs/heads/main/install-github-template.sh && sh /tmp/routerdash-installer.sh
```

После запуска откроется мастер с меню:

1. Установить / обновить
2. Удалить RouterDash
3. Переустановить RouterDash
4. Показать статус

Установщик теперь выводит цветные акценты и понятные нумерованные этапы.

## Неинтерактивный режим

```sh
sh /tmp/routerdash-installer.sh --lang=ru --action=install
sh /tmp/routerdash-installer.sh --lang=ru --action=uninstall
sh /tmp/routerdash-installer.sh --lang=ru --action=reinstall
sh /tmp/routerdash-installer.sh --lang=ru --action=status
```

## Управление сервисом

```sh
/etc/init.d/routerdash status
/etc/init.d/routerdash restart
/etc/init.d/routerdash stop
/etc/init.d/routerdash start
```

## Значения по умолчанию

- host: `0.0.0.0`
- port: `1999`
- polling interval: `1500 ms`
- offline grace: `120 sec`
- activity threshold: `250 Kbit/s`
- local network: `192.168.0.0/24`

## Лицензия

MIT
