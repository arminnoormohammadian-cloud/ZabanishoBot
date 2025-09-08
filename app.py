
import os
import json
import time
import requests
from flask import Flask, request

# پکیج‌های Google
import gspread
from google.oauth2.service_account import Credentials

# OpenAI
import openai

app = Flask(__name__)

# ---------- خواندن متغیرهای محیطی ----------
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")  # از BotFather
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")  # اختیاری، برای AI
SPREADSHEET_ID = os.environ.get("SPREADSHEET_ID")  # از URL شیت
GOOGLE_CREDENTIALS = os.environ.get("GOOGLE_CREDENTIALS")  # محتوی JSON فایل سرویس اکانت

if not TELEGRAM_TOKEN:
    raise Exception("لطفا TELEGRAM_TOKEN را در متغیرهای محیطی تنظیم کنید.")

# ---------- راه‌اندازی Google Sheets ----------
if GOOGLE_CREDENTIALS:
    with open("credentials.json", "w", encoding="utf-8") as f:
        f.write(GOOGLE_CREDENTIALS)

scopes = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
creds = Credentials.from_service_account_file("credentials.json", scopes=scopes)
gc = gspread.authorize(creds)
sh = gc.open_by_key(SPREADSHEET_ID)

try:
    students_ws = sh.worksheet("students")
except Exception:
    students_ws = sh.add_worksheet(title="students", rows="1000", cols="10")
    students_ws.append_row(["timestamp","chat_id","name","phone","level","notes"])

try:
    states_ws = sh.worksheet("states")
except Exception:
    states_ws = sh.add_worksheet(title="states", rows="1000", cols="5")
    states_ws.append_row(["chat_id","state","temp"])

# ---------- توابع کمکی ----------
TELEGRAM_API = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}"

def send_message(chat_id, text, reply_markup=None):
    url = f"{TELEGRAM_API}/sendMessage"
    payload = {"chat_id": chat_id, "text": text, "parse_mode":"HTML"}
    if reply_markup:
        payload["reply_markup"] = json.dumps(reply_markup)
    requests.post(url, data=payload)

def set_state(chat_id, state, temp=""):
    try:
        cell = states_ws.find(str(chat_id))
        row = cell.row
        states_ws.update_cell(row, 2, state)
        states_ws.update_cell(row, 3, temp)
    except gspread.exceptions.CellNotFound:
        states_ws.append_row([str(chat_id), state, temp])

def get_state(chat_id):
    try:
        cell = states_ws.find(str(chat_id))
        row = cell.row
        state = states_ws.cell(row,2).value
        temp = states_ws.cell(row,3).value
        return state, temp
    except Exception:
        return None, None

def clear_state(chat_id):
    try:
        cell = states_ws.find(str(chat_id))
        row = cell.row
        states_ws.update_cell(row,2,"")
        states_ws.update_cell(row,3,"")
    except Exception:
        pass

def save_student(chat_id, name, phone, level, notes=""):
    ts = time.strftime("%Y-%m-%d %H:%M:%S")
    students_ws.append_row([ts, str(chat_id), name, phone, level, notes])

# ---------- OpenAI helper ----------
if OPENAI_API_KEY:
    openai.api_key = OPENAI_API_KEY

def ask_openai(prompt):
    if not OPENAI_API_KEY:
        return "AI در دسترس نیست. (کلید OPENAI تنظیم نشده)"
    resp = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=[{"role":"user","content":prompt}],
        max_tokens=500
    )
    return resp["choices"][0]["message"]["content"].strip()

# ---------- مسیر وبهوک ----------
@app.route("/webhook", methods=["POST"])
def webhook():
    data = request.get_json()
    if "message" in data:
        message = data["message"]
        chat_id = message["chat"]["id"]
        text = message.get("text","")
        handle_message(chat_id, text)
    return "", 200

def handle_message(chat_id, text):
    text = (text or "").strip()
    state, temp = get_state(chat_id)

    if text == "/start":
        keyboard = {
            "keyboard": [[{"text":"ثبت‌نام"}], [{"text":"پرسش از AI"}], [{"text":"رفتن به کانال"}]],
            "resize_keyboard": True
        }
        send_message(chat_id, "سلام! من ربات آموزش زبان هستم. برای ثبت‌نام دکمهٔ «ثبت‌نام» را بزن.", reply_markup=keyboard)
        return

    if state == "await_name":
        set_state(chat_id, "await_phone", temp=text)
        send_message(chat_id, "ممنون! حالا شماره تماس (مثلاً 0912...) را وارد کن:")
        return

    if state == "await_phone":
        name = temp or ""
        phone = text
        set_state(chat_id, "await_level", temp=f"{name}||{phone}")
        send_message(chat_id, "عالی. سطح زبان خود را بنویس (مبتدی / متوسط / پیشرفته):")
        return

    if state == "await_level":
        parts = (temp or "").split("||")
        name = parts[0] if parts else ""
        phone = parts[1] if len(parts)>1 else ""
        level = text
        save_student(chat_id, name, phone, level)
        clear_state(chat_id)
        send_message(chat_id, f"تشکر {name}! اطلاعات ذخیره شد. برای ثبت‌نام نهایی لطفاً به لینک کانال یا فرم مراجعه کن.")
        return

    if text == "ثبت‌نام":
        set_state(chat_id, "await_name")
        send_message(chat_id, "لطفاً اسم و نام خود را وارد کنید:")
        return

    if text == "پرسش از AI":
        set_state(chat_id, "ai_mode")
        send_message(chat_id, "سوالت رو بپرس؛ من با AI جواب می‌دم.")
        return

    if state == "ai_mode":
        answer = ask_openai(text)
        send_message(chat_id, answer)
        return

    send_message(chat_id, "متوجه نشدم. برای شروع /start را بزن یا «ثبت‌نام» را انتخاب کن.")

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
