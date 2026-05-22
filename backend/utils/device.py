import requests as _requests


def parse_device(user_agent: str) -> str:
    ua = user_agent or ""
    if "iPhone" in ua:
        return "iPhone"
    if "iPad" in ua:
        return "iPad"
    if "Android" in ua:
        return "Android"
    if "Macintosh" in ua or "Mac OS X" in ua:
        return "macOS"
    if "Windows NT" in ua:
        return "Windows"
    if "Linux" in ua:
        return "Linux"
    return "Browser"


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
