<p align="center">
  <img src="docs/routerdash-preview.svg" alt="RouterDash preview" width="100%">
</p>

<h1 align="center">RouterDash для OpenWrt</h1>

<p align="center">
  <b>Красивая веб-панель для OpenWrt: реальные устройства дома, скорость, соединения и Telegram-уведомления.</b>
</p>

<p align="center">
  <img alt="OpenWrt" src="https://img.shields.io/badge/OpenWrt-25.12%2B-00B5E2?style=for-the-badge">
  <img alt="Python" src="https://img.shields.io/badge/Python-3.x-3776AB?style=for-the-badge">
  <img alt="Flask" src="https://img.shields.io/badge/Flask-Web%20UI-111827?style=for-the-badge">
  <img alt="Telegram" src="https://img.shields.io/badge/Telegram-Alerts-229ED9?style=for-the-badge">
</p>

---

## Быстрый старт

Одна команда на OpenWrt:

```sh
rm -rf /tmp/routerdash-github-install /tmp/routerdash-installer.sh && wget -O /tmp/routerdash-installer.sh "https://raw.githubusercontent.com/t4kyofc/RouterDASH---OpenWRT/refs/heads/main/install-github-template.sh?nocache=$(date +%s)" && sh /tmp/routerdash-installer.sh
```

После установки откройте панель:

```text
http://IP_РОУТЕРА:1999
```

Например:

```text
http://192.168.1.1:1999
```

При первом входе RouterDash предложит создать логин и пароль администратора.

---

## Что такое RouterDash

**RouterDash** — это лёгкая веб-панель для OpenWrt, которая показывает реальную картину домашней сети: какие устройства сейчас дома, какие активны, какие ушли из зоны Wi‑Fi/LAN, сколько трафика они используют и когда нужно отправить Telegram-уведомление.

Главная идея проекта — не просто показать DHCP-таблицу, а определить **реальное присутствие устройства**. DHCP lease может висеть ещё долго после ухода телефона из дома, поэтому RouterDash использует несколько источников данных и делает контрольную проверку перед offline-уведомлением.

---

## Возможности

- Современная web-панель на порту `1999`.
- Адаптивный UI для телефона и ПК.
- Статусы устройств: `online`, `idle`, `offline`.
- Определение реального присутствия, а не только DHCP lease.
- Telegram-уведомления о появлении и уходе устройств.
- Выбор конкретных устройств для уведомлений.
- Скорость по каждому устройству: download, upload, total.
- Активные соединения и направления трафика.
- История событий в панели.
- RU/EN интерфейс.
- Настройки прямо из UI: Telegram, CIDR сети, пороги активности, порт, логин и пароль.
- Автоустановка, обновление, переустановка и удаление через один установщик.

---

## Как RouterDash понимает, что устройство дома

Устройство считается присутствующим, если есть хотя бы один сильный сигнал:

1. есть активные записи в `conntrack`;
2. есть прирост трафика через `nlbwmon`;
3. Wi‑Fi-клиент подтверждён через `ubus hostapd`;
4. ARP/ND показывает состояние `REACHABLE`, `DELAY`, `PROBE` или `PERMANENT`;
5. контрольная проверка `ping` + `ip neigh` подтверждает, что устройство ещё доступно.

Если активности нет дольше `offline_grace_sec`, RouterDash не отправляет offline сразу. Сначала он проверяет последние известные IP-адреса устройства. Только если устройство не подтверждается, оно считается покинувшим сеть.

---

## Установка / обновление / переустановка / удаление

Запускается одной командой:

```sh
rm -rf /tmp/routerdash-github-install /tmp/routerdash-installer.sh && wget -O /tmp/routerdash-installer.sh "https://raw.githubusercontent.com/t4kyofc/RouterDASH---OpenWRT/refs/heads/main/install-github-template.sh?nocache=$(date +%s)" && sh /tmp/routerdash-installer.sh
```

Установщик покажет меню:

```text
1) Установить / обновить
2) Удалить RouterDash
3) Переустановить RouterDash
```

Что делает установщик:

- скачивает актуальные файлы проекта из GitHub;
- очищает временную папку перед новой установкой;
- ставит зависимости через `apk`;
- копирует файлы в `/opt/routerdash`;
- создаёт конфигурацию в `/etc/routerdash`;
- настраивает `nlbwmon`;
- устанавливает init.d-сервис `/etc/init.d/routerdash`;
- включает автозапуск;
- запускает сервис;
- показывает адрес панели.

---

## Управление сервисом

```sh
service routerdash start
service routerdash stop
service routerdash restart
service routerdash status
service routerdash enable
service routerdash disable
```

Логи:

```sh
logread -e routerdash
```

---

## Рекомендуемые настройки

| Параметр | Рекомендация | Описание |
|---|---:|---|
| `poll_interval_ms` | `1000–2000` | Частота обновления панели и мониторинга. |
| `offline_grace_sec` | `120–240` | Сколько ждать без активности перед проверкой ухода. |
| `presence_probe_cooldown_sec` | `20–45` | Интервал между контрольными проверками устройства. |
| `activity_total_kbps` | `250` | Порог, выше которого устройство считается активным. |
| `notification_total_kbps` | `500` | Порог уведомлений об активном использовании. |
| `local_network_cidr` | ваша LAN-сеть | Например `192.168.1.0/24` или `172.20.1.0/24`. |

Для сценария «понять, пришёл человек домой или ушёл» не ставьте слишком маленький `offline_grace_sec`. Телефоны часто засыпают и временно не создают соединений.

---

## Telegram-уведомления

RouterDash может отправлять уведомления, когда:

- устройство появилось в сети;
- устройство подтверждённо покинуло сеть;
- устройство стало активно использовать сеть;
- активность устройства снизилась.

Пример:

```text
🟢 POCO-X7-Pro появился в сети
IP: 172.20.1.252
MAC: c2:e4:cd:10:8c:50
```

Offline-уведомление отправляется только после контрольной проверки, чтобы не было ложных сообщений из-за сна телефона или краткого пропадания соединений.

---

## Зависимости

Установщик ставит всё автоматически:

- `python3`
- `python3-flask`
- `ca-bundle`
- `nlbwmon`
- `iwinfo`
- дополнительные сетевые утилиты, если доступны

---

## Структура проекта

```text
RouterDASH---OpenWRT/
├── routerdash.py                  # Flask backend + web UI
├── routerdash.init                # init.d service для OpenWrt
├── install.sh                     # основной установщик
├── install-github-template.sh     # bootstrap-установщик из GitHub
├── blinker.py                     # совместимость Flask-зависимостей
├── docs/
│   └── routerdash-preview.svg     # превью README
└── README.md
```

---

## Если apk занят

Если установка была остановлена через `Ctrl+Z`, старый процесс может держать lock `apk`. Очистите его:

```sh
jobs -l
kill %1 2>/dev/null || true
pkill -f '/tmp/routerdash' 2>/dev/null || true
pkill -f 'apk update' 2>/dev/null || true
pkill -f 'apk add' 2>/dev/null || true
```

Проверьте:

```sh
apk info >/dev/null && echo "apk свободен" || echo "apk всё ещё занят"
```

После этого снова запустите одну команду установки из раздела «Быстрый старт».

---

## Безопасность

- Панель защищается логином и паролем.
- Telegram token хранится локально в `/etc/routerdash/config.json`.
- Не публикуйте порт `1999` напрямую в интернет.
- Для внешнего доступа используйте VPN или защищённый reverse proxy.

---

<p align="center">
  <b>RouterDash</b> — не просто список клиентов, а понятная картина домашней сети.
</p>
