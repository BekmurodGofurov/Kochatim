"""
Unit tests — utils/errors.py
ok() va fail() response helperlar testlanadi.
Flask app context talab qilinadi.
"""
import pytest


@pytest.fixture(scope="module")
def flask_app():
    import os, sys
    BACKEND_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "backend"))
    if BACKEND_DIR not in sys.path:
        sys.path.insert(0, BACKEND_DIR)
    from unittest.mock import patch
    with patch("extensions.init_pool"), patch("db_init.init_db"):
        from app import create_app
        app = create_app()
        app.config["TESTING"] = True
    return app


# ─── ok() ─────────────────────────────────────────────────────────────────────

class TestOkResponse:
    def test_status_200_by_default(self, flask_app):
        with flask_app.app_context():
            from utils.errors import ok
            response, status = ok({"key": "value"})
            assert status == 200

    def test_body_has_ok_true(self, flask_app):
        with flask_app.app_context():
            from utils.errors import ok
            response, _ = ok({"x": 1})
            data = response.get_json()
            assert data["ok"] is True

    def test_data_field_contains_payload(self, flask_app):
        with flask_app.app_context():
            from utils.errors import ok
            response, _ = ok({"name": "test"})
            data = response.get_json()
            assert data["data"] == {"name": "test"}

    def test_null_data(self, flask_app):
        with flask_app.app_context():
            from utils.errors import ok
            response, _ = ok(None)
            data = response.get_json()
            assert data["data"] is None

    def test_list_data(self, flask_app):
        with flask_app.app_context():
            from utils.errors import ok
            response, _ = ok([1, 2, 3])
            data = response.get_json()
            assert data["data"] == [1, 2, 3]

    def test_custom_status_code(self, flask_app):
        with flask_app.app_context():
            from utils.errors import ok
            response, status = ok({"created": True}, status=201)
            assert status == 201

    def test_empty_dict_data(self, flask_app):
        with flask_app.app_context():
            from utils.errors import ok
            response, status = ok({})
            data = response.get_json()
            assert data["ok"] is True
            assert data["data"] == {}


# ─── fail() ───────────────────────────────────────────────────────────────────

class TestFailResponse:
    def test_status_400_by_default(self, flask_app):
        with flask_app.app_context():
            from utils.errors import fail
            _, status = fail("Bad request")
            assert status == 400

    def test_body_has_ok_false(self, flask_app):
        with flask_app.app_context():
            from utils.errors import fail
            response, _ = fail("Error")
            data = response.get_json()
            assert data["ok"] is False

    def test_error_message(self, flask_app):
        with flask_app.app_context():
            from utils.errors import fail
            response, _ = fail("User not found")
            data = response.get_json()
            assert data["error"]["message"] == "User not found"

    def test_error_without_code(self, flask_app):
        with flask_app.app_context():
            from utils.errors import fail
            response, _ = fail("Error")
            data = response.get_json()
            assert "code" not in data["error"]

    def test_error_with_code(self, flask_app):
        with flask_app.app_context():
            from utils.errors import fail
            response, _ = fail("Not found", code="NOT_FOUND")
            data = response.get_json()
            assert data["error"]["code"] == "NOT_FOUND"

    def test_error_without_extra(self, flask_app):
        with flask_app.app_context():
            from utils.errors import fail
            response, _ = fail("Error")
            data = response.get_json()
            assert "extra" not in data["error"]

    def test_error_with_extra(self, flask_app):
        with flask_app.app_context():
            from utils.errors import fail
            response, _ = fail("Server error", extra="traceback here")
            data = response.get_json()
            assert data["error"]["extra"] == "traceback here"

    def test_custom_status_401(self, flask_app):
        with flask_app.app_context():
            from utils.errors import fail
            _, status = fail("Unauthorized", 401)
            assert status == 401

    def test_custom_status_404(self, flask_app):
        with flask_app.app_context():
            from utils.errors import fail
            _, status = fail("Not found", 404)
            assert status == 404

    def test_custom_status_500(self, flask_app):
        with flask_app.app_context():
            from utils.errors import fail
            _, status = fail("Server error", 500)
            assert status == 500

    def test_all_fields_combined(self, flask_app):
        with flask_app.app_context():
            from utils.errors import fail
            response, status = fail("Conflict", 409, code="DUPLICATE", extra="detail")
            data = response.get_json()
            assert status == 409
            assert data["ok"] is False
            assert data["error"]["message"] == "Conflict"
            assert data["error"]["code"] == "DUPLICATE"
            assert data["error"]["extra"] == "detail"
