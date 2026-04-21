# RouterDASH fixed files pack

Это архив с исправленными файлами для проекта `t4kyofc/RouterDASH---OpenWRT`.

Что исправлено:

- `install-github-template.sh` теперь передаёт действие и язык в локальный установщик через именованные аргументы:
  - `./install.sh --action="..." --lang="..."`
- `install.sh` больше не падает на удалении/переустановке из-за отсутствующих локальных файлов.
- `install.sh` мягче обрабатывает `enable/restart/start` сервиса.
- `install.sh` теперь обрезает `/24` и подобные суффиксы из LAN IP при выводе адреса панели.

Почему в панели могли оставаться старые Telegram token/chat_id:

- в исходных дефолтных настройках проекта эти поля пустые;
- старые значения оставались из уже существующего `/etc/routerdash/config.json`, потому что удаление ранее срабатывало некорректно.

## Как применить

Замени этими файлами одноимённые файлы в репозитории:

- `install-github-template.sh`
- `install.sh`
- `routerdash.init`

`routerdash.py` в этот архив не включён, потому что проблема была не в его дефолтных значениях, а в сломанном сценарии удаления/переустановки.

## Быстрый локальный тест

```sh
chmod +x install-github-template.sh install.sh
./install.sh --action=uninstall --lang=ru
./install.sh --action=reinstall --lang=ru
```
