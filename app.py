import os, json, logging
from flask import Flask, request, abort, jsonify
import requests
import gspread
from google.oauth2 import service_account

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)

# --- Env vars ---
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN", "")
SPREADSHEET_ID = os.environ.get("SPREADSHEET_ID", "")
GOOGLE_CREDENTIALS = os.environ.get("GOOGLE_CREDENTIALS", "")

if not TELEGRAM_TOKEN:
    logging.error("ENV MISSING: TELEGRAM_TOKEN")
if not SPREADSHEET_ID:
    logging.error("ENV MISSING: SPREADSHEET_ID")
if not GOOGLE_CREDENTIALS:
    logging.error("ENV MISSING: GOOGLE_CREDENTIALS")

# --- Google Sheets lazy client (برای اینکه اگر مشکل داشت سرویس کرش نکند) ---
_gc = None
_ws = None

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]

def get_worksheet():
    global _gc, _ws
    if _ws:
        return _ws
    try:
        creds_info = json.loads(GOOGLE_CREDENTIALS)
        creds = service_account.Credentials.from_service_account_info(creds_info, scopes=SCOPES)
        _gc = gspread.authorize(creds)
        sh = _gc.open_by_key(SPREADSHEET_ID)
        _ws = sh.sheet1
        logging.info("Google Sheets connected ✅")
        return _ws
    except Exception as e:
        logging.exception("Google Sheets connect failed ❌")
        return None

# --- Telegram helper ---
def tg_send_message(chat_id, text):
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
        payload = {"chat_id": chat_id, "text": text}
        r = requests.post(url, json=payload, timeout=10)
        if r.status_code != 200:
            logging.error("Telegram sendMessage failed: %s %s", r.status_code, r.text)
    except Exception:
        logging.exception("Telegram sendMessage exception")

# --- Health routes ---
@app.get("/")
def index():
    return "OK: bot is running ✅", 200

@app.get("/health")
def health():
    return jsonify(ok=True), 200

# --- Telegram webhook ---
@app.post("/webhook/<token>")
def telegram_webhook(token):
    if token != TELEGRAM_TOKEN:
        abort(403)

    update = request.get_json(silent=True) or {}
    logging.info("Update: %s", update)

    message = update.get("message") or {}
    chat = message.get("chat") or {}
    chat_id = chat.get("id")
    text = message.get("text", "")

    # همیشه جواب بدهیم که بات دانگ نگیرد
    if not chat_id:
        return jsonify(ok=True)

    # لاگ و اکوی ساده
    if text == "/start":
        tg_send_message(chat_id, "سلام! ربات فعاله ✅ پیامت رسید.")
    else:
        tg_send_message(chat_id, f"پیامت رسید: {text}")

    # تلاش برای نوشتن در شیت (اگر کانفیگ درست باشد)
    ws = get_worksheet()
    if ws:
        try:
            ws.append_row([str(chat_id), text], value_input_option="RAW")
        except Exception:
            logging.exception("Append to sheet failed")

    return jsonify(ok=True)
