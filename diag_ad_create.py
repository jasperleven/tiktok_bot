#!/usr/bin/env python3
"""
Диагностика ошибки 40002 "Some automatic creative settings aren't supported".

1) Берёт ПОСЛЕДНИЙ упавший запрос SMART+ AD CREATE из /tmp/tiktok_api.log.
2) Шлёт его в TikTok в нескольких вариантах (по одному изменению за раз)
   и печатает код/сообщение каждого — видно, какое поле ломает.
3) Печатает ad_configuration рабочих объявлений этого же кабинета
   (например, созданных вручную) — для сравнения.

ВНИМАНИЕ: успешный вариант создаёт реальное объявление в той же группе
(оно создаётся в статусе группы; удалить можно в Ads Manager).
Запуск:  cd /root/tiktok_bot && python3 diag_ad_create.py
"""
import json, os, re, sys, copy, urllib.request

LOG = "/tmp/tiktok_api.log"
BASE = "https://business-api.tiktok.com/open_api/v1.3"

# --- токены из .env -----------------------------------------------------------
env = {}
for path in (".env", "/root/tiktok_bot/.env"):
    if os.path.exists(path):
        for line in open(path, encoding="utf-8"):
            if "=" in line and not line.strip().startswith("#"):
                k, v = line.split("=", 1)
                env[k.strip()] = v.strip().strip('"').strip("'")
        break
TOKENS = [t for t in (env.get("TIKTOK_MARKETING_TOKEN"), env.get("TIKTOK_MARKETING_TOKEN_NASTYA")) if t]


def call(method, path, token, body=None, params=None):
    url = BASE + path
    if params:
        url += "?" + "&".join(f"{k}={urllib.parse.quote(str(v))}" for k, v in params.items())
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(url, data=data, method=method,
                                 headers={"Access-Token": token, "Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.loads(r.read())


import urllib.parse

# --- последний упавший запрос из лога ----------------------------------------
text = open(LOG, encoding="utf-8").read()
blocks = re.split(r"\n=== [^\n]*\| ", text)
payload = None
for b in reversed(blocks):
    if not b.startswith("SMART+ AD CREATE"):
        continue
    m = re.search(r"REQUEST: (\{.*?\n\})\nRESPONSE: (\{.*?\n\})", b, re.S)
    if not m:
        continue
    resp = json.loads(m.group(2))
    if resp.get("code") != 0:
        payload = json.loads(m.group(1))
        break
if not payload:
    sys.exit("В логе не найден упавший SMART+ AD CREATE")

adv = payload["advertiser_id"]
print(f"Кабинет {adv}, группа {payload['adgroup_id']}, креативов: {len(payload['creative_list'])}")

# подбираем токен, который видит этот кабинет
token = None
for t in TOKENS:
    r = call("GET", "/smart_plus/ad/get/", t, params={"advertiser_id": adv, "page_size": 50})
    if r.get("code") == 0:
        token, existing = t, r
        break
if not token:
    sys.exit("Ни один токен из .env не видит этот кабинет")

# --- рабочие объявления кабинета для сравнения -------------------------------
print("\n=== Существующие объявления кабинета (ad_configuration + первый creative_info) ===")
for ad in (existing.get("data") or {}).get("list", [])[:5]:
    ci = ((ad.get("creative_list") or [{}])[0] or {}).get("creative_info", {})
    print(f"\n# {ad.get('ad_name')}  id={ad.get('smart_plus_ad_id')}")
    print("ad_configuration:", json.dumps(ad.get("ad_configuration"), ensure_ascii=False))
    print("creative_info keys:", {k: v for k, v in ci.items() if k not in ('video_info', 'image_info')})

# --- варианты -----------------------------------------------------------------
def variant(name, fn):
    p = copy.deepcopy(payload)
    fn(p)
    p["ad_name"] = (p.get("ad_name") or "diag")[:30] + " diag"
    r = call("POST", "/smart_plus/ad/create/", token, body=p)
    print(f"\n[{name}] code={r.get('code')} {r.get('message')}")
    return r.get("code") == 0

def drop_cfg(*keys):
    def f(p):
        for k in keys:
            (p.get("ad_configuration") or {}).pop(k, None)
    return f

def one_creative(p):
    p["creative_list"] = p["creative_list"][:1]

def no_identity_in_ci(p):
    for c in p["creative_list"]:
        for k in ("identity_type", "identity_id", "identity_authorized_bc_id"):
            c["creative_info"].pop(k, None)

def dark_post(p):
    for c in p["creative_list"]:
        c["creative_info"]["dark_post_status"] = "ON"

def no_names(p):
    for c in p["creative_list"]:
        c["creative_info"].pop("material_name", None)
        c["creative_info"]["video_info"].pop("file_name", None)

print("\n=== Пробы (по одному изменению). Остановлюсь на первом успешном. ===")
tests = [
    ("как есть", lambda p: None),
    ("без product_info_enabled", drop_cfg("product_info_enabled")),
    ("без creative_auto_add_toggle", drop_cfg("creative_auto_add_toggle")),
    ("без utm_params", drop_cfg("utm_params")),
    ("без identity в ad_configuration", drop_cfg("identity_type", "identity_id", "identity_authorized_bc_id")),
    ("без ad_configuration вообще", lambda p: p.pop("ad_configuration", None)),
    ("dark_post_status=ON", dark_post),
    ("без material_name/file_name", no_names),
    ("один креатив", one_creative),
    ("без call_to_action_list", lambda p: p.pop("call_to_action_list", None)),
]
for name, fn in tests:
    if variant(name, fn):
        print(f"\n>>> ПРИЧИНА: помогло «{name}». Созданное diag-объявление удали в Ads Manager.")
        break
else:
    print("\n>>> Ни одно одиночное изменение не помогло — пришли весь вывод.")
