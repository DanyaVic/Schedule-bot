# Основной файл Telegram бота расписания

import logging
from datetime import datetime, timedelta
from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    filters,
    ContextTypes,
    ConversationHandler,
    CallbackQueryHandler,
    CallbackContext
)

from config import (
    TELEGRAM_BOT_TOKEN, DAYS_RU, DAYS_SHORT, SCHEDULE_FILE,
    WELCOME_MESSAGE, HELP_MESSAGE, ERROR_NO_SCHEDULE, ERROR_GROUP_NOT_FOUND,
    AVAILABLE_TIMES
)
from schedule_parser import ScheduleParser
from user_database import UserDatabase

# Логирование
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Инициализация
db = UserDatabase()
parser = ScheduleParser(SCHEDULE_FILE)

# Состояния для ConversationHandler
CHOOSING_GROUP = 1
CHOOSING_ACTION = 2
CHOOSING_NOTIFICATION_TIME = 3
CHOOSING_DAY = 4



def get_groups_keyboard():
    """Создает клавиатуру со всеми группами"""
    groups = parser.get_groups()
    if not groups:
        return None

    # Разбиваем группы на ряды по 2 кнопки
    keyboard = []
    for i in range(0, len(groups), 2):
        row = [groups[i]]
        if i + 1 < len(groups):
            row.append(groups[i + 1])
        keyboard.append(row)

    return ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True)


def get_time_keyboard():
    """Создает клавиатуру с временем"""
    keyboard = []
    for i in range(0, len(AVAILABLE_TIMES), 3):
        row = AVAILABLE_TIMES[i:i + 3]
        keyboard.append(row)
    keyboard.append(['Отмена'])
    return ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True)


def get_days_keyboard():
    """Создает клавиатуру со всеми днями недели"""
    keyboard = [
        ['пн', 'вт', 'ср'],
        ['чт', 'пт', 'сб'],
        ['вс', 'Отмена']
    ]
    return ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True)


def get_action_keyboard():
    """Создает клавиатуру с основными действиями"""
    keyboard = [
        ['📅 Сегодня', '📅 Завтра'],
        ['📅 Неделя', '🔍 День'],
        ['⏰ Время уведомлений', '✏️ Изменить группу'],
        ['❌ Выход']
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)


# ОБРАБОТЧИКИ КОМАНД

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /start"""
    user_id = update.effective_user.id

    # Проверяем, зарегистрирован ли пользователь
    if db.user_exists(user_id):
        current_group = db.get_user_group(user_id)
        await update.message.reply_text(
            f"👋 Добро пожаловать назад!\n\n"
            f"Ваша группа: {current_group}\n\n"
            f"Выберите действие:",
            reply_markup=get_action_keyboard()
        )
        return CHOOSING_ACTION

    # Новый пользователь
    await update.message.reply_text(
        WELCOME_MESSAGE,
        reply_markup=get_groups_keyboard()
    )
    return CHOOSING_GROUP


async def set_notification_time(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Позволяет установить время отправки расписания"""
    user_id = update.effective_user.id
    group = db.get_user_group(user_id)

    if not group:
        await update.message.reply_text("❌ Сначала выберите группу: /start")
        return CHOOSING_ACTION

    current_time = db.get_notification_time(user_id)
    await update.message.reply_text(
        f"⏰ Текущее время отправки: {current_time}\n\n"
        f"Выберите новое время:",
        reply_markup=get_time_keyboard()
    )
    return CHOOSING_NOTIFICATION_TIME


async def handle_time_selection(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик выбора времени"""
    user_id = update.effective_user.id
    time_str = update.message.text.strip()

    if time_str == 'Отмена':
        await update.message.reply_text(
            "Выберите действие:",
            reply_markup=get_action_keyboard()
        )
        return CHOOSING_ACTION

    # Проверяем, валидно ли время
    if time_str not in AVAILABLE_TIMES:
        await update.message.reply_text(
            f"❌ Неверный формат времени. Выберите из предложенных:",
            reply_markup=get_time_keyboard()
        )
        return CHOOSING_NOTIFICATION_TIME

    # Сохраняем время
    if db.set_notification_time(user_id, time_str):
        await update.message.reply_text(
            f"✅ Расписание будет отправляться в {time_str}\n\n"
            f"Выберите действие:",
            reply_markup=get_action_keyboard()
        )
    else:
        await update.message.reply_text(
            f"❌ Ошибка при сохранении времени. Попытайтесь еще раз:",
            reply_markup=get_time_keyboard()
        )
        return CHOOSING_NOTIFICATION_TIME

    return CHOOSING_ACTION


async def choose_group(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик выбора группы"""
    user_id = update.effective_user.id
    group = update.message.text.strip()

    # Проверяем, существует ли такая группа
    if group not in parser.get_groups():
        await update.message.reply_text(
            f"{ERROR_GROUP_NOT_FOUND}\n\nПопытайтесь еще раз:",
            reply_markup=get_groups_keyboard()
        )
        return CHOOSING_GROUP

    # Сохраняем группу пользователя
    db.add_user(user_id, group)

    await update.message.reply_text(
        f"✅ Спасибо! Вы выбрали группу: {group}\n\n"
        f"Теперь выберите действие:",
        reply_markup=get_action_keyboard()
    )

    return CHOOSING_ACTION


async def show_today_schedule(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показывает расписание на сегодня"""
    user_id = update.effective_user.id
    group = db.get_user_group(user_id)

    if not group:
        await update.message.reply_text("❌ Сначала выберите группу: /start")
        return

    today = datetime.now().weekday()
    if today > 6:
        await update.message.reply_text(ERROR_NO_SCHEDULE)
        return

    day_name = DAYS_RU[today]
    schedule_text = parser.format_day_schedule(group, day_name)

    await update.message.reply_text(
        schedule_text,
        reply_markup=get_action_keyboard()
    )


async def show_tomorrow_schedule(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показывает расписание на завтра"""
    user_id = update.effective_user.id
    group = db.get_user_group(user_id)

    if not group:
        await update.message.reply_text("❌ Сначала выберите группу: /start")
        return

    tomorrow = (datetime.now() + timedelta(days=1)).weekday()
    if tomorrow > 6:
        await update.message.reply_text(ERROR_NO_SCHEDULE)
        return

    day_name = DAYS_RU[tomorrow]
    schedule_text = parser.format_day_schedule(group, day_name)

    await update.message.reply_text(
        schedule_text,
        reply_markup=get_action_keyboard()
    )


async def show_week_schedule(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показывает расписание на неделю"""
    user_id = update.effective_user.id
    group = db.get_user_group(user_id)

    if not group:
        await update.message.reply_text("❌ Сначала выберите группу: /start")
        return

    schedule_text = parser.get_schedule_for_week(group)

    # Telegram ограничивает длину сообщения до 4096 символов
    # Разбиваем расписание по дням
    messages = schedule_text.split('\n\n')
    full_messages = []
    current_msg = ""

    for msg in messages:
        if len(current_msg) + len(msg) < 3000:
            current_msg += msg + "\n\n"
        else:
            if current_msg:
                full_messages.append(current_msg)
            current_msg = msg + "\n\n"

    if current_msg:
        full_messages.append(current_msg)

    for msg in full_messages:
        await update.message.reply_text(msg)

    await update.message.reply_text(
        "Выберите действие:",
        reply_markup=get_action_keyboard()
    )


async def choose_day(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Запрашивает выбор дня недели"""
    await update.message.reply_text(
        "📅 Выберите день недели:",
        reply_markup=get_days_keyboard()
    )
    return CHOOSING_DAY


async def show_day_schedule(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показывает расписание для выбранного дня"""
    user_id = update.effective_user.id
    group = db.get_user_group(user_id)

    if not group:
        await update.message.reply_text("❌ Сначала выберите группу: /start")
        return CHOOSING_ACTION

    day_input = update.message.text.strip().lower()

    if day_input == "отмена":
        await update.message.reply_text(
            "Выберите действие:",
            reply_markup=get_action_keyboard()
        )
        return CHOOSING_ACTION

    # Преобразуем сокращение дня в полное название
    day_name = None
    for i, short in enumerate(DAYS_SHORT):
        if day_input == short:
            day_name = DAYS_RU[i]
            break

    if not day_name:
        await update.message.reply_text(
            "❌ Неизвестный день. Выберите из предложенных:",
            reply_markup=get_days_keyboard()
        )
        return CHOOSING_DAY

    schedule_text = parser.format_day_schedule(group, day_name)

    await update.message.reply_text(
        schedule_text,
        reply_markup=get_action_keyboard()
    )
    return CHOOSING_ACTION


async def change_group(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Позволяет изменить группу"""
    await update.message.reply_text(
        "Выберите новую группу:",
        reply_markup=get_groups_keyboard()
    )
    return CHOOSING_GROUP


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /help"""
    await update.message.reply_text(HELP_MESSAGE)


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик выхода"""
    await update.message.reply_text(
        "👋 До свидания! Используйте /start для перезагрузки.",
        reply_markup=ReplyKeyboardRemove()
    )
    return ConversationHandler.END


async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик текстовых сообщений"""
    text = update.message.text.strip()

    if text == "📅 Сегодня":
        await show_today_schedule(update, context)
    elif text == "📅 Завтра":
        await show_tomorrow_schedule(update, context)
    elif text == "📅 Неделя":
        await show_week_schedule(update, context)
    elif text == "🔍 День":
        return await choose_day(update, context)
    elif text == "⏰ Время уведомлений":
        return await set_notification_time(update, context)
    elif text == "✏️ Изменить группу":
        return await change_group(update, context)
    elif text == "❌ Выход":
        return await cancel(update, context)
    else:
        await update.message.reply_text(
            "❌ Неизвестная команда. Используйте /help для справки.",
            reply_markup=get_action_keyboard()
        )


# ============= ИНИЦИАЛИЗАЦИЯ БОТА =============

async def post_init(app: Application):
    """Инициализация после запуска"""
    logger.info("🤖 Бот запущен!")

    # Парсим расписание при запуске
    if parser.parse():
        logger.info(f"✅ Расписание загружено. Групп: {len(parser.get_groups())}")
    else:
        logger.error("❌ Не удалось загрузить расписание!")

    # Добавляем планировщик уведомлений
    app.job_queue.run_repeating(
        send_scheduled_notifications,
        interval=60,  # каждые 60 секунд
        first=0,
        name='send_daily_schedule'
    )
    logger.info("✅ Планировщик уведомлений запущен")


async def send_scheduled_notifications(context: ContextTypes.DEFAULT_TYPE):
    """Отправляет расписание на день всем пользователям в нужное время"""
    current_time = datetime.now().strftime('%H:%M')

    # Получаем пользователей, у которых сейчас время уведомлений
    users = db.get_users_by_notification_time(current_time)

    if not users:
        return

    today = datetime.now().weekday()

    # Не отправляем в выходные (сб=5, вс=6)
    if today > 4:
        logger.info("📭 Выходной день - расписание не отправляем")
        return

    day_name = DAYS_RU[today]

    for user_id, group in users.items():
        try:
            schedule_text = parser.format_day_schedule(group, day_name)
            await context.bot.send_message(
                chat_id=user_id,
                text=f"📅 Расписание на {day_name}:\n\n{schedule_text}"
            )
            logger.info(f"✅ Расписание отправлено {user_id}")
        except Exception as e:
            logger.error(f"❌ Ошибка при отправке {user_id}: {str(e)}")


def main():
    """Главная функция запуска бота"""
    # Создаем приложение
    app = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

    # Добавляем обработчик инициализации
    app.post_init = post_init

    # ConversationHandler для основного потока
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            CHOOSING_GROUP: [MessageHandler(filters.TEXT & ~filters.COMMAND, choose_group)],
            CHOOSING_ACTION: [
                MessageHandler(filters.Regex(
                    r'^(📅 Сегодня|📅 Завтра|📅 Неделя|🔍 День|⏰ Время уведомлений|✏️ Изменить группу|❌ Выход)$'),
                    handle_text),
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text)
            ],
            CHOOSING_DAY: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, show_day_schedule),
            ],
            CHOOSING_NOTIFICATION_TIME: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_time_selection),
            ],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )

    # Добавляем обработчики
    app.add_handler(conv_handler)
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("today", show_today_schedule))
    app.add_handler(CommandHandler("tomorrow", show_tomorrow_schedule))
    app.add_handler(CommandHandler("week", show_week_schedule))

    # Запускаем бота
    logger.info("🚀 Запуск бота...")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()