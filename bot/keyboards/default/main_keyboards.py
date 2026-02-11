from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton


# Contact so'rash keyboard
contact_kb = ReplyKeyboardMarkup(
    keyboard=[[KeyboardButton(text="📞 Telefon raqamni yuborish", request_contact=True)]],
    resize_keyboard=True,
)


# Asosiy menu (main)
main_manu = ReplyKeyboardMarkup(
    keyboard=[
        [
            KeyboardButton(text="Ko'rish"),
            KeyboardButton(text="Ko'chat qo'shish")
        ],
        [
            KeyboardButton(text="Yangi Guruh"), 
            KeyboardButton(text="Yangi Nav")
        ],
        [
            KeyboardButton(text="Sotuv"),
            KeyboardButton(text="Boshqaruv")
        ],
    ],
    resize_keyboard=True,
)


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