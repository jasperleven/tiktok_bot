import asyncio
import os
import json
import threading
import aiohttp
import tempfile
import hashlib
import time
from urllib.parse import urlparse, parse_qs
from http.server import HTTPServer, BaseHTTPRequestHandler
from aiogram import Bot, Dispatcher, types, F
from aiogram.client.session.aiohttp import AiohttpSession
from aiogram.client.telegram import TelegramAPIServer
from aiogram.client.default import DefaultBotProperties
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

ACCOUNTS_FILE = "accounts.json"

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
    "🎯 Охват": "REACH",
    "🌐 Трафик": "TRAFFIC",
    "▶️ Просмотры видео": "VIDEO_VIEWS",
    "📋 Лидогенерация": "LEAD_GENERATION",
    "✅ Конверсии": "CONVERSIONS",
    "📱 Установки приложения": "APP_PROMOTION",
    "🛒 Продажи": "SHOPPING",
}

COUNTRIES = {
    "🇧🇾 Беларусь": 630336,
    "🇷🇺 Россия": 2017370,
    "🇰🇿 Казахстан": 1522867,
    "🇺🇿 Узбекистан": 1512440,
    "🇩🇪 Германия": 2921044,
    "🇺🇸 США": 6252001,
    "🇬🇧 Великобритания": 2635167,
    "🇵🇱 Польша": 798544,
}

ADGROUP_OPT_MAP = {
    "REACH":            ("REACH",            "CPM",  "WEBSITE"),
    "TRAFFIC":          ("CLICK",            "CPC",  "WEBSITE"),
    "VIDEO_VIEWS":      ("VIDEO_PLAY",       "CPV",  "WEBSITE"),
    "LEAD_GENERATION":  ("LEAD_GENERATION",  "OCPM", "LEAD_GENERATION"),
    "CONVERSIONS":      ("CONVERT",          "OCPM", "WEBSITE"),
    "APP_PROMOTION":    ("INSTALL",          "OCPM", "APP"),
    "SHOPPING":         ("CLICK",            "CPC",  "WEBSITE"),
}

def load_accounts():
    if os.path.exists(ACCOUNTS_FILE):
        with open(ACCOUNTS_FILE, "r") as f:
            return json.load(f)
    return {}

def save_accounts(accs):
    with open(ACCOUNTS_FILE, "w") as f:
        json.dump(accs, f)

from aiogram.client.telegram import TelegramAPIServer

bot = Bot(
    token=BOT_TOKEN,
    default=DefaultBotProperties(),
    session=AiohttpSession(api=TelegramAPIServer.from_base("http://localhost:8081"))
)
dp = Dispatcher(storage=MemoryStorage())
accounts = load_accounts()


class PostStates(StatesGroup):
    waiting_video    = State()
    waiting_caption  = State()
    waiting_hashtags = State()
    waiting_accounts = State()
    waiting_code     = State()


class CampaignStates(StatesGroup):
    select_advertisers = State()
    campaign_name      = State()
    campaign_objective = State()
    budget_level       = State()   # кампания или группа
    budget_mode        = State()   # дневной или общий
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


# ─── Утилиты ─────────────────────────────────────────────────────────────────

async def log_api(step, payload, response):
    import datetime
    with open("/tmp/tiktok_api.log", "a") as f:
        f.write(f"\n=== {datetime.datetime.now()} | {step} ===\n")
        f.write(f"REQUEST: {json.dumps(payload, indent=2, ensure_ascii=False)}\n")
        f.write(f"RESPONSE: {json.dumps(response, indent=2, ensure_ascii=False)}\n")


async def search_pixels(advertiser_id, query):
    try:
        async with aiohttp.ClientSession() as session:
            resp = await session.get(
                "https://business-api.tiktok.com/open_api/v1.3/pixel/list/",
                params={"advertiser_id": advertiser_id, "page_size": 20},
                headers={"Access-Token": MARKETING_TOKEN}
            )
            data = await resp.json()
            if data.get("code") != 0:
                return []
            pixels = data.get("data", {}).get("pixels", [])
            # Нормализуем — берём pixel_name из ответа
            result = []
            for p in pixels:
                result.append({
                    "pixel_id": str(p.get("pixel_id", "")),
                    "name": p.get("pixel_name") or p.get("name") or ""
                })
            if not query or query == ".":
                return result[:20]
            q = query.lower()
            return [p for p in result if q in p["name"].lower() or q in p["pixel_id"].lower()]
    except Exception:
        return []


async def get_identity(advertiser_id, session, base_url, headers):
    try:
        resp = await session.get(
            f"{base_url}/identity/get/",
            params={"advertiser_id": advertiser_id},
            headers=headers
        )
        data = await resp.json()
        ident_list = data.get("data", {}).get("identity_list", [])
        # Предпочитаем BC_AUTH_TT NORMAL
        for i in ident_list:
            if i.get("identity_type") == "BC_AUTH_TT" and not i.get("ads_only_mode"):
                return i
        # Если нет NORMAL — берём любой BC_AUTH_TT
        for i in ident_list:
            if i.get("identity_type") == "BC_AUTH_TT":
                return i
        if ident_list:
            return ident_list[0]
    except Exception:
        pass
    return None


async def publish_video_to_tiktok(identity, video_path, title, session, base_url, headers):
    """Публикует видео в TikTok аккаунт и возвращает tiktok_item_id"""
    # Используем TikTok Content Posting API через identity
    with open(video_path, "rb") as f:
        video_bytes = f.read()
    file_size = len(video_bytes)

    # Инициализируем загрузку
    init_resp = await session.post(
        "https://open.tiktokapis.com/v2/post/publish/video/init/",
        json={
            "post_info": {
                "title": title[:150],
                "privacy_level": "PUBLIC_TO_EVERYONE",
                "disable_duet": False,
                "disable_comment": False,
                "disable_stitch": False,
            },
            "source_info": {
                "source": "FILE_UPLOAD",
                "video_size": file_size,
                "chunk_size": file_size,
                "total_chunk_count": 1,
            }
        },
        headers={"Authorization": f"Bearer {identity.get('access_token', '')}", "Content-Type": "application/json"}
    )
    init_data = await init_resp.json()
    if init_data.get("error", {}).get("code") != "ok":
        raise Exception(f"Ошибка инициализации публикации: {init_data}")

    upload_url = init_data["data"]["upload_url"]
    publish_id = init_data["data"]["publish_id"]

    # Загружаем видео
    upload_resp = await session.put(
        upload_url,
        data=video_bytes,
        headers={
            "Content-Type": "video/mp4",
            "Content-Range": f"bytes 0-{file_size-1}/{file_size}",
            "Content-Length": str(file_size),
        }
    )
    if upload_resp.status not in [200, 201, 206]:
        raise Exception(f"Ошибка загрузки видео: {upload_resp.status}")

    # Ждём обработки и получаем item_id
    await asyncio.sleep(15)
    for _ in range(10):
        status_resp = await session.post(
            "https://open.tiktokapis.com/v2/post/publish/status/fetch/",
            json={"publish_id": publish_id},
            headers={"Authorization": f"Bearer {identity.get('access_token', '')}", "Content-Type": "application/json"}
        )
        status_data = await status_resp.json()
        status = status_data.get("data", {}).get("status", "")
        if status == "PUBLISH_COMPLETE":
            return status_data["data"]["publicaly_available_post_id"][0]
        elif status in ["FAILED", "CANCELLED"]:
            raise Exception(f"Публикация провалилась: {status_data}")
        await asyncio.sleep(5)

    raise Exception("Таймаут ожидания публикации видео")


# ─── Клавиатуры ──────────────────────────────────────────────────────────────

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


def build_confirm_keyboard(selected):
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


# ─── Web server ───────────────────────────────────────────────────────────────

class CallbackHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        parsed = urlparse(self.path)
        params = parse_qs(parsed.query)
        if parsed.path == "/callback" and "code" in params and "state" in params:
            code = params["code"][0]
            telegram_user_id = int(params["state"][0])
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b"<html><body><h2>Authorization successful!</h2></body></html>")
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

async def exchange_code(code, telegram_user_id):
    async with aiohttp.ClientSession() as session:
        resp = await session.post(
            "https://open.tiktokapis.com/v2/oauth/token/",
            data={
                "client_key": TIKTOK_CLIENT_KEY,
                "client_secret": TIKTOK_CLIENT_SECRET,
                "code": code,
                "grant_type": "authorization_code",
                "redirect_uri": TIKTOK_REDIRECT_URI,
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
    await bot.send_message(telegram_user_id, f"✅ Аккаунт подключён: {display_name}")


# ─── Команды ─────────────────────────────────────────────────────────────────

@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    await message.answer(
        "👋 TikTok Ads Manager Bot\n\n"
        "📢 Реклама:\n"
        "/newcampaign — создать рекламную кампанию\n"
        "/mycampaigns — просмотр и удаление кампаний\n"
        "/deletecampaign — удалить кампанию по ID\n\n"
        "📱 Постинг:\n"
        "/connect — подключить TikTok аккаунт\n"
        "/accounts — список аккаунтов\n"
        "/post — опубликовать видео\n\n"
        "/restart — сбросить текущее состояние",
        reply_markup=ReplyKeyboardRemove()
    )


@dp.message(Command("deletecampaign"))
async def cmd_delete_campaign(message: types.Message):
    args = message.text.split()
    if len(args) < 3:
        await message.answer(
            "Использование:\n"
            "/deletecampaign ADVERTISER_ID CAMPAIGN_ID\n\n"
            "Пример:\n"
            "/deletecampaign 7652299857702961172 1870817126333617"
        )
        return

    advertiser_id = args[1]
    campaign_id = args[2]

    async with aiohttp.ClientSession() as session:
        headers = {"Access-Token": MARKETING_TOKEN, "Content-Type": "application/json"}
        base_url = "https://business-api.tiktok.com/open_api/v1.3"

        # Пробуем удалить через Smart+ endpoint
        r = await session.post(
            f"{base_url}/smart_plus/campaign/status/update/",
            json={"advertiser_id": advertiser_id, "campaign_ids": [campaign_id], "operation_status": "DELETE"},
            headers=headers
        )
        d = await r.json()

        if d.get("code") == 0:
            await message.answer(f"✅ Кампания {campaign_id} удалена")
            return

        # Если не Smart+ — пробуем обычный endpoint
        r = await session.post(
            f"{base_url}/campaign/status/update/",
            json={"advertiser_id": advertiser_id, "campaign_ids": [campaign_id], "operation_status": "DELETE"},
            headers=headers
        )
        d = await r.json()

        if d.get("code") == 0:
            await message.answer(f"✅ Кампания {campaign_id} удалена")
        else:
            await message.answer(f"❌ Ошибка: {d.get('message')}")


class DeleteCampaignStates(StatesGroup):
    select_advertiser = State()
    select_campaigns  = State()
    confirm_delete    = State()


@dp.message(Command("mycampaigns"))
async def cmd_mycampaigns(message: types.Message, state: FSMContext):
    await state.set_state(DeleteCampaignStates.select_advertiser)
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=name, callback_data=f"deladv_{adv_id}")]
        for adv_id, name in list(ADVERTISERS.items())[:20]
    ])
    await message.answer("Выбери кабинет для просмотра кампаний:", reply_markup=keyboard)


@dp.callback_query(F.data.startswith("deladv_"))
async def got_delete_advertiser(callback: types.CallbackQuery, state: FSMContext):
    adv_id = callback.data.replace("deladv_", "")
    await state.update_data(delete_adv_id=adv_id, delete_camp_ids=[])

    async with aiohttp.ClientSession() as session:
        headers = {"Access-Token": MARKETING_TOKEN}
        base_url = "https://business-api.tiktok.com/open_api/v1.3"
        r = await session.get(f"{base_url}/smart_plus/campaign/get/",
            params={"advertiser_id": adv_id, "page_size": 20}, headers=headers)
        d = await r.json()
        camps = d.get("data", {}).get("list", [])

    if not camps:
        await callback.message.answer("Нет активных кампаний в этом кабинете.")
        await callback.answer()
        return

    await state.update_data(delete_camps=camps)
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(
            text=f"☐ {c['campaign_name'][:40]}",
            callback_data=f"delcamp_{c['campaign_id']}"
        )]
        for c in camps
    ] + [[InlineKeyboardButton(text="🗑 Удалить выбранные", callback_data="confirm_delete")]])

    await callback.message.answer(
        f"Кампании в {ADVERTISERS.get(adv_id, adv_id)}:\nВыбери для удаления:",
        reply_markup=keyboard
    )
    await state.set_state(DeleteCampaignStates.select_campaigns)
    await callback.answer()


@dp.callback_query(F.data.startswith("delcamp_"))
async def toggle_delete_campaign(callback: types.CallbackQuery, state: FSMContext):
    camp_id = callback.data.replace("delcamp_", "")
    data = await state.get_data()
    selected = data.get("delete_camp_ids", [])
    camps = data.get("delete_camps", [])

    if camp_id in selected:
        selected.remove(camp_id)
    else:
        selected.append(camp_id)
    await state.update_data(delete_camp_ids=selected)

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(
            text=f"{'✅' if c['campaign_id'] in selected else '☐'} {c['campaign_name'][:40]}",
            callback_data=f"delcamp_{c['campaign_id']}"
        )]
        for c in camps
    ] + [[InlineKeyboardButton(text=f"🗑 Удалить выбранные ({len(selected)})", callback_data="confirm_delete")]])

    try:
        await callback.message.edit_reply_markup(reply_markup=keyboard)
    except Exception:
        pass
    await callback.answer()


@dp.callback_query(F.data == "confirm_delete")
async def confirm_delete_campaigns(callback: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()
    selected = data.get("delete_camp_ids", [])
    adv_id = data.get("delete_adv_id")

    if not selected:
        await callback.answer("Выбери хотя бы одну кампанию!", show_alert=True)
        return

    camps = data.get("delete_camps", [])
    names = [c["campaign_name"] for c in camps if c["campaign_id"] in selected]

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Да, удалить", callback_data="do_delete")],
        [InlineKeyboardButton(text="❌ Отмена", callback_data="cancel_delete")],
    ])
    await callback.message.answer(
        f"⚠️ Удалить {len(selected)} кампаний?\n\n" + "\n".join(f"• {n}" for n in names),
        reply_markup=keyboard
    )
    await callback.answer()


@dp.callback_query(F.data == "do_delete")
async def do_delete_campaigns(callback: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()
    selected = data.get("delete_camp_ids", [])
    adv_id = data.get("delete_adv_id")

    async with aiohttp.ClientSession() as session:
        headers = {"Access-Token": MARKETING_TOKEN, "Content-Type": "application/json"}
        base_url = "https://business-api.tiktok.com/open_api/v1.3"
        r = await session.post(f"{base_url}/smart_plus/campaign/status/update/",
            headers=headers,
            json={"advertiser_id": adv_id, "campaign_ids": selected, "operation_status": "DELETE"})
        d = await r.json()

    if d.get("code") == 0:
        await callback.message.answer(f"✅ Удалено {len(selected)} кампаний")
    else:
        await callback.message.answer(f"❌ Ошибка: {d.get('message')}")

    await state.clear()
    await callback.answer()


@dp.callback_query(F.data == "cancel_delete")
async def cancel_delete(callback: types.CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.answer("❌ Удаление отменено")
    await callback.answer()


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
    await message.answer("Нажми кнопку для авторизации, потом отправь URL из браузера:", reply_markup=keyboard)


@dp.message(PostStates.waiting_code)
async def got_code(message: types.Message, state: FSMContext):
    import re
    text = message.text.strip()
    match = re.search(r'code=([^&\s]+)', text)
    code = match.group(1) if match else text
    await state.clear()
    await message.answer("⏳ Получаю токен...")
    await exchange_code(code, message.from_user.id)


@dp.message(Command("accounts"))
async def cmd_accounts(message: types.Message):
    if not accounts:
        await message.answer("Нет подключённых аккаунтов. Используй /connect")
        return
    text = "📋 Подключённые аккаунты:\n\n"
    for open_id, info in accounts.items():
        text += f"• {info['display_name']} ({open_id})\n"
    await message.answer(text)


# ─── Постинг видео ────────────────────────────────────────────────────────────

@dp.message(Command("post"))
async def cmd_post(message: types.Message, state: FSMContext):
    if not accounts:
        await message.answer("Сначала подключи аккаунт через /connect")
        return
    await state.set_state(PostStates.waiting_video)
    await message.answer("📹 Отправь видео")


@dp.message(PostStates.waiting_video, F.video | F.document)
async def got_post_video(message: types.Message, state: FSMContext):
    file_id = message.document.file_id if message.document else message.video.file_id
    await state.update_data(file_id=file_id)
    await state.set_state(PostStates.waiting_caption)
    await message.answer("✏️ Введи описание видео")


@dp.message(PostStates.waiting_caption)
async def got_caption(message: types.Message, state: FSMContext):
    await state.update_data(caption=message.text)
    await state.set_state(PostStates.waiting_hashtags)
    await message.answer("🏷 Хэштеги через пробел или отправь — чтобы пропустить")


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
    await message.answer("👤 Выбери аккаунты:", reply_markup=keyboard)


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
    await callback.message.answer("⏳ Публикую...")
    await state.clear()
    full_text = f"{data.get('caption', '')}\n{data.get('hashtags', '')}".strip()
    results = []
    for open_id in selected:
        acc = accounts[open_id]
        success, msg = await post_to_tiktok(acc["access_token"], data["file_id"], full_text)
        results.append(f"{'✅' if success else '❌'} {acc['display_name']}: {msg}")
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
                "https://open.tiktokapis.com/v2/post/publish/video/init/",
                json={
                    "post_info": {"title": title[:150], "privacy_level": "SELF_ONLY", "disable_duet": False, "disable_comment": False, "disable_stitch": False},
                    "source_info": {"source": "FILE_UPLOAD", "video_size": file_size, "chunk_size": file_size, "total_chunk_count": 1}
                },
                headers={"Authorization": f"Bearer {access_token}", "Content-Type": "application/json"}
            )
            init_data = await init_resp.json()
            if init_data.get("error", {}).get("code") != "ok":
                return False, str(init_data.get("error", init_data))
            upload_url = init_data["data"]["upload_url"]
            publish_id = init_data["data"]["publish_id"]
            upload_resp = await session.put(
                upload_url, data=video_bytes,
                headers={"Content-Type": "video/mp4", "Content-Range": f"bytes 0-{file_size-1}/{file_size}", "Content-Length": str(file_size)}
            )
            if upload_resp.status not in [200, 201, 206]:
                return False, f"Ошибка загрузки: {upload_resp.status}"
            return True, f"опубликовано (publish_id: {publish_id})"
    except Exception as e:
        return False, str(e)


# ─── Создание кампании — шаги ─────────────────────────────────────────────────

@dp.message(Command("newcampaign"))
async def cmd_new_campaign(message: types.Message, state: FSMContext):
    await state.set_state(CampaignStates.select_advertisers)
    await state.update_data(selected_advertisers=[])
    await message.answer(
        "📢 *Создание рекламной кампании*\n\nШаг 1/17 — Выбери рекламные кабинеты:",
        parse_mode="Markdown",
        reply_markup=build_advertisers_keyboard([])
    )


@dp.callback_query(F.data.startswith("adv_") & ~F.data.in_({"adv_all", "adv_none"}))
async def toggle_advertiser(callback: types.CallbackQuery, state: FSMContext):
    adv_id = callback.data.replace("adv_", "")
    if adv_id not in ADVERTISERS:
        await callback.answer()
        return
    data = await state.get_data()
    selected = data.get("selected_advertisers", [])
    if adv_id in selected:
        selected.remove(adv_id)
    else:
        selected.append(adv_id)
    await state.update_data(selected_advertisers=selected)
    try:
        current_state = await state.get_state()
        if current_state == CampaignStates.select_advertisers:
            await callback.message.edit_reply_markup(reply_markup=build_advertisers_keyboard(selected))
        else:
            await callback.message.edit_reply_markup(reply_markup=build_confirm_keyboard(selected))
    except Exception:
        pass
    await callback.answer()


@dp.callback_query(F.data == "adv_all")
async def select_all_advertisers(callback: types.CallbackQuery, state: FSMContext):
    selected = list(ADVERTISERS.keys())
    await state.update_data(selected_advertisers=selected)
    try:
        current_state = await state.get_state()
        if current_state == CampaignStates.select_advertisers:
            await callback.message.edit_reply_markup(reply_markup=build_advertisers_keyboard(selected))
        else:
            await callback.message.edit_reply_markup(reply_markup=build_confirm_keyboard(selected))
    except Exception:
        pass
    await callback.answer(f"Выбрано {len(selected)} кабинетов")


@dp.callback_query(F.data == "adv_none")
async def deselect_all_advertisers(callback: types.CallbackQuery, state: FSMContext):
    await state.update_data(selected_advertisers=[])
    try:
        current_state = await state.get_state()
        if current_state == CampaignStates.select_advertisers:
            await callback.message.edit_reply_markup(reply_markup=build_advertisers_keyboard([]))
        else:
            await callback.message.edit_reply_markup(reply_markup=build_confirm_keyboard([]))
    except Exception:
        pass
    await callback.answer("Все сняты")


@dp.callback_query(F.data == "advertisers_done")
async def advertisers_done(callback: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()
    selected = data.get("selected_advertisers", [])
    if not selected:
        await callback.answer("Выбери хотя бы один кабинет!", show_alert=True)
        return
    await state.set_state(CampaignStates.campaign_name)
    await callback.message.answer(f"✅ Выбрано {len(selected)} кабинетов\n\nШаг 2/17 — Введи название кампании:", reply_markup=ReplyKeyboardRemove())
    await callback.answer()


@dp.message(CampaignStates.campaign_name, F.text != "◀️ Назад")
async def got_campaign_name(message: types.Message, state: FSMContext):
    await state.update_data(campaign_name=message.text)
    await state.set_state(CampaignStates.campaign_objective)
    keyboard = ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text=k)] for k in OBJECTIVES.keys()] + [[KeyboardButton(text="◀️ Назад")]],
        resize_keyboard=True, one_time_keyboard=True
    )
    await message.answer("Шаг 3/17 — Выбери цель рекламы:", reply_markup=keyboard)


@dp.message(CampaignStates.campaign_objective, F.text != "◀️ Назад")
async def got_objective(message: types.Message, state: FSMContext):
    if message.text not in OBJECTIVES:
        await message.answer("Выбери цель из списка 👇")
        return
    await state.update_data(objective=OBJECTIVES[message.text])
    await state.set_state(CampaignStates.budget_level)
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="📊 На кампанию (CBO)")],
            [KeyboardButton(text="📁 На группу объявлений")],
            [KeyboardButton(text="◀️ Назад")],
        ],
        resize_keyboard=True, one_time_keyboard=True
    )
    await message.answer("Шаг 4/17 — Где устанавливать бюджет?", reply_markup=keyboard)


@dp.message(CampaignStates.budget_level, F.text != "◀️ Назад")
async def got_budget_level(message: types.Message, state: FSMContext):
    if message.text == "📊 На кампанию (CBO)":
        await state.update_data(budget_optimize_on=True)
    elif message.text == "📁 На группу объявлений":
        await state.update_data(budget_optimize_on=False)
    else:
        await message.answer("Выбери из списка 👇")
        return
    await state.set_state(CampaignStates.budget_mode)
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="📅 Дневной")],
            [KeyboardButton(text="💰 Общий")],
            [KeyboardButton(text="◀️ Назад")],
        ],
        resize_keyboard=True, one_time_keyboard=True
    )
    await message.answer("Шаг 5/17 — Тип бюджета:", reply_markup=keyboard)


@dp.message(CampaignStates.budget_mode, F.text != "◀️ Назад")
async def got_budget_mode(message: types.Message, state: FSMContext):
    if message.text == "📅 Дневной":
        await state.update_data(budget_mode="BUDGET_MODE_DAY")
    elif message.text == "💰 Общий":
        await state.update_data(budget_mode="BUDGET_MODE_TOTAL")
    else:
        await message.answer("Выбери из списка 👇")
        return
    await state.set_state(CampaignStates.budget_amount)
    await message.answer("Шаг 6/17 — Введи сумму бюджета (USD):", reply_markup=ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text="◀️ Назад")]], resize_keyboard=True))


@dp.message(CampaignStates.budget_amount, F.text != "◀️ Назад")
async def got_budget_amount(message: types.Message, state: FSMContext):
    try:
        amount = float(message.text.replace(",", "."))
        if amount <= 0:
            await message.answer("❌ Введи сумму больше 0")
            return
    except ValueError:
        await message.answer("❌ Введи число. Например: 20")
        return
    await state.update_data(budget=amount)
    await state.set_state(CampaignStates.adgroup_name)
    await message.answer("Шаг 7/17 — Введи название группы объявлений:", reply_markup=ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text="◀️ Назад")]], resize_keyboard=True))


@dp.message(CampaignStates.adgroup_name, F.text != "◀️ Назад")
async def got_adgroup_name(message: types.Message, state: FSMContext):
    await state.update_data(adgroup_name=message.text)
    await state.set_state(CampaignStates.placement)
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="🎵 Только TikTok")],
            [KeyboardButton(text="🌐 Автоматически")],
            [KeyboardButton(text="◀️ Назад")],
        ],
        resize_keyboard=True, one_time_keyboard=True
    )
    await message.answer("Шаг 8/17 — Плейсменты:", reply_markup=keyboard)


@dp.message(CampaignStates.placement, F.text != "◀️ Назад")
async def got_placement(message: types.Message, state: FSMContext):
    if message.text == "🎵 Только TikTok":
        await state.update_data(placement_type="PLACEMENT_TYPE_NORMAL", placements=["PLACEMENT_TIKTOK"])
    elif message.text == "🌐 Автоматически":
        await state.update_data(placement_type="PLACEMENT_TYPE_AUTOMATIC", placements=[])
    else:
        await message.answer("Выбери из списка 👇")
        return
    await state.set_state(CampaignStates.geo)
    keyboard = ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text=k)] for k in COUNTRIES.keys()] + [[KeyboardButton(text="◀️ Назад")]],
        resize_keyboard=True, one_time_keyboard=True
    )
    await message.answer("Шаг 9/17 — Гео:", reply_markup=keyboard)


@dp.message(CampaignStates.geo, F.text != "◀️ Назад")
async def got_geo(message: types.Message, state: FSMContext):
    if message.text not in COUNTRIES:
        await message.answer("Выбери страну из списка 👇")
        return
    await state.update_data(geo=COUNTRIES[message.text])
    await state.set_state(CampaignStates.schedule_start)
    await message.answer(
        "Шаг 10/17 — Дата начала\nФормат: `YYYY-MM-DD HH:MM:SS`\nНапример: `2026-07-20 10:00:00`",
        reply_markup=ReplyKeyboardRemove()
    )


@dp.message(CampaignStates.schedule_start, F.text != "◀️ Назад")
async def got_schedule_start(message: types.Message, state: FSMContext):
    await state.update_data(schedule_start=message.text)
    await state.set_state(CampaignStates.schedule_end)
    keyboard = ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="♾ Без даты окончания")], [KeyboardButton(text="◀️ Назад")]],
        resize_keyboard=True, one_time_keyboard=True
    )
    await message.answer(
        "Шаг 11/17 — Дата окончания\nФормат: `YYYY-MM-DD HH:MM:SS`\nИли кнопку:",
        reply_markup=keyboard
    )


@dp.message(CampaignStates.schedule_end, F.text != "◀️ Назад")
async def got_schedule_end(message: types.Message, state: FSMContext):
    end = None if message.text == "♾ Без даты окончания" else message.text
    await state.update_data(schedule_end=end)
    data = await state.get_data()
    if data.get("objective") == "LEAD_GENERATION":
        # Smart+ не поддерживает ручную ставку
        await state.update_data(bid_type="BID_TYPE_NO_BID", bid_amount=None)
        await show_pixel_list(message, state)
    else:
        await state.set_state(CampaignStates.bid_type)
        keyboard = ReplyKeyboardMarkup(
            keyboard=[
                [KeyboardButton(text="🤖 Автоставка")],
                [KeyboardButton(text="✍️ Ручная ставка")],
                [KeyboardButton(text="◀️ Назад")],
            ],
            resize_keyboard=True, one_time_keyboard=True
        )
        await message.answer("Шаг 12/17 — Ставка:", reply_markup=keyboard)


async def show_pixel_list(message_or_callback, state: FSMContext):
    """Показывает список пикселей из всех выбранных кабинетов"""
    m = message_or_callback if isinstance(message_or_callback, types.Message) else message_or_callback.message
    data = await state.get_data()
    selected = data.get("selected_advertisers", [])

    await m.answer("🔍 Загружаю пиксели...", reply_markup=ReplyKeyboardRemove())

    all_pixels = {}  # pixel_id -> {name, advertisers}
    text_lines = []

    for adv_id in selected:
        name = ADVERTISERS.get(adv_id, adv_id)
        pixels = await search_pixels(adv_id, "")
        if pixels:
            text_lines.append(f"📋 {name}:")
            for p in pixels[:5]:
                pid = p["pixel_id"]
                pname = p.get("name") or pid
                text_lines.append(f"  • {pname}")
                if pid not in all_pixels:
                    all_pixels[pid] = {"name": pname, "advertisers": []}
                all_pixels[pid]["advertisers"].append(adv_id)

    if not all_pixels:
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="◀️ Назад", callback_data="back_to_bid")],
            [InlineKeyboardButton(text="⏭ Пропустить", callback_data="pixel_skip")]
        ])
        await m.answer("❌ Пиксели не найдены ни в одном кабинете.", reply_markup=keyboard)
        return

    # Показываем текстовый список
    await m.answer("Шаг 13/17 — Пиксели по кабинетам:\n\n" + "\n".join(text_lines))

    # Показываем кнопки выбора (уникальные пиксели)
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(
            text=info["name"],
            callback_data=f"pixel_{pid}"
        )]
        for pid, info in list(all_pixels.items())[:15]
    ] + [
        [InlineKeyboardButton(text="◀️ Назад", callback_data="back_to_bid")],
        [InlineKeyboardButton(text="⏭ Пропустить", callback_data="pixel_skip")]
    ])
    await m.answer("Выбери пиксель:", reply_markup=keyboard)
    await state.set_state(CampaignStates.pixel_select)


@dp.message(CampaignStates.bid_type, F.text != "◀️ Назад")
async def got_bid_type(message: types.Message, state: FSMContext):
    if message.text == "🤖 Автоставка":
        await state.update_data(bid_type="BID_TYPE_NO_BID", bid_amount=None)
        await show_pixel_list(message, state)
    elif message.text == "✍️ Ручная ставка":
        await state.update_data(bid_type="BID_TYPE_CUSTOM", bid_amount=None)
        await state.set_state(CampaignStates.bid_amount)
        await message.answer("Шаг 12/17 — Введи ставку (USD):", reply_markup=ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text="◀️ Назад")]], resize_keyboard=True))
    else:
        await message.answer("Выбери из списка 👇")


@dp.message(CampaignStates.bid_amount, F.text != "◀️ Назад")
async def got_bid_amount(message: types.Message, state: FSMContext):
    try:
        bid = float(message.text.replace(",", "."))
        if bid <= 0:
            await message.answer("❌ Ставка должна быть больше 0")
            return
    except ValueError:
        await message.answer("❌ Введи число. Например: 5")
        return
    await state.update_data(bid_amount=bid)
    await log_api("BID AMOUNT SAVED", {"bid_amount": bid, "bid_type": (await state.get_data()).get("bid_type")}, {})
    await show_pixel_list(message, state)


@dp.message(Command("skippixel"))
async def skip_pixel(message: types.Message, state: FSMContext):
    await state.update_data(pixel_id=None)
    await state.set_state(CampaignStates.video_upload)
    await message.answer("Шаг 14/17 — Отправь видео файлом (не как медиа)")


@dp.message(CampaignStates.pixel_search, F.text != "◀️ Назад")
async def got_pixel_search(message: types.Message, state: FSMContext):
    # Оставляем для совместимости — перенаправляем на список
    await show_pixel_list(message, state)


@dp.callback_query(F.data.startswith("pixel_") & ~F.data.endswith("skip"))
async def got_pixel_select(callback: types.CallbackQuery, state: FSMContext):
    pixel_id = callback.data.replace("pixel_", "")
    await state.update_data(pixel_id=pixel_id)
    await callback.message.answer(f"✅ Пиксель: {pixel_id}")
    await state.set_state(CampaignStates.video_upload)
    await callback.message.answer("Шаг 14/17 — Отправь видео файлом (не как медиа)\n⚠️ Если не загружается — уменьши размер\n/restart — начать заново")
    await callback.answer()


@dp.callback_query(F.data == "pixel_skip")
async def skip_pixel_callback(callback: types.CallbackQuery, state: FSMContext):
    await state.update_data(pixel_id=None)
    await state.set_state(CampaignStates.video_upload)
    await callback.message.answer("Шаг 14/17 — Отправь видео файлом (не как медиа)\n⚠️ Если не загружается — уменьши размер\n/restart — начать заново")
    await callback.answer()


@dp.message(Command("restart"))
async def cmd_restart(message: types.Message, state: FSMContext):
    await state.clear()
    await message.answer("🔄 Состояние сброшено. Начни заново с /newcampaign", reply_markup=ReplyKeyboardRemove())


@dp.message(CampaignStates.video_upload, F.video | F.document)
async def got_campaign_video(message: types.Message, state: FSMContext):
    import tempfile, shutil
    file_id = message.document.file_id if message.document else message.video.file_id

    await message.answer("⏳ Скачиваю видео на сервер...")

    try:
        tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".mp4", dir="/tmp")
        video_path = tmp.name
        tmp.close()

        async with aiohttp.ClientSession() as session:
            # Получаем путь к файлу через локальный Bot API
            resp = await session.get(
                f"http://localhost:8081/bot{BOT_TOKEN}/getFile",
                params={"file_id": file_id}
            )
            data = await resp.json()
            if not data.get("ok"):
                raise Exception(f"getFile error: {data.get('description')}")
            file_path = data["result"]["file_path"]

        # В local mode file_path содержит абсолютный путь внутри контейнера
        # Маппим /var/lib/telegram-bot-api -> /tmp/telegram-bot-api
        local_file = file_path.replace("/var/lib/telegram-bot-api", "/tmp/telegram-bot-api")
        if os.path.exists(local_file):
            shutil.copy2(local_file, video_path)
        else:
            raise Exception(f"Файл не найден: {local_file}")

        await state.update_data(video_path=video_path)
        await state.set_state(CampaignStates.ad_text)
        size = os.path.getsize(video_path)
        data = await state.get_data()
        videos = data.get("videos", [])
        await message.answer(
            f"✅ Видео {len(videos)+1} скачано ({size//1024//1024} MB)!\n\nВведи текст объявления (до 100 символов):",
            reply_markup=ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text="◀️ Назад")]], resize_keyboard=True)
        )
    except Exception as e:
        await message.answer(f"❌ Ошибка скачивания видео: {e}\n/restart — начать заново")


@dp.message(CampaignStates.ad_text, F.text != "◀️ Назад")
async def got_ad_text(message: types.Message, state: FSMContext):
    data = await state.get_data()
    # Сохраняем текущее видео + текст в список
    videos = data.get("videos", [])
    videos.append({
        "video_path": data.get("video_path"),
        "ad_text": message.text[:100]
    })
    await state.update_data(videos=videos, video_path=None)

    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="➕ Добавить ещё видео")],
            [KeyboardButton(text="✅ Готово, ввести URL")],
        ],
        resize_keyboard=True, one_time_keyboard=True
    )
    await message.answer(
        f"✅ Видео {len(videos)} добавлено с текстом.\n\nДобавить ещё видео или перейти к URL?",
        reply_markup=keyboard
    )
    await state.set_state(CampaignStates.ad_url)


@dp.message(CampaignStates.ad_url, F.text == "➕ Добавить ещё видео")
async def add_more_video(message: types.Message, state: FSMContext):
    await state.set_state(CampaignStates.video_upload)
    await message.answer(
        "Отправь следующее видео файлом:",
        reply_markup=ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text="◀️ Назад")]], resize_keyboard=True)
    )


@dp.message(CampaignStates.ad_url, F.text == "✅ Готово, ввести URL")
async def ready_for_url(message: types.Message, state: FSMContext):
    await message.answer(
        "Шаг 16/17 — Ссылка на лендинг (URL):",
        reply_markup=ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text="◀️ Назад")]], resize_keyboard=True)
    )


@dp.message(CampaignStates.ad_url, F.text != "◀️ Назад", F.text != "➕ Добавить ещё видео", F.text != "✅ Готово, ввести URL")
async def got_ad_url(message: types.Message, state: FSMContext):
    await state.update_data(ad_url=message.text)
    data = await state.get_data()
    selected = data.get("selected_advertisers", [])
    names = [ADVERTISERS.get(a, a) for a in selected]
    videos = data.get("videos", [])
    text = (
        f"Шаг 17/17 — Подтверждение\n\n"
        f"📋 {data['campaign_name']}\n"
        f"🎯 Цель: {data['objective']}\n"
        f"💰 Бюджет: {data['budget']} USD\n"
        f"🎬 Видео: {len(videos)} шт.\n"
        f"📁 Кабинетов: {len(selected)}\n\n" +
        "\n".join(f"• {n}" for n in names)
    )
    await message.answer(text, reply_markup=build_confirm_keyboard(selected))


@dp.callback_query(F.data == "create_campaign")
async def create_campaign(callback: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()
    selected = data.get("selected_advertisers", [])
    if not selected:
        await callback.answer("Выбери хотя бы один кабинет!", show_alert=True)
        return

    await callback.message.answer(
        f"⏳ Создаю кампанию {data['campaign_name']} на {len(selected)} кабинетах..."
    )
    await state.clear()

    await callback.message.answer("⏳ Создаю кампании...")

    videos = data.get("videos", [])
    video_path = data.get("video_path")

    # Проверяем что есть хотя бы одно видео
    if not videos and (not video_path or not os.path.exists(video_path)):
        await callback.message.answer("❌ Видео не найдено. Начни заново /newcampaign")
        return

    for adv_id in selected:
        name = ADVERTISERS.get(adv_id, adv_id)
        success, msg = await create_tiktok_campaign(adv_id, data, video_path)
        status = "✅" if success else "❌"
        for _ in range(5):
            try:
                await callback.message.answer(f"{status} {name}\n{msg}")
                break
            except Exception:
                await asyncio.sleep(3)

    # Удаляем все временные видео
    for vid_item in videos:
        vp = vid_item.get("video_path")
        if vp and os.path.exists(vp):
            os.remove(vp)
    if video_path and os.path.exists(video_path):
        os.remove(video_path)

    await callback.message.answer("✅ Готово! Все кабинеты обработаны.")


# ─── TikTok API ───────────────────────────────────────────────────────────────

async def create_tiktok_campaign(advertiser_id, data, video_path):
    try:
        headers = {
            "Access-Token": MARKETING_TOKEN,
            "Content-Type": "application/json"
        }
        base_url = "https://business-api.tiktok.com/open_api/v1.3"
        objective = data["objective"]

        # Получаем video_path из videos списка если не передан напрямую
        videos = data.get("videos", [])
        if not video_path and videos:
            video_path = videos[0].get("video_path")

        async with aiohttp.ClientSession() as session:
            identity = await get_identity(advertiser_id, session, base_url, headers)

            # Загружаем видео файлом на сервер TikTok
            with open(video_path, "rb") as f:
                video_bytes = f.read()
            md5_hash = hashlib.md5(video_bytes).hexdigest()
            form = aiohttp.FormData()
            form.add_field("advertiser_id", advertiser_id)
            form.add_field("upload_type", "UPLOAD_BY_FILE")
            form.add_field("video_signature", md5_hash)
            form.add_field("video_file", video_bytes,
                filename=f"video_{advertiser_id}_{int(time.time())}.mp4",
                content_type="video/mp4")
            upload_resp = await session.post(
                f"{base_url}/file/video/ad/upload/",
                data=form,
                headers={"Access-Token": MARKETING_TOKEN}
            )
            upload_data = await upload_resp.json()
            await log_api("VIDEO UPLOAD", {"advertiser_id": advertiser_id}, upload_data)
            if upload_data.get("code") != 0:
                return False, f"Ошибка загрузки видео: {upload_data.get('message')}"
            d = upload_data["data"]
            item = d[0] if isinstance(d, list) else d
            video_id = item["video_id"]
            video_cover_url = item.get("video_cover_url")

            # Если обложки нет — ищем через filtering
            if not video_cover_url:
                for _ in range(6):
                    search_resp = await session.get(
                        f"{base_url}/file/video/ad/search/",
                        params={
                            "advertiser_id": advertiser_id,
                            "filtering": f'{{"video_ids":["{video_id}"]}}'
                        },
                        headers=headers
                    )
                    search_data = await search_resp.json()
                    videos = search_data.get("data", {}).get("list", [])
                    if videos and videos[0].get("video_cover_url"):
                        video_cover_url = videos[0]["video_cover_url"]
                        break
                    await asyncio.sleep(10)

            # Загружаем обложку
            web_uri = None
            if video_cover_url:
                cover_resp = await session.post(
                    f"{base_url}/file/image/ad/upload/",
                    json={"advertiser_id": advertiser_id, "upload_type": "UPLOAD_BY_URL", "image_url": video_cover_url},
                    headers=headers
                )
                cover_data = await cover_resp.json()
                if cover_data.get("code") == 0:
                    web_uri = cover_data["data"]["image_id"]

            if not web_uri:
                return False, "Не удалось загрузить обложку видео"

            if objective == "LEAD_GENERATION":
                # ── Smart+ flow ───────────────────────────────────────────────
                if not identity:
                    return False, "Не найден TikTok аккаунт для кабинета"

                # Кампания
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
                    return False, f"Ошибка кампании: {sp_camp_data.get('message')}"
                campaign_id = sp_camp_data["data"]["campaign_id"]

                # Adgroup
                sp_adgroup_payload = {
                    "advertiser_id": advertiser_id,
                    "campaign_id": campaign_id,
                    "adgroup_name": data["adgroup_name"],
                    "optimization_goal": "LEAD_GENERATION",
                    "promotion_type": "LEAD_GENERATION",
                    "bid_type": data.get("bid_type", "BID_TYPE_NO_BID"),
                    "billing_event": "OCPM",
                    "schedule_type": "SCHEDULE_START_END" if data.get("schedule_end") else "SCHEDULE_FROM_NOW",
                    "schedule_start_time": data["schedule_start"],
                    "placement_type": "PLACEMENT_TYPE_NORMAL",
                    "placements": ["PLACEMENT_TIKTOK"],
                    "targeting_spec": {"location_ids": [str(data["geo"])]},
                    "request_id": str(int(time.time() * 1000)),
                }
                if data.get("bid_amount") and data.get("bid_type") == "BID_TYPE_CUSTOM":
                    sp_adgroup_payload["bid_price"] = float(data["bid_amount"])
                if data.get("schedule_end"):
                    sp_adgroup_payload["schedule_end_time"] = data["schedule_end"]
                # Проверяем что пиксель существует в этом кабинете
                if data.get("pixel_id"):
                    pixels = await search_pixels(advertiser_id, "")
                    pixel_ids = [p["pixel_id"] for p in pixels]
                    if data["pixel_id"] in pixel_ids:
                        sp_adgroup_payload["pixel_id"] = data["pixel_id"]

                sp_adgroup_resp = await session.post(f"{base_url}/smart_plus/adgroup/create/", json=sp_adgroup_payload, headers=headers)
                sp_adgroup_data = await sp_adgroup_resp.json()
                await log_api("SMART+ ADGROUP CREATE", sp_adgroup_payload, sp_adgroup_data)
                if sp_adgroup_data.get("code") != 0:
                    return False, f"Ошибка группы: {sp_adgroup_data.get('message')}"
                adgroup_id = sp_adgroup_data["data"]["adgroup_id"]

                # Объявления — по одному для каждого видео
                videos = data.get("videos", [])
                if not videos:
                    # Обратная совместимость — одно видео
                    videos = [{"video_path": video_path, "ad_text": data.get("ad_text", "")}]

                ad_ids = []
                for i, vid_item in enumerate(videos):
                    # Загружаем видео для этого объявления
                    vid_path = vid_item.get("video_path") or video_path
                    with open(vid_path, "rb") as f:
                        vbytes = f.read()
                    vmd5 = hashlib.md5(vbytes).hexdigest()
                    vform = aiohttp.FormData()
                    vform.add_field("advertiser_id", advertiser_id)
                    vform.add_field("upload_type", "UPLOAD_BY_FILE")
                    vform.add_field("video_signature", vmd5)
                    vform.add_field("video_file", vbytes,
                        filename=f"video_{advertiser_id}_{int(time.time())}_{i}.mp4",
                        content_type="video/mp4")
                    vup_resp = await session.post(
                        f"{base_url}/file/video/ad/upload/",
                        data=vform,
                        headers={"Access-Token": MARKETING_TOKEN}
                    )
                    vup_data = await vup_resp.json()
                    if vup_data.get("code") != 0:
                        continue
                    vd = vup_data["data"]
                    vid_id = vd[0]["video_id"] if isinstance(vd, list) else vd["video_id"]
                    vid_cover_url = vd[0].get("video_cover_url") if isinstance(vd, list) else vd.get("video_cover_url")

                    # Ищем обложку
                    vid_web_uri = None
                    if not vid_cover_url:
                        for _ in range(6):
                            sr = await session.get(f"{base_url}/file/video/ad/search/",
                                params={"advertiser_id": advertiser_id, "filtering": f'{{"video_ids":["{vid_id}"]}}'},
                                headers=headers)
                            sd = await sr.json()
                            vlist = sd.get("data", {}).get("list", [])
                            if vlist and vlist[0].get("video_cover_url"):
                                vid_cover_url = vlist[0]["video_cover_url"]
                                break
                            await asyncio.sleep(10)

                    if vid_cover_url:
                        cr = await session.post(f"{base_url}/file/image/ad/upload/",
                            json={"advertiser_id": advertiser_id, "upload_type": "UPLOAD_BY_URL", "image_url": vid_cover_url},
                            headers=headers)
                        cd = await cr.json()
                        if cd.get("code") == 0:
                            vid_web_uri = cd["data"]["image_id"]

                    if not vid_web_uri:
                        continue

                    ci = {
                        "ad_format": "SINGLE_VIDEO",
                        "video_info": {"video_id": vid_id},
                        "image_info": [{"web_uri": vid_web_uri}],
                        "identity_type": identity["identity_type"],
                        "identity_id": identity["identity_id"],
                        "identity_authorized_bc_id": identity.get("identity_authorized_bc_id", ""),
                    }
                    if identity.get("ads_only_mode"):
                        ci["dark_post_status"] = "ON"

                    sp_ad_payload = {
                        "advertiser_id": advertiser_id,
                        "adgroup_id": adgroup_id,
                        "ad_name": f"{data['campaign_name']} #{i+1}",
                        "creative_list": [{"creative_info": ci}],
                        "ad_text_list": [{"ad_text": vid_item.get("ad_text", "")}],
                        "landing_page_url_list": [{"landing_page_url": data.get("ad_url", "")}] if data.get("ad_url") else [],
                        "call_to_action_list": [{"call_to_action": "LEARN_MORE"}],
                    }
                    sp_ad_resp = await session.post(f"{base_url}/smart_plus/ad/create/", json=sp_ad_payload, headers=headers)
                    sp_ad_data = await sp_ad_resp.json()
                    await log_api("SMART+ AD CREATE", sp_ad_payload, sp_ad_data)
                    if sp_ad_data.get("code") == 0:
                        ad_ids.append(sp_ad_data["data"]["smart_plus_ad_id"])

                if not ad_ids:
                    return False, "Не удалось создать ни одного объявления"

                return True, f"campaign: {campaign_id} | ads: {len(ad_ids)} шт."

            else:
                # ── Обычный flow для остальных целей ─────────────────────────
                budget_optimize_on = data.get("budget_optimize_on", False)
                camp_payload = {
                    "advertiser_id": advertiser_id,
                    "campaign_name": data["campaign_name"],
                    "objective_type": objective,
                    "budget_mode": data["budget_mode"],
                    "budget": data["budget"],
                }
                if budget_optimize_on:
                    camp_payload["budget_optimize_on"] = True

                camp_resp = await session.post(f"{base_url}/campaign/create/", json=camp_payload, headers=headers)
                camp_data = await camp_resp.json()
                await log_api("CAMPAIGN CREATE", camp_payload, camp_data)
                if camp_data.get("code") != 0:
                    return False, f"Ошибка кампании: {camp_data.get('message')}"
                campaign_id = camp_data["data"]["campaign_id"]

                # Adgroup
                optimize_goal, billing_event, promotion_type = ADGROUP_OPT_MAP.get(objective, ("CLICK", "CPC", "WEBSITE"))
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
                    "optimization_goal": optimize_goal,
                    "billing_event": billing_event,
                    "promotion_type": promotion_type,
                    "bid_type": data.get("bid_type", "BID_TYPE_NO_BID"),
                    "pacing": "PACING_MODE_SMOOTH",
                }
                if data.get("bid_amount"):
                    adgroup_payload["conversion_bid_price"] = data["bid_amount"]
                if data.get("schedule_end"):
                    adgroup_payload["schedule_end_time"] = data["schedule_end"]
                if data["placement_type"] == "PLACEMENT_TYPE_NORMAL":
                    adgroup_payload["placements"] = data["placements"]
                if data.get("pixel_id"):
                    adgroup_payload["pixel_id"] = data["pixel_id"]

                adgroup_resp = await session.post(f"{base_url}/adgroup/create/", json=adgroup_payload, headers=headers)
                adgroup_data = await adgroup_resp.json()
                await log_api("ADGROUP CREATE", adgroup_payload, adgroup_data)
                if adgroup_data.get("code") != 0:
                    return False, f"Ошибка группы: {adgroup_data.get('message')}"
                adgroup_id = adgroup_data["data"]["adgroup_id"]

                # Объявление
                creative = {
                    "ad_name": data["campaign_name"],
                    "ad_text": data.get("ad_text", ""),
                    "video_id": video_id,
                    "landing_page_url": data.get("ad_url", ""),
                    "call_to_action": "LEARN_MORE",
                    "ad_format": "SINGLE_VIDEO",
                }
                if identity:
                    creative["identity_id"] = identity["identity_id"]
                    creative["identity_type"] = identity["identity_type"]
                    if identity.get("identity_authorized_bc_id"):
                        creative["identity_authorized_bc_id"] = identity["identity_authorized_bc_id"]

                ad_resp = await session.post(
                    f"{base_url}/ad/create/",
                    json={"advertiser_id": advertiser_id, "adgroup_id": adgroup_id, "creatives": [creative]},
                    headers=headers
                )
                ad_data = await ad_resp.json()
                await log_api("AD CREATE", {}, ad_data)
                if ad_data.get("code") != 0:
                    return False, f"Ошибка объявления: {ad_data.get('message')}"

                return True, f"campaign_id: {campaign_id}"

    except Exception as e:
        import traceback
        return False, f"{str(e)} | {traceback.format_exc()[-300:]}"



# ─── Кнопки "Назад" ──────────────────────────────────────────────────────────

async def show_step(state, msg_or_cb, step_name):
    """Показывает нужный шаг"""
    m = msg_or_cb if isinstance(msg_or_cb, types.Message) else msg_or_cb.message
    data = await state.get_data()

    if step_name == "select_advertisers":
        selected = data.get("selected_advertisers", [])
        await state.set_state(CampaignStates.select_advertisers)
        await m.answer("Шаг 1/17 — Выбери рекламные кабинеты:", reply_markup=build_advertisers_keyboard(selected))

    elif step_name == "campaign_name":
        await state.set_state(CampaignStates.campaign_name)
        kb = ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text="◀️ Назад")]], resize_keyboard=True)
        await m.answer("Шаг 2/17 — Введи название кампании:", reply_markup=kb)

    elif step_name == "campaign_objective":
        await state.set_state(CampaignStates.campaign_objective)
        keyboard = ReplyKeyboardMarkup(
            keyboard=[[KeyboardButton(text=k)] for k in OBJECTIVES.keys()] + [[KeyboardButton(text="◀️ Назад")]],
            resize_keyboard=True, one_time_keyboard=True
        )
        await m.answer("Шаг 3/17 — Выбери цель рекламы:", reply_markup=keyboard)

    elif step_name == "budget_level":
        await state.set_state(CampaignStates.budget_level)
        keyboard = ReplyKeyboardMarkup(
            keyboard=[[KeyboardButton(text="📊 На кампанию (CBO)")], [KeyboardButton(text="📁 На группу объявлений")], [KeyboardButton(text="◀️ Назад")]],
            resize_keyboard=True, one_time_keyboard=True
        )
        await m.answer("Шаг 4/17 — Где устанавливать бюджет?", reply_markup=keyboard)

    elif step_name == "budget_mode":
        await state.set_state(CampaignStates.budget_mode)
        keyboard = ReplyKeyboardMarkup(
            keyboard=[[KeyboardButton(text="📅 Дневной")], [KeyboardButton(text="💰 Общий")], [KeyboardButton(text="◀️ Назад")]],
            resize_keyboard=True, one_time_keyboard=True
        )
        await m.answer("Шаг 5/17 — Тип бюджета:", reply_markup=keyboard)

    elif step_name == "budget_amount":
        await state.set_state(CampaignStates.budget_amount)
        kb = ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text="◀️ Назад")]], resize_keyboard=True)
        await m.answer("Шаг 6/17 — Введи сумму бюджета (USD):", reply_markup=kb)

    elif step_name == "adgroup_name":
        await state.set_state(CampaignStates.adgroup_name)
        kb = ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text="◀️ Назад")]], resize_keyboard=True)
        await m.answer("Шаг 7/17 — Введи название группы объявлений:", reply_markup=kb)

    elif step_name == "placement":
        await state.set_state(CampaignStates.placement)
        keyboard = ReplyKeyboardMarkup(
            keyboard=[[KeyboardButton(text="🎵 Только TikTok")], [KeyboardButton(text="🌐 Автоматически")], [KeyboardButton(text="◀️ Назад")]],
            resize_keyboard=True, one_time_keyboard=True
        )
        await m.answer("Шаг 8/17 — Плейсменты:", reply_markup=keyboard)

    elif step_name == "geo":
        await state.set_state(CampaignStates.geo)
        keyboard = ReplyKeyboardMarkup(
            keyboard=[[KeyboardButton(text=k)] for k in COUNTRIES.keys()] + [[KeyboardButton(text="◀️ Назад")]],
            resize_keyboard=True, one_time_keyboard=True
        )
        await m.answer("Шаг 9/17 — Гео:", reply_markup=keyboard)

    elif step_name == "schedule_start":
        await state.set_state(CampaignStates.schedule_start)
        kb = ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text="◀️ Назад")]], resize_keyboard=True)
        await m.answer("Шаг 10/17 — Дата начала\nФормат: YYYY-MM-DD HH:MM:SS", reply_markup=kb)

    elif step_name == "schedule_end":
        await state.set_state(CampaignStates.schedule_end)
        keyboard = ReplyKeyboardMarkup(
            keyboard=[[KeyboardButton(text="♾ Без даты окончания")], [KeyboardButton(text="◀️ Назад")]],
            resize_keyboard=True, one_time_keyboard=True
        )
        await m.answer("Шаг 11/17 — Дата окончания:", reply_markup=keyboard)

    elif step_name == "bid_type":
        await state.set_state(CampaignStates.bid_type)
        keyboard = ReplyKeyboardMarkup(
            keyboard=[[KeyboardButton(text="🤖 Автоставка")], [KeyboardButton(text="✍️ Ручная ставка")], [KeyboardButton(text="◀️ Назад")]],
            resize_keyboard=True, one_time_keyboard=True
        )
        await m.answer("Шаг 12/17 — Ставка:", reply_markup=keyboard)

    elif step_name == "pixel_search":
        await state.set_state(CampaignStates.pixel_search)
        kb = ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text="◀️ Назад")]], resize_keyboard=True)
        await m.answer("Шаг 13/17 — Пиксель\nВведи часть названия или ID\nИли . чтобы показать все пиксели\nИли /skippixel чтобы пропустить:", reply_markup=kb)

    elif step_name == "video_upload":
        await state.set_state(CampaignStates.video_upload)
        kb = ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text="◀️ Назад")]], resize_keyboard=True)
        await m.answer("Шаг 14/17 — Отправь видео файлом (не как медиа)", reply_markup=kb)

    elif step_name == "ad_text":
        await state.set_state(CampaignStates.ad_text)
        kb = ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text="◀️ Назад")]], resize_keyboard=True)
        await m.answer("Шаг 15/17 — Текст объявления (до 100 символов):", reply_markup=kb)

    elif step_name == "ad_url":
        await state.set_state(CampaignStates.ad_url)
        kb = ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text="◀️ Назад")]], resize_keyboard=True)
        await m.answer("Шаг 16/17 — Ссылка на лендинг (URL):", reply_markup=kb)


# Маппинг шагов назад
BACK_MAP = {
    CampaignStates.campaign_name: "select_advertisers",
    CampaignStates.campaign_objective: "campaign_name",
    CampaignStates.budget_level: "campaign_objective",
    CampaignStates.budget_mode: "budget_level",
    CampaignStates.budget_amount: "budget_mode",
    CampaignStates.adgroup_name: "budget_amount",
    CampaignStates.placement: "adgroup_name",
    CampaignStates.geo: "placement",
    CampaignStates.schedule_start: "geo",
    CampaignStates.schedule_end: "schedule_start",
    CampaignStates.bid_type: "schedule_end",
    CampaignStates.bid_amount: "bid_type",
    CampaignStates.pixel_search: "bid_type",
    CampaignStates.pixel_select: "pixel_search",
    CampaignStates.video_upload: "pixel_search",
    CampaignStates.ad_text: "video_upload",
    CampaignStates.ad_url: "ad_text",
}


@dp.message(F.text == "◀️ Назад")
async def go_back(message: types.Message, state: FSMContext):
    current = await state.get_state()
    # Конвертируем строку состояния в объект
    for state_obj, back_step in BACK_MAP.items():
        if current == state_obj:
            await show_step(state, message, back_step)
            return
    # Если не нашли — возвращаем к выбору кабинетов
    await show_step(state, message, "select_advertisers")


@dp.callback_query(F.data == "back_to_bid")
async def back_to_bid(callback: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()
    if data.get("bid_type") == "BID_TYPE_CUSTOM":
        await show_step(state, callback, "bid_amount")
    else:
        await show_step(state, callback, "bid_type")
    await callback.answer()


loop = None

async def main():
    global loop
    loop = asyncio.get_event_loop()
    # Чистим старые временные видео при старте
    import glob
    for f in glob.glob("/tmp/*.mp4"):
        try:
            os.remove(f)
        except Exception:
            pass
    threading.Thread(target=run_web, daemon=True).start()
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
