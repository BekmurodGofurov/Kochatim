"""
Integration tests — api/public.py

GET /api/v1/public/categories — autentifikatsiyasiz ochiq endpoint.
Ro'yxatga olinishi `public_bp` orqali, `api_bp` emas, shuning uchun
url_prefix="/api" qo'llanmaydi va to'liq yo'l qo'lda yozilgan.
"""
from unittest.mock import patch

import psycopg2
import pytest


class TestPublicCategories:
    URL = "/api/v1/public/categories"

    def test_returns_categories(self, client):
        rows = [{"id": 1, "name": "Mevali"}, {"id": 2, "name": "Manzarali"}]
        with patch("api.public.fetch_all", return_value=rows):
            resp = client.get(self.URL)
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["ok"] is True
        assert data["data"] == rows

    def test_empty_result_returns_empty_list(self, client):
        with patch("api.public.fetch_all", return_value=[]):
            resp = client.get(self.URL)
        assert resp.status_code == 200
        assert resp.get_json()["data"] == []

    def test_needs_no_auth(self, client):
        """Ochiq endpoint — landing sahifa uchun."""
        with patch("api.public.fetch_all", return_value=[]):
            resp = client.get(self.URL)
        assert resp.status_code == 200

    def test_aliases_columns_to_id_and_name(self, client):
        with patch("api.public.fetch_all", return_value=[]) as mock_fetch:
            client.get(self.URL)
        query = mock_fetch.call_args[0][0]
        assert "c_id AS id" in query
        assert "c_name AS name" in query

    def test_sorted_by_name(self, client):
        with patch("api.public.fetch_all", return_value=[]) as mock_fetch:
            client.get(self.URL)
        assert "ORDER BY c_name ASC" in mock_fetch.call_args[0][0]

    def test_exposes_no_owner_ids(self, client):
        """
        Ochiq ro'yxat u_id qaytarmasligi kerak — aks holda har bir
        bog'bonning Telegram ID'si anonim tarzda yig'ilib ketadi.
        """
        with patch("api.public.fetch_all", return_value=[]) as mock_fetch:
            client.get(self.URL)
        assert "u_id" not in mock_fetch.call_args[0][0]

    def test_db_failure_returns_500_with_handled_message(self, client):
        """Bu endpoint xatoni o'zi ushlaydi va 500 bilan javob beradi."""
        with patch("api.public.fetch_all",
                   side_effect=psycopg2.OperationalError("db down")):
            resp = client.get(self.URL)
        assert resp.status_code == 500
        data = resp.get_json()
        assert data["ok"] is False
        assert data["error"]["message"] == "Failed to fetch categories"

    def test_post_is_not_allowed(self, client):
        resp = client.post(self.URL, json={})
        assert resp.status_code in (405, 500)
