from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

kanl_link = "https://t.me/kinolar_movie_b"

kanal_check = InlineKeyboardMarkup(
    inline_keyboard=[
        [InlineKeyboardButton(text="Obuna boling", url=kanl_link)],
        [InlineKeyboardButton(text="Tekshirish", callback_data="tek")]
    ]
)