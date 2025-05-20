import openai
import os
import logging
from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler, MessageHandler, filters

BOT_TOKEN = os.getenv("BOT_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
openai.api_key = OPENAI_API_KEY

logging.basicConfig(level=logging.INFO)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("✅ Бот запущен. Напиши любой вопрос, и я проверю GPT.")

async def gpt_test(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        user_input = update.message.text
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "Ты консультант по кредитам."},
                {"role": "user", "content": user_input}
            ]
        )
        await update.message.reply_text(response["choices"][0]["message"]["content"])
    except Exception as e:
        logging.error(f"GPT ERROR: {e}")
        await update.message.reply_text("❌ GPT API не отвечает. Проверь ключ и лимиты.")

def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, gpt_test))
    app.run_polling()

if __name__ == "__main__":
    main()
