import os
import json
import requests
from flask import Flask, request

app = Flask(__name__)

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_API_URL = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"

@app.route("/", methods=["GET"])
def index():
    return "Bot is running!", 200

@app.route("/webhook", methods=["POST"])
def webhook():
    update = request.get_json(force=True)
    print("Incoming update:", json.dumps(update, indent=2, ensure_ascii=False))

    if "message" in update:
        chat_id = update["message"]["chat"]["id"]
        text = update["message"].get("text", "")

        reply_text = f"You said: {text}"
        payload = {"chat_id": chat_id, "text": reply_text}

        try:
            res = requests.post(TELEGRAM_API_URL, json=payload)
            print("Telegram API response:", res.status_code, res.text)
        except Exception as e:
            print("Error sending message:", str(e))

    return "ok", 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
