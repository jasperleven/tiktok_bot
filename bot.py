import asyncio
import os
import json
import threading
import aiohttp
import tempfile
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
MARKETING_TOKEN = os.getenv("TIKTOK_MARKETING_TOKEN")

ADVERTISERS = {
    "7379547391218696193": "AM_2_dverirb.online",
    "7380323349555413008": "#245 TikTok Boost Ads I Vlad RB",
    "7390291557712298001": "AM_2_Стиралки/холодильники",
    "7441163654311165969": "AM_3_technowave-ad10",
    "7458571671717429249": "#245 TikTok Boost I Vlad RB",
    "7467552788675854353": "ITB_Vlad_moto",
    "7467552998789578768": "ITB_Vlad_tractor",
    "7467553177400147985": "ITB_Vlad_moped",
    "7467553366952935441": "ITB_Vlad_scuter",
    "7467553550734901264": "ITB_Vlad_lodki",
    "7470066457113083905": "AM_3_technowave-ad22",
    "7473561071866134529": "WGC-M-S-technowave-ad37",
    "7481290249352642576": "WGC-M-S-mega-techno-4",
    "7496487210787717138": "WGC-M-S-online-saletech",
    "7505007920823107591": "WGC-M-S-cool-by-shop-xyz",
    "7505007952001253377": "WGC-M-S-cool-by-shoptechh",
    "7505009554032345096": "WGC-M-S-cool-shop-by-online",
    "7522063277921288200": "WGC-M-S-alfa-shopxyz",
    "7525368248519507975": "WGC-M-S-techshop-onlineonline",
    "7525370413484867592": "WGC-M-S-techshop-online-tech",
    "7594384691119734801": "WGC-M-S-dacha-shop.xyz2",
    "7608919922311331856": "WGC-M-S-dacha",
    "7610323536325902352": "WGC-M-S-dacha-shop-1",
    "7610323651145269264": "WGC-M-S-dacha-shop-2",
    "7610324072874049553": "WGC-M-S-dacha-shop-4",
    "7628935051379752978": "WGC-M-S-dacha-shop.xyz1",
    "7632400068336500737": "TechnoWave",
    "7636704658911805460": "WGC-M-S-cool-shopby-2",
    "7636704984830230548": "WGC-M-S-cool-shop-1",
    "7636706608449617941": "WGC-M-S-cool-shop-3",
    "7636707477756805141": "WGC-M-S-cool-shop-4",
    "7636707899250655252": "WGC-M-S-cool-shop-5",
    "7636708554946248725": "WGC-M-S-cool-shop-6",
    "7636708691615268884": "WGC-M-S-cool-shop-7",
    "7636708912552493076": "WGC-M-S-cool-shop-8",
    "7636709412069179412": "WGC-M-S-cool-shop-9",
    "7636710982693470229": "WGC-M-S-cool-shop-10",
    "7643732056840765457": "Artaged_BC_VLD",
    "7647080900043505684": "WGC-M-S-cool-shop-11",
    "7647081382459670549": "WGC-M-S-cool-shop-12",
    "7652299468439765012": "WGC-M-S-cool-shop-13",
    "7652299641001787412": "WGC-M-S-cool-shop-14",
    "7652299857702961172": "WGC-M-S-cool-shop-15",
}

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

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())

class CampaignStates(StatesGroup):
    select_advertisers = State()
    campaign_name      = State()
    campaign_objective = State()
    budget_level       = State()
    budget_mode        = State()
    budget_amount      = State()
    adgroup_name       = State()
    placement          = State()
    geo                = State()
    schedule_start     = State()
    schedule_end       = State()
    bid_type           = State()
    bid_amount         = State()
    pixel_search       = State()
    pixel_select       = State()
    video_upload       = State()
    ad_text            = State()
    ad_url             = State()

class HealthHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"OK")
    def log_message(self, format, *args):
        pass

def run_web():
    port = int(os.environ.get("PORT", 8080))
    server = HTTPServer(("0.0.0.0", port), HealthHandler)
    server.serve_forever()

def build_advertisers_keyboard(selected):
    rows = []
    for adv_id, name in ADVERTISERS.items():
        mark = "✅" if adv_id in selected else "☐"
        rows.append([InlineKeyboardButton(text=f"{mark} {name}", callback_data=f"adv_{adv_id}")])
    rows.append([
        InlineKeyboardButton(text="✅ Выбрать все", callback_data="adv_all"),
        InlineKeyboardButton(text="❌ Снять все", callback_data="adv_none"),
    ])
    rows.append([InlineKeyboardButton(text="➡️ Далее", callback_data="advertisers_done")])
    return InlineKeyboardMarkup(inline_keyboard=rows)

def build_advertisers_keyboard_final(selected):
    rows = []
    for adv_id, name in ADVERTISERS.items():
        mark = "✅" if adv_id in selected else "☐"
        rows.append([InlineKeyboardButton(text=f"{mark} {name}", callback_data=f"adv_{adv_id}")])
    rows.append([
        InlineKeyboardButton(text="✅ Выбрать все", callback_data="adv_all"),
        InlineKeyboardButton(text="❌ Снять все", callback_data="adv_none"),
    ])
    rows.append([InlineKeyboardButton(text="🚀 Создать кампанию", callback_data="create_campaign")])
    return InlineKeyboardMarkup(inline_keyboard=rows)

async def search_pixels(advertiser_id, query):
    """Поиск пикселей в рекламном кабинете по части названия"""
    try:
        async with aiohttp.ClientSession() as session:
            resp = await session.get(
                f"https://business-api.tiktok.com/open_api/v1.3/pixel/list/",
                params={"advertiser_id": advertiser_id},
                headers={"Access-Token": MARKETING_TOKEN}
            )
            data = await resp.json()
            if data.get("code") != 0:
                return []
            pixels = data.get("data", {}).get("pixels", [])
            query_lower = query.lower()
            return [p for p in pixels if query_lower in p.get("name", "").lower()]
    except Exception:
        return []

async def download_video_to_hetzner(file_id):
    """Скачивает видео из Telegram на сервер и возвращает путь к файлу"""
    file = await bot.get_file(file_id)
    file_url = f"https://api.telegram.org/file/bot{BOT_TOKEN}/{file.file_path}"
    
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".mp4", dir="/tmp")
    tmp_path = tmp.name
    tmp.close()
    
    async with aiohttp.ClientSession() as session:
        async with session.get(file_url) as resp:
            with open(tmp_path, "wb") as f:
                async for chunk in resp.content.iter_chunked(1024 * 1024):
                    f.write(chunk)
    
    return tmp_path

async def upload_video_to_tiktok(advertiser_id, video_path):
    """Загружает видео с сервера в TikTok и возвращает video_id"""
    import hashlib
    async with aiohttp.ClientSession() as session:
        with open(video_path, "rb") as f:
            video_bytes = f.read()
        
        md5_hash = hashlib.md5(video_bytes).hexdigest()
        
        form = aiohttp.FormData()
        form.add_field("advertiser_id", advertiser_id)
        form.add_field("upload_type", "UPLOAD_BY_FILE")
        form.add_field("video_signature", md5_hash)
        import time
        unique_name = f"video_{advertiser_id}_{int(time.time())}.mp4"
        form.add_field("video_file", video_bytes, filename=unique_name, content_type="video/mp4")
        
        resp = await session.post(
            "https://business-api.tiktok.com/open_api/v1.3/file/video/ad/upload/",
            data=form,
            headers={"Access-Token": MARKETING_TOKEN}
        )
        data = await resp.json()
        
        if data.get("code") != 0:
            raise Exception(f"Ошибка загрузки видео: {data.get('message')} | raw: {data}")
        
        # data["data"] может быть списком или словарём
        d = data["data"]
        if isinstance(d, list):
            return d[0]["video_id"]
        return d["video_id"]

@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    await message.answer(
        "👋 *TikTok Ads Manager Bot*\n\n"
        "📢 Команды:\n"
        "/newcampaign — создать рекламную кампанию",
        parse_mode="Markdown",
        reply_markup=ReplyKeyboardRemove()
    )

@dp.message(Command("newcampaign"))
async def cmd_new_campaign(message: types.Message, state: FSMContext):
    await state.set_state(CampaignStates.select_advertisers)
    await state.update_data(selected_advertisers=[])
    await message.answer(
        "📢 *Создание рекламной кампании*\n\n"
        "Шаг 1/13 — Выбери рекламные кабинеты:",
        parse_mode="Markdown",
        reply_markup=build_advertisers_keyboard([])
    )

@dp.message(CampaignStates.campaign_name)
async def got_campaign_name(message: types.Message, state: FSMContext):
    await state.update_data(campaign_name=message.text)
    await state.set_state(CampaignStates.campaign_objective)
    keyboard = ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text=k)] for k in OBJECTIVES.keys()],
        resize_keyboard=True, one_time_keyboard=True
    )
    await message.answer("Шаг 2/13 — Выбери цель рекламы:", reply_markup=keyboard)

@dp.message(CampaignStates.campaign_objective)
async def got_objective(message: types.Message, state: FSMContext):
    if message.text not in OBJECTIVES:
        await message.answer("Выбери цель из списка 👇")
        return
    await state.update_data(objective=OBJECTIVES[message.text], objective_name=message.text)
    await state.set_state(CampaignStates.budget_level)
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="📊 Бюджет на кампанию")],
            [KeyboardButton(text="📁 Бюджет на группу объявлений")],
        ],
        resize_keyboard=True, one_time_keyboard=True
    )
    await message.answer("Шаг 3/13 — Где устанавливать бюджет?", reply_markup=keyboard)

@dp.message(CampaignStates.budget_level)
async def got_budget_level(message: types.Message, state: FSMContext):
    if message.text == "📊 Бюджет на кампанию":
        await state.update_data(budget_level="campaign")
    elif message.text == "📁 Бюджет на группу объявлений":
        await state.update_data(budget_level="adgroup")
    else:
        await message.answer("Выбери из списка 👇")
        return
    await state.set_state(CampaignStates.budget_mode)
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="📅 Дневной бюджет")],
            [KeyboardButton(text="💰 Общий бюджет")],
        ],
        resize_keyboard=True, one_time_keyboard=True
    )
    await message.answer("Шаг 4/13 — Тип бюджета:", reply_markup=keyboard)

@dp.message(CampaignStates.budget_mode)
async def got_budget_mode(message: types.Message, state: FSMContext):
    if message.text == "📅 Дневной бюджет":
        mode = "BUDGET_MODE_DAY"
    elif message.text == "💰 Общий бюджет":
        mode = "BUDGET_MODE_TOTAL"
    else:
        await message.answer("Выбери тип бюджета 👇")
        return
    await state.update_data(budget_mode=mode)
    await state.set_state(CampaignStates.budget_amount)
    await message.answer("Шаг 5/13 — Введи сумму бюджета (USD, минимум 50):", reply_markup=ReplyKeyboardRemove())

@dp.message(CampaignStates.budget_amount)
async def got_budget_amount(message: types.Message, state: FSMContext):
    try:
        amount = float(message.text.replace(",", "."))
        if amount < 50:
            await message.answer("❌ Минимум 50 USD. Введи ещё раз:")
            return
    except ValueError:
        await message.answer("❌ Введи число. Например: 100")
        return
    await state.update_data(budget=amount)
    await state.set_state(CampaignStates.adgroup_name)
    await message.answer("Шаг 6/13 — Введи название группы объявлений:")

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
    await message.answer("Шаг 7/13 — Плейсменты:", reply_markup=keyboard)

@dp.message(CampaignStates.placement)
async def got_placement(message: types.Message, state: FSMContext):
    if message.text == "🎵 Только TikTok":
        placement_type = "PLACEMENT_TYPE_NORMAL"
        placements = ["PLACEMENT_TIKTOK"]
    elif message.text == "🌐 Автоматически (все площадки)":
        placement_type = "PLACEMENT_TYPE_AUTOMATIC"
        placements = []
    else:
        await message.answer("Выбери плейсмент 👇")
        return
    await state.update_data(placement_type=placement_type, placements=placements)
    await state.set_state(CampaignStates.geo)
    keyboard = ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text=k)] for k in COUNTRIES.keys()],
        resize_keyboard=True, one_time_keyboard=True
    )
    await message.answer("Шаг 8/13 — Выбери страну таргетинга:", reply_markup=keyboard)

@dp.message(CampaignStates.geo)
async def got_geo(message: types.Message, state: FSMContext):
    if message.text not in COUNTRIES:
        await message.answer("Выбери страну из списка 👇")
        return
    await state.update_data(geo=COUNTRIES[message.text], geo_name=message.text)
    await state.set_state(CampaignStates.schedule_start)
    await message.answer(
        "Шаг 9/13 — Дата и время начала кампании\n"
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
        "Дата и время окончания\n"
        "Формат: `YYYY-MM-DD HH:MM:SS`\n"
        "Или нажми кнопку:",
        reply_markup=keyboard,
        parse_mode="Markdown"
    )

@dp.message(CampaignStates.schedule_end)
async def got_schedule_end(message: types.Message, state: FSMContext):
    end = None if message.text == "♾ Без даты окончания" else message.text
    await state.update_data(schedule_end=end)
    await state.set_state(CampaignStates.bid_type)
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="🤖 Автоставка (без bid)")],
            [KeyboardButton(text="✏️ Ручная ставка (указать bid)")],
        ],
        resize_keyboard=True, one_time_keyboard=True
    )
    await message.answer("Шаг 10/13 — Тип ставки (bid):", reply_markup=keyboard)

@dp.message(CampaignStates.bid_type)
async def got_bid_type(message: types.Message, state: FSMContext):
    if message.text == "🤖 Автоставка (без bid)":
        await state.update_data(bid_type="auto", bid_amount=None)
        await state.set_state(CampaignStates.pixel_search)
        await message.answer(
            "Шаг 11/13 — Введи часть названия пикселя для поиска\n"
            "Например: `ART` или `ERC`\n\n"
            "Или нажми /skippixel чтобы пропустить",
            reply_markup=ReplyKeyboardRemove(),
            parse_mode="Markdown"
        )
    elif message.text == "✏️ Ручная ставка (указать bid)":
        await state.update_data(bid_type="manual")
        await state.set_state(CampaignStates.bid_amount)
        await message.answer("Введи сумму ставки (USD):", reply_markup=ReplyKeyboardRemove())
    else:
        await message.answer("Выбери тип ставки 👇")

@dp.message(CampaignStates.bid_amount)
async def got_bid_amount(message: types.Message, state: FSMContext):
    try:
        bid = float(message.text.replace(",", "."))
    except ValueError:
        await message.answer("❌ Введи число. Например: 0.5")
        return
    await state.update_data(bid_amount=bid)
    await state.set_state(CampaignStates.pixel_search)
    await message.answer(
        "Шаг 11/13 — Введи часть названия пикселя для поиска\n"
        "Например: `ART` или `ERC`\n\n"
        "Или отправь /skippixel чтобы пропустить",
        parse_mode="Markdown"
    )

@dp.callback_query(F.data == "advertisers_done")
async def advertisers_done(callback: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()
    selected = data.get("selected_advertisers", [])
    if not selected:
        await callback.answer("Выбери хотя бы один кабинет!", show_alert=True)
        return
    await state.set_state(CampaignStates.campaign_name)
    await callback.message.answer(
        f"✅ Выбрано {len(selected)} кабинетов\n\n"
        "Шаг 2/13 — Введи название кампании:",
        reply_markup=ReplyKeyboardRemove()
    )
    await callback.answer()

@dp.message(Command("skippixel"))
async def skip_pixel(message: types.Message, state: FSMContext):
    await state.update_data(pixel_id=None)
    await state.set_state(CampaignStates.video_upload)
    await message.answer("Шаг 12/13 — Отправь видео для рекламного объявления:")

@dp.message(CampaignStates.pixel_search)
async def got_pixel_search(message: types.Message, state: FSMContext):
    query = message.text.strip()
    await message.answer(f"🔍 Ищу пиксели с '{query}'...")

    data = await state.get_data()
    selected_advertisers = data.get("selected_advertisers", [])
    
    # Ищем в первом выбранном кабинете
    search_adv_id = selected_advertisers[0] if selected_advertisers else list(ADVERTISERS.keys())[0]
    
    pixels = await search_pixels(search_adv_id, query)
    
    if not pixels:
        await message.answer(
            f"❌ Пиксели с '{query}' не найдены.\n"
            "Попробуй другой запрос или отправь /skippixel чтобы пропустить."
        )
        return

    await state.update_data(found_pixels=pixels)
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(
            text=f"{p['name']} ({p['pixel_id']})",
            callback_data=f"pixel_{p['pixel_id']}"
        )]
        for p in pixels[:10]
    ] + [[InlineKeyboardButton(text="⏭ Пропустить пиксель", callback_data="pixel_skip")]])
    
    await message.answer("Выбери пиксель:", reply_markup=keyboard)
    await state.set_state(CampaignStates.pixel_select)

@dp.callback_query(F.data.startswith("pixel_") & ~F.data.endswith("skip"))
async def got_pixel_select(callback: types.CallbackQuery, state: FSMContext):
    pixel_id = callback.data.replace("pixel_", "")
    await state.update_data(pixel_id=pixel_id)
    await callback.message.answer(f"✅ Пиксель выбран: `{pixel_id}`", parse_mode="Markdown")
    await state.set_state(CampaignStates.video_upload)
    await callback.message.answer("Шаг 12/13 — Отправь видео для рекламного объявления:")
    await callback.answer()

@dp.callback_query(F.data == "pixel_skip")
async def skip_pixel_callback(callback: types.CallbackQuery, state: FSMContext):
    await state.update_data(pixel_id=None)
    await state.set_state(CampaignStates.video_upload)
    await callback.message.answer("Шаг 12/13 — Отправь видео для рекламного объявления:")
    await callback.answer()

@dp.message(CampaignStates.video_upload, F.video | F.document)
async def got_campaign_video(message: types.Message, state: FSMContext):
    file_id = message.document.file_id if message.document else message.video.file_id
    await state.update_data(video_file_id=file_id)
    await state.set_state(CampaignStates.ad_text)
    await message.answer("✅ Видео получено!\n\nТекст объявления (до 100 символов):")

@dp.message(CampaignStates.ad_text)
async def got_ad_text(message: types.Message, state: FSMContext):
    await state.update_data(ad_text=message.text[:100])
    await state.set_state(CampaignStates.ad_url)
    await message.answer("Ссылка на лендинг (URL):")

@dp.message(CampaignStates.ad_url)
async def got_ad_url(message: types.Message, state: FSMContext):
    await state.update_data(ad_url=message.text)
    data = await state.get_data()
    selected = data.get("selected_advertisers", [])
    names = [ADVERTISERS.get(a, a) for a in selected]
    await message.answer(
        f"✅ Всё готово! Нажми *Создать кампанию* для запуска на {len(selected)} кабинетах:\n" +
        "\n".join(f"• {n}" for n in names),
        parse_mode="Markdown",
        reply_markup=build_advertisers_keyboard_final(selected)
    )

@dp.callback_query(F.data.startswith("adv_") & ~F.data.endswith("all") & ~F.data.endswith("none"))
async def toggle_advertiser(callback: types.CallbackQuery, state: FSMContext):
    adv_id = callback.data.replace("adv_", "")
    data = await state.get_data()
    selected = data.get("selected_advertisers", [])
    if adv_id in selected:
        selected.remove(adv_id)
    else:
        selected.append(adv_id)
    await state.update_data(selected_advertisers=selected)
    try:
        await callback.message.edit_reply_markup(reply_markup=build_advertisers_keyboard(selected))
    except Exception:
        pass
    await callback.answer()

@dp.callback_query(F.data == "adv_all")
async def select_all_advertisers(callback: types.CallbackQuery, state: FSMContext):
    selected = list(ADVERTISERS.keys())
    await state.update_data(selected_advertisers=selected)
    try:
        await callback.message.edit_reply_markup(reply_markup=build_advertisers_keyboard(selected))
    except Exception:
        pass
    await callback.answer(f"Выбрано {len(selected)} кабинетов")

@dp.callback_query(F.data == "adv_none")
async def deselect_all_advertisers(callback: types.CallbackQuery, state: FSMContext):
    await state.update_data(selected_advertisers=[])
    try:
        await callback.message.edit_reply_markup(reply_markup=build_advertisers_keyboard([]))
    except Exception:
        pass
    await callback.answer("Все кабинеты сняты")

@dp.callback_query(F.data == "create_campaign")
async def create_campaign(callback: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()
    selected = data.get("selected_advertisers", [])
    if not selected:
        await callback.answer("Выбери хотя бы один кабинет!", show_alert=True)
        return

    await callback.message.answer(
        f"⏳ Создаю кампанию *{data['campaign_name']}*\n"
        f"На {len(selected)} кабинетах...\n\n"
        f"Скачиваю видео на сервер...",
        parse_mode="Markdown"
    )
    await state.clear()

    # Скачиваем видео на Hetzner один раз
    video_path = None
    try:
        video_path = await download_video_to_hetzner(data["video_file_id"])
        await callback.message.answer("✅ Видео загружено на сервер. Создаю кампании...")
    except Exception as e:
        await callback.message.answer(f"❌ Ошибка скачивания видео: {e}")
        return

    # Создаём кампанию в каждом кабинете
    for adv_id in selected:
        name = ADVERTISERS.get(adv_id, adv_id)
        success, msg = await create_tiktok_campaign(adv_id, data, video_path)
        status = "✅" if success else "❌"
        result_text = f"{status} *{name}*\n`{msg}`"
        for _ in range(5):
            try:
                await callback.message.answer(result_text, parse_mode="Markdown")
                break
            except Exception:
                await asyncio.sleep(3)

    # Удаляем видео с сервера
    if video_path and os.path.exists(video_path):
        os.remove(video_path)

    for _ in range(5):
        try:
            await callback.message.answer("✅ Готово! Все кабинеты обработаны.")
            break
        except Exception:
            await asyncio.sleep(3)

async def create_tiktok_campaign(advertiser_id, data, video_path):
    try:
        headers = {
            "Access-Token": MARKETING_TOKEN,
            "Content-Type": "application/json"
        }
        base_url = "https://business-api.tiktok.com/open_api/v1.3"
        budget_level = data.get("budget_level", "campaign")

        async with aiohttp.ClientSession() as session:
            # 1. Создаём кампанию
            camp_payload = {
                "advertiser_id": advertiser_id,
                "campaign_name": data["campaign_name"],
                "objective_type": data["objective"],
            }
            if budget_level == "campaign":
                camp_payload["budget_mode"] = data["budget_mode"]
                camp_payload["budget"] = data["budget"]
            else:
                camp_payload["budget_mode"] = "BUDGET_MODE_INFINITE"

            camp_resp = await session.post(f"{base_url}/campaign/create/", json=camp_payload, headers=headers)
            camp_data = await camp_resp.json()
            if camp_data.get("code") != 0:
                return False, f"Ошибка кампании: {camp_data.get('message')}"
            campaign_id = camp_data["data"]["campaign_id"]

            # 2. Загружаем видео в TikTok
            video_id = await upload_video_to_tiktok(advertiser_id, video_path)

            # 3. Создаём группу объявлений
            optimize_goal = "CLICK" if data["objective"] == "TRAFFIC" else "REACH"
            billing_event = "CPC" if data["objective"] == "TRAFFIC" else "CPM"

            adgroup_payload = {
                "advertiser_id": advertiser_id,
                "campaign_id": campaign_id,
                "adgroup_name": data["adgroup_name"],
                "placement_type": data["placement_type"],
                "location_ids": [str(data["geo"])],
                "schedule_type": "SCHEDULE_START_END" if data.get("schedule_end") else "SCHEDULE_FROM_NOW",
                "schedule_start_time": data["schedule_start"],
                "optimize_goal": optimize_goal,
                "billing_event": billing_event,
                "pacing": "PACING_MODE_SMOOTH",
            }

            if budget_level == "adgroup":
                adgroup_payload["budget_mode"] = data["budget_mode"]
                adgroup_payload["budget"] = data["budget"]

            if data.get("schedule_end"):
                adgroup_payload["schedule_end_time"] = data["schedule_end"]

            if data["placement_type"] == "PLACEMENT_TYPE_NORMAL":
                adgroup_payload["placements"] = data["placements"]

            if data.get("bid_type") == "manual" and data.get("bid_amount"):
                adgroup_payload["bid_type"] = "BID_TYPE_CUSTOM"
                adgroup_payload["bid_price"] = data["bid_amount"]
            else:
                adgroup_payload["bid_type"] = "BID_TYPE_NO_BID"

            if data.get("pixel_id"):
                adgroup_payload["pixel_id"] = data["pixel_id"]

            adgroup_resp = await session.post(f"{base_url}/adgroup/create/", json=adgroup_payload, headers=headers)
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

    except TypeError as e:
        import traceback
        return False, f"TypeError: {str(e)} | {traceback.format_exc()[-200:]}"

    except Exception as e:
        return False, str(e)

async def main():
    threading.Thread(target=run_web, daemon=True).start()
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
