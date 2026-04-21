<p align="center">
  <a href="./README.md"><b>English documentation</b></a> · <b>Русская документация</b>
</p>

# RouterDash для OpenWrt

Адаптированный комплект установки для `t4kyofc/RouterDASH---OpenWRT`.

## Что изменено

- GitHub-установщик теперь **сначала скачивает файлы в `/opt/routerdash-installer`**
- после загрузки сразу выставляет нужные `chmod`
- затем запускает локальный `install.sh`
- локальный установщик **сначала спрашивает язык**, а потом показывает меню действий на выбранном языке
- добавлен локальный файл `blinker.py`, чтобы RouterDash запускался даже там, где в OpenWrt нет пакета `python3-blinker`

## Файлы в комплекте

- `install-github-template.sh`
- `install.sh`
- `blinker.py`
- `routerdash.init`
- `README.md`
- `README_ru.md`

## Быстрая установка с GitHub

```sh
wget -O /tmp/routerdash-installer.sh https://raw.githubusercontent.com/t4kyofc/RouterDASH---OpenWRT/refs/heads/main/install-github-template.sh && sh /tmp/routerdash-installer.sh
```

Что происходит:

1. создаётся каталог `/opt/routerdash-installer`
2. туда скачиваются `install.sh`, `routerdash.py`, `routerdash.init`, `blinker.py`
3. на `install.sh`, `routerdash.py`, `routerdash.init` ставится `chmod 0755`
4. запускается локальный `install.sh`
5. локальный установщик спрашивает язык
6. после выбора языка показывает меню действий

## Локальная установка

Если файлы уже лежат в `/opt/routerdash-installer` или другой папке:

```sh
cd /opt/routerdash-installer
sh ./install.sh
```

## Неинтерактивные варианты

```sh
sh ./install.sh --lang=ru --action=install
sh ./install.sh --lang=ru --action=uninstall
sh ./install.sh --lang=ru --action=reinstall
sh ./install.sh --lang=ru --action=status
```

## Что копируется при установке

- приложение: `/opt/routerdash/routerdash.py`
- локальный fallback для Flask signals: `/opt/routerdash/blinker.py`
- конфиг: `/etc/routerdash/config.json`
- сервис: `/etc/init.d/routerdash`

## Пакеты

Установщик ставит:

- `python3`
- `python3-flask`
- `ca-bundle`
- `nlbwmon`
- `iwinfo`

Пакет `python3-blinker` **не требуется**, потому что используется локальный `blinker.py`.

## Замена файлов в репозитории

Замените в репозитории как минимум:

- `install-github-template.sh`
- `install.sh`
- добавьте новый файл `blinker.py`
- при желании обновите `README.md` и `README_ru.md`
