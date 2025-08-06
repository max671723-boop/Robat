import requests
import time
import threading
from flask import Flask

TOKEN = "7105294830:AAG2XSAMhAQR7ipDSkhh3CQMED9K_esLqcM"
API_URL = f"https://api.telegram.org/bot{TOKEN}/"

ADMINS = [7210975276]

user_states = {}
orders = {}

def send_message(chat_id, text, buttons=None):
    data = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "HTML"
    }
    if buttons:
        data["reply_markup"] = {"inline_keyboard": buttons}
    requests.post(API_URL + "sendMessage", json=data)

def get_updates(offset=None):
    params = {"timeout": 100, "offset": offset}
    response = requests.get(API_URL + "getUpdates", params=params)
    if response.status_code == 200:
        return response.json()
    return None

def handle_message(message):
    chat_id = message["chat"]["id"]
    text = message.get("text", "")

    if text.startswith("/start"):
        user_states[chat_id] = None
        buttons = [
            [{"text": "🛒 ثبت سفارش", "callback_data": "order"}]
        ]
        send_message(chat_id, "سلام! به ربات فروش VPN خوش اومدی 🌐\n\nیکی از گزینه‌ها رو انتخاب کن:", buttons)

    elif user_states.get(chat_id) == "ask_name":
        if chat_id not in orders:
            orders[chat_id] = {}
        orders[chat_id]["name"] = text
        user_states[chat_id] = "ask_duration"
        buttons = [[{"text": "⏳ مدت‌زمان: ۱ ماهه", "callback_data": "1month"}]]
        send_message(chat_id, "⏳ مدت‌زمان سرویس را انتخاب کن:", buttons)

    else:
        send_message(chat_id, "برای شروع لطفاً روی /start بزن.")

def handle_callback_query(callback):
    from_id = callback["from"]["id"]
    data = callback["data"]
    chat_id = callback["message"]["chat"]["id"]

    if data == "order":
        buttons = [
            [{"text": "📦 ۲۰ گیگ", "callback_data": "20"}, {"text": "📦 ۳۰ گیگ", "callback_data": "30"}],
            [{"text": "📦 ۴۰ گیگ", "callback_data": "40"}, {"text": "📦 ۵۰ گیگ", "callback_data": "50"}]
        ]
        send_message(chat_id, "لطفاً مقدار حجم موردنظر را انتخاب کن:", buttons)

    elif data in ["20", "30", "40", "50"]:
        orders[chat_id] = {"volume": data}
        buttons = [
            [{"text": "🏪 موبایل صدف", "callback_data": "store_sadaf"}],
            [{"text": "🏪 موبایل آرمان", "callback_data": "store_arman"}]
        ]
        send_message(chat_id, "🏬 فروشگاه موردنظر را انتخاب کن:", buttons)

    elif data.startswith("store_"):
        if chat_id not in orders:
            orders[chat_id] = {}
        store = "موبایل صدف" if data == "store_sadaf" else "موبایل آرمان"
        orders[chat_id]["store"] = store
        user_states[chat_id] = "ask_name"
        send_message(chat_id, "👤 لطفاً نام کامل مشتری را وارد کن:")

    elif data == "1month":
        if chat_id not in orders:
            orders[chat_id] = {}
        orders[chat_id]["duration"] = "۱ ماهه"
        user_states[chat_id] = None
        save_order(chat_id)

    elif data.startswith("approve_"):
        customer_id = int(data.split("_")[1])
        send_message(customer_id, "✅ سفارش شما توسط ادمین تایید شد. منتظر دریافت سرویس باشید.")
        send_message(from_id, "✅ سفارش تأیید شد و به کاربر اطلاع داده شد.")

    elif data.startswith("reject_"):
        customer_id = int(data.split("_")[1])
        send_message(customer_id, "❌ سفارش شما توسط ادمین رد شد. لطفاً دوباره اقدام کنید.")
        send_message(from_id, "❌ سفارش رد شد و به کاربر اطلاع داده شد.")

    elif data.startswith("sent_"):
        if from_id not in ADMINS:
            return
        customer_id = int(data.split("_")[1])
        send_message(from_id, f"📤 سفارش مربوط به <code>{customer_id}</code> با موفقیت به دایرکت ارسال شد ✅")

def save_order(chat_id):
    order = orders.get(chat_id, {})
    volume = order.get("volume", "❓")
    store = order.get("store", "❓")
    name = order.get("name", "❓")
    duration = order.get("duration", "❓")

    msg = f"""
📥 <b>سفارش جدید</b>

👤 <b>نام مشتری:</b> {name}
📦 <b>حجم:</b> {volume} گیگ
⏳ <b>مدت:</b> {duration}
🏪 <b>فروشگاه:</b> {store}
🆔 <b>آی‌دی کاربر:</b> <code>{chat_id}</code>
""".strip()

    buttons = [
        [
            {"text": "✅ تایید سفارش", "callback_data": f"approve_{chat_id}"},
            {"text": "❌ رد سفارش", "callback_data": f"reject_{chat_id}"}
        ],
        [
            {"text": "📤 ارسال شد به دایرکت", "callback_data": f"sent_{chat_id}"}
        ]
    ]

    for admin_id in ADMINS:
        send_message(admin_id, msg, buttons)

    send_message(chat_id, "✅ سفارش شما ثبت شد.\nمنتظر تایید از طرف ادمین باشید.")

def bot_polling():
    offset = None
    print("✅ ربات با polling در حال اجراست...")
    while True:
        updates = get_updates(offset)
        if updates and updates["ok"]:
            for update in updates["result"]:
                offset = update["update_id"] + 1
                if "message" in update:
                    handle_message(update["message"])
                elif "callback_query" in update:
                    handle_callback_query(update["callback_query"])
        time.sleep(1)

app = Flask(__name__)

@app.route('/')
def hello_world():
    return 'Bot is running!'

def run_flask_app():
    # پورت 8080 برای اجرای روی Replit مناسب است.
    app.run(host='0.0.0.0', port=8080)

if __name__ == "__main__":
    flask_thread = threading.Thread(target=run_flask_app)
    flask_thread.start()
    bot_polling()
