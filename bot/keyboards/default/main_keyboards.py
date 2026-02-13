from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo
from data.config import WEB_URL


# Contact so'rash keyboard
contact_kb = ReplyKeyboardMarkup(
    keyboard=[[KeyboardButton(text="📞 Telefon raqamni yuborish", request_contact=True)]],
    resize_keyboard=True,
)


# Dinamik menu konstruktori
def get_main_menu(has_cats=True, has_types=True):
    kb = ReplyKeyboardMarkup(resize_keyboard=True)
    
    web_button = KeyboardButton(text="💻 Saytni ochish", web_app=WebAppInfo(url=WEB_URL))

    if not has_cats:
        # Faqat guruh qo'shish
        kb.add(KeyboardButton(text="Yangi Guruh"))
        kb.add(web_button)
        return kb
    
    if not has_types:
        # Guruh bor, lekin nav yo'q
        kb.row(KeyboardButton(text="Yangi Guruh"), KeyboardButton(text="Yangi Nav"))
        kb.row(KeyboardButton(text="Ko'rish"), web_button)
        return kb
    
    # To'liq menu - endi "Qo'shish" tugmasi bilan
    kb.row(KeyboardButton(text="Ko'rish"), KeyboardButton(text="Qo'shish"))
    kb.row(KeyboardButton(text="Sotuv"), KeyboardButton(text="Boshqaruv"))
    kb.add(web_button)
    return kb


# Qo'shish sub-menusi
def get_add_menu():
    kb = ReplyKeyboardMarkup(resize_keyboard=True)
    kb.row(KeyboardButton(text="Yangi Guruh"), KeyboardButton(text="Yangi Nav"))
    kb.row(KeyboardButton(text="Ko'chat qo'shish"))
    kb.row(KeyboardButton(text="Asosiy menu"))
    return kb


# Eski main_manu (compat)
main_manu = get_main_menu(True, True)


new_cat = ReplyKeyboardMarkup( keyboard=[
        [
            KeyboardButton(text="Yangi Guruh")
        ]
    ],resize_keyboard=True,
)
# add_cat.py import qiladigan keyboard
new_type = ReplyKeyboardMarkup( keyboard=[
        [
            KeyboardButton(text="Yangi Nav")
        ]
    ],resize_keyboard=True,
)
new_tree = ReplyKeyboardMarkup( keyboard=[
        [
            KeyboardButton(text="Ko'chat qo'shish")
        ]
    ],resize_keyboard=True,
)


def _as_text(item):
    """
    item string bo‘lsa → o‘zi
    item dict bo‘lsa → c_name yoki t_name
    """
    if isinstance(item, str):
        return item

    if isinstance(item, dict):
        return item.get("c_name") or item.get("t_name")

    return None


def cat_keyboard(arr):
    kb = ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)

    new_cat_button = KeyboardButton(text="Yangi Gruh")

    if not arr:
        kb.add(new_cat_button)
        return kb

    buttons = []
    for item in arr:
        text = _as_text(item)
        if text:
            buttons.append(KeyboardButton(text=text))

    kb.add(*buttons)
    kb.add(new_cat_button)
    return kb


def ty_keyboard(arr):
    kb = ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)

    new_ty_button = KeyboardButton(text="Yangi Nav")

    if not arr:
        kb.add(new_ty_button)
        return kb

    buttons = []
    for item in arr:
        text = _as_text(item)
        if text:
            buttons.append(KeyboardButton(text=text))

    kb.add(*buttons)
    kb.add(new_ty_button)
    return kb


def manage_cat_inline(c_id: int):
    kb = InlineKeyboardMarkup(row_width=2)
    kb.add(
        InlineKeyboardButton(text="✏️ Tahrirlash", callback_data=f"edit_cat:{c_id}"),
        InlineKeyboardButton(text="❌ O'chirish", callback_data=f"delete_cat:{c_id}")
    )
    return kb

def manage_ty_inline(t_id: int):
    kb = InlineKeyboardMarkup(row_width=2)
    kb.add(
        InlineKeyboardButton(text="✏️ Tahrirlash", callback_data=f"edit_ty:{t_id}"),
        InlineKeyboardButton(text="❌ O'chirish", callback_data=f"delete_ty:{t_id}")
    )
    return kb

def delete_confirm_inline(item_type: str, item_id: int):
    kb = InlineKeyboardMarkup(row_width=2)
    kb.add(
        InlineKeyboardButton(text="✅ Ha, o'chirish", callback_data=f"conf_del_{item_type}:{item_id}"),
        InlineKeyboardButton(text="🚫 Yo'q", callback_data=f"cancel_del")
    )
    return kb