import hashlib
import ipaddress

import requests as _requests

from config import Config


def _browser(ua: str) -> str:
    if "SamsungBrowser" in ua:
        return "Samsung"
    if "OPR/" in ua or "Opera" in ua:
        return "Opera"
    if "Edg/" in ua or "EdgA/" in ua:
        return "Edge"
    if "Firefox/" in ua or "FxiOS/" in ua:
        return "Firefox"
    if "Chrome/" in ua or "CriOS/" in ua:
        return "Chrome"
    if "Safari/" in ua:
        return "Safari"
    return "Browser"


def _os(ua: str) -> str:
    if "iPhone" in ua:
        return "iPhone"
    if "iPad" in ua:
        return "iPad"
    if "Android" in ua:
        if "Tablet" in ua or "Tab" in ua:
            return "Android Tablet"
        return "Android"
    if "Macintosh" in ua or "Mac OS X" in ua:
        return "macOS"
    if "Windows NT" in ua:
        return "Windows"
    if "Linux" in ua:
        return "Linux"
    return ""


def parse_device(user_agent: str) -> str:
    """Returns label like 'Chrome macOS' or 'Safari iPhone'"""
    ua = user_agent or ""
    browser = _browser(ua)
    os = _os(ua)
    if os:
        return f"{browser} {os}"
    return browser


def client_fingerprint(user_agent: str) -> str:
    """
    Coarse, stable id of the browser + OS a session was created from.

    Version numbers are left out on purpose: a browser auto-update must not
    log anyone out. A different browser or OS family is a different device.
    """
    ua = user_agent or ""
    return hashlib.sha256(f"{_browser(ua)}|{_os(ua)}".encode("utf-8")).hexdigest()[:32]


def _parse_ip(value):
    """Return an ip_address object, or None for anything that is not an IP."""
    try:
        ip = ipaddress.ip_address((value or "").strip())
    except ValueError:
        return None
    if ip.version == 6 and ip.ipv4_mapped is not None:
        return ip.ipv4_mapped
    return ip


def _is_trusted_proxy(ip) -> bool:
    for entry in Config.TRUSTED_PROXIES:
        try:
            if ip in ipaddress.ip_network(entry, strict=False):
                return True
        except ValueError:
            continue
    return False


def get_client_ip(flask_request) -> str:
    """
    The caller's address, decided by the server -- never by the caller.

    The TCP peer cannot be forged. Behind our own nginx the peer is the
    proxy, and nginx puts the real client in X-Real-IP (it overwrites any
    value the client sent). That header is believed only when the peer is a
    configured trusted proxy; X-Forwarded-For is not read at all, because a
    client can prepend to it. The result is validated, so a header cannot
    smuggle anything but an IP address into the session table or the
    geolocation URL. Returns "" when nothing valid can be determined.
    """
    peer = _parse_ip(flask_request.remote_addr)
    if peer is None:
        return ""
    if _is_trusted_proxy(peer):
        real = _parse_ip(flask_request.headers.get("X-Real-IP", ""))
        if real is not None:
            return str(real)
    return str(peer)


def get_city(ip: str) -> str:
    """City for a public IP. Private, loopback and malformed input never leave the server."""
    parsed = _parse_ip(ip)
    if parsed is None or not parsed.is_global:
        return ""
    try:
        r = _requests.get(
            f"http://ip-api.com/json/{parsed}",
            params={"fields": "status,city"},
            timeout=2,
        )
        data = r.json()
        if data.get("status") == "success":
            return data.get("city") or ""
    except Exception:
        pass
    return ""
