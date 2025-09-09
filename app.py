import os
import logging
import requests
import gspread
from flask import Flask, request, jsonify
from oauth2client.service_account import ServiceAccountCredentials

# Logging setup
logging.basicConfig(level=logging.INFO)

# Environment variables
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
GOOGLE_SHEET_ID = os.getenv("GOOGLE_SHEET_ID")
GOOGLE_APPLICATION_CREDENTIALS = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")

if not all([TELEGRAM_BOT_TOKEN, OPENAI_API_KEY, GOOGLE_SHEET_ID, GOOGLE_APPLICATION_CREDENTIALS]):
    raise ValueError("Missing environment variables. Please check your .env file.")

TELEGRAM_API_URL = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"

# Flask app
app = Flask(__name__)

# Google Sheets auth
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
creds = ServiceAccountCredentials.from_json_keyfile_name(GOOGLE_APPLICATION_CREDENTIALS, scope)
client = gspread.authorize(creds)
sheet = client.open_by_key(GOOGLE_SHEET_ID).sheet1

@app.route("/", methods=["GET"])
def index():
    return "Bot is running!", 200

@app.route("/webhook", methods=["POST"])
def webhook():
    update = request.get_json()
    logging.info(f"Incoming update: {update}")

    if "message" in update and "text" in update["message"]:
        chat_id = update["message"]["chat"]["id"]
        text = update["message"]["text"]

        # Save message to Google Sheets
        try:
            sheet.append_row([str(chat_id), text])
        except Exception as e:
            logging.error(f"Error saving to Google Sheets: {e}")

        # Reply to user
        reply = {
            "chat_id": chat_id,
            "text": f"✅ Your message has been saved to Google Sheets!"
        }
        requests.post(TELEGRAM_API_URL, json=reply)

    return jsonify({"ok": True})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
