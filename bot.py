import asyncio
import os
import json
import threading
import aiohttp
from urllib.parse import urlparse, parse_qs
from http.server import HTTPServer, BaseHTTPRequestHandler
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
TIKTOK_CLIENT_KEY = os.getenv("TIKTOK_CLIENT_KEY")
TIKTOK_CLIENT_SECRET = os.getenv("TIKTOK_CLIENT_SECRET")
TIKTOK_REDIRECT_URI = os.getenv("TIKTOK_REDIRECT_URI")
MARKETING_TOKEN = os.getenv("TIKTOK_MARKETING_TOKEN")
MARKETING_APP_ID = os.getenv("TIKTOK_APP_ID")
MARKETING_SECRET = os.getenv("TIKTOK_MARKETING_SECRET", "823db7c1b59d8e9184053ace981d0c1bbdbba1c7")

ACCOUNTS_FILE = "accounts.json"
ADS_ACCOUNTS_FILE = "ads_accounts.json"

ADVERTISER_IDS = [
    "7379547391218696193","7380323349555413008","7390291557712298001",
    "7441163654311165969","7458571671717429249","7467552788675854353",
    "7467552998789578768","7467553177400147985","7467553366952935441",
    "7467553550734901264","7470066457113083905","7473561071866134529",
    "7481290249352642576","7496487210787717138","7505007920823107591",
    "7505007952001253377","7505009554032345096","7522063277921288200",
    "7525368248519507975","7525370413484867592","7594384691119734801",
    "7608919922311331856","7610323536325902352","7610323651145269264",
    "7610324072874049553","7628935051379752978","7632400068336500737",
    "7636704658911805460","7636704984830230548","7636706608449617941",
    "7636707477756805141","7636707899250655252","7636708554946248725",
    "7636708691615268884","7636708912552493076","7636709412069179412",
    "7636710982693470229","7643732056840765457","7647080900043505684",
    "7647081382459670549","7652299468439765012","7652299641001787412",
    "7652299857702961172"
]

OBJECTIVES = {
    "🎯 Охват (Reach)": "REACH",
    "🌐 Трафик (Traffic)": "TRAFFIC",
    "▶️ Просмотры видео": "VIDEO_VIEWS",
    "📋 Лидогенерация": "LEAD_GENERATION",
    "✅ Конверсии": "CONVERSIONS",
    "📱 Установки приложения": "APP_PROMOTION",
    "🛒 Продажи": "SHOPPING",
}

COUNTRIES = {
    "🇷🇺 Россия": 2017370,
    "🇧🇾 Беларусь": 630336,
    "🇺🇦 Украина": 690791,
    "🇰🇿 Казахстан": 1522867,
    "🇺🇿 Узбекистан": 1512440,
    "🇩🇪 Германия": 2921044,
    "🇺🇸 США": 6252001,
    "🇬🇧 Великобритания": 2635167,
    "🇵🇱 Польша": 798544,
}

def load_accounts():
    if os.path.exists(ACCOUNTS_FILE):
        with open(ACCOUNTS_FILE, "r") as f:
            return json.load(f)
    return {}

def save_accounts(accs):
    with open(ACCOUNTS_FILE, "w") as f:
        json.dump(accs, f)

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())
accounts = load_accounts()

class PostStates(StatesGroup):
    waiting_video    = State()
    waiting_caption  = State()
    waiting_hashtags = State()
    waiting_accounts = State()
    waiting_code     = State()

class CampaignStates(StatesGroup):
    campaign_name     = State()
    campaign_objective= State()
    budget_mode       = State()
    budget_amount     = State()
    adgroup_name      = State()
    placement         = State()
    geo               = State()
    schedule_start    = State()
    schedule_end      = State()
    video_upload      = State()
    ad_text           = State()
    ad_url            = State()
    select_advertisers= State()
    confirm           = State()

async def exchange_code(code, telegram_user_id):
    async with aiohttp.ClientSession() as session:
        resp = await session.post(
            "https://open.tiktokapis.com/v2/oauth/token/",
            data={
                "client_key":    TIKTOK_CLIENT_KEY,
                "client_secret": TIKTOK_CLIENT_SECRET,
                "code":          code,
                "grant_type":    "authorization_code",
                "redirect_uri":  TIKTOK_REDIRECT_URI,
            },
            headers={"Content-Type": "application/x-www-form-urlencoded"}
        )
        data = await resp.json()

    if "access_token" not in data:
        await bot.send_message(telegram_user_id, f"❌ Ошибка авторизации: {data}")
        return

    access_token = data["access_token"]
    open_id = data["open_id"]

    async with aiohttp.ClientSession() as session:
        resp = await session.get(
            "https://open.tiktokapis.com/v2/user/info/?fields=display_name",
            headers={"Authorization": f"Bearer {access_token}"}
        )
        user_data = await resp.json()

    display_name = user_data.get("data", {}).get("user", {}).get("display_name", open_id)
    accounts[open_id] = {"access_token": access_token, "display_name": display_name}
    save_accounts(accounts)
    await bot.send_message(telegram_user_id, f"✅ Аккаунт подключён: *{display_name}*", parse_mode="Markdown")

class CallbackHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        parsed = urlparse(self.path)
        params = parse_qs(parsed.query)
        if parsed.path == "/callback" and "code" in params and "state" in params:
            code = params["code"][0]
            telegram_user_id = int(params["state"][0])
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b"<html><body><h2>Authorization successful!</h2><p>You can close this tab and return to Telegram.</p></body></html>")
            asyncio.run_coroutine_threadsafe(exchange_code(code, telegram_user_id), loop)
        else:
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b"OK")
    def log_message(self, format, *args):
        pass

def run_web():
    port = int(os.environ.get("PORT", 8080))
    server = HTTPServer(("0.0.0.0", port), CallbackHandler)
    server.serve_forever()

# ===== КОМАНДЫ =====

@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    await message.answer(
        "👋 *TikTok Auto Poster & Ads Manager*\n\n"
        "📱 *Постинг видео:*\n"
        "/connect — подключить TikTok аккаунт\n"
        "/accounts — список аккаунтов\n"
        "/post — опубликовать видео\n\n"
        "📢 *Реклама:*\n"
        "/newcampaign — создать рекламную кампанию\n"
        "/status — статус последней публикации",
        parse_mode="Markdown"
    )

@dp.message(Command("connect"))
async def cmd_connect(message: types.Message, state: FSMContext):
    oauth_url = (
        f"https://www.tiktok.com/v2/auth/authorize/"
        f"?client_key={TIKTOK_CLIENT_KEY}"
        f"&scope=user.info.basic,video.publish,video.upload"
        f"&response_type=code"
        f"&redirect_uri={TIKTOK_REDIRECT_URI}"
        f"&state={message.from_user.id}"
    )
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔗 Подключить TikTok аккаунт", url=oauth_url)]
    ])
    await state.set_state(PostStates.waiting_code)
    await message.answer(
        "1. Нажми кнопку ниже для авторизации\n"
        "2. После редиректа скопируй полный URL из браузера\n"
        "3. Отправь его сюда",
        reply_markup=keyboard
    )

@dp.message(PostStates.waiting_code)
async def got_code(message: types.Message, state: FSMContext):
    import re
    text = message.text.strip()
    if "code=" in text:
        match = re.search(r'code=([^&\s]+)', text)
        if match:
            code = match.group(1)
        else:
            await message.answer("❌ Не удалось извлечь code. Попробуй ещё раз.")
            return
    else:
        code = text
    await state.clear()
    await message.answer("⏳ Получаю токен...")
    await exchange_code(code, message.from_user.id)

@dp.message(Command("accounts"))
async def cmd_accounts(message: types.Message):
    if not accounts:
        await message.answer("Нет подключённых аккаунтов. Используй /connect")
        return
    text = "📋 *Подключённые аккаунты:*\n\n"
    for open_id, info in accounts.items():
        text += f"• {info['display_name']} (`{open_id}`)\n"
    await message.answer(text, parse_mode="Markdown")

@dp.message(Command("status"))
async def cmd_status(message: types.Message):
    parts = message.text.split(maxsplit=1)
    if len(parts) < 2:
        await message.answer("Использование: /status PUBLISH_ID")
        return
    publish_id = parts[1].strip()
    if not accounts:
        await message.answer("Нет подключённых аккаунтов.")
        return
    access_token = list(accounts.values())[0]["access_token"]
    async with aiohttp.ClientSession() as session:
        resp = await session.post(
            "https://open.tiktokapis.com/v2/post/publish/status/fetch/",
            json={"publish_id": publish_id},
            headers={"Authorization": f"Bearer {access_token}", "Content-Type": "application/json"}
        )
        data = await resp.json()
    await message.answer(f"📊 Статус:\n`{json.dumps(data, indent=2)}`", parse_mode="Markdown")

# ===== ПОСТИНГ ВИДЕО =====

@dp.message(Command("post"))
async def cmd_post(message: types.Message, state: FSMContext):
    if not accounts:
        await message.answer("Сначала подключи аккаунт через /connect")
        return
    await state.set_state(PostStates.waiting_video)
    await message.answer("📹 Отправь видео")

@dp.message(PostStates.waiting_video, F.document)
async def got_video_doc(message: types.Message, state: FSMContext):
    await state.update_data(file_id=message.document.file_id)
    await state.set_state(PostStates.waiting_caption)
    await message.answer("✏️ Введи описание видео")

@dp.message(PostStates.waiting_video, F.video)
async def got_video(message: types.Message, state: FSMContext):
    await state.update_data(file_id=message.video.file_id)
    await state.set_state(PostStates.waiting_caption)
    await message.answer("✏️ Введи описание видео")

@dp.message(PostStates.waiting_caption)
async def got_caption(message: types.Message, state: FSMContext):
    await state.update_data(caption=message.text)
    await state.set_state(PostStates.waiting_hashtags)
    await message.answer("🏷 Введи хэштеги через пробел (например #тренд #видео)\nИли отправь — чтобы пропустить")

@dp.message(PostStates.waiting_hashtags)
async def got_hashtags(message: types.Message, state: FSMContext):
    hashtags = "" if message.text == "—" else message.text
    await state.update_data(hashtags=hashtags)
    await state.set_state(PostStates.waiting_accounts)
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=f"☐ {info['display_name']}", callback_data=f"acc_{oid}")]
        for oid, info in accounts.items()
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
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=f"{'✅' if oid in selected else '☐'} {info['display_name']}", callback_data=f"acc_{oid}")]
        for oid, info in accounts.items()
    ] + [[InlineKeyboardButton(text="🚀 Опубликовать", callback_data="publish")]])
    try:
        await callback.message.edit_reply_markup(reply_markup=keyboard)
    except Exception:
        pass
    await callback.answer()

@dp.callback_query(F.data == "publish")
async def publish_video(callback: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()
    selected = data.get("selected_accounts", [])
    if not selected:
        await callback.answer("Выбери хотя бы один аккаунт!", show_alert=True)
        return
    if "file_id" not in data:
        await callback.message.answer("❌ Сессия истекла. Начни заново с /post")
        await state.clear()
        return
    await callback.message.answer("⏳ Публикую...")
    await state.clear()
    caption = data.get("caption", "")
    hashtags = data.get("hashtags", "")
    full_text = f"{caption}\n{hashtags}".strip()
    results = []
    for open_id in selected:
        acc = accounts[open_id]
        success, msg = await post_to_tiktok(acc["access_token"], data["file_id"], full_text)
        status = "✅" if success else "❌"
        results.append(f"{status} {acc['display_name']}: {msg}")
    await callback.message.answer("📊 Результат:\n\n" + "\n".join(results))

async def post_to_tiktok(access_token, file_id, title):
    try:
        file = await bot.get_file(file_id)
        file_url = f"https://api.telegram.org/file/bot{BOT_TOKEN}/{file.file_path}"
        async with aiohttp.ClientSession() as session:
            async with session.get(file_url) as resp:
                video_bytes = await resp.read()
            file_size = len(video_bytes)
            init_resp = await session.post(
                'https://open.tiktokapis.com/v2/post/publish/video/init/',
                json={
                    'post_info': {'title': title[:150], 'privacy_level': 'SELF_ONLY', 'disable_duet': False, 'disable_comment': False, 'disable_stitch': False},
                    'source_info': {'source': 'FILE_UPLOAD', 'video_size': file_size, 'chunk_size': file_size, 'total_chunk_count': 1}
                },
                headers={'Authorization': f'Bearer {access_token}', 'Content-Type': 'application/json'}
            )
            init_data = await init_resp.json()
            if init_data.get('error', {}).get('code') != 'ok':
                return False, str(init_data.get('error', init_data))
            upload_url = init_data['data']['upload_url']
            publish_id = init_data['data']['publish_id']
            upload_resp = await session.put(
                upload_url, data=video_bytes,
                headers={'Content-Type': 'video/mp4', 'Content-Range': f'bytes 0-{file_size-1}/{file_size}', 'Content-Length': str(file_size)}
            )
            if upload_resp.status not in [200, 201, 206]:
                return False, f'Ошибка загрузки: {upload_resp.status}'
            return True, f'опубликовано (publish_id: {publish_id})'
    except Exception as e:
        return False, str(e)

# ===== СОЗДАНИЕ РЕКЛАМНОЙ КАМПАНИИ =====

@dp.message(Command("newcampaign"))
async def cmd_new_campaign(message: types.Message, state: FSMContext):
    await state.set_state(CampaignStates.campaign_name)
    await message.answer(
        "📢 *Создание рекламной кампании*\n\n"
        "Шаг 1/10 — Введи название кампании:",
        parse_mode="Markdown",
        reply_markup=ReplyKeyboardRemove()
    )

@dp.message(CampaignStates.campaign_name)
async def got_campaign_name(message: types.Message, state: FSMContext):
    await state.update_data(campaign_name=message.text)
    await state.set_state(CampaignStates.campaign_objective)
    keyboard = ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text=k)] for k in OBJECTIVES.keys()],
        resize_keyboard=True, one_time_keyboard=True
    )
    await message.answer("Шаг 2/10 — Выбери цель рекламы:", reply_markup=keyboard)

@dp.message(CampaignStates.campaign_objective)
async def got_objective(message: types.Message, state: FSMContext):
    if message.text not in OBJECTIVES:
        await message.answer("Выбери цель из списка ниже 👇")
        return
    await state.update_data(objective=OBJECTIVES[message.text], objective_name=message.text)
    await state.set_state(CampaignStates.budget_mode)
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="📅 Дневной бюджет")],
            [KeyboardButton(text="💰 Общий бюджет")],
        ],
        resize_keyboard=True, one_time_keyboard=True
    )
    await message.answer("Шаг 3/10 — Тип бюджета кампании:", reply_markup=keyboard)

@dp.message(CampaignStates.budget_mode)
async def got_budget_mode(message: types.Message, state: FSMContext):
    if message.text == "📅 Дневной бюджет":
        mode = "BUDGET_MODE_DAY"
    elif message.text == "💰 Общий бюджет":
        mode = "BUDGET_MODE_TOTAL"
    else:
        await message.answer("Выбери тип бюджета из списка 👇")
        return
    await state.update_data(budget_mode=mode)
    await state.set_state(CampaignStates.budget_amount)
    await message.answer("Шаг 4/10 — Введи сумму бюджета (в USD, минимум 50):", reply_markup=ReplyKeyboardRemove())

@dp.message(CampaignStates.budget_amount)
async def got_budget_amount(message: types.Message, state: FSMContext):
    try:
        amount = float(message.text.replace(",", "."))
        if amount < 50:
            await message.answer("❌ Минимальный бюджет 50 USD. Введи сумму ещё раз:")
            return
    except ValueError:
        await message.answer("❌ Введи число. Например: 100")
        return
    await state.update_data(budget=amount)
    await state.set_state(CampaignStates.adgroup_name)
    await message.answer("Шаг 5/10 — Введи название группы объявлений:")

@dp.message(CampaignStates.adgroup_name)
async def got_adgroup_name(message: types.Message, state: FSMContext):
    await state.update_data(adgroup_name=message.text)
    await state.set_state(CampaignStates.placement)
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="🎵 Только TikTok")],
            [KeyboardButton(text="🌐 Автоматически (все площадки)")],
        ],
        resize_keyboard=True, one_time_keyboard=True
    )
    await message.answer("Шаг 6/10 — Плейсменты:", reply_markup=keyboard)

@dp.message(CampaignStates.placement)
async def got_placement(message: types.Message, state: FSMContext):
    if message.text == "🎵 Только TikTok":
        placement_type = "PLACEMENT_TYPE_NORMAL"
        placements = ["PLACEMENT_TIKTOK"]
    elif message.text == "🌐 Автоматически (все площадки)":
        placement_type = "PLACEMENT_TYPE_AUTOMATIC"
        placements = []
    else:
        await message.answer("Выбери плейсмент из списка 👇")
        return
    await state.update_data(placement_type=placement_type, placements=placements)
    await state.set_state(CampaignStates.geo)
    keyboard = ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text=k)] for k in COUNTRIES.keys()],
        resize_keyboard=True, one_time_keyboard=True
    )
    await message.answer("Шаг 7/10 — Выбери страну таргетинга:", reply_markup=keyboard)

@dp.message(CampaignStates.geo)
async def got_geo(message: types.Message, state: FSMContext):
    if message.text not in COUNTRIES:
        await message.answer("Выбери страну из списка 👇")
        return
    await state.update_data(geo=COUNTRIES[message.text], geo_name=message.text)
    await state.set_state(CampaignStates.schedule_start)
    await message.answer(
        "Шаг 8/10 — Введи дату и время начала кампании\n"
        "Формат: `YYYY-MM-DD HH:MM:SS`\n"
        "Например: `2026-06-20 10:00:00`",
        reply_markup=ReplyKeyboardRemove(),
        parse_mode="Markdown"
    )

@dp.message(CampaignStates.schedule_start)
async def got_schedule_start(message: types.Message, state: FSMContext):
    await state.update_data(schedule_start=message.text)
    await state.set_state(CampaignStates.schedule_end)
    keyboard = ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="♾ Без даты окончания")]],
        resize_keyboard=True, one_time_keyboard=True
    )
    await message.answer(
        "Дата и время окончания кампании\n"
        "Формат: `YYYY-MM-DD HH:MM:SS`\n"
        "Или нажми кнопку чтобы не устанавливать:",
        reply_markup=keyboard,
        parse_mode="Markdown"
    )

@dp.message(CampaignStates.schedule_end)
async def got_schedule_end(message: types.Message, state: FSMContext):
    end = None if message.text == "♾ Без даты окончания" else message.text
    await state.update_data(schedule_end=end)
    await state.set_state(CampaignStates.video_upload)
    await message.answer("Шаг 9/10 — Отправь видео для рекламного объявления:", reply_markup=ReplyKeyboardRemove())

@dp.message(CampaignStates.video_upload, F.video | F.document)
async def got_campaign_video(message: types.Message, state: FSMContext):
    file_id = message.document.file_id if message.document else message.video.file_id
    await state.update_data(video_file_id=file_id)
    await state.set_state(CampaignStates.ad_text)
    await message.answer("Текст объявления (до 100 символов):")

@dp.message(CampaignStates.ad_text)
async def got_ad_text(message: types.Message, state: FSMContext):
    await state.update_data(ad_text=message.text[:100])
    await state.set_state(CampaignStates.ad_url)
    await message.answer("Ссылка на лендинг (URL):")

@dp.message(CampaignStates.ad_url)
async def got_ad_url(message: types.Message, state: FSMContext):
    await state.update_data(ad_url=message.text)
    await state.set_state(CampaignStates.select_advertisers)

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=f"☐ {adv_id[-6:]}", callback_data=f"adv_{adv_id}")]
        for adv_id in ADVERTISER_IDS[:20]
    ] + [
        [InlineKeyboardButton(text=f"☐ {adv_id[-6:]}", callback_data=f"adv_{adv_id}")]
        for adv_id in ADVERTISER_IDS[20:]
    ] + [
        [InlineKeyboardButton(text="✅ Выбрать все", callback_data="adv_all")],
        [InlineKeyboardButton(text="🚀 Создать кампанию", callback_data="create_campaign")]
    ])
    await state.update_data(selected_advertisers=[])
    await message.answer("Шаг 10/10 — Выбери рекламные аккаунты:", reply_markup=keyboard)

@dp.callback_query(F.data.startswith("adv_") & ~F.data.endswith("all"))
async def toggle_advertiser(callback: types.CallbackQuery, state: FSMContext):
    adv_id = callback.data.replace("adv_", "")
    data = await state.get_data()
    selected = data.get("selected_advertisers", [])
    if adv_id in selected:
        selected.remove(adv_id)
    else:
        selected.append(adv_id)
    await state.update_data(selected_advertisers=selected)
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=f"{'✅' if aid in selected else '☐'} {aid[-6:]}", callback_data=f"adv_{aid}")]
        for aid in ADVERTISER_IDS[:20]
    ] + [
        [InlineKeyboardButton(text=f"{'✅' if aid in selected else '☐'} {aid[-6:]}", callback_data=f"adv_{aid}")]
        for aid in ADVERTISER_IDS[20:]
    ] + [
        [InlineKeyboardButton(text="✅ Выбрать все", callback_data="adv_all")],
        [InlineKeyboardButton(text="🚀 Создать кампанию", callback_data="create_campaign")]
    ])
    try:
        await callback.message.edit_reply_markup(reply_markup=keyboard)
    except Exception:
        pass
    await callback.answer()

@dp.callback_query(F.data == "adv_all")
async def select_all_advertisers(callback: types.CallbackQuery, state: FSMContext):
    await state.update_data(selected_advertisers=ADVERTISER_IDS.copy())
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=f"✅ {aid[-6:]}", callback_data=f"adv_{aid}")]
        for aid in ADVERTISER_IDS[:20]
    ] + [
        [InlineKeyboardButton(text=f"✅ {aid[-6:]}", callback_data=f"adv_{aid}")]
        for aid in ADVERTISER_IDS[20:]
    ] + [
        [InlineKeyboardButton(text="✅ Выбрать все", callback_data="adv_all")],
        [InlineKeyboardButton(text="🚀 Создать кампанию", callback_data="create_campaign")]
    ])
    try:
        await callback.message.edit_reply_markup(reply_markup=keyboard)
    except Exception:
        pass
    await callback.answer(f"Выбрано {len(ADVERTISER_IDS)} аккаунтов")

@dp.callback_query(F.data == "create_campaign")
async def create_campaign(callback: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()
    selected = data.get("selected_advertisers", [])
    if not selected:
        await callback.answer("Выбери хотя бы один рекламный аккаунт!", show_alert=True)
        return

    await callback.message.answer(
        f"⏳ Создаю кампанию *{data['campaign_name']}*\n"
        f"На {len(selected)} аккаунтах...",
        parse_mode="Markdown"
    )
    await state.clear()

    results = []
    for adv_id in selected:
        success, msg = await create_tiktok_campaign(adv_id, data)
        status = "✅" if success else "❌"
        results.append(f"{status} `{adv_id[-6:]}`: {msg}")

    text = f"📊 *Результат создания кампании:*\n\n" + "\n".join(results)
    await callback.message.answer(text, parse_mode="Markdown")

async def get_identity(advertiser_id, session, base_url, headers):
    """Получает первый доступный BC_AUTH_TT identity для кабинета"""
    try:
        resp = await session.get(
            f"{base_url}/identity/get/",
            params={"advertiser_id": advertiser_id},
            headers=headers
        )
        data = await resp.json()
        ident_list = data.get("data", {}).get("identity_list", [])
        # Предпочитаем BC_AUTH_TT
        for i in ident_list:
            if i.get("identity_type") == "BC_AUTH_TT":
                return i
        if ident_list:
            return ident_list[0]
    except Exception:
        pass
    return None


async def get_tiktok_posts(advertiser_id, identity, session, base_url, headers):
    """Получает список постов из TikTok аккаунта"""
    try:
        resp = await session.get(
            f"{base_url}/identity/video/get/",
            params={
                "advertiser_id": advertiser_id,
                "identity_type": identity["identity_type"],
                "identity_id": identity["identity_id"],
                "identity_authorized_bc_id": identity.get("identity_authorized_bc_id", ""),
                "page_size": 20,
            },
            headers=headers
        )
        data = await resp.json()
        return data.get("data", {}).get("video_list", [])
    except Exception:
        return []


async def log_api(step, payload, response):
    import datetime
    with open("/tmp/tiktok_api.log", "a") as f:
        f.write(f"\n=== {datetime.datetime.now()} | {step} ===\n")
        f.write(f"REQUEST: {json.dumps(payload, indent=2)}\n")
        f.write(f"RESPONSE: {json.dumps(response, indent=2)}\n")


async def create_tiktok_campaign(advertiser_id, data):
    try:
        import hashlib, time
        headers = {
            "Access-Token": MARKETING_TOKEN,
            "Content-Type": "application/json"
        }
        base_url = "https://business-api.tiktok.com/open_api/v1.3"
        objective = data["objective"]

        async with aiohttp.ClientSession() as session:

            # ── LEAD_GENERATION: используем Smart+ API ────────────────────────
            if objective == "LEAD_GENERATION":
                identity = await get_identity(advertiser_id, session, base_url, headers)
                if not identity:
                    return False, "Не найден identity (TikTok аккаунт) для кабинета"

                # 1. Кампания
                sp_camp_payload = {
                    "advertiser_id": advertiser_id,
                    "campaign_name": data["campaign_name"],
                    "objective_type": "LEAD_GENERATION",
                    "budget": data["budget"],
                    "request_id": str(int(time.time() * 1000)),
                }
                sp_camp_resp = await session.post(f"{base_url}/smart_plus/campaign/create/", json=sp_camp_payload, headers=headers)
                sp_camp_data = await sp_camp_resp.json()
                await log_api("SMART+ CAMPAIGN CREATE", sp_camp_payload, sp_camp_data)
                if sp_camp_data.get("code") != 0:
                    return False, f"Ошибка Smart+ кампании: {sp_camp_data.get('message')}"
                campaign_id = sp_camp_data["data"]["campaign_id"]

                # 2. Adgroup
                sp_adgroup_payload = {
                    "advertiser_id": advertiser_id,
                    "campaign_id": campaign_id,
                    "adgroup_name": data["adgroup_name"],
                    "optimization_goal": "LEAD_GENERATION",
                    "promotion_type": "LEAD_GENERATION",
                    "bid_type": "BID_TYPE_NO_BID",
                    "billing_event": "OCPM",
                    "schedule_type": "SCHEDULE_START_END" if data.get("schedule_end") else "SCHEDULE_FROM_NOW",
                    "schedule_start_time": data["schedule_start"],
                    "placement_type": "PLACEMENT_TYPE_NORMAL",
                    "placements": ["PLACEMENT_TIKTOK"],
                    "targeting_spec": {
                        "location_ids": [str(data["geo"])],
                    },
                    "request_id": str(int(time.time() * 1000)),
                }
                if data.get("schedule_end"):
                    sp_adgroup_payload["schedule_end_time"] = data["schedule_end"]

                sp_adgroup_resp = await session.post(f"{base_url}/smart_plus/adgroup/create/", json=sp_adgroup_payload, headers=headers)
                sp_adgroup_data = await sp_adgroup_resp.json()
                await log_api("SMART+ ADGROUP CREATE", sp_adgroup_payload, sp_adgroup_data)
                if sp_adgroup_data.get("code") != 0:
                    return False, f"Ошибка Smart+ группы: {sp_adgroup_data.get('message')}"
                adgroup_id = sp_adgroup_data["data"]["adgroup_id"]

                # 3. Получаем первый доступный пост
                posts = await get_tiktok_posts(advertiser_id, identity, session, base_url, headers)
                if not posts:
                    return False, "Нет доступных TikTok постов для объявления"
                tiktok_item_id = data.get("tiktok_item_id") or posts[0]["item_id"]

                # 4. Объявление
                sp_ad_payload = {
                    "advertiser_id": advertiser_id,
                    "adgroup_id": adgroup_id,
                    "ad_name": data["campaign_name"],
                    "creative_list": [{
                        "creative_info": {
                            "ad_format": "SINGLE_VIDEO",
                            "identity_type": identity["identity_type"],
                            "identity_id": identity["identity_id"],
                            "identity_authorized_bc_id": identity.get("identity_authorized_bc_id", ""),
                            "tiktok_item_id": tiktok_item_id,
                        }
                    }],
                    "ad_text_list": [{"ad_text": data.get("ad_text", "")}],
                    "landing_page_url_list": [{"landing_page_url": data.get("ad_url", "")}] if data.get("ad_url") else [],
                    "call_to_action_list": [{"call_to_action": "LEARN_MORE"}],
                }
                sp_ad_resp = await session.post(f"{base_url}/smart_plus/ad/create/", json=sp_ad_payload, headers=headers)
                sp_ad_data = await sp_ad_resp.json()
                await log_api("SMART+ AD CREATE", sp_ad_payload, sp_ad_data)
                if sp_ad_data.get("code") != 0:
                    return False, f"Ошибка Smart+ объявления: {sp_ad_data.get('message')}"

                smart_plus_ad_id = sp_ad_data["data"]["smart_plus_ad_id"]
                return True, f"campaign: {campaign_id} | ad: {smart_plus_ad_id}"

            # ── Все остальные цели: старый flow с видео ───────────────────────

            # 1. Создаём кампанию
            camp_resp = await session.post(
                f"{base_url}/campaign/create/",
                json={
                    "advertiser_id": advertiser_id,
                    "campaign_name": data["campaign_name"],
                    "objective_type": data["objective"],
                    "budget_mode": data["budget_mode"],
                    "budget": data["budget"],
                },
                headers=headers
            )
            camp_data = await camp_resp.json()
            if camp_data.get("code") != 0:
                return False, f"Ошибка кампании: {camp_data.get('message')}"
            campaign_id = camp_data["data"]["campaign_id"]

            # 2. Загружаем видео
            file = await bot.get_file(data["video_file_id"])
            file_url = f"https://api.telegram.org/file/bot{BOT_TOKEN}/{file.file_path}"
            async with session.get(file_url) as resp:
                video_bytes = await resp.read()

            md5_hash = hashlib.md5(video_bytes).hexdigest()
            form = aiohttp.FormData()
            form.add_field("advertiser_id", advertiser_id)
            form.add_field("upload_type", "UPLOAD_BY_FILE")
            form.add_field("video_signature", md5_hash)
            form.add_field(
                "video_file", video_bytes,
                filename=f"video_{advertiser_id}_{int(time.time())}.mp4",
                content_type="video/mp4"
            )
            upload_resp = await session.post(
                f"{base_url}/file/video/ad/upload/",
                data=form,
                headers={"Access-Token": MARKETING_TOKEN}
            )
            upload_data = await upload_resp.json()
            if upload_data.get("code") != 0:
                return False, f"Ошибка загрузки видео: {upload_data.get('message')}"
            d = upload_data["data"]
            video_id = d[0]["video_id"] if isinstance(d, list) else d["video_id"]

            # 3. Создаём группу объявлений
            optimize_goal, billing_event, promotion_type = get_adgroup_optimization(objective)

            adgroup_payload = {
                "advertiser_id": advertiser_id,
                "campaign_id": campaign_id,
                "adgroup_name": data["adgroup_name"],
                "placement_type": data["placement_type"],
                "location_ids": [str(data["geo"])],
                "budget_mode": data["budget_mode"],
                "budget": data["budget"],
                "schedule_type": "SCHEDULE_START_END" if data.get("schedule_end") else "SCHEDULE_FROM_NOW",
                "schedule_start_time": data["schedule_start"],
                "optimize_goal": optimize_goal,
                "billing_event": billing_event,
                "promotion_type": promotion_type,
                "bid_type": "BID_TYPE_NO_BID",
                "pacing": "PACING_MODE_SMOOTH",
            }
            if data.get("schedule_end"):
                adgroup_payload["schedule_end_time"] = data["schedule_end"]
            if data["placement_type"] == "PLACEMENT_TYPE_NORMAL":
                adgroup_payload["placements"] = data["placements"]

            adgroup_resp = await session.post(
                f"{base_url}/adgroup/create/",
                json=adgroup_payload,
                headers=headers
            )
            adgroup_data = await adgroup_resp.json()
            if adgroup_data.get("code") != 0:
                return False, f"Ошибка группы: {adgroup_data.get('message')}"
            adgroup_id = adgroup_data["data"]["adgroup_id"]

            # 4. Создаём объявление
            ad_resp = await session.post(
                f"{base_url}/ad/create/",
                json={
                    "advertiser_id": advertiser_id,
                    "adgroup_id": adgroup_id,
                    "creatives": [{
                        "ad_name": data["campaign_name"],
                        "ad_text": data["ad_text"],
                        "video_id": video_id,
                        "landing_page_url": data["ad_url"],
                        "call_to_action": "LEARN_MORE",
                    }]
                },
                headers=headers
            )
            ad_data = await ad_resp.json()
            if ad_data.get("code") != 0:
                return False, f"Ошибка объявления: {ad_data.get('message')}"

            return True, f"campaign_id: {campaign_id}"

    except Exception as e:
        import traceback
        return False, f"{str(e)} | {traceback.format_exc()[-300:]}"

loop = None

async def main():
    global loop
    loop = asyncio.get_event_loop()
    threading.Thread(target=run_web, daemon=True).start()
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
