import os
import logging
from openai import OpenAI
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, BotCommand
from telegram.ext import (
    ApplicationBuilder, ContextTypes, CommandHandler,
    MessageHandler, CallbackQueryHandler, ConversationHandler, filters
)
from datetime import datetime
import gspread
from oauth2client.service_account import ServiceAccountCredentials

logging.basicConfig(level=logging.INFO)

BOT_TOKEN = os.getenv("BOT_TOKEN")
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

def init_sheet():
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    creds = ServiceAccountCredentials.from_json_keyfile_name("credentials.json", scope)
    client_gs = gspread.authorize(creds)
    return client_gs.open_by_url("https://docs.google.com/spreadsheets/d/15-xtnsn6VDq0O4QHPCWnIMpTqc_7zNQCrk6M47e2u3M/edit").sheet1

sheet = init_sheet()

ASK_NAME, ASK_AGE, ASK_ARREST, ASK_OVERDUE, ASK_AMOUNT, CONFIRM = range(6)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["source"] = update.message.text.split(" ")[1] if len(update.message.text.split(" ")) > 1 else "direct"
    await update.message.reply_text("👋 Привет! Я помогу вам подать заявку на кредит.\n\nВведите ваше ФИО:")
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
    summary = f"""📋 Ваша заявка:\n\nФИО: {context.user_data['name']}\nВозраст: {context.user_data['age']}\nАресты: {context.user_data['arrest']}\nПросрочки: {context.user_data['overdue']}\nСумма: {context.user_data['amount']}"""
    buttons = [
        [InlineKeyboardButton("✅ Отправить", callback_data="confirm")],
        [InlineKeyboardButton("✏️ Редактировать заявку", callback_data="edit")],
        [InlineKeyboardButton("💬 Связаться с менеджером", callback_data="ask")],
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
    await update.callback_query.edit_message_text("✅ Заявка отправлена! Наш менеджер скоро свяжется с вами.\n\nЕсли у вас есть вопросы, нажмите кнопку ниже.")
    return ConversationHandler.END

async def edit(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.answer()
    await update.callback_query.edit_message_text("✏️ Давайте изменим вашу заявку. Введите ФИО заново:")
    return ASK_NAME

async def restart(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.answer()
    await update.callback_query.edit_message_text("🔁 Перезапуск бота...\nВведите /start для начала.")
    return ConversationHandler.END

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("❌ Операция отменена. Введите /start для новой заявки.")
    return ConversationHandler.END

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("ℹ️ Чтобы начать оформление заявки, введите /start.\nЕсли у вас есть вопрос — используйте кнопку в анкете.")

async def ask_gpt(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.answer()
    await update.callback_query.message.reply_text("💬 Задайте ваш вопрос, я отвечу как менеджер банка.")

async def gpt_reply(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        user_question = update.message.text
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "Ты вежливый и понятный менеджер банка, который консультирует клиента по вопросам кредитования физических лиц."},
                {"role": "user", "content": user_question}
            ]
        )
        await update.message.reply_text(response.choices[0].message.content)
    except Exception as e:
        logging.error(f"GPT ERROR: {e}")
        await update.message.reply_text("❌ GPT API не отвечает. Проверь ключ или повтори позже.")

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
                CallbackQueryHandler(restart, pattern="^restart$"),
                CallbackQueryHandler(ask_gpt, pattern="^ask$")
            ],
        },
        fallbacks=[CommandHandler("cancel", cancel)]
    )

    app.add_handler(conv_handler)
    app.add_handler(CommandHandler("restart", restart))
    app.add_handler(CommandHandler("cancel", cancel))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, gpt_reply))

    async def startup(application):
        await application.bot.set_my_commands([
            BotCommand("start", "Начать оформление заявки"),
            BotCommand("help", "Помощь и частые вопросы"),
            BotCommand("cancel", "Отменить заявку"),
            BotCommand("restart", "Перезапустить бота")
        ])

    app.post_init = startup
    app.run_polling()

if __name__ == "__main__":
    main()







