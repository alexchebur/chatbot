# telegram_bot.py

import logging
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    filters,
    ContextTypes,
    ConversationHandler,
)
from ocr_handler import process_images
from summary_handler import generate_summary
from evaluation_handler import evaluate_document

# Настройка логов
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Состояния диалога
PHOTO, SUMMARY = range(2)

# Конфигурация
TELEGRAM_BOT_TOKEN = "ВАШ_ТОКЕН"

# Клавиатура
reply_keyboard = [
    ["📷 Распознать фото", "📄 Создать саммари"],
    ["⚖️ Оценить текст", "❓ Помощь"]
]
markup = ReplyKeyboardMarkup(reply_keyboard, resize_keyboard=True)

# Стартовая команда
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Выберите действие:", reply_markup=markup)
    return PHOTO  # Переход в состояние ожидания фото

# Обработка фотографии
async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        # Получаем фото
        photo_file = await update.message.photo[-1].get_file()
        image_data = await photo_file.download_as_bytearray()
        
        # Вызываем OCR
        text = process_images([image_data])  
        context.user_data["ocr_text"] = text
        
        await update.message.reply_text(
            f"✅ Распознанный текст:\n\n{text}\n\nВыберите действие:",
            reply_markup=markup
        )
        return SUMMARY  # Переход в состояние работы с текстом
        
    except Exception as e:
        logger.error(f"Ошибка OCR: {e}")
        await update.message.reply_text("❌ Ошибка распознавания")
        return ConversationHandler.END

# Создание саммари
async def create_summary(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if "ocr_text" not in context.user_data:
        await update.message.reply_text("⚠️ Сначала отправьте фото!")
        return PHOTO
        
    text = context.user_data["ocr_text"]
    summary = generate_summary(text)  # Вызов саммаризации
    context.user_data["summary"] = summary
    
    await update.message.reply_text(
        f"📝 Саммари:\n\n{summary}\n\nВыберите действие:", 
        reply_markup=markup
    )
    return SUMMARY

# Юридическая оценка
async def evaluate_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if "summary" not in context.user_data:
        await update.message.reply_text("⚠️ Сначала создайте саммари!")
        return SUMMARY
        
    evaluation = evaluate_document(
        context.user_data["ocr_text"],
        context.user_data["summary"]
    )
    await update.message.reply_text(
        f"⚖️ Правовая оценка:\n\n{evaluation}", 
        reply_markup=markup
    )
    return ConversationHandler.END

# Помощь
async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    help_text = """
📷 Распознать фото - отправьте изображение документа
📄 Создать саммари - сгенерировать краткое содержание
⚖️ Оценить текст - юридический анализ документа
"""
    await update.message.reply_text(help_text, reply_markup=markup)
    return PHOTO  # Возврат в начальное состояние

def main():
    application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
    
    # Настройка ConversationHandler
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            PHOTO: [
                MessageHandler(filters.PHOTO, handle_photo),
                MessageHandler(filters.Regex(r"^❓ Помощь$"), help_command),
                MessageHandler(filters.Regex(r"^📄 Создать саммари$"), 
                    lambda u, c: u.message.reply_text("⚠️ Сначала отправьте фото!")),
                MessageHandler(filters.Regex(r"^⚖️ Оценить текст$"), 
                    lambda u, c: u.message.reply_text("⚠️ Сначала создайте саммари!"))
            ],
            SUMMARY: [
                MessageHandler(filters.Regex(r"^📄 Создать саммари$"), create_summary),
                MessageHandler(filters.Regex(r"^⚖️ Оценить текст$"), evaluate_text),
                MessageHandler(filters.Regex(r"^❓ Помощь$"), help_command),
                MessageHandler(filters.PHOTO, handle_photo)
            ]
        },
        fallbacks=[CommandHandler("help", help_command)]
    )
    
    application.add_handler(conv_handler)
    application.run_polling()

if __name__ == "__main__":
    main()
