import os
import requests
from flask import Flask, request
import gspread
from google.oauth2.service_account import Credentials

app = Flask(__name__)

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_API_URL = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
SPREADSHEET_ID = os.getenv("SPREADSHEET_ID")

# Google Sheets setup
scopes = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
credentials = Credentials.from_service_account_file(
    "service_account.json",
    scopes=scopes
)
client = gspread.authorize(credentials)
sheet = client.open_by_key(SPREADSHEET_ID).sheet1

@app.route("/")
def home():
    return "Bot is running!"

@app.route("/webhook", methods=["POST"])
def webhook():
    update = request.get_json()
    print("Incoming update:", update)

    if "message" in update and "text" in update["message"]:
        chat_id = update["message"]["chat"]["id"]
        text = update["message"]["text"]

        # ذخیره پیام در Google Sheet
        sheet.append_row([str(chat_id), text])

        # پاسخ به کاربر
        reply = {
            "chat_id": chat_id,
            "text": f"پیامت دریافت شد: {text}"
        }
        requests.post(TELEGRAM_API_URL, json=reply)

    return "ok", 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
