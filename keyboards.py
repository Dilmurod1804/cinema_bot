# keyboards.py
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton

def admin_keyboard():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="📥 Kino qo'shish")],
            [KeyboardButton(text="🎞 Kinolar ro'yxati"), KeyboardButton(text="✏️ Kino tahrirlash")],
            [KeyboardButton(text="🗑 Kino o'chirish")],
            [KeyboardButton(text="➕ Kanal qo'shish"), KeyboardButton(text="➖ Kanal o'chirish")],
            [KeyboardButton(text="📢 Reklama yuborish")],
            [KeyboardButton(text="⬅️ Chiqish")]
        ],
        resize_keyboard=True
    )

def user_keyboard():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="🎬 Kino izlash"), KeyboardButton(text="🔎 Nom bo'yicha qidirish")],
        ],
        resize_keyboard=True
    )

def make_subscription_markup(channels):
    buttons = [[InlineKeyboardButton(text=f"📡 @{ch.strip('@')}", url=f"https://t.me/{ch.strip('@')}")] for ch in channels]
    check_btn = [InlineKeyboardButton(text="✅ Tekshirish", callback_data="check_subs")]
    return InlineKeyboardMarkup(inline_keyboard=buttons + [check_btn])