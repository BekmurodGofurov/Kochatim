"""
Tests — bot/data/database.py

Bu modul `api_client.py` dan ALOHIDA, ikkinchi HTTP clienti: o'z
`get_session`, `_request` va `BackendAPIError` ga ega. Handlerlarning
ko'pchiligi aynan shuni ishlatadi (`api_client` faqat login va
hamkorlik uchun). Ikkisida ham `ensure_user` bor — `docs/bot.md` ga
qarang.

Uchta narsa alohida tekshiriladi, chunki handlerlar ularga tayanadi:

1. `get_all_cat` / `get_all_ty` ro'yxatdan faqat NOMLARNI qaytaradi —
   aiogram klaviaturalari satr kutadi, dict emas.
2. `get_cat_id` / `get_type_id` nomni ID ga aylantiradi, registr va
   bo'shliqqa qaramay, va topilmasa None beradi.
3. `c_id`/`t_name` dict bo'lib kelishi mumkin — klaviatura butun
   obyektni qaytarib qo'yadi — va funksiyalar buni ko'taradi.
"""
import pytest

from conftest import TEST_API_KEY, TEST_API_URL, TEST_U_ID

pytestmark = pytest.mark.asyncio


def ok_body(data):
    return {"ok": True, "data": data}


def fail_body(message="nope", code=None):
    err = {"message": message}
    if code:
        err["code"] = code
    return {"ok": False, "error": err}


CATS = [
    {"c_id": 1, "c_name": "Mevali daraxtlar"},
    {"c_id": 2, "c_name": "Manzarali"},
]
TYPES = [
    {"t_id": 10, "t_name": "Olma"},
    {"t_id": 11, "t_name": "Nok"},
]


# ─── _request ─────────────────────────────────────────────────────────────────

class TestRequest:
    async def test_sends_api_key(self, database, db_backend):
        db_backend.respond(payload=ok_body(None))
        await database.get_user(TEST_U_ID)
        assert db_backend.last["headers"]["X-API-KEY"] == TEST_API_KEY

    async def test_missing_config_raises(self, database):
        database.API_URL = ""
        with pytest.raises(database.BackendAPIError, match="not configured"):
            await database.get_user(TEST_U_ID)

    async def test_ok_false_raises_on_http_200(self, database, db_backend):
        db_backend.respond(status=200, payload=fail_body("User not found"))
        with pytest.raises(database.BackendAPIError):
            await database.get_user(TEST_U_ID)

    async def test_error_status_raises(self, database, db_backend):
        db_backend.respond(status=500, payload=fail_body("boom"))
        with pytest.raises(database.BackendAPIError):
            await database.get_user(TEST_U_ID)

    async def test_non_json_body_raises_backend_api_error(self, database, db_backend):
        """
        Nginx 404 HTML qaytarsa, modul uni o'z xatosiga o'raydi —
        `api_client` esa xom ValueError ni o'tkazib yuboradi. Ikki
        clientning farqi shu yerda ko'rinadi.
        """
        db_backend.respond(status=404, json_error=ValueError("not json"),
                           text="<html>404</html>")
        with pytest.raises(database.BackendAPIError, match="Not JSON"):
            await database.get_user(TEST_U_ID)

    async def test_returns_data_section(self, database, db_backend):
        db_backend.respond(payload=ok_body({"u_id": TEST_U_ID}))
        assert await database.get_user(TEST_U_ID) == {"u_id": TEST_U_ID}

    async def test_sends_query_params(self, database, db_backend):
        db_backend.respond(payload=ok_body([]))
        await database.get_all_cat_rows(TEST_U_ID)
        assert db_backend.last["params"] == {"u_id": TEST_U_ID}


# ─── Users ────────────────────────────────────────────────────────────────────

class TestUsers:
    async def test_db_start_is_a_no_op(self, database):
        assert await database.db_start() is True

    async def test_new_user_posts_to_ensure(self, database, db_backend):
        db_backend.respond(payload=ok_body({}))
        await database.new_user(TEST_U_ID, "Ali", "ali")
        assert db_backend.last["url"].endswith("/api/users/ensure")
        assert db_backend.last["json"]["u_id"] == TEST_U_ID

    async def test_ensure_user_delegates_to_new_user(self, database, db_backend):
        db_backend.respond(payload=ok_body({}))
        await database.ensure_user(TEST_U_ID, "Ali", "ali", "+998901234567", 25)
        body = db_backend.last["json"]
        assert body["u_phone"] == "+998901234567"
        assert body["u_age"] == 25

    async def test_ensure_user_does_not_send_u_photo(self, database, db_backend):
        """
        MUHIM: bu `ensure_user` u_photo ni QABUL QILMAYDI —
        `api_client.ensure_user` esa qabul qiladi. start.py avatar
        yuborish uchun api_client'dagisini import qiladi.
        """
        db_backend.respond(payload=ok_body({}))
        await database.ensure_user(TEST_U_ID, "Ali", "ali")
        assert "u_photo" not in db_backend.last["json"]

    async def test_string_u_id_is_coerced(self, database, db_backend):
        db_backend.respond(payload=ok_body({}))
        await database.new_user("123456789", "Ali")
        assert db_backend.last["json"]["u_id"] == 123456789

    async def test_get_user_puts_id_in_path(self, database, db_backend):
        db_backend.respond(payload=ok_body({}))
        await database.get_user(TEST_U_ID)
        assert db_backend.last["url"].endswith(f"/api/users/{TEST_U_ID}")


# ─── Categories ───────────────────────────────────────────────────────────────

class TestCategories:
    async def test_rows_returns_full_dicts(self, database, db_backend):
        db_backend.respond(payload=ok_body(CATS))
        assert await database.get_all_cat_rows(TEST_U_ID) == CATS

    async def test_get_all_cat_returns_names_only(self, database, db_backend):
        """aiogram klaviaturasi satr kutadi."""
        db_backend.respond(payload=ok_body(CATS))
        assert await database.get_all_cat(TEST_U_ID) == [
            "Mevali daraxtlar", "Manzarali"
        ]

    async def test_get_all_cat_empty_list(self, database, db_backend):
        db_backend.respond(payload=ok_body([]))
        assert await database.get_all_cat(TEST_U_ID) == []

    async def test_get_all_cat_handles_null_data(self, database, db_backend):
        db_backend.respond(payload=ok_body(None))
        assert await database.get_all_cat(TEST_U_ID) == []

    async def test_get_all_cat_skips_rows_without_a_name(self, database, db_backend):
        db_backend.respond(payload=ok_body([{"c_id": 1, "c_name": None},
                                            {"c_id": 2, "c_name": "Ok"}]))
        assert await database.get_all_cat(TEST_U_ID) == ["Ok"]

    async def test_get_cat_id_finds_by_name(self, database, db_backend):
        db_backend.respond(payload=ok_body(CATS))
        assert await database.get_cat_id(TEST_U_ID, "Manzarali") == 2

    async def test_get_cat_id_is_case_insensitive(self, database, db_backend):
        db_backend.respond(payload=ok_body(CATS))
        assert await database.get_cat_id(TEST_U_ID, "mAnZaRaLi") == 2

    async def test_get_cat_id_ignores_surrounding_whitespace(self, database, db_backend):
        db_backend.respond(payload=ok_body(CATS))
        assert await database.get_cat_id(TEST_U_ID, "  Manzarali  ") == 2

    async def test_get_cat_id_returns_none_when_absent(self, database, db_backend):
        db_backend.respond(payload=ok_body(CATS))
        assert await database.get_cat_id(TEST_U_ID, "Yo'q") is None

    async def test_get_cat_id_accepts_a_dict_with_c_id(self, database, db_backend):
        """Klaviatura butun qatorni qaytarib qo'ysa — HTTP so'rov kerak emas."""
        assert await database.get_cat_id(TEST_U_ID, {"c_id": 5, "c_name": "X"}) == 5
        assert db_backend.calls == []

    async def test_get_cat_id_falls_back_to_name_in_dict(self, database, db_backend):
        db_backend.respond(payload=ok_body(CATS))
        assert await database.get_cat_id(TEST_U_ID, {"c_name": "Manzarali"}) == 2

    async def test_get_cat_id_none_returns_none(self, database, db_backend):
        db_backend.respond(payload=ok_body(CATS))
        assert await database.get_cat_id(TEST_U_ID, None) is None

    async def test_new_cat_posts_name_and_user(self, database, db_backend):
        db_backend.respond(payload=ok_body({"created": True, "c_id": 3}))
        await database.new_cat(TEST_U_ID, "Yangi")
        assert db_backend.last["method"] == "POST"
        assert db_backend.last["json"] == {"u_id": TEST_U_ID, "c_name": "Yangi"}

    async def test_update_cat_puts_to_the_id(self, database, db_backend):
        db_backend.respond(payload=ok_body({"updated": True}))
        await database.update_cat(TEST_U_ID, 2, "Yangi nom")
        assert db_backend.last["method"] == "PUT"
        assert db_backend.last["url"].endswith("/api/categories/2")

    async def test_delete_cat_scopes_by_user(self, database, db_backend):
        db_backend.respond(payload=ok_body({"deleted": True}))
        await database.delete_cat(TEST_U_ID, 2)
        assert db_backend.last["method"] == "DELETE"
        assert db_backend.last["params"] == {"u_id": TEST_U_ID}


# ─── Types ────────────────────────────────────────────────────────────────────

class TestTypes:
    async def test_rows_sends_both_filters(self, database, db_backend):
        db_backend.respond(payload=ok_body(TYPES))
        await database.get_all_ty_rows(TEST_U_ID, 1)
        assert db_backend.last["params"] == {"u_id": TEST_U_ID, "c_id": 1}

    async def test_get_all_ty_returns_names_only(self, database, db_backend):
        db_backend.respond(payload=ok_body(TYPES))
        assert await database.get_all_ty(TEST_U_ID, 1) == ["Olma", "Nok"]

    async def test_get_all_ty_empty(self, database, db_backend):
        db_backend.respond(payload=ok_body([]))
        assert await database.get_all_ty(TEST_U_ID, 1) == []

    async def test_get_type_id_finds_by_name(self, database, db_backend):
        db_backend.respond(payload=ok_body(TYPES))
        assert await database.get_type_id(TEST_U_ID, 1, "Nok") == 11

    async def test_get_type_id_is_case_insensitive(self, database, db_backend):
        db_backend.respond(payload=ok_body(TYPES))
        assert await database.get_type_id(TEST_U_ID, 1, "nOk") == 11

    async def test_get_type_id_returns_none_when_absent(self, database, db_backend):
        db_backend.respond(payload=ok_body(TYPES))
        assert await database.get_type_id(TEST_U_ID, 1, "Yo'q") is None

    async def test_get_type_id_accepts_a_dict_with_t_id(self, database, db_backend):
        assert await database.get_type_id(TEST_U_ID, 1, {"t_id": 7}) == 7
        assert db_backend.calls == []

    async def test_new_ty_sends_all_fields(self, database, db_backend):
        db_backend.respond(payload=ok_body({"t_id": 12}))
        await database.new_ty(TEST_U_ID, 1, "Shaftoli", "Shirin")
        assert db_backend.last["json"] == {
            "u_id": TEST_U_ID, "c_id": 1, "t_name": "Shaftoli", "deff": "Shirin",
        }

    async def test_new_ty_unwraps_a_dict_c_id(self, database, db_backend):
        db_backend.respond(payload=ok_body({}))
        await database.new_ty(TEST_U_ID, {"c_id": 4, "c_name": "X"}, "Olcha")
        assert db_backend.last["json"]["c_id"] == 4

    async def test_new_ty_unwraps_a_dict_id_key(self, database, db_backend):
        db_backend.respond(payload=ok_body({}))
        await database.new_ty(TEST_U_ID, {"id": 6}, "Olcha")
        assert db_backend.last["json"]["c_id"] == 6

    async def test_new_ty_defaults_deff_to_none(self, database, db_backend):
        db_backend.respond(payload=ok_body({}))
        await database.new_ty(TEST_U_ID, 1, "Olcha")
        assert db_backend.last["json"]["deff"] is None

    async def test_update_ty_puts_to_the_id(self, database, db_backend):
        db_backend.respond(payload=ok_body({}))
        await database.update_ty(TEST_U_ID, 10, "Olma", "Yangi")
        assert db_backend.last["url"].endswith("/api/types/10")

    async def test_delete_ty_scopes_by_user(self, database, db_backend):
        db_backend.respond(payload=ok_body({}))
        await database.delete_ty(TEST_U_ID, 10)
        assert db_backend.last["params"] == {"u_id": TEST_U_ID}

    async def test_get_all_types_for_user(self, database, db_backend):
        db_backend.respond(payload=ok_body(TYPES))
        assert await database.get_all_types_for_user(TEST_U_ID) == TYPES
        assert db_backend.last["params"] == {"u_id": TEST_U_ID}

    async def test_get_a_ty_uses_by_id(self, database, db_backend):
        db_backend.respond(payload=ok_body(TYPES[0]))
        await database.get_a_ty(TEST_U_ID, 10)
        assert db_backend.last["url"].endswith("/api/types/by-id")

    async def test_get_type_info_uses_type_info(self, database, db_backend):
        db_backend.respond(payload=ok_body({"t_name": "Olma"}))
        await database.get_type_info(TEST_U_ID, 10)
        assert db_backend.last["url"].endswith("/api/type-info")


# ─── Seedlings ────────────────────────────────────────────────────────────────

class TestSeedlings:
    async def test_new_seedling_posts_three_grades(self, database, db_backend):
        db_backend.respond(payload=ok_body({"saved": True}))
        await database.new_seedling(TEST_U_ID, 10, 5, 3, 1)
        assert db_backend.last["json"] == {
            "u_id": TEST_U_ID, "t_id": 10,
            "quality_1": 5, "quality_2": 3, "quality_3": 1,
        }

    async def test_new_seedling_treats_none_as_zero(self, database, db_backend):
        db_backend.respond(payload=ok_body({}))
        await database.new_seedling(TEST_U_ID, 10, None, None, None)
        body = db_backend.last["json"]
        assert (body["quality_1"], body["quality_2"], body["quality_3"]) == (0, 0, 0)

    async def test_new_seedling_coerces_strings(self, database, db_backend):
        db_backend.respond(payload=ok_body({}))
        await database.new_seedling(TEST_U_ID, 10, "5", "3", "1")
        assert db_backend.last["json"]["quality_1"] == 5

    async def test_get_seedling_count_sends_both_ids(self, database, db_backend):
        db_backend.respond(payload=ok_body({"quality_1": 5}))
        await database.get_seedling_count(TEST_U_ID, 10)
        assert db_backend.last["params"] == {"u_id": TEST_U_ID, "t_id": 10}

    async def test_insufficient_stock_raises(self, database, db_backend):
        db_backend.respond(status=400,
                           payload=fail_body("Yetarli ko'chat yo'q",
                                             code="INSUFFICIENT_STOCK"))
        with pytest.raises(database.BackendAPIError, match="INSUFFICIENT_STOCK"):
            await database.new_seedling(TEST_U_ID, 10, 1, 1, 1)


# ─── Images ───────────────────────────────────────────────────────────────────

class TestImages:
    async def test_add_new_img_posts_url(self, database, db_backend):
        db_backend.respond(payload=ok_body({"saved": True}))
        await database.add_new_img(10, "AgACAgIAAxk")
        assert db_backend.last["json"] == {"t_id": 10, "i_url": "AgACAgIAAxk"}

    async def test_get_img_url_sends_t_id(self, database, db_backend):
        db_backend.respond(payload=ok_body("https://i.ibb.co/a.png"))
        assert await database.get_img_url(10) == "https://i.ibb.co/a.png"
        assert db_backend.last["params"] == {"t_id": 10}

    async def test_missing_image_returns_none(self, database, db_backend):
        db_backend.respond(payload=ok_body(None))
        assert await database.get_img_url(999) is None


# ─── Sales ────────────────────────────────────────────────────────────────────

class TestSales:
    async def test_add_sale_sends_every_field(self, database, db_backend):
        db_backend.respond(payload=ok_body({"saved": True}))
        await database.add_sale(TEST_U_ID, 1, 10, 5, 3, 1, 150000)
        assert db_backend.last["json"] == {
            "u_id": TEST_U_ID, "c_id": 1, "t_id": 10,
            "q1_sold": 5, "q2_sold": 3, "q3_sold": 1, "price": 150000,
        }

    async def test_add_sale_defaults_quantities_to_zero(self, database, db_backend):
        db_backend.respond(payload=ok_body({}))
        await database.add_sale(TEST_U_ID, 1, 10)
        body = db_backend.last["json"]
        assert (body["q1_sold"], body["q2_sold"], body["q3_sold"]) == (0, 0, 0)

    async def test_add_sale_passes_price_through_unconverted(self, database, db_backend):
        """
        price int() ga o'tkazilmaydi — backend o'zi tekshiradi va
        yaroqsiz bo'lsa 400 beradi.
        """
        db_backend.respond(payload=ok_body({}))
        await database.add_sale(TEST_U_ID, 1, 10, price=None)
        assert db_backend.last["json"]["price"] is None

    async def test_oversell_raises(self, database, db_backend):
        db_backend.respond(status=400,
                           payload=fail_body("Yetarli ko'chat yo'q",
                                             code="INSUFFICIENT_STOCK"))
        with pytest.raises(database.BackendAPIError):
            await database.add_sale(TEST_U_ID, 1, 10, 999)

    async def test_type_not_owned_raises(self, database, db_backend):
        db_backend.respond(status=404,
                           payload=fail_body("Type not found", code="NOT_FOUND"))
        with pytest.raises(database.BackendAPIError, match="NOT_FOUND"):
            await database.add_sale(TEST_U_ID, 1, 999, 1)
