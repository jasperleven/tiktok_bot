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
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
TIKTOK_CLIENT_KEY = os.getenv("TIKTOK_CLIENT_KEY")
TIKTOK_CLIENT_SECRET = os.getenv("TIKTOK_CLIENT_SECRET")
TIKTOK_REDIRECT_URI = os.getenv("TIKTOK_REDIRECT_URI")

ACCOUNTS_FILE = "accounts.json"

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
        await bot.send_message(telegram_user_id, f"❌ Auth error: {data}")
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
    await bot.send_message(telegram_user_id, f"✅ Account connected: *{display_name}*", parse_mode="Markdown")

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
            asyncio.run_coroutine_threadsafe(
                exchange_code(code, telegram_user_id),
                loop
            )
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

@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    await message.answer(
        "👋 TikTok Auto Poster\n\n"
        "Commands:\n"
        "/post — publish a video\n"
        "/accounts — list connected accounts\n"
        "/connect — connect a new TikTok account"
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
        [InlineKeyboardButton(text="🔗 Connect TikTok Account", url=oauth_url)]
    ])
    await state.set_state(PostStates.waiting_code)
    await message.answer(
        "1. Click the button below to authorize\n"
        "2. After redirect copy the full URL from browser\n"
        "3. Send it here",
        reply_markup=keyboard
    )

@dp.message(PostStates.waiting_code)
async def got_code(message: types.Message, state: FSMContext):
    text = message.text.strip()
    # Extract code from URL if full URL was sent
    if "code=" in text:
        import re
        match = re.search(r'code=([^&\s]+)', text)
        if match:
            code = match.group(1)
        else:
            await message.answer("❌ Could not extract code. Try again.")
            return
    else:
        code = text

    await state.clear()
    await message.answer("⏳ Getting token...")
    await exchange_code(code, message.from_user.id)

@dp.message(Command("accounts"))
async def cmd_accounts(message: types.Message):
    if not accounts:
        await message.answer("No connected accounts. Use /connect")
        return
    text = "📋 Connected accounts:\n\n"
    for open_id, info in accounts.items():
        text += f"• {info['display_name']} (`{open_id}`)\n"
    await message.answer(text, parse_mode="Markdown")

@dp.message(Command("status"))
async def cmd_status(message: types.Message):
    parts = message.text.split(maxsplit=1)
    if len(parts) < 2:
        await message.answer("Usage: /status PUBLISH_ID")
        return

    publish_id = parts[1].strip()
    if not accounts:
        await message.answer("No connected accounts.")
        return

    access_token = list(accounts.values())[0]["access_token"]

    async with aiohttp.ClientSession() as session:
        resp = await session.post(
            "https://open.tiktokapis.com/v2/post/publish/status/fetch/",
            json={"publish_id": publish_id},
            headers={
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json"
            }
        )
        data = await resp.json()

    await message.answer(f"📊 Status:\n`{json.dumps(data, indent=2)}`", parse_mode="Markdown")

@dp.message(Command("post"))
async def cmd_post(message: types.Message, state: FSMContext):
    if not accounts:
        await message.answer("Please connect an account first using /connect")
        return
    await state.set_state(PostStates.waiting_video)
    await message.answer("📹 Send the video as a file (document)")

@dp.message(PostStates.waiting_video, F.document)
async def got_video_doc(message: types.Message, state: FSMContext):
    await state.update_data(file_id=message.document.file_id)
    await state.set_state(PostStates.waiting_caption)
    await message.answer("✏️ Enter the video caption")

@dp.message(PostStates.waiting_video, F.video)
async def got_video(message: types.Message, state: FSMContext):
    await state.update_data(file_id=message.video.file_id)
    await state.set_state(PostStates.waiting_caption)
    await message.answer("✏️ Enter the video caption")

@dp.message(PostStates.waiting_caption)
async def got_caption(message: types.Message, state: FSMContext):
    await state.update_data(caption=message.text)
    await state.set_state(PostStates.waiting_hashtags)
    await message.answer("🏷 Enter hashtags separated by spaces (e.g. #trend #video)\nOr send — to skip")

@dp.message(PostStates.waiting_hashtags)
async def got_hashtags(message: types.Message, state: FSMContext):
    hashtags = "" if message.text == "—" else message.text
    await state.update_data(hashtags=hashtags)
    await state.set_state(PostStates.waiting_accounts)

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(
            text=f"☐ {info['display_name']}",
            callback_data=f"acc_{open_id}"
        )]
        for open_id, info in accounts.items()
    ] + [[InlineKeyboardButton(text="🚀 Publish", callback_data="publish")]])

    await state.update_data(selected_accounts=[])
    await message.answer("👤 Select accounts to publish to:", reply_markup=keyboard)

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
        [InlineKeyboardButton(
            text=f"{'✅' if oid in selected else '☐'} {info['display_name']}",
            callback_data=f"acc_{oid}"
        )]
        for oid, info in accounts.items()
    ] + [[InlineKeyboardButton(text="🚀 Publish", callback_data="publish")]])

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
        await callback.answer("Please select at least one account!", show_alert=True)
        return

    if "file_id" not in data:
        await callback.message.answer("❌ Session expired. Please start over with /post")
        await state.clear()
        return

    await callback.message.answer("⏳ Publishing...")
    await state.clear()

    caption   = data.get("caption", "")
    hashtags  = data.get("hashtags", "")
    full_text = f"{caption}\n{hashtags}".strip()

    results = []
    for open_id in selected:
        acc = accounts[open_id]
        success, msg = await post_to_tiktok(acc["access_token"], data["file_id"], full_text)
        status = "✅" if success else "❌"
        results.append(f"{status} {acc['display_name']}: {msg}")

    await callback.message.answer("📊 Result:\n\n" + "\n".join(results))

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
                    'post_info': {
                        'title':           title[:150],
                        'privacy_level':   'SELF_ONLY',
                        'disable_duet':    False,
                        'disable_comment': False,
                        'disable_stitch':  False,
                    },
                    'source_info': {
                        'source':            'FILE_UPLOAD',
                        'video_size':        file_size,
                        'chunk_size':        file_size,
                        'total_chunk_count': 1
                    }
                },
                headers={
                    'Authorization': f'Bearer {access_token}',
                    'Content-Type':  'application/json'
                }
            )
            init_data = await init_resp.json()

            if init_data.get('error', {}).get('code') != 'ok':
                return False, str(init_data.get('error', init_data))

            upload_url = init_data['data']['upload_url']
            publish_id = init_data['data']['publish_id']

            upload_resp = await session.put(
                upload_url,
                data=video_bytes,
                headers={
                    'Content-Type':   'video/mp4',
                    'Content-Range':  f'bytes 0-{file_size-1}/{file_size}',
                    'Content-Length': str(file_size)
                }
            )

            if upload_resp.status not in [200, 201, 206]:
                return False, f'Upload failed: {upload_resp.status}'

            return True, f'published (publish_id: {publish_id})'

    except Exception as e:
        return False, str(e)

loop = None

async def main():
    global loop
    loop = asyncio.get_event_loop()
    threading.Thread(target=run_web, daemon=True).start()
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
