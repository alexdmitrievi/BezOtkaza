import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler, MessageHandler, filters, CallbackQueryHandler, ConversationHandler
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import openai
import os
from datetime import datetime
import traceback

# Загрузка токенов
BOT_TOKEN = os.getenv("BOT_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
openai.api_key = OPENAI_API_KEY

# Логирование
logging.basicConfig(level=logging.INFO)

# Google Sheets
def init_sheet():
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    creds = ServiceAccountCredentials.from_json_keyfile_name("credentials.json", scope)
    client = gspread.authorize(creds)
    return client.open_by_url("https://docs.google.com/spreadsheets/d/15-xtnsn6VDq0O4QHPCWnIMpTqc_7zNQCrk6M47e2u3M/edit").sheet1

sheet = init_sheet()

# Состояния
ASK_NAME, ASK_AGE, ASK_ARREST, ASK_OVERDUE, ASK_AMOUNT, CONFIRM = range(6)

# Команда /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["source"] = update.message.text.split(" ")[1] if len(update.message.text.split(" ")) > 1 else "direct"
    await update.message.reply_text(
        "👋 Привет! Я помогу вам подать заявку на кредит.

Введите ваше ФИО:"
    )
    return ASK_NAME

async def ask_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["name"] = update.message.text
    await update.message.reply_text("Укажите ваш возраст:")
    return ASK_AGE

async def ask_age(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["age"] = update.message.text
    buttons = [[InlineKeyboardButton("Да", callback_data="арест_да"), InlineKeyboardButton("Нет", callback_data="арест_нет")]]
    await update.message.reply_text("Есть ли у вас аресты?", reply_markup=InlineKeyboardMarkup(buttons))
    return ASK_ARREST

async def ask_arrest(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["arrest"] = "Да" if update.callback_query.data == "арест_да" else "Нет"
    await update.callback_query.answer()
    buttons = [[InlineKeyboardButton("Да", callback_data="просрочка_да"), InlineKeyboardButton("Нет", callback_data="просрочка_нет")]]
    await update.callback_query.edit_message_text("Есть ли текущие просрочки?", reply_markup=InlineKeyboardMarkup(buttons))
    return ASK_OVERDUE

async def ask_overdue(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["overdue"] = "Да" if update.callback_query.data == "просрочка_да" else "Нет"
    await update.callback_query.answer()
    await update.callback_query.edit_message_text("Какую сумму кредита вы хотите?")
    return ASK_AMOUNT

async def ask_amount(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["amount"] = update.message.text
    return await show_summary(update, context)

async def show_summary(update_or_callback, context: ContextTypes.DEFAULT_TYPE):
    summary = f"📋 Ваша заявка:

ФИО: {context.user_data['name']}
Возраст: {context.user_data['age']}
Аресты: {context.user_data['arrest']}
Просрочки: {context.user_data['overdue']}
Сумма: {context.user_data['amount']}"
    buttons = [
        [InlineKeyboardButton("✅ Отправить", callback_data="confirm")],
        [InlineKeyboardButton("✏️ Редактировать заявку", callback_data="edit")],
        [InlineKeyboardButton("📞 Связаться с менеджером", url="https://t.me/zhbankov_alex")],
        [InlineKeyboardButton("🔁 Перезапустить", callback_data="restart")]
    ]
    if hasattr(update_or_callback, "message"):
        await update_or_callback.message.reply_text(summary, reply_markup=InlineKeyboardMarkup(buttons))
    else:
        await update_or_callback.callback_query.edit_message_text(summary, reply_markup=InlineKeyboardMarkup(buttons))
        await update_or_callback.callback_query.answer()
    return CONFIRM

async def confirm(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.answer()
    sheet.append_row([
        str(update.effective_user.id),
        update.effective_user.username,
        context.user_data.get("source", "unknown"),
        datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        context.user_data["name"],
        context.user_data["age"],
        context.user_data["arrest"],
        context.user_data["overdue"],
        context.user_data["amount"]
    ])
    await update.callback_query.edit_message_text("✅ Заявка отправлена! Наш менеджер скоро свяжется с вами.")
    return ConversationHandler.END

async def edit(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.answer()
    await update.callback_query.edit_message_text("✏️ Давайте изменим вашу заявку. Введите ФИО заново:")
    return ASK_NAME

async def restart(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.answer()
    await update.callback_query.edit_message_text("🔁 Перезапуск бота...
Введите /start для начала.")
    return ConversationHandler.END

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("❌ Операция отменена. Введите /start для новой заявки.")
    return ConversationHandler.END

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("ℹ️ Чтобы начать оформление заявки, введите /start.
Если у вас есть вопрос — напишите, я помогу!")

async def gpt_reply(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        user_question = update.message.text
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": user_question}]
        )
        await update.message.reply_text(response["choices"][0]["message"]["content"])
    except Exception as e:
        logging.error(traceback.format_exc())
        await update.message.reply_text("🤖 Произошла ошибка при обращении к GPT. Попробуйте позже.")

def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            ASK_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_name)],
            ASK_AGE: [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_age)],
            ASK_ARREST: [CallbackQueryHandler(ask_arrest, pattern="^арест_")],
            ASK_OVERDUE: [CallbackQueryHandler(ask_overdue, pattern="^просрочка_")],
            ASK_AMOUNT: [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_amount)],
            CONFIRM: [
                CallbackQueryHandler(confirm, pattern="^confirm$"),
                CallbackQueryHandler(edit, pattern="^edit$"),
                CallbackQueryHandler(restart, pattern="^restart$")
            ],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )

    app.add_handler(conv_handler)
    app.add_handler(CommandHandler("restart", restart))
    app.add_handler(CommandHandler("cancel", cancel))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, gpt_reply))

    app.run_polling()

if __name__ == "__main__":
    main()

