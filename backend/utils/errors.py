# backend/utils/errors.py
from flask import jsonify


def ok(data=None, status=200):
    return jsonify({"ok": True, "data": data}), status


def fail(message="Error", status=400, code=None, extra=None):
    payload = {"ok": False, "error": {"message": message}}
    if code is not None:
        payload["error"]["code"] = code
    if extra is not None:
        payload["error"]["extra"] = extra
    return jsonify(payload), status