import os
import telebot
from flask import Flask
from threading import Thread

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
bot = telebot.TeleBot(TOKEN)
app = Flask('')

@app.route('/')
def home():
    return "✅ Bot Premium Avanzado activo"

def run():
    port = int(os.environ.get('PORT', 3000))
    app.run(host='0.0.0.0', port=port)

Thread(target=run).start()

@bot.message_handler(commands=['start'])
def start(message):
    bot.send_message(message.chat.id, "👋 Bot activo y listo para señales.")

bot.polling()
