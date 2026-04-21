<p align="center">
  <img src="./docs/preview.png" alt="RouterDash preview" width="100%">
</p>

<p align="center">
  <a href="./README.md"><b>English documentation</b></a> · <b>Русская документация</b>
</p>

# RouterDash для OpenWrt

RouterDash — лёгкая веб-панель для OpenWrt, которая показывает устройства в локальной сети, текущую скорость, активность, активные соединения, историю присутствия и Telegram-уведомления.

## Что входит в проект

- `routerdash.py` — основное веб-приложение
- `routerdash.init` — init-скрипт OpenWrt (`/etc/init.d/routerdash`)
- `blinker.py` — локальный fallback-модуль для сборок OpenWrt без пакета `python3-blinker`
- `install.sh` — локальный установщик/удаление для уже скачанных файлов
- `install-github-template.sh` — стартовый GitHub-установщик, который скачивает нужные файлы и запускает `install.sh`

## Требования

- OpenWrt 25.12 и новее
- пакетный менеджер `apk`
- SSH-доступ к роутеру
- доступ к GitHub для установки одной командой

## Быстрая установка с GitHub

```sh
wget -O /tmp/routerdash-installer.sh https://raw.githubusercontent.com/t4kyofc/RouterDASH---OpenWRT/refs/heads/main/install-github-template.sh && sh /tmp/routerdash-installer.sh
```

Что происходит дальше:

1. GitHub-лаунчер спрашивает только язык установки
2. Скачивает файлы в `/opt/routerdash-installer`
3. Выставляет для них нужный `chmod`
4. Запускает локальный установщик уже на выбранном языке
5. Устанавливает и запускает сервис `routerdash`

GitHub-установщик теперь работает последовательно: сначала выбор языка, затем установка на выбранном языке без повторного вопроса про язык. Установщик совместим с BusyBox-окружением OpenWrt и не требует внешней утилиты `install`.

## Локальная установка из уже скачанных файлов

Если файлы проекта уже загружены на роутер или распакованы из архива, запустите:

```sh
cd /path/to/RouterDASH---OpenWRT
sh ./install.sh --lang=ru --action=install
```

Обязательные файлы в одной папке:

- `install.sh`
- `routerdash.py`
- `routerdash.init`

## Быстрое удаление

Через GitHub-лаунчер:

```sh
wget -O /tmp/routerdash-installer.sh https://raw.githubusercontent.com/t4kyofc/RouterDASH---OpenWRT/refs/heads/main/install-github-template.sh && sh /tmp/routerdash-installer.sh --lang=ru --action=uninstall
```

Через локальные файлы:

```sh
cd /path/to/RouterDASH---OpenWRT
sh ./install.sh --lang=ru --action=uninstall
```

## Дополнительные действия

```sh
sh ./install.sh --lang=ru --action=reinstall
sh ./install.sh --lang=ru --action=status
```

Интерактивный установщик также поддерживает меню:

1. Установить / обновить
2. Удалить RouterDash
3. Переустановить RouterDash
4. Показать статус

## Пути после установки

После установки используются такие пути:

- приложение: `/opt/routerdash/routerdash.py`
- конфиг: `/etc/routerdash/config.json`
- сервис: `/etc/init.d/routerdash`

## Значения по умолчанию

- bind host: `0.0.0.0`
- port: `1999`
- язык: выбранный при установке
- polling interval: `1500 ms`
- offline grace: `120 sec`
- activity threshold: `250 Kbit/s`
- local network: определяется автоматически по текущей LAN-сети OpenWrt

## Управление сервисом

```sh
/etc/init.d/routerdash status
/etc/init.d/routerdash restart
/etc/init.d/routerdash stop
/etc/init.d/routerdash start
logread -e routerdash
```

## Примечания

- Установщик также настраивает и перезапускает `nlbwmon`
- При первом открытии панели RouterDash предложит создать логин и пароль администратора
- Панель открывается в браузере по адресу `http://LAN_IP:1999`

## Лицензия

MIT
