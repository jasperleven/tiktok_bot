import asyncio
import os
import aiohttp
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
TIKTOK_CLIENT_KEY = os.getenv("TIKTOK_CLIENT_KEY")
TIKTOK_CLIENT_SECRET = os.getenv("TIKTOK_CLIENT_SECRET")
TIKTOK_REDIRECT_URI = os.getenv("TIKTOK_REDIRECT_URI")

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())

# Хранилище токенов аккаунтов { open_id: { access_token, display_name } }
accounts = {}

class PostStates(StatesGroup):
    waiting_video    = State()
    waiting_caption  = State()
    waiting_hashtags = State()
    waiting_accounts = State()

# =============================================================================
# /start
# =============================================================================
@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    await message.answer(
        "👋 TikTok Auto Poster\n\n"
        "Команды:\n"
        "/post — опубликовать видео\n"
        "/accounts — список подключённых аккаунтов\n"
        "/connect — подключить новый аккаунт"
    )

# =============================================================================
# /connect — OAuth авторизация аккаунта
# =============================================================================
@dp.message(Command("connect"))
async def cmd_connect(message: types.Message):
    oauth_url = (
        f"https://www.tiktok.com/v2/auth/authorize/"
        f"?client_key={TIKTOK_CLIENT_KEY}"
        f"&scope=user.info.basic,video.publish,video.upload"
        f"&response_type=code"
        f"&redirect_uri={TIKTOK_REDIRECT_URI}"
        f"&state={message.from_user.id}"
    )
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔗 Авторизовать аккаунт TikTok", url=oauth_url)]
    ])
    await message.answer(
        "Нажми кнопку ниже, авторизуйся в TikTok и скопируй код из адресной строки после редиректа.\n"
        "Затем отправь его сюда командой:\n`/token КОД`",
        reply_markup=keyboard,
        parse_mode="Markdown"
    )

# =============================================================================
# /token CODE — обмен кода на access token
# =============================================================================
@dp.message(Command("token"))
async def cmd_token(message: types.Message):
    parts = message.text.split(maxsplit=1)
    if len(parts) < 2:
        await message.answer("Использование: /token КОД")
        return

    code = parts[1].strip()
    await message.answer("⏳ Получаю токен...")

    async with aiohttp.ClientSession() as session:
        resp = await session.post(
            "https://open.tiktokapis.com/v2/oauth/token/",
            data={
                "client_key":     TIKTOK_CLIENT_KEY,
                "client_secret":  TIKTOK_CLIENT_SECRET,
                "code":           code,
                "grant_type":     "authorization_code",
                "redirect_uri":   TIKTOK_REDIRECT_URI,
            },
            headers={"Content-Type": "application/x-www-form-urlencoded"}
        )
        data = await resp.json()

    if "access_token" not in data:
        await message.answer(f"❌ Ошибка: {data}")
        return

    access_token = data["access_token"]
    open_id      = data["open_id"]

    # Получаем имя аккаунта
    async with aiohttp.ClientSession() as session:
        resp = await session.get(
            "https://open.tiktokapis.com/v2/user/info/?fields=display_name",
            headers={"Authorization": f"Bearer {access_token}"}
        )
        user_data = await resp.json()

    display_name = (
        user_data.get("data", {}).get("user", {}).get("display_name", open_id)
    )

    accounts[open_id] = {
        "access_token": access_token,
        "display_name": display_name
    }

    await message.answer(f"✅ Аккаунт подключён: **{display_name}**", parse_mode="Markdown")

# =============================================================================
# /accounts — список подключённых аккаунтов
# =============================================================================
@dp.message(Command("accounts"))
async def cmd_accounts(message: types.Message):
    if not accounts:
        await message.answer("Нет подключённых аккаунтов. Используй /connect")
        return
    text = "📋 Подключённые аккаунты:\n\n"
    for open_id, info in accounts.items():
        text += f"• {info['display_name']} (`{open_id}`)\n"
    await message.answer(text, parse_mode="Markdown")

# =============================================================================
# /post — начало публикации
# =============================================================================
@dp.message(Command("post"))
async def cmd_post(message: types.Message, state: FSMContext):
    if not accounts:
        await message.answer("Сначала подключи аккаунты через /connect")
        return
    await state.set_state(PostStates.waiting_video)
    await message.answer("📹 Отправь видео для публикации")

@dp.message(PostStates.waiting_video, F.video)
async def got_video(message: types.Message, state: FSMContext):
    await state.update_data(file_id=message.video.file_id)
    await state.set_state(PostStates.waiting_caption)
    await message.answer("✏️ Напиши описание для видео")

@dp.message(PostStates.waiting_caption)
async def got_caption(message: types.Message, state: FSMContext):
    await state.update_data(caption=message.text)
    await state.set_state(PostStates.waiting_hashtags)
    await message.answer("🏷 Напиши хэштеги через пробел (например: #тренд #видео)\nИли отправь — чтобы пропустить")

@dp.message(PostStates.waiting_hashtags)
async def got_hashtags(message: types.Message, state: FSMContext):
    hashtags = "" if message.text == "—" else message.text
    await state.update_data(hashtags=hashtags)
    await state.set_state(PostStates.waiting_accounts)

    # Показываем кнопки выбора аккаунтов
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(
            text=f"{'✅' if False else '☐'} {info['display_name']}",
            callback_data=f"acc_{open_id}"
        )]
        for open_id, info in accounts.items()
    ] + [[InlineKeyboardButton(text="🚀 Опубликовать", callback_data="publish")]])

    await state.update_data(selected_accounts=[])
    await message.answer("👤 Выбери аккаунты для публикации:", reply_markup=keyboard)

@dp.callback_query(F.data.startswith("acc_"))
async def toggle_account(callback: types.CallbackQuery, state: FSMContext):
    open_id = callback.data.replace("acc_", "")
    data = await state.get_data()
    selected = data.get("selected_accounts", [])

    if open_id in selected:
        selected.remove(open_id)
    else:
        selected.append(open_id)

    await state.update_data(selected_accounts=selected)

    # Обновляем кнопки
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(
            text=f"{'✅' if oid in selected else '☐'} {info['display_name']}",
            callback_data=f"acc_{oid}"
        )]
        for oid, info in accounts.items()
    ] + [[InlineKeyboardButton(text="🚀 Опубликовать", callback_data="publish")]])

    await callback.message.edit_reply_markup(reply_markup=keyboard)
    await callback.answer()

@dp.callback_query(F.data == "publish")
async def publish_video(callback: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()
    selected = data.get("selected_accounts", [])

    if not selected:
        await callback.answer("Выбери хотя бы один аккаунт!", show_alert=True)
        return

    await callback.message.answer("⏳ Публикую...")
    await state.clear()

    # Скачиваем видео из Telegram
    file = await bot.get_file(data["file_id"])
    file_url = f"https://api.telegram.org/file/bot{BOT_TOKEN}/{file.file_path}"

    caption   = data.get("caption", "")
    hashtags  = data.get("hashtags", "")
    full_text = f"{caption}\n{hashtags}".strip()

    results = []
    for open_id in selected:
        acc = accounts[open_id]
        success, msg = await post_to_tiktok(acc["access_token"], file_url, full_text)
        status = "✅" if success else "❌"
        results.append(f"{status} {acc['display_name']}: {msg}")

    await callback.message.answer("📊 Результат:\n\n" + "\n".join(results))

# =============================================================================
# Публикация видео в TikTok
# =============================================================================
async def post_to_tiktok(access_token, video_url, title):
    try:
        async with aiohttp.ClientSession() as session:
            # Инициализируем загрузку
            resp = await session.post(
                "https://open.tiktokapis.com/v2/post/publish/video/init/",
                json={
                    "post_info": {
                        "title":        title[:150],
                        "privacy_level": "SELF_ONLY",  # для теста — только ты видишь
                        "disable_duet":  False,
                        "disable_comment": False,
                        "disable_stitch": False,
                    },
                    "source_info": {
                        "source":    "PULL_FROM_URL",
                        "video_url": video_url,
                    }
                },
                headers={
                    "Authorization": f"Bearer {access_token}",
                    "Content-Type":  "application/json"
                }
            )
            result = await resp.json()

        if result.get("error", {}).get("code") != "ok":
            return False, str(result.get("error", result))

        return True, "опубликовано"

    except Exception as e:
        return False, str(e)

# =============================================================================
# Запуск
# =============================================================================
async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())