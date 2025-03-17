# telegram_bot.py

import random
import aiohttp
import nest_asyncio
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import (
    Application,
    MessageHandler,
    CommandHandler,
    filters,
    ContextTypes,
    ConversationHandler,
)
from ocr_handler import process_images
from summary_handler import generate_summary
from evaluation_handler import evaluate_document

nest_asyncio.apply()

# Состояния разговора
PHOTO, SUMMARY = range(2)

# Конфигурация
TELEGRAM_BOT_TOKEN = '7734922120:AAFT2qyYyjpCUUNna0EILRYET9a1ZmEcozI'
VSEGPT_API_KEY = 'sk-or-vv-a8d6e009e2bbe09474b0679fbba83b015ff1c4f255ed76f33b48ccb1632bdc32'
VSEGPT_API_URL = 'https://api.vsegpt.ru/v1/chat/completions'
MODEL_ID = 'anthropic/claude-3-haiku'

# Клавиатура с основными кнопками
reply_keyboard = [
    ["📷 Распознать фото", "📄 Создать саммари"],
    ["⚖️ Оценить текст", "❓ Помощь"]
]
markup = ReplyKeyboardMarkup(reply_keyboard, resize_keyboard=True)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Выберите действие:",
        reply_markup=markup
    )

async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    photo_file = await update.message.photo[-1].get_file()
    image_data = await photo_file.download_as_bytearray()
    
    try:
        # Сохраняем изображение во временное хранилище
        context.user_data['image'] = image_data
        # Вызываем OCR обработчик
        text = process_images([image_data])
        context.user_data['ocr_text'] = text
        await update.message.reply_text(
            f"Текст распознан:\n\n{text}\n\nВыберите следующее действие",
            reply_markup=markup
        )
        return SUMMARY
    except Exception as e:
        await update.message.reply_text(f"Ошибка распознавания: {str(e)}")
        return ConversationHandler.END

async def create_summary(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if 'ocr_text' not in context.user_data:
        await update.message.reply_text("Сначала отправьте фото для распознавания")
        return
    
    text = context.user_data['ocr_text']
    summary = generate_summary(text)
    context.user_data['summary'] = summary
    
    await update.message.reply_text(
        f"Саммари документа:\n\n{summary}\n\nВыберите действие:",
        reply_markup=markup
    )

async def evaluate_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if 'ocr_text' not in context.user_data:
        await update.message.reply_text("Сначала отправьте фото для распознавания")
        return
    if 'summary' not in context.user_data:
        await update.message.reply_text("Сначала создайте саммари")
        return
    
    evaluation = evaluate_document(
        context.user_data['ocr_text'],
        context.user_data['summary']
    )
    await update.message.reply_text(
        f"Правовая оценка:\n\n{evaluation}",
        reply_markup=markup
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    help_text = """
📷 Распознать фото - отправьте фото документа для распознавания текста
📄 Создать саммари - создайте краткое содержание распознанного текста
⚖️ Оценить текст - получите юридическую оценку документа
"""
    await update.message.reply_text(help_text, reply_markup=markup)

def main():
    application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

    conv_handler = ConversationHandler(
        entry_points=[
            CommandHandler('start', start),
            MessageHandler(filters.TEXT & ~filters.COMMAND, start)
        ],
        states={
            PHOTO: [MessageHandler(filters.PHOTO, handle_photo)],
            SUMMARY: [
                MessageHandler(filters.Regex("^📄 Создать саммари$"), create_summary),
                MessageHandler(filters.Regex("^⚖️ Оценить текст$"), evaluate_text)
            ]
        },
        fallbacks=[CommandHandler('help', help_command)]
    )

    application.add_handler(conv_handler)
    application.add_handler(MessageHandler(filters.Regex("^❓ Помощь$"), help_command))
    application.add_handler(MessageHandler(filters.Regex("^📷 Распознать фото$"), lambda u,c: None))
    application.run_polling()

if __name__ == '__main__':
    main()
