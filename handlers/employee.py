from datetime import datetime, timedelta
from telegram import Update
from telegram.ext import ContextTypes
from sqlalchemy import select, and_
from database.models import User, Service, Appointment, Employee
from database.database import async_session
from keyboards.employee import EmployeeKeyboards
from utils.helpers import format_appointment_info
import config


class EmployeeHandlers:
    """Обработчики для сотрудников"""

    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик команды /start для сотрудника"""
        welcome_message = (
            f"Добро пожаловать в рабочий кабинет салона «{config.SALON_INFO['name']}»! 👋\n\n"
            "Здесь вы можете:\n"
            "• Просматривать свои записи\n"
            "• Управлять расписанием\n"
            "• Отмечать выполненные процедуры"
        )

        await update.message.reply_text(
            welcome_message,
            reply_markup=EmployeeKeyboards.main_menu()
        )

    async def show_today_appointments(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Показать записи на сегодня"""
        user_id = update.effective_user.id

        async with async_session() as session:
            # Получаем сотрудника
            result = await session.execute(
                select(Employee).join(User).where(User.telegram_id == user_id)
            )
            employee = result.scalars().first()

            if not employee:
                await update.message.reply_text("Ошибка: сотрудник не найден.")
                return

            # Получаем записи на сегодня
            today_start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
            today_end = datetime.now().replace(hour=23, minute=59, second=59, microsecond=999999)

            result = await session.execute(
                select(Appointment, Service, User).join(
                    Service, Appointment.service_id == Service.id
                ).join(
                    User, Appointment.user_id == User.id
                ).where(
                    Appointment.employee_id == employee.id,
                    Appointment.appointment_date >= today_start,
                    Appointment.appointment_date <= today_end,
                    Appointment.status == 'scheduled'
                ).order_by(Appointment.appointment_date)
            )
            appointments_data = result.all()

            if not appointments_data:
                await update.message.reply_text(
                    "На сегодня у вас нет записей.",
                    reply_markup=EmployeeKeyboards.main_menu()
                )
                return

            # Формируем сообщение
            message = f"📅 Ваши записи на сегодня ({datetime.now().strftime('%d.%m.%Y')}):\n\n"

            for appointment, service, user in appointments_data:
                time_str = appointment.appointment_date.strftime('%H:%M')
                client_name = f"{user.first_name} {user.last_name or ''}".strip()

                message += (
                    f"⏰ {time_str}\n"
                    f"💆 {service.name}\n"
                    f"👤 Клиент: {client_name}\n"
                    f"📞 Телефон: {user.phone or 'не указан'}\n"
                    f"{'─' * 30}\n\n"
                )

            appointments = [a[0] for a in appointments_data]
            await update.message.reply_text(
                message,
                reply_markup=EmployeeKeyboards.appointment_list(appointments)
            )

    async def show_week_schedule(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Показать расписание на неделю"""
        user_id = update.effective_user.id

        # Генерируем даты на следующие 7 дней
        available_dates = []
        for i in range(7):
            date = datetime.now() + timedelta(days=i)
            if date.weekday() in config.WORK_DAYS:
                available_dates.append(date)

        await update.message.reply_text(
            "Выберите дату для просмотра расписания:",
            reply_markup=EmployeeKeyboards.select_date_for_schedule(available_dates)
        )

    async def show_date_schedule(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Показать расписание на выбранную дату"""
        query = update.callback_query
        await query.answer()

        selected_date_str = query.data.split('_', 2)[2]
        selected_date = datetime.strptime(selected_date_str, '%Y-%m-%d')
        user_id = update.effective_user.id

        async with async_session() as session:
            # Получаем сотрудника
            result = await session.execute(
                select(Employee).join(User).where(User.telegram_id == user_id)
            )
            employee = result.scalars().first()

            if not employee:
                await query.edit_message_text("Ошибка: сотрудник не найден.")
                return

            # Получаем записи на выбранную дату
            day_start = selected_date.replace(hour=0, minute=0, second=0, microsecond=0)
            day_end = selected_date.replace(hour=23, minute=59, second=59, microsecond=999999)

            result = await session.execute(
                select(Appointment, Service, User).join(
                    Service, Appointment.service_id == Service.id
                ).join(
                    User, Appointment.user_id == User.id
                ).where(
                    Appointment.employee_id == employee.id,
                    Appointment.appointment_date >= day_start,
                    Appointment.appointment_date <= day_end,
                    Appointment.status == 'scheduled'
                ).order_by(Appointment.appointment_date)
            )
            appointments_data = result.all()

            if not appointments_data:
                await query.edit_message_text(
                    f"На {selected_date.strftime('%d.%m.%Y')} у вас нет записей."
                )
                return

            # Формируем сообщение
            message = f"📅 Расписание на {selected_date.strftime('%d.%m.%Y')}:\n\n"

            for appointment, service, user in appointments_data:
                time_str = appointment.appointment_date.strftime('%H:%M')
                client_name = f"{user.first_name} {user.last_name or ''}".strip()

                message += (
                    f"⏰ {time_str}\n"
                    f"💆 {service.name}\n"
                    f"👤 {client_name}\n"
                    f"📞 {user.phone or 'не указан'}\n"
                    f"{'─' * 30}\n\n"
                )

            await query.edit_message_text(message)

    async def show_appointment_detail(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Показать детали записи"""
        query = update.callback_query
        await query.answer()

        appointment_id = int(query.data.split('_')[2])

        async with async_session() as session:
            result = await session.execute(
                select(Appointment, Service, Employee, User).join(
                    Service, Appointment.service_id == Service.id
                ).join(
                    Employee, Appointment.employee_id == Employee.id
                ).join(
                    User, Appointment.user_id == User.id
                ).where(Appointment.id == appointment_id)
            )
            row = result.first()

            if not row:
                await query.edit_message_text("Запись не найдена.")
                return

            appointment, service, employee, user = row

            client_name = f"{user.first_name} {user.last_name or ''}".strip()
            date_str = appointment.appointment_date.strftime('%d.%m.%Y в %H:%M')

            info = (
                f"📅 Запись на {date_str}\n\n"
                f"💆 Услуга: {service.name}\n"
                f"💰 Цена: {service.price} ₽\n"
                f"⏱ Длительность: {service.duration} мин\n\n"
                f"👤 Клиент: {client_name}\n"
                f"📞 Телефон: {user.phone or 'не указан'}"
            )

            await query.edit_message_text(
                info,
                reply_markup=EmployeeKeyboards.appointment_actions(appointment_id)
            )

    async def complete_appointment(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Отметить запись как выполненную"""
        query = update.callback_query
        await query.answer()

        appointment_id = int(query.data.split('_')[2])

        async with async_session() as session:
            result = await session.execute(
                select(Appointment).where(Appointment.id == appointment_id)
            )
            appointment = result.scalars().first()

            if appointment:
                appointment.status = 'completed'
                await session.commit()

                await query.edit_message_text(
                    "✅ Запись отмечена как выполненная!"
                )

    async def cancel_appointment(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Отменить запись"""
        query = update.callback_query
        await query.answer()

        appointment_id = int(query.data.split('_')[2])

        async with async_session() as session:
            result = await session.execute(
                select(Appointment).where(Appointment.id == appointment_id)
            )
            appointment = result.scalars().first()

            if appointment:
                appointment.status = 'cancelled'
                await session.commit()

                await query.edit_message_text(
                    "❌ Запись отменена."
                )

    async def show_appointments_for_completion(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Показать записи для отметки выполнения"""
        user_id = update.effective_user.id

        async with async_session() as session:
            # Получаем сотрудника
            result = await session.execute(
                select(Employee).join(User).where(User.telegram_id == user_id)
            )
            employee = result.scalars().first()

            if not employee:
                await update.message.reply_text("Ошибка: сотрудник не найден.")
                return

            # Получаем записи за последние 3 дня
            three_days_ago = datetime.now() - timedelta(days=3)

            result = await session.execute(
                select(Appointment).where(
                    Appointment.employee_id == employee.id,
                    Appointment.appointment_date >= three_days_ago,
                    Appointment.status == 'scheduled'
                ).order_by(Appointment.appointment_date.desc())
            )
            appointments = result.scalars().all()

            if not appointments:
                await update.message.reply_text(
                    "Нет записей для отметки выполнения.",
                    reply_markup=EmployeeKeyboards.main_menu()
                )
                return

            await update.message.reply_text(
                "Выберите запись для отметки выполнения:",
                reply_markup=EmployeeKeyboards.appointments_for_completion(appointments)
            )

    async def mark_complete(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Отметить как выполненное (из списка)"""
        query = update.callback_query
        await query.answer()

        appointment_id = int(query.data.split('_')[3])

        async with async_session() as session:
            result = await session.execute(
                select(Appointment).where(Appointment.id == appointment_id)
            )
            appointment = result.scalars().first()

            if appointment:
                appointment.status = 'completed'
                await session.commit()

                await query.edit_message_text(
                    "✅ Запись успешно отмечена как выполненная!"
                )

    async def show_salon_info(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Показать информацию о салоне"""
        info = (
            f"🏢 Салон красоты «{config.SALON_INFO['name']}»\n\n"
            f"📍 Адрес:\n{config.SALON_INFO['address']}\n\n"
            f"📞 Телефон: {config.SALON_INFO['phone']}\n\n"
            f"🕐 Режим работы:\n{config.SALON_INFO['schedule']}"
        )

        await update.message.reply_text(info, reply_markup=EmployeeKeyboards.main_menu())
