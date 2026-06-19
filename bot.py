import asyncio
import os
import json
import threading
import aiohttp
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

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())

class CampaignStates(StatesGroup):
    campaign_name      = State()
    campaign_objective = State()
    budget_mode        = State()
    budget_amount      = State()
    adgroup_name       = State()
    placement          = State()
    geo                = State()
    schedule_start     = State()
    schedule_end       = State()
    video_upload       = State()
    ad_text            = State()
    ad_url             = State()
    select_advertisers = State()

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

@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    await message.answer(
        "👋 *TikTok Ads Manager Bot*\n\n"
        "📢 Команды:\n"
        "/newcampaign — создать рекламную кампанию\n",
        parse_mode="Markdown",
        reply_markup=ReplyKeyboardRemove()
    )

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
        for adv_id in ADVERTISER_IDS
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
        for aid in ADVERTISER_IDS
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
        for aid in ADVERTISER_IDS
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

    text = f"📊 *Результат:*\n\n" + "\n".join(results)
    for i in range(3):
        try:
            await callback.message.answer(text, parse_mode="Markdown")
            break
        except Exception:
            await asyncio.sleep(2)

async def create_tiktok_campaign(advertiser_id, data):
    try:
        headers = {
            "Access-Token": MARKETING_TOKEN,
            "Content-Type": "application/json"
        }
        base_url = "https://business-api.tiktok.com/open_api/v1.3"

        async with aiohttp.ClientSession() as session:
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

            form = aiohttp.FormData()
            form.add_field("advertiser_id", advertiser_id)
            form.add_field("video_file", video_bytes, filename="video.mp4", content_type="video/mp4")

            upload_resp = await session.post(
                f"{base_url}/file/video/ad/upload/",
                data=form,
                headers={"Access-Token": MARKETING_TOKEN}
            )
            upload_data = await upload_resp.json()
            if upload_data.get("code") != 0:
                return False, f"Ошибка загрузки видео: {upload_data.get('message')}"
            video_id = upload_data["data"]["video_id"]

            # 3. Создаём группу объявлений
            adgroup_payload = {
                "advertiser_id": advertiser_id,
                "campaign_id": campaign_id,
                "adgroup_name": data["adgroup_name"],
                "placement_type": data["placement_type"],
                "location_ids": [data["geo"]],
                "budget_mode": data["budget_mode"],
                "budget": data["budget"],
                "schedule_type": "SCHEDULE_START_END" if data.get("schedule_end") else "SCHEDULE_FROM_NOW",
                "schedule_start_time": data["schedule_start"],
                "optimize_goal": "CLICK" if data["objective"] == "TRAFFIC" else "REACH",
                "billing_event": "CPC" if data["objective"] == "TRAFFIC" else "CPM",
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
        return False, str(e)

async def main():
    threading.Thread(target=run_web, daemon=True).start()
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
