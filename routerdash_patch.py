#!/usr/bin/env python3
import sys
from pathlib import Path

path = Path(sys.argv[1]) if len(sys.argv) > 1 else None
if not path or not path.exists():
    raise SystemExit("routerdash.py not found")
text = path.read_text(encoding='utf-8')
original = text

old_split = '''def split_device_ips(ips: List[str], local_ipv4_cidr: str, include_ipv6: bool = True) -> Tuple[List[str], List[str]]:
    ipv4_list: List[str] = []
    ipv6_list: List[str] = []
    seen4 = set()
    seen6 = set()
    net4 = safe_network(local_ipv4_cidr)

    for raw in ips:
        ip = (raw or '').strip()
        if not ip:
            continue
        try:
            addr = ipaddress.ip_address(ip)
        except Exception:
            continue

        if addr.version == 4:
            if net4 is not None and addr not in net4:
                continue
            if ip not in seen4:
                seen4.add(ip)
                ipv4_list.append(ip)
            continue

        if addr.version == 6:
            if not include_ipv6:
                continue
            if addr.is_unspecified or addr.is_loopback or addr.is_multicast:
                continue
            if ip not in seen6:
                seen6.add(ip)
                ipv6_list.append(ip)

    return ipv4_list, ipv6_list
'''

new_split = '''def split_device_ips(ips: List[str], local_ipv4_cidr: str, include_ipv6: bool = True) -> Tuple[List[str], List[str]]:
    ipv4_matches: List[str] = []
    ipv4_private_fallback: List[str] = []
    ipv4_any_fallback: List[str] = []
    ipv6_list: List[str] = []
    seen4 = set()
    seen6 = set()
    net4 = safe_network(local_ipv4_cidr)

    for raw in ips:
        ip = (raw or '').strip()
        if not ip:
            continue
        try:
            addr = ipaddress.ip_address(ip)
        except Exception:
            continue

        if addr.version == 4:
            if ip in seen4:
                continue
            seen4.add(ip)
            ipv4_any_fallback.append(ip)
            if getattr(addr, 'is_private', False):
                ipv4_private_fallback.append(ip)
            if net4 is None or addr in net4:
                ipv4_matches.append(ip)
            continue

        if addr.version == 6:
            if not include_ipv6:
                continue
            if addr.is_unspecified or addr.is_loopback or addr.is_multicast:
                continue
            if ip not in seen6:
                seen6.add(ip)
                ipv6_list.append(ip)

    if ipv4_matches:
        ipv4_list = ipv4_matches
    elif ipv4_private_fallback:
        ipv4_list = ipv4_private_fallback
    else:
        ipv4_list = ipv4_any_fallback

    return ipv4_list, ipv6_list
'''

if old_split not in text:
    raise SystemExit('Expected split_device_ips block not found; repository version changed.')
text = text.replace(old_split, new_split)

old_choose = '''                name = meta.get("alias") or meta.get("hostname") or (ipv4_list[0] if ipv4_list else meta.get("last_ip")) or mac
'''
new_choose = '''                name = meta.get("alias") or meta.get("hostname") or (ipv4_list[0] if ipv4_list else (meta.get("last_ip") or mac))
'''
if old_choose in text:
    text = text.replace(old_choose, new_choose)

old_effective = '''def get_effective_local_network_cidr(settings: Optional[Dict[str, Any]] = None) -> str:
    raw = ''
    if settings:
        raw = str((settings or {}).get("local_network_cidr", "") or '').strip()
    normalized = _normalize_ipv4_network(raw)
    if normalized:
        return normalized
    return detect_system_local_network_cidr()
'''
new_effective = '''def get_effective_local_network_cidr(settings: Optional[Dict[str, Any]] = None) -> str:
    system_detected = detect_system_local_network_cidr()
    raw = ''
    if settings:
        raw = str((settings or {}).get("local_network_cidr", "") or '').strip()
    normalized = _normalize_ipv4_network(raw)
    if not normalized:
        return system_detected
    if normalized == LEGACY_DEFAULT_LOCAL_NETWORK_CIDR and system_detected != LEGACY_DEFAULT_LOCAL_NETWORK_CIDR:
        return system_detected
    return normalized
'''
if old_effective in text:
    text = text.replace(old_effective, new_effective)

if text != original:
    path.write_text(text, encoding='utf-8')
