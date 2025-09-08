import os
from flask import Flask, request
import requests

app = Flask(__name__)

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
WEBHOOK_SECRET = os.getenv("WEBHOOK_SECRET", "mysecret")

@app.route("/", methods=["GET"])
def index():
    return "Bot is running!"

@app.route("/webhook", methods=["POST"])
def webhook():
    if request.method == "POST":
        update = request.get_json()
        if update and "message" in update:
            chat_id = update["message"]["chat"]["id"]
            text = update["message"].get("text", "")

            # پاسخ ساده به پیام کاربر
            reply_text = f"You said: {text}"
            requests.post(
                f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
                json={"chat_id": chat_id, "text": reply_text}
            )
        return {"ok": True}
    return {"ok": False}, 400

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
