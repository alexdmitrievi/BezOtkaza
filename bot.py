import os
import logging
import openai
from telegram import Update
from telegram.ext import ContextTypes

openai.api_key = os.getenv("OPENROUTER_API_KEY")
openai.base_url = "https://openrouter.ai/api/v1"

async def gpt_reply(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        user_question = update.message.text
        response = openai.ChatCompletion.create(
            model="openai/gpt-3.5-turbo",  # можно заменить на 'mistralai/mistral-7b-instruct'
            messages=[
                {"role": "system", "content": "Ты вежливый и понятный менеджер банка, который консультирует клиента по вопросам кредитования физических лиц."},
                {"role": "user", "content": user_question}
            ]
        )
        await update.message.reply_text(response["choices"][0]["message"]["content"])
    except Exception as e:
        logging.error(f"OpenRouter GPT ERROR: {e}")
        await update.message.reply_text("❌ Ошибка при подключении к OpenRouter. Попробуйте позже.")


