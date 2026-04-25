#!/bin/sh
set -eu
APP_DIR=/opt/routerdash
CONF_DIR=/etc/routerdash
INIT_FILE=/etc/init.d/routerdash
SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
LANG_CHOICE=ru
ACTION=install

for arg in "$@"; do
  case "$arg" in
    --lang=en|en|english) LANG_CHOICE=en ;;
    --lang=ru|ru|russian) LANG_CHOICE=ru ;;
    uninstall|remove|--action=uninstall) ACTION=uninstall ;;
    reinstall|--action=reinstall) ACTION=reinstall ;;
  esac
done

has_tty(){ [ -t 1 ] && [ -r /dev/tty ] && [ -w /dev/tty ]; }
prompt(){ printf '%s' "$1" >/dev/tty; IFS= read -r a </dev/tty || true; printf '%s' "$a"; }

if [ $# -eq 0 ] && has_tty; then
  echo "Select installation language / Выберите язык установки" >/dev/tty
  echo "  1) Русский" >/dev/tty
  echo "  2) English" >/dev/tty
  ans="$(prompt 'Choice [1/2, default 1]: ')"
  [ "$ans" = "2" ] && LANG_CHOICE=en || LANG_CHOICE=ru
  echo "Выберите действие / Choose action" >/dev/tty
  echo "  1) Install / update" >/dev/tty
  echo "  2) Remove" >/dev/tty
  echo "  3) Reinstall" >/dev/tty
  ans="$(prompt 'Choice [1/2/3, default 1]: ')"
  case "$ans" in 2) ACTION=uninstall;; 3) ACTION=reinstall;; *) ACTION=install;; esac
fi

say(){
  case "$LANG_CHOICE:$1" in
    ru:pkg) echo "Установка пакетов";; en:pkg) echo "Installing packages";;
    ru:copy) echo "Копирование файлов";; en:copy) echo "Copying files";;
    ru:cfg) echo "Подготовка конфигурации";; en:cfg) echo "Preparing config";;
    ru:start) echo "Запуск сервиса";; en:start) echo "Starting service";;
    ru:done) echo "Готово";; en:done) echo "Done";;
    ru:remove) echo "Удаление RouterDash";; en:remove) echo "Removing RouterDash";;
    ru:open) echo "Откройте";; en:open) echo "Open";;
    *) echo "$1";;
  esac
}

uninstall(){
  echo "[1/2] $(say remove)"
  [ -x "$INIT_FILE" ] && "$INIT_FILE" stop >/dev/null 2>&1 || true
  [ -x "$INIT_FILE" ] && "$INIT_FILE" disable >/dev/null 2>&1 || true
  pkill -f '/opt/routerdash/routerdash.py' >/dev/null 2>&1 || true
  echo "[2/2] rm -rf"
  rm -f "$INIT_FILE"
  rm -rf "$APP_DIR" "$CONF_DIR"
}

install(){
  command -v apk >/dev/null 2>&1 || { echo "OpenWrt 25.12+ with apk required" >&2; exit 1; }
  echo "[1/5] $(say pkg)"
  apk update
  apk add python3 python3-flask ca-bundle nlbwmon iwinfo ip-full bridge-utils >/dev/null 2>&1 || apk add python3 python3-flask ca-bundle nlbwmon iwinfo >/dev/null
  echo "[2/5] $(say copy)"
  mkdir -p "$APP_DIR" "$CONF_DIR"
  install -m 0755 "$SCRIPT_DIR/routerdash.py" "$APP_DIR/routerdash.py"
  install -m 0644 "$SCRIPT_DIR/blinker.py" "$APP_DIR/blinker.py"
  install -m 0755 "$SCRIPT_DIR/routerdash.init" "$INIT_FILE"
  echo "[3/5] $(say cfg)"
  LANG_CHOICE="$LANG_CHOICE" CONF_DIR="$CONF_DIR" python3 - <<'PY'
import os,json,secrets,ipaddress,subprocess
conf=os.environ['CONF_DIR']; lang=os.environ.get('LANG_CHOICE','ru')
path=os.path.join(conf,'config.json')
def cmd(a):
    try:
        p=subprocess.run(a,capture_output=True,text=True,timeout=3); return p.stdout.strip() if p.returncode==0 else ''
    except Exception: return ''
def detect():
    ip=cmd(['uci','-q','get','network.lan.ipaddr']); mask=cmd(['uci','-q','get','network.lan.netmask'])
    try:
        if ip:
            return str(ipaddress.ip_network(f'{ip}/{mask or "24"}', strict=False)) if '/' not in ip else str(ipaddress.ip_interface(ip).network)
    except Exception: pass
    return '192.168.0.0/24'
try:
    data=json.load(open(path,encoding='utf-8')) if os.path.exists(path) else {}
except Exception: data={}
data.setdefault('version',2); data.setdefault('secret_key',secrets.token_hex(32)); data.setdefault('admin',{'username':'','password_hash':''})
s=data.setdefault('settings',{})
defaults={'bind_host':'0.0.0.0','port':1999,'language':lang,'poll_interval_ms':1500,'offline_grace_sec':120,'presence_probe_cooldown_sec':20,'activity_total_kbps':250,'local_network_cidr':detect(),'track_ipv6':True,'notify_online':True,'notify_offline':True,'notify_active':False,'notify_inactive':False,'notification_total_kbps':500,'telegram_enabled':False,'telegram_bot_token':'','telegram_chat_id':'','telegram_limit_to_selected_devices':False,'telegram_selected_devices':[],'telegram_selection_initialized':False}
for k,v in defaults.items(): s.setdefault(k,v)
s['language']=lang
if s.get('local_network_cidr') in ('','192.168.0.0/24'): s['local_network_cidr']=detect()
json.dump(data,open(path,'w',encoding='utf-8'),ensure_ascii=False,indent=2,sort_keys=True)
PY
  /etc/init.d/nlbwmon enable >/dev/null 2>&1 || true
  /etc/init.d/nlbwmon restart >/dev/null 2>&1 || true
  echo "[4/5] $(say start)"
  "$INIT_FILE" enable >/dev/null 2>&1 || true
  "$INIT_FILE" restart >/dev/null 2>&1 || "$INIT_FILE" start >/dev/null 2>&1 || true
  echo "[5/5] $(say done)"
  LAN_IP="$(uci -q get network.lan.ipaddr || echo 192.168.1.1)"; LAN_IP="${LAN_IP%%/*}"
  echo "$(say open): http://$LAN_IP:1999"
}

[ "$ACTION" = "reinstall" ] && uninstall && install && exit 0
[ "$ACTION" = "uninstall" ] && uninstall && exit 0
install
