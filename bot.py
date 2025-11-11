#!/usr/bin/env python3
"""
Telegram бот для записи на массаж в салон красоты "Баланс"
"""

import logging
import asyncio
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ConversationHandler,
    filters,
)

import config
from database.database import init_db, async_session
from database.models import Employee, User
from handlers.client import ClientHandlers, SELECTING_SERVICE, SELECTING_DATE, SELECTING_TIME, CONFIRMING_BOOKING
from handlers.employee import EmployeeHandlers
from handlers.admin import AdminHandlers, EDITING_EMPLOYEE, EDITING_SERVICE
from utils.scheduler import NotificationScheduler
from utils.helpers import get_user_role
from sqlalchemy import select

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)


class MassageBookingBot:
    """Главный класс бота"""

    def __init__(self):
        self.application = None
        self.scheduler = None
        self.client_handlers = None
        self.employee_handlers = None
        self.admin_handlers = None

    async def post_init(self, application: Application):
        """Инициализация после создания приложения"""
        # Инициализация базы данных
        await init_db()
        logger.info("Database initialized")

        # Создание сотрудника Наталья, если её ещё нет
        await self.create_initial_employee()

        # Запуск планировщика уведомлений
        self.scheduler = NotificationScheduler(application.bot)
        self.scheduler.start()
        logger.info("Notification scheduler started")

    async def create_initial_employee(self):
        """Создание начального сотрудника"""
        async with async_session() as session:
            # Проверяем, есть ли уже сотрудники
            result = await session.execute(select(Employee))
            if result.scalars().first():
                return  # Сотрудник уже есть

            # Проверяем, есть ли пользователь с первым employee_id
            if config.EMPLOYEE_IDS:
                employee_telegram_id = config.EMPLOYEE_IDS[0]

                result = await session.execute(
                    select(User).where(User.telegram_id == employee_telegram_id)
                )
                user = result.scalars().first()

                user_id = user.id if user else None

                # Создаём сотрудника Наталья
                employee = Employee(
                    user_id=user_id,
                    name='Наталья',
                    description='Опытный мастер массажа',
                    is_active=True
                )
                session.add(employee)
                await session.commit()
                logger.info("Initial employee 'Наталья' created")

    async def get_user_role_handler(self, telegram_id: int) -> str:
        """Определение роли пользователя"""
        async with async_session() as session:
            return await get_user_role(telegram_id, session)

    async def route_start_command(self, update: Update, context):
        """Маршрутизация команды /start в зависимости от роли"""
        user_id = update.effective_user.id
        role = await self.get_user_role_handler(user_id)

        if role == config.ROLE_ADMIN:
            await self.admin_handlers.start(update, context)
        elif role == config.ROLE_EMPLOYEE:
            await self.employee_handlers.start(update, context)
        else:
            await self.client_handlers.start(update, context)

    async def route_message(self, update: Update, context):
        """Маршрутизация текстовых сообщений"""
        user_id = update.effective_user.id
        role = await self.get_user_role_handler(user_id)
        text = update.message.text

        # Общие для всех
        if text == "ℹ️ О салоне" or text == "ℹ️ Информация о салоне":
            if role == config.ROLE_ADMIN:
                await self.admin_handlers.show_salon_info(update, context)
            elif role == config.ROLE_EMPLOYEE:
                await self.employee_handlers.show_salon_info(update, context)
            else:
                await self.client_handlers.show_salon_info(update, context)
            return

        # Клиент
        if role == config.ROLE_CLIENT:
            if text == "📋 Наши услуги":
                await self.client_handlers.show_services(update, context)
            elif text == "📅 Записаться на процедуру":
                await self.client_handlers.show_services(update, context)
            elif text == "📝 Мои записи":
                await self.client_handlers.show_my_appointments(update, context)
            elif text == "📞 Контакты":
                await self.client_handlers.show_contacts(update, context)

        # Сотрудник
        elif role == config.ROLE_EMPLOYEE:
            if text == "📅 Мои записи на сегодня":
                await self.employee_handlers.show_today_appointments(update, context)
            elif text == "📆 Расписание на неделю":
                await self.employee_handlers.show_week_schedule(update, context)
            elif text == "✅ Отметить выполнение":
                await self.employee_handlers.show_appointments_for_completion(update, context)

        # Администратор
        elif role == config.ROLE_ADMIN:
            if text == "👥 Управление сотрудниками":
                await self.admin_handlers.show_employees_menu(update, context)
            elif text == "💆 Управление услугами":
                await self.admin_handlers.show_services_menu(update, context)
            elif text == "📊 Статистика":
                await self.admin_handlers.show_statistics_menu(update, context)
            elif text == "📅 Все записи":
                await self.admin_handlers.show_appointments_filter(update, context)

    async def route_callback(self, update: Update, context):
        """Маршрутизация callback запросов"""
        query = update.callback_query
        data = query.data
        user_id = update.effective_user.id
        role = await self.get_user_role_handler(user_id)

        # Клиент (обработка НЕ-ConversationHandler callbacks)
        if role == config.ROLE_CLIENT:
            if data.startswith("category_"):
                await self.client_handlers.show_category_services(update, context)
            elif data.startswith("service_") and not data.startswith("service_actions"):
                await self.client_handlers.show_service_detail(update, context)
            elif data.startswith("appointment_") and not data.startswith("cancel_appointment_"):
                await self.client_handlers.show_appointment_detail(update, context)
            elif data.startswith("cancel_appointment_"):
                await self.client_handlers.cancel_appointment(update, context)
            # Обработка кнопок "Назад"
            elif data.startswith("back_"):
                await self.client_handlers.handle_back_button(update, context)
            # book_, date_, time_, confirm_booking, cancel_booking обрабатываются ConversationHandler

        # Сотрудник
        elif role == config.ROLE_EMPLOYEE:
            if data.startswith("emp_date_"):
                await self.employee_handlers.show_date_schedule(update, context)
            elif data.startswith("emp_appointment_"):
                await self.employee_handlers.show_appointment_detail(update, context)
            elif data.startswith("emp_complete_"):
                await self.employee_handlers.complete_appointment(update, context)
            elif data.startswith("emp_cancel_"):
                await self.employee_handlers.cancel_appointment(update, context)
            elif data.startswith("emp_mark_complete_"):
                await self.employee_handlers.mark_complete(update, context)

        # Администратор
        elif role == config.ROLE_ADMIN:
            if data == "admin_list_employees":
                await self.admin_handlers.show_employees_list(update, context)
            elif data.startswith("admin_edit_employee_"):
                await self.admin_handlers.start_edit_employee(update, context)
            elif data.startswith("admin_employee_") and "toggle" not in data and "edit" not in data:
                await self.admin_handlers.show_employee_detail(update, context)
            elif data.startswith("admin_toggle_employee_"):
                await self.admin_handlers.toggle_employee_status(update, context)
            elif data == "admin_list_services":
                await self.admin_handlers.show_services_list(update, context)
            elif data.startswith("admin_edit_service_"):
                await self.admin_handlers.start_edit_service(update, context)
            elif data.startswith("admin_service_") and "toggle" not in data and "edit" not in data:
                await self.admin_handlers.show_service_detail(update, context)
            elif data.startswith("admin_toggle_service_"):
                await self.admin_handlers.toggle_service_status(update, context)
            elif data.startswith("admin_stats_"):
                await self.admin_handlers.show_statistics(update, context)
            elif data.startswith("admin_appointments_"):
                if data in ["admin_appointments_today", "admin_appointments_week", "admin_appointments_all"]:
                    await self.admin_handlers.show_filtered_appointments(update, context)
                else:
                    await self.admin_handlers.show_appointment_detail(update, context)
            elif data.startswith("admin_cancel_appointment_"):
                await self.admin_handlers.cancel_appointment(update, context)
            # Обработка кнопок "Назад"
            elif data.startswith("admin_") and ("back" in data or data in ["admin_employees_menu", "admin_services_menu", "admin_list_employees", "admin_list_services", "admin_appointments_filter"]):
                await self.admin_handlers.handle_back_button(update, context)

    def run(self):
        """Запуск бота"""
        # Создание приложения
        self.application = Application.builder().token(config.BOT_TOKEN).post_init(self.post_init).build()

        # Инициализация обработчиков
        self.client_handlers = ClientHandlers(None)  # scheduler будет установлен позже
        self.employee_handlers = EmployeeHandlers()
        self.admin_handlers = AdminHandlers()

        # Устанавливаем scheduler в client_handlers после инициализации
        async def set_scheduler():
            self.client_handlers.scheduler = self.scheduler

        self.application.job_queue.run_once(lambda _: asyncio.create_task(set_scheduler()), 1)

        # Регистрация обработчиков
        self.application.add_handler(CommandHandler("start", self.route_start_command))
        self.application.add_handler(MessageHandler(filters.CONTACT, self.client_handlers.handle_contact))

        # ConversationHandler для процесса бронирования клиентов
        booking_handler = ConversationHandler(
            entry_points=[
                CallbackQueryHandler(self.client_handlers.start_booking, pattern="^book_"),
            ],
            states={
                SELECTING_DATE: [
                    CallbackQueryHandler(self.client_handlers.select_date, pattern="^date_"),
                    CallbackQueryHandler(self.client_handlers.cancel_booking, pattern="^cancel_booking$"),
                ],
                SELECTING_TIME: [
                    CallbackQueryHandler(self.client_handlers.select_time, pattern="^time_"),
                    CallbackQueryHandler(self.client_handlers.cancel_booking, pattern="^cancel_booking$"),
                ],
                CONFIRMING_BOOKING: [
                    CallbackQueryHandler(self.client_handlers.confirm_booking, pattern="^confirm_booking$"),
                    CallbackQueryHandler(self.client_handlers.cancel_booking, pattern="^cancel_booking$"),
                ],
            },
            fallbacks=[
                CallbackQueryHandler(self.client_handlers.cancel_booking, pattern="^cancel_booking$"),
            ],
        )

        # ConversationHandler для редактирования сотрудников
        edit_employee_handler = ConversationHandler(
            entry_points=[CallbackQueryHandler(
                self.admin_handlers.start_edit_employee,
                pattern="^admin_edit_employee_"
            )],
            states={
                EDITING_EMPLOYEE: [
                    MessageHandler(filters.PHOTO, self.admin_handlers.process_employee_edit),
                    MessageHandler(filters.TEXT & ~filters.COMMAND, self.admin_handlers.process_employee_edit),
                    CommandHandler("done", self.admin_handlers.process_employee_edit),
                    CommandHandler("cancel", self.admin_handlers.process_employee_edit),
                ]
            },
            fallbacks=[CommandHandler("cancel", self.admin_handlers.process_employee_edit)],
        )

        # ConversationHandler для редактирования услуг
        edit_service_handler = ConversationHandler(
            entry_points=[CallbackQueryHandler(
                self.admin_handlers.start_edit_service,
                pattern="^admin_edit_service_"
            )],
            states={
                EDITING_SERVICE: [
                    MessageHandler(filters.TEXT & ~filters.COMMAND, self.admin_handlers.process_service_edit),
                    CommandHandler("done", self.admin_handlers.process_service_edit),
                    CommandHandler("cancel", self.admin_handlers.process_service_edit),
                ]
            },
            fallbacks=[CommandHandler("cancel", self.admin_handlers.process_service_edit)],
        )

        self.application.add_handler(booking_handler)
        self.application.add_handler(edit_employee_handler)
        self.application.add_handler(edit_service_handler)
        self.application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.route_message))
        self.application.add_handler(CallbackQueryHandler(self.route_callback))

        # Запуск бота
        logger.info("Bot started")
        self.application.run_polling(allowed_updates=Update.ALL_TYPES)


def main():
    """Главная функция"""
    if not config.BOT_TOKEN:
        logger.error("BOT_TOKEN is not set. Please check your .env file")
        return

    bot = MassageBookingBot()
    bot.run()


if __name__ == '__main__':
    main()
