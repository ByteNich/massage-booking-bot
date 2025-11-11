from datetime import datetime, timedelta
from telegram import Update
from telegram.ext import ContextTypes, ConversationHandler
from sqlalchemy import select, func, and_
from database.models import User, Service, Appointment, Employee
from database.database import async_session
from keyboards.admin import AdminKeyboards
import config

# States для ConversationHandler
ADDING_SERVICE, ADDING_EMPLOYEE, EDITING_SERVICE, EDITING_EMPLOYEE = range(4)


class AdminHandlers:
    """Обработчики для администратора"""

    def __init__(self):
        self.temp_data = {}  # Временное хранилище данных

    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик команды /start для администратора"""
        welcome_message = (
            f"Панель администратора салона «{config.SALON_INFO['name']}» 🔧\n\n"
            "Доступные функции:\n"
            "• Управление сотрудниками\n"
            "• Управление услугами\n"
            "• Просмотр статистики\n"
            "• Управление записями"
        )

        await update.message.reply_text(
            welcome_message,
            reply_markup=AdminKeyboards.main_menu()
        )

    # Управление сотрудниками
    async def show_employees_menu(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Показать меню управления сотрудниками"""
        await update.message.reply_text(
            "Управление сотрудниками:",
            reply_markup=AdminKeyboards.employees_menu()
        )

    async def show_employees_list(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Показать список сотрудников"""
        query = update.callback_query
        await query.answer()

        async with async_session() as session:
            result = await session.execute(
                select(Employee).order_by(Employee.name)
            )
            employees = result.scalars().all()

            if not employees:
                await query.edit_message_text(
                    "Список сотрудников пуст.",
                    reply_markup=AdminKeyboards.employees_menu()
                )
                return

            await query.edit_message_text(
                "Список сотрудников:",
                reply_markup=AdminKeyboards.employees_list(employees)
            )

    async def show_employee_detail(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Показать детали сотрудника"""
        query = update.callback_query
        await query.answer()

        employee_id = int(query.data.split('_')[2])

        async with async_session() as session:
            result = await session.execute(
                select(Employee).where(Employee.id == employee_id)
            )
            employee = result.scalars().first()

            if not employee:
                await query.edit_message_text("Сотрудник не найден.")
                return

            status = "Активен" if employee.is_active else "Неактивен"
            info = (
                f"👤 {employee.name}\n\n"
                f"Статус: {status}\n"
                f"Описание: {employee.description or 'не указано'}"
            )

            await query.edit_message_text(
                info,
                reply_markup=AdminKeyboards.employee_actions(employee_id, employee.is_active)
            )

    async def toggle_employee_status(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Изменить статус сотрудника"""
        query = update.callback_query
        await query.answer()

        employee_id = int(query.data.split('_')[3])

        async with async_session() as session:
            result = await session.execute(
                select(Employee).where(Employee.id == employee_id)
            )
            employee = result.scalars().first()

            if employee:
                employee.is_active = not employee.is_active
                await session.commit()

                status = "активирован" if employee.is_active else "деактивирован"
                await query.answer(f"Сотрудник {status}!")

                # Обновляем сообщение
                await self.show_employee_detail(update, context)

    # Управление услугами
    async def show_services_menu(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Показать меню управления услугами"""
        await update.message.reply_text(
            "Управление услугами:",
            reply_markup=AdminKeyboards.services_menu()
        )

    async def show_services_list(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Показать список услуг"""
        query = update.callback_query
        await query.answer()

        async with async_session() as session:
            result = await session.execute(
                select(Service).order_by(Service.category, Service.name)
            )
            services = result.scalars().all()

            if not services:
                await query.edit_message_text(
                    "Список услуг пуст.",
                    reply_markup=AdminKeyboards.services_menu()
                )
                return

            await query.edit_message_text(
                "Список услуг:",
                reply_markup=AdminKeyboards.services_list(services)
            )

    async def show_service_detail(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Показать детали услуги"""
        query = update.callback_query
        await query.answer()

        service_id = int(query.data.split('_')[2])

        async with async_session() as session:
            result = await session.execute(
                select(Service).where(Service.id == service_id)
            )
            service = result.scalars().first()

            if not service:
                await query.edit_message_text("Услуга не найдена.")
                return

            status = "Активна" if service.is_active else "Неактивна"
            info = (
                f"💆 {service.name}\n\n"
                f"💰 Цена: {service.price} ₽\n"
                f"⏱ Длительность: {service.duration} мин\n"
                f"📁 Категория: {service.category}\n"
                f"📊 Статус: {status}\n\n"
                f"Описание:\n{service.description or 'не указано'}"
            )

            await query.edit_message_text(
                info,
                reply_markup=AdminKeyboards.service_actions(service_id, service.is_active)
            )

    async def toggle_service_status(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Изменить статус услуги"""
        query = update.callback_query
        await query.answer()

        service_id = int(query.data.split('_')[3])

        async with async_session() as session:
            result = await session.execute(
                select(Service).where(Service.id == service_id)
            )
            service = result.scalars().first()

            if service:
                service.is_active = not service.is_active
                await session.commit()

                status = "активирована" if service.is_active else "деактивирована"
                await query.answer(f"Услуга {status}!")

                # Обновляем сообщение
                await self.show_service_detail(update, context)

    # Статистика
    async def show_statistics_menu(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Показать меню статистики"""
        await update.message.reply_text(
            "Выберите период для статистики:",
            reply_markup=AdminKeyboards.statistics_menu()
        )

    async def show_statistics(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Показать статистику"""
        query = update.callback_query
        await query.answer()

        period = query.data.split('_')[2]  # today, week, month

        # Определяем временные рамки
        now = datetime.now()
        if period == 'today':
            start_date = now.replace(hour=0, minute=0, second=0, microsecond=0)
            period_name = "сегодня"
        elif period == 'week':
            start_date = now - timedelta(days=7)
            period_name = "за неделю"
        else:  # month
            start_date = now - timedelta(days=30)
            period_name = "за месяц"

        async with async_session() as session:
            # Общее количество записей
            result = await session.execute(
                select(func.count(Appointment.id)).where(
                    Appointment.appointment_date >= start_date
                )
            )
            total_appointments = result.scalar()

            # Выполненные записи
            result = await session.execute(
                select(func.count(Appointment.id)).where(
                    and_(
                        Appointment.appointment_date >= start_date,
                        Appointment.status == 'completed'
                    )
                )
            )
            completed_appointments = result.scalar()

            # Отмененные записи
            result = await session.execute(
                select(func.count(Appointment.id)).where(
                    and_(
                        Appointment.appointment_date >= start_date,
                        Appointment.status == 'cancelled'
                    )
                )
            )
            cancelled_appointments = result.scalar()

            # Запланированные записи
            result = await session.execute(
                select(func.count(Appointment.id)).where(
                    and_(
                        Appointment.appointment_date >= start_date,
                        Appointment.status == 'scheduled'
                    )
                )
            )
            scheduled_appointments = result.scalar()

            # Общий доход (только выполненные)
            result = await session.execute(
                select(func.sum(Service.price)).select_from(Appointment).join(
                    Service, Appointment.service_id == Service.id
                ).where(
                    and_(
                        Appointment.appointment_date >= start_date,
                        Appointment.status == 'completed'
                    )
                )
            )
            total_revenue = result.scalar() or 0

            # Топ-3 популярных услуги
            result = await session.execute(
                select(Service.name, func.count(Appointment.id).label('count')).select_from(
                    Appointment
                ).join(
                    Service, Appointment.service_id == Service.id
                ).where(
                    Appointment.appointment_date >= start_date
                ).group_by(Service.name).order_by(func.count(Appointment.id).desc()).limit(3)
            )
            popular_services = result.all()

            # Формируем сообщение
            stats_message = f"📊 Статистика {period_name}:\n\n"
            stats_message += f"📅 Всего записей: {total_appointments}\n"
            stats_message += f"✅ Выполнено: {completed_appointments}\n"
            stats_message += f"📝 Запланировано: {scheduled_appointments}\n"
            stats_message += f"❌ Отменено: {cancelled_appointments}\n\n"
            stats_message += f"💰 Доход: {total_revenue:.2f} ₽\n\n"

            if popular_services:
                stats_message += "🔥 Популярные услуги:\n"
                for i, (service_name, count) in enumerate(popular_services, 1):
                    stats_message += f"{i}. {service_name} ({count})\n"

            await query.edit_message_text(stats_message)

    # Управление записями
    async def show_appointments_filter(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Показать фильтр записей"""
        await update.message.reply_text(
            "Выберите период:",
            reply_markup=AdminKeyboards.all_appointments_filter()
        )

    async def show_filtered_appointments(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Показать отфильтрованные записи"""
        query = update.callback_query
        await query.answer()

        filter_type = query.data.split('_')[2]  # today, week, all

        now = datetime.now()
        if filter_type == 'today':
            start_date = now.replace(hour=0, minute=0, second=0, microsecond=0)
            end_date = now.replace(hour=23, minute=59, second=59, microsecond=999999)
            period_name = "на сегодня"
        elif filter_type == 'week':
            start_date = now
            end_date = now + timedelta(days=7)
            period_name = "на неделю"
        else:  # all
            start_date = now
            end_date = now + timedelta(days=365)
            period_name = "все активные"

        async with async_session() as session:
            result = await session.execute(
                select(Appointment).where(
                    and_(
                        Appointment.appointment_date >= start_date,
                        Appointment.appointment_date <= end_date,
                        Appointment.status == 'scheduled'
                    )
                ).order_by(Appointment.appointment_date)
            )
            appointments = result.scalars().all()

            if not appointments:
                await query.edit_message_text(
                    f"Нет записей ({period_name})."
                )
                return

            await query.edit_message_text(
                f"Записи {period_name}:",
                reply_markup=AdminKeyboards.appointments_list(appointments)
            )

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
                f"📞 Телефон: {user.phone or 'не указан'}\n"
                f"👨‍💼 Мастер: {employee.name}\n\n"
                f"📊 Статус: {appointment.status}"
            )

            await query.edit_message_text(
                info,
                reply_markup=AdminKeyboards.appointment_actions(appointment_id)
            )

    async def cancel_appointment(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Отменить запись"""
        query = update.callback_query
        await query.answer()

        appointment_id = int(query.data.split('_')[3])

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

    async def show_salon_info(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Показать информацию о салоне"""
        info = (
            f"🏢 Салон красоты «{config.SALON_INFO['name']}»\n\n"
            f"📍 Адрес:\n{config.SALON_INFO['address']}\n\n"
            f"📞 Телефон: {config.SALON_INFO['phone']}\n\n"
            f"🕐 Режим работы:\n{config.SALON_INFO['schedule']}"
        )

        await update.message.reply_text(info, reply_markup=AdminKeyboards.main_menu())
