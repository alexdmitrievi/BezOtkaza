import os
import logging
import openai
from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler, MessageHandler, filters

# OpenRouter key и базовый URL
openai.api_key = os.getenv("OPENROUTER_API_KEY")
openai.base_url = "https://openrouter.ai/api/v1"

BOT_TOKEN = os.getenv("BOT_TOKEN")

logging.basicConfig(level=logging.INFO)

# /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("👋 Привет! Я GPT-менеджер. Напиши вопрос, и я помогу с кредитованием.")

# ответ GPT
async def gpt_reply(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        user_question = update.message.text
        response = openai.ChatCompletion.create(
            model="openai/gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "Ты вежливый и понятный менеджер банка, который консультирует клиента по вопросам кредитования физических лиц."},
                {"role": "user", "content": user_question}
            ]
        )
        await update.message.reply_text(response["choices"][0]["message"]["content"])
    except Exception as e:
        logging.error(f"OpenRouter GPT ERROR: {e}")
        await update.message.reply_text("❌ Ошибка при подключении к OpenRouter. Попробуйте позже.")

# основной запуск
def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, gpt_reply))
    app.run_polling()

if __name__ == "__main__":
    main()


