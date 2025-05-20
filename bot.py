import os
import logging
from telegram import Update
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler,
    ContextTypes, filters
)
from openai import OpenAI

# ключи
BOT_TOKEN = os.getenv("BOT_TOKEN")
client = OpenAI(
    api_key=os.getenv("OPENROUTER_API_KEY"),
    base_url="https://openrouter.ai/api/v1"
)

# логирование
logging.basicConfig(level=logging.INFO)

# /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("👋 Бот запущен. Напиши вопрос по кредитованию.")

# GPT-ответ
async def gpt_reply(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        user_input = update.message.text
        response = client.chat.completions.create(
            model="openai/gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "Ты банковский менеджер, отвечай ясно и дружелюбно."},
                {"role": "user", "content": user_input}
            ]
        )
        await update.message.reply_text(response.choices[0].message.content)
    except Exception as e:
        logging.error(f"GPT ERROR: {e}")
        await update.message.reply_text("❌ GPT временно недоступен.")

# точка входа
def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, gpt_reply))
    app.run_polling()

if __name__ == "__main__":
    main()




