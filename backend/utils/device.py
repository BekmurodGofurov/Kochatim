import requests as _requests


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


def get_city(ip: str) -> str:
    if not ip or ip in ("127.0.0.1", "::1", ""):
        return ""
    try:
        r = _requests.get(
            f"http://ip-api.com/json/{ip}",
            params={"fields": "status,city"},
            timeout=2,
        )
        data = r.json()
        if data.get("status") == "success":
            return data.get("city") or ""
    except Exception:
        pass
    return ""


def get_client_ip(flask_request) -> str:
    xff = flask_request.headers.get("X-Forwarded-For", "")
    if xff:
        return xff.split(",")[0].strip()
    return flask_request.remote_addr or ""
