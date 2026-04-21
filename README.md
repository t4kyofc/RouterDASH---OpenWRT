# RouterDash для OpenWrt 25.12

Веб‑деш на Python для OpenWrt с портом `1999`.

Что умеет:

- показывает список устройств, подключавшихся к роутеру;
- считает по каждому устройству:
  - текущую скорость скачивания;
  - текущую скорость отдачи;
  - количество соединений;
- определяет статус:
  - **Подключен, активность выявлена**;
  - **Подключен, малоактивен**;
  - **Вышел из зоны WiFi**;
- сохраняет устройство в списке даже после пропадания из сети;
- при первом входе просит создать логин и пароль администратора;
- позволяет подключить Telegram‑бота и `chat_id`/ID пользователя для уведомлений;
- позволяет выбрать, по каким устройствам отправлять Telegram‑уведомления;
- настройки Telegram, учётной записи и пороги активности редактируются через панель по шестерёнке;
- последние события открываются отдельной панелью логов слева сверху.

---

## Как это работает

- Для трафика и количества соединений используется `nlbwmon` / `nlbw`.
- Для обнаружения Wi‑Fi клиентов используется `ubus call hostapd.* get_clients`.
- Для DHCP‑имён и IP используется `/tmp/dhcp.leases`.
- Для живых соседей в LAN используется `ip neigh show`.

Такой подход опирается на штатные механизмы OpenWrt.

---

## Установка через терминал

### 1. Подключиться по SSH к роутеру

```sh
ssh root@192.168.1.1
```

### 2. Создать каталоги

```sh
mkdir -p /opt/routerdash /etc/routerdash /tmp/routerdash_upload
cd /tmp/routerdash_upload
```

### 3. Загрузить в роутер файлы из архива

С ПК распакуйте архив и скопируйте файлы `routerdash.py`, `routerdash.init`, `install.sh` в `/tmp/routerdash_upload`.

Пример с Linux/macOS:

```sh
scp routerdash.py routerdash.init install.sh root@192.168.1.1:/tmp/routerdash_upload/
```

Пример с Windows PowerShell:

```powershell
scp .\routerdash.py .\routerdash.init .\install.sh root@192.168.1.1:/tmp/routerdash_upload/
```

### 4. Запустить установщик

На роутере:

```sh
cd /tmp/routerdash_upload
chmod +x install.sh
./install.sh
```

---

## Ручная установка без install.sh

```sh
apk update
apk add python3 python3-flask ca-bundle nlbwmon iwinfo

mkdir -p /opt/routerdash /etc/routerdash
cp /tmp/routerdash_upload/routerdash.py /opt/routerdash/routerdash.py
chmod +x /opt/routerdash/routerdash.py
cp /tmp/routerdash_upload/routerdash.init /etc/init.d/routerdash
chmod +x /etc/init.d/routerdash

if ! uci -q get nlbwmon.@nlbwmon[0] >/dev/null 2>&1; then
  uci add nlbwmon nlbwmon >/dev/null
fi
uci -q del_list nlbwmon.@nlbwmon[0].local_network='lan' >/dev/null 2>&1 || true
uci add_list nlbwmon.@nlbwmon[0].local_network='lan'
uci set nlbwmon.@nlbwmon[0].refresh_interval='30s'
uci set nlbwmon.@nlbwmon[0].database_directory='/var/lib/nlbwmon'
uci commit nlbwmon

/etc/init.d/nlbwmon enable
/etc/init.d/nlbwmon restart
/etc/init.d/routerdash enable
/etc/init.d/routerdash restart
```

---

## Вход в деш

Открыть в браузере:

```text
http://IP_РОУТЕРА:1999
```

Обычно это:

```text
http://192.168.1.1:1999
```

При первом входе откроется страница создания логина и пароля.

---

## Управление сервисом

```sh
/etc/init.d/routerdash status
/etc/init.d/routerdash restart
/etc/init.d/routerdash stop
/etc/init.d/routerdash start
```

Логи:

```sh
logread -e routerdash
```

Или так:

```sh
/etc/init.d/routerdash restart
sleep 2
logread | tail -n 50
```

---

## Telegram

В деше есть поля:

- `Токен Telegram-бота`
- `ID пользователя / chat_id`
- включатели уведомлений
- пороги активности

Внутри даша есть кнопка отправки тестового сообщения.

---

## Если страница не открывается

Проверить, что процесс поднялся:

```sh
ps | grep routerdash
ss -lntp | grep 1999
```

Если у вас кастомный firewall и доступ к самому роутеру с LAN ограничен, разрешите TCP/1999.

Пример UCI‑правила:

```sh
uci add firewall rule
uci set firewall.@rule[-1].name='Allow-RouterDash-LAN'
uci set firewall.@rule[-1].src='lan'
uci set firewall.@rule[-1].dest_port='1999'
uci set firewall.@rule[-1].proto='tcp'
uci set firewall.@rule[-1].target='ACCEPT'
uci commit firewall
/etc/init.d/firewall restart
```

---

## Важное замечание

Проект рассчитан на домашний/малый офис и старается быть лёгким, но на очень слабых роутерах с маленьким объёмом RAM работа Python + Flask может быть тяжеловата.

