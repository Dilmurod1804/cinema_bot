# handlers.py (Yangi va yakuniy versiya)
from aiogram import Router, F
from aiogram.filters import CommandStart
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.exceptions import TelegramBadRequest, TelegramForbiddenError 
import re # Qo'shimcha import

from config import ADMINS
from database import (
    add_user, add_movie, get_movie_by_code, search_movies_by_title,
    delete_movie_by_id, list_movies, add_channel, remove_channel, list_channels,
    list_users, update_movie, increment_views_by_code
)
from keyboards import admin_keyboard, user_keyboard, make_subscription_markup

router = Router()

# --- States ---
class AddMovie(StatesGroup):
    title = State()
    genre = State()
    year = State()
    description = State()
    video = State()

class DeleteMovie(StatesGroup):
    movie_id = State()

class EditMovie(StatesGroup):
    movie_id = State()
    field = State()
    new_value = State()

class ChannelState(StatesGroup):
    username = State()

class SendAd(StatesGroup):
    text = State()

class SearchMovie(StatesGroup):
    code = State()

class SearchByName(StatesGroup):
    query = State()

# -------------------- Utility Functions --------------------

async def check_user_subscription(bot, user_id, channels):
    """Foydalanuvchining majburiy kanallarga obunasini tekshiradi."""
    not_subscribed = []
    for ch in channels:
        try:
            member = await bot.get_chat_member(chat_id=ch, user_id=user_id)
            if member.status in ["left", "kicked"]:
                not_subscribed.append(ch)
        except Exception:
            # Agar kanal bot topa olmasa yoki bot admin emas bo'lsa
            not_subscribed.append(ch)
    return not_subscribed

async def handle_movie_code_search(message: Message, code: str):
    """Kino kodini qidirish va yuborishning asosiy logikasi."""
    movie = get_movie_by_code(code)
    
    if not movie:
        await message.answer("❌ Bunday koddagi kino topilmadi.")
        return

    channels = list_channels()
    if channels:
        # Obuna tekshiruvi
        not_subscribed = await check_user_subscription(message.bot, message.from_user.id, channels)
        
        if not_subscribed:
            markup = make_subscription_markup(channels)
            await message.answer(
                "📣 Botdan foydalanish uchun quyidagi kanallarga obuna bo‘ling:", 
                reply_markup=markup
            )
            return

    # Obuna sharti bajarilgan yoki kanal yo'q. Kinoni yuboramiz.
    title, genre, year, description, file_id, views = movie
    
    # Ko'rishlar sonini avvalroq aniqlash
    new_views = views + 1
    
    text = f"🎬 <b>{title}</b>\n📚 Janr: {genre}\n📅 Yil: {year}\n📝 Tavsif: {description}\n👁️ Ko'rishlar: {new_views}"
    await message.answer(text)
    
    try:
        caption_text = f"🎬 {title} | Kod: <b>{code}</b>"
        
        # ✅ MUAMMO TUZATILDI: message.answer_video o'rniga message.bot.send_video ishlatildi
        await message.bot.send_video(
            chat_id=message.from_user.id,
            video=file_id,
            caption=caption_text,
            parse_mode=message.bot.default.parse_mode
        )
        increment_views_by_code(code)
    except TelegramForbiddenError:
        # Bot foydalanuvchiga xabar yubora olmasa (bloklangan)
        await message.answer("❗️ Videoni yuborishda xatolik: Bot sizga yubora olmadi. Iltimos, botni blokdan chiqaring.")
    except TelegramBadRequest as e:
        # File_ID noto'g'ri yoki Telegram serverlarida o'chirilgan
        await message.answer(f"❌ Videoni yuborishda jiddiy xatolik (File ID muammo). \nSabab: <code>{e}</code>. Adminlar yuklangan kinoni tekshirsin.")
    except Exception as e:
        # Boshqa umumiy xatolar (tarmoq uzilishi, timeout)
        await message.answer(f"❗️ Videoni yubishda noma'lum muammo yuz berdi. \nSabab: <code>{type(e).__name__}: {e}</code>")
        
# -------------------- Handlers --------------------

@router.message(CommandStart())
async def start_bot(message: Message, state: FSMContext):
    await state.clear() 
    add_user(message.from_user.id)

    if message.from_user.id in ADMINS:
        await message.answer("👋 Admin panelga xush kelibsiz!", reply_markup=admin_keyboard())
        return

    channels = list_channels()
    if not channels:
        await message.answer("🎬 Bot ishga tushdi! Kino izlashga tayyorman.", reply_markup=user_keyboard())
        return

    markup = make_subscription_markup(channels)
    await message.answer("📣 Botdan foydalanish uchun quyidagi kanallarga obuna bo‘ling:", reply_markup=markup)

# --- callback: check subs ---
@router.callback_query(F.data == "check_subs")
async def check_subscriptions(callback: CallbackQuery):
    user_id = callback.from_user.id
    channels = list_channels()
    bot = callback.message.bot
    
    not_subscribed = await check_user_subscription(bot, user_id, channels)

    if not_subscribed:
        await callback.answer("Hali barcha kanallarga obuna emassiz!", show_alert=True)
        text = "❗️ Quyidagi kanallarga obuna bo‘ling:\n" + "\n".join(not_subscribed)
        try:
             await callback.message.edit_text(text, reply_markup=make_subscription_markup(channels))
        except TelegramBadRequest:
             pass 
    else:
        await callback.answer("✅ Barchaga obuna bo‘lgansiz!", show_alert=True)
        await callback.message.answer("🎬 Endi kinolarni qidirishingiz mumkin:", reply_markup=user_keyboard())
        await callback.message.delete()


# ---------------- Admin: add movie ----------------
@router.message(F.text == "📥 Kino qo'shish")
async def admin_add_movie(message: Message, state: FSMContext):
    if message.from_user.id not in ADMINS:
        return
    await state.set_state(AddMovie.title)
    await message.answer("🎞 Sarlavha kiriting:")

@router.message(AddMovie.title)
async def add_title(message: Message, state: FSMContext):
    if message.text.lower() in ["/cancel", "bekor qilish"]:
        await state.clear()
        await message.answer("❌ Kino qo'shish bekor qilindi.", reply_markup=admin_keyboard())
        return

    await state.update_data(title=message.text)
    await state.set_state(AddMovie.genre)
    await message.answer("📚 Janr kiriting:")

@router.message(AddMovie.genre)
async def add_genre(message: Message, state: FSMContext):
    await state.update_data(genre=message.text)
    await state.set_state(AddMovie.year)
    await message.answer("📅 Yilni kiriting (misol: 2021):")

@router.message(AddMovie.year)
async def add_year(message: Message, state: FSMContext):
    if not message.text.isdigit() or len(message.text) != 4: 
        await message.answer("❗️ Iltimos, yilni to'g'ri 4 xonali raqam bilan kiriting:")
        return
    await state.update_data(year=int(message.text))
    await state.set_state(AddMovie.description)
    await message.answer("📝 Tavsif kiriting:")

@router.message(AddMovie.description)
async def add_desc(message: Message, state: FSMContext):
    await state.update_data(description=message.text)
    await state.set_state(AddMovie.video)
    await message.answer("📤 Endi videoni yuboring (fayl sifatida):")

@router.message(AddMovie.video, F.content_type.in_({'video', 'document'}))
async def add_video(message: Message, state: FSMContext):
    file_id = None
    if message.video:
        file_id = message.video.file_id
    elif message.document and message.document.mime_type and message.document.mime_type.startswith('video/'):
        file_id = message.document.file_id

    if not file_id:
        await message.answer("❗️ Videodan fayl ID ni olib bo'lmadi. Qayta urinib ko'ring.")
        return
    
    data = await state.get_data()
    title = data.get("title")
    genre = data.get("genre")
    year = data.get("year")
    description = data.get("description")
    
    try:
        movie_id, code = add_movie(title, genre, year, description, file_id)
        await message.answer(f"✅ Kino qo'shildi! Kod: <b>{code}</b>\nID: {movie_id}", reply_markup=admin_keyboard())
    except Exception as e:
        await message.answer(f"❌ Kino bazaga yozishda xatolik yuz berdi: <code>{e}</code>")
        
    await state.clear()

@router.message(AddMovie.video)
async def add_video_invalid(message: Message):
    await message.answer("❗️ Iltimos, faqat video fayl yuboring.")

# ---------------- Admin: list / delete / edit / exit ----------------
@router.message(F.text == "🎞 Kinolar ro'yxati")
async def admin_list_movies(message: Message):
    if message.from_user.id not in ADMINS:
        return
    movies = list_movies()
    if not movies:
        await message.answer("📭 Kinolar topilmadi.")
        return
    text = "🎬 Kinolar ro'yxati:\n\n"
    for m in movies:
        text += f"ID: {m[0]} | {m[1]} ({m[3]}) — Kod: <b>{m[4]}</b>\n" 
    await message.answer(text)

@router.message(F.text == "⬅️ Chiqish")
async def admin_exit(message: Message, state: FSMContext):
    if message.from_user.id not in ADMINS:
        return
    await state.clear()
    await message.answer("👋 Admin panelidan chiqildi. Endi siz foydalanuvchi klaviaturasini ko'rasiz.", reply_markup=user_keyboard())

# ... (Qolgan admin funksiyalari o'zgarishsiz qoldirildi, ular barqaror) ...

# ---------------- Channels ----------------
@router.message(F.text == "➕ Kanal qo'shish")
async def admin_add_channel_start(message: Message, state: FSMContext):
    if message.from_user.id not in ADMINS:
        return
    await state.set_state(ChannelState.username)
    await message.answer("➕ Kanal link yoki username kiriting (https://t.me/Name yoki @Name):")

@router.message(ChannelState.username)
async def admin_add_channel_save(message: Message, state: FSMContext):
    raw = message.text.strip()
    username = re.sub(r'https?://t\.me/', '@', raw, flags=re.IGNORECASE).strip()
    if not username.startswith('@'):
         username = "@" + username

    if add_channel(username):
        await message.answer(f"✅ Kanal <b>{username}</b> qo'shildi. Endi botni bu kanalga admin qilib qo'ying.")
    else:
        await message.answer("❌ Kanal allaqachon mavjud yoki xato.")
    await state.clear()

@router.message(F.text == "➖ Kanal o'chirish")
async def admin_remove_channel_start(message: Message):
    if message.from_user.id not in ADMINS:
        return
    channels = list_channels()
    if not channels:
         await message.answer("🗑 Hozirda hech qanday kanal qo'shilmagan.")
         return
         
    text = "🗑 O'chiriladigan kanal(lar) username yoki linkini kiriting:\n"
    text += "\n".join(channels)
    await message.answer(text)

@router.message(F.text.startswith(("@", "https://t.me/", "t.me/")))
async def admin_remove_channel_confirm(message: Message):
    if message.from_user.id not in ADMINS:
         return
         
    raw = message.text.strip()
    username = re.sub(r'https?://t\.me/', '@', raw, flags=re.IGNORECASE).strip()
    if not username.startswith('@'):
         username = "@" + username

    if remove_channel(username):
        await message.answer(f"✅ Kanal <b>{username}</b> o'chirildi.")
    else:
        await message.answer(f"❌ Kanal <b>{username}</b> topilmadi.")

# ---------------- Ads ----------------
@router.message(F.text == "📢 Reklama yuborish")
async def admin_send_ad_start(message: Message, state: FSMContext):
    if message.from_user.id not in ADMINS:
        return
    await state.set_state(SendAd.text)
    await message.answer("📢 Reklama matnini kiriting:")

@router.message(SendAd.text)
async def admin_send_ad_confirm(message: Message, state: FSMContext):
    text = message.html_text 
    users = list_users()
    success_count = 0
    
    for user_id in users:
        try:
            await message.bot.send_message(user_id, text)
            success_count += 1
        except TelegramForbiddenError:
            # Bot tomonidan bloklangan foydalanuvchilar
            continue
        except Exception:
            # Boshqa xatolar
            continue
            
    await message.answer(f"📢 Reklama <b>{success_count}</b> foydalanuvchiga muvaffaqiyatli yuborildi.")
    await state.clear()

# ---------------- User: search by code (tugma orqali) ----------------
@router.message(F.text == "🎬 Kino izlash")
async def user_search_start(message: Message, state: FSMContext):
    await state.set_state(SearchMovie.code)
    await message.answer("🎬 Iltimos, kinoning kodini kiriting (4 xonali raqam):")

@router.message(SearchMovie.code)
async def user_search_by_code_fsm(message: Message, state: FSMContext):
    code = message.text.strip()
    await state.clear() 
    
    if not code.isdigit() or len(code) != 4:
         await message.answer("❌ Kino kodi 4 xonali raqam bo'lishi kerak.")
         return
         
    await handle_movie_code_search(message, code)


# ⚠️ To'g'ridan-to'g'ri kodni qabul qilish
@router.message(F.text.regexp(r"^\d{4}$")) # 4 xonali raqam (kod)
async def user_search_inline_code(message: Message, state: FSMContext):
    current_state = await state.get_state()
    if current_state:
        return
    
    if message.from_user.id in ADMINS:
        return
        
    code = message.text.strip()
    await handle_movie_code_search(message, code)


# ---------------- User: search by name ----------------
@router.message(F.text == "🔎 Nom bo'yicha qidirish")
async def user_search_name_start(message: Message, state: FSMContext):
    await state.set_state(SearchByName.query)
    await message.answer("🔎 Qidiruv uchun kinoning nomidan bir qismini kiriting:")

@router.message(SearchByName.query)
async def user_search_name_result(message: Message, state: FSMContext):
    q = message.text.strip()
    await state.clear()
    
    results = search_movies_by_title(q)
    
    if not results:
        await message.answer(f"❌ '{q}' so'rovi bo'yicha natija topilmadi.")
        return
        
    text = "🔎 Topildi (eng so'nggi 20 ta):\n\n"
    for r in results[:20]:
        text += f"ID:{r[0]} | {r[1]} ({r[3]}) — Kod: <b>{r[4]}</b>\n"
        
    text += "\nKinoni ko‘rish uchun yuqoridagi <b>kodni</b> yuboring yoki 🎬 Kino izlash orqali kod bilan qidiring."
    await message.answer(text)

# -------------------- General Catch-all Handler (Oxirgi) --------------------

@router.message()
async def all_messages_handler(message: Message, state: FSMContext):
    current_state = await state.get_state()
    
    # Faqat adminlar uchun kanal o'chirish logikasi o'tib ketgan bo'lsa
    if message.from_user.id in ADMINS and not current_state:
        # Bu yerga faqat admin yuborgan, lekin hech qanday handler ushlamagan xabar keladi.
        await message.answer("❓ Tushunarsiz buyruq. Admin panelidan foydalanish uchun to'g'ri tugmalarni bosing.")
    
    if message.from_user.id not in ADMINS and not current_state:
        await message.answer("❓ Tushunarsiz buyruq. Kino izlash uchun klaviaturadagi tugmalarni ishlating.")