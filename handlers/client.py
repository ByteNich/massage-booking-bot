from datetime import datetime, timedelta
from telegram import Update
from telegram.ext import ContextTypes, ConversationHandler
from sqlalchemy import select
from database.models import User, Service, Appointment, Employee
from database.database import async_session
from keyboards.client import ClientKeyboards
from utils.helpers import get_or_create_user, format_service_info, format_appointment_info, get_available_time_slots
import config

# States для ConversationHandler
SELECTING_SERVICE, SELECTING_DATE, SELECTING_TIME, CONFIRMING_BOOKING = range(4)


class ClientHandlers:
    """Обработчики для клиентов"""

    def __init__(self, scheduler):
        self.scheduler = scheduler
        self.booking_data = {}  # Временное хранилище данных о записи

    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик команды /start"""
        user = update.effective_user

        async with async_session() as session:
            db_user = await get_or_create_user(
                telegram_id=user.id,
                username=user.username,
                first_name=user.first_name,
                last_name=user.last_name,
                session=session
            )

            # Проверяем, есть ли у пользователя телефон
            if not db_user.phone:
                await update.message.reply_text(
                    "Добро пожаловать в салон красоты «Баланс»! 💆‍♀️\n\n"
                    "Для записи на процедуры нам необходим ваш номер телефона.\n"
                    "Пожалуйста, нажмите кнопку ниже, чтобы поделиться им.",
                    reply_markup=ClientKeyboards.request_phone()
                )
                return

        welcome_message = (
            f"Добро пожаловать в салон красоты «{config.SALON_INFO['name']}»! 💆‍♀️\n\n"
            f"Я помогу вам записаться на процедуру.\n\n"
            f"Используйте меню ниже для навигации:"
        )

        await update.message.reply_text(
            welcome_message,
            reply_markup=ClientKeyboards.main_menu()
        )

    async def handle_contact(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработка полученного контакта"""
        contact = update.message.contact

        async with async_session() as session:
            result = await session.execute(
                select(User).where(User.telegram_id == contact.user_id)
            )
            user = result.scalars().first()

            if user:
                user.phone = contact.phone_number
                await session.commit()

        await update.message.reply_text(
            "Спасибо! Ваш номер телефона сохранён.\n\n"
            "Теперь вы можете пользоваться всеми функциями бота.",
            reply_markup=ClientKeyboards.main_menu()
        )

    async def show_services(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Показать категории услуг"""
        async with async_session() as session:
            result = await session.execute(
                select(Service.category).distinct().where(Service.is_active == True)
            )
            categories = [row[0] for row in result.all()]

        await update.message.reply_text(
            "Выберите категорию услуг:",
            reply_markup=ClientKeyboards.services_categories(categories)
        )

    async def show_category_services(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Показать услуги категории"""
        query = update.callback_query
        await query.answer()

        category = query.data.split('_', 1)[1]

        async with async_session() as session:
            result = await session.execute(
                select(Service).where(
                    Service.category == category,
                    Service.is_active == True
                )
            )
            services = result.scalars().all()

        await query.edit_message_text(
            f"Услуги категории «{category}»:",
            reply_markup=ClientKeyboards.services_list(services)
        )

    async def show_service_detail(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Показать детали услуги"""
        query = update.callback_query
        await query.answer()

        service_id = int(query.data.split('_')[1])

        async with async_session() as session:
            result = await session.execute(
                select(Service).where(Service.id == service_id)
            )
            service = result.scalars().first()

            if not service:
                await query.edit_message_text("Услуга не найдена.")
                return

            info = format_service_info(service)
            await query.edit_message_text(
                info,
                reply_markup=ClientKeyboards.service_actions(service_id)
            )

    async def start_booking(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Начать процесс записи"""
        query = update.callback_query
        await query.answer()

        service_id = int(query.data.split('_')[1])
        user_id = update.effective_user.id

        # Сохраняем service_id в данных пользователя
        if user_id not in self.booking_data:
            self.booking_data[user_id] = {}
        self.booking_data[user_id]['service_id'] = service_id

        # Генерируем доступные даты (следующие 14 дней)
        available_dates = []
        for i in range(14):
            date = datetime.now() + timedelta(days=i)
            # Проверяем, является ли день рабочим
            if date.weekday() in config.WORK_DAYS:
                available_dates.append(date)

        await query.edit_message_text(
            "Выберите дату:",
            reply_markup=ClientKeyboards.select_date(available_dates)
        )

        return SELECTING_DATE

    async def select_date(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Выбор даты"""
        query = update.callback_query
        await query.answer()

        selected_date_str = query.data.split('_', 1)[1]
        selected_date = datetime.strptime(selected_date_str, '%Y-%m-%d')
        user_id = update.effective_user.id

        # Сохраняем дату
        self.booking_data[user_id]['date'] = selected_date_str

        # Получаем занятые слоты на эту дату
        async with async_session() as session:
            # Получаем первого доступного сотрудника (в данном случае Наталья)
            result = await session.execute(
                select(Employee).where(Employee.is_active == True).limit(1)
            )
            employee = result.scalars().first()

            if not employee:
                await query.edit_message_text(
                    "К сожалению, в данный момент нет доступных мастеров."
                )
                return ConversationHandler.END

            # Получаем все записи на эту дату
            start_of_day = selected_date.replace(hour=0, minute=0, second=0, microsecond=0)
            end_of_day = selected_date.replace(hour=23, minute=59, second=59, microsecond=999999)

            result = await session.execute(
                select(Appointment).where(
                    Appointment.employee_id == employee.id,
                    Appointment.appointment_date >= start_of_day,
                    Appointment.appointment_date <= end_of_day,
                    Appointment.status == 'scheduled'
                )
            )
            existing_appointments = result.scalars().all()

            # Получаем длительность услуги
            service_id = self.booking_data[user_id]['service_id']
            result = await session.execute(
                select(Service).where(Service.id == service_id)
            )
            service = result.scalars().first()

            # Получаем доступные слоты
            time_slots = get_available_time_slots(selected_date, existing_appointments, service.duration)

            if not time_slots:
                await query.edit_message_text(
                    "К сожалению, на эту дату нет свободных слотов.\n"
                    "Пожалуйста, выберите другую дату."
                )
                return SELECTING_DATE

            self.booking_data[user_id]['employee_id'] = employee.id

            await query.edit_message_text(
                f"Выберите время на {selected_date.strftime('%d.%m.%Y')}:",
                reply_markup=ClientKeyboards.select_time(time_slots, selected_date_str)
            )

        return SELECTING_TIME

    async def select_time(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Выбор времени"""
        query = update.callback_query
        await query.answer()

        parts = query.data.split('_')
        time_str = parts[2]
        user_id = update.effective_user.id

        # Сохраняем время
        self.booking_data[user_id]['time'] = time_str

        # Показываем подтверждение
        async with async_session() as session:
            service_id = self.booking_data[user_id]['service_id']
            result = await session.execute(
                select(Service).where(Service.id == service_id)
            )
            service = result.scalars().first()

            employee_id = self.booking_data[user_id]['employee_id']
            result = await session.execute(
                select(Employee).where(Employee.id == employee_id)
            )
            employee = result.scalars().first()

            date_str = self.booking_data[user_id]['date']

            confirmation_text = (
                "Пожалуйста, подтвердите запись:\n\n"
                f"📅 Дата: {date_str} в {time_str}\n"
                f"💆 Услуга: {service.name}\n"
                f"💰 Цена: {service.price} ₽\n"
                f"👤 Мастер: {employee.name}\n"
                f"⏱ Длительность: {service.duration} мин\n\n"
                f"📍 Адрес: {config.SALON_INFO['address']}"
            )

            await query.edit_message_text(
                confirmation_text,
                reply_markup=ClientKeyboards.confirm_booking()
            )

        return CONFIRMING_BOOKING

    async def confirm_booking(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Подтверждение записи"""
        query = update.callback_query
        await query.answer()

        user_id = update.effective_user.id
        booking_info = self.booking_data.get(user_id)

        if not booking_info:
            await query.edit_message_text("Ошибка: данные о записи не найдены.")
            return ConversationHandler.END

        async with async_session() as session:
            # Получаем пользователя
            result = await session.execute(
                select(User).where(User.telegram_id == user_id)
            )
            user = result.scalars().first()

            # Создаём запись
            appointment_datetime = datetime.strptime(
                f"{booking_info['date']} {booking_info['time']}",
                '%Y-%m-%d %H:%M'
            )

            appointment = Appointment(
                user_id=user.id,
                employee_id=booking_info['employee_id'],
                service_id=booking_info['service_id'],
                appointment_date=appointment_datetime,
                status='scheduled'
            )

            session.add(appointment)
            await session.commit()
            await session.refresh(appointment)

            # Получаем данные для уведомления
            result = await session.execute(
                select(Service).where(Service.id == booking_info['service_id'])
            )
            service = result.scalars().first()

            result = await session.execute(
                select(Employee).where(Employee.id == booking_info['employee_id'])
            )
            employee = result.scalars().first()

            # Отправляем уведомление
            await self.scheduler.notify_new_appointment(appointment, user, service, employee)

        # Очищаем данные о записи
        del self.booking_data[user_id]

        await query.edit_message_text(
            "✅ Отлично! Ваша запись успешно создана!\n\n"
            "Мы отправим вам напоминание за 24 часа и за 3 часа до визита."
        )

        return ConversationHandler.END

    async def cancel_booking(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Отмена процесса записи"""
        query = update.callback_query
        await query.answer()

        user_id = update.effective_user.id
        if user_id in self.booking_data:
            del self.booking_data[user_id]

        await query.edit_message_text("Запись отменена.")
        return ConversationHandler.END

    async def show_my_appointments(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Показать записи пользователя"""
        user_id = update.effective_user.id

        async with async_session() as session:
            result = await session.execute(
                select(User).where(User.telegram_id == user_id)
            )
            user = result.scalars().first()

            result = await session.execute(
                select(Appointment).where(
                    Appointment.user_id == user.id,
                    Appointment.status == 'scheduled',
                    Appointment.appointment_date >= datetime.now()
                ).order_by(Appointment.appointment_date)
            )
            appointments = result.scalars().all()

            if not appointments:
                await update.message.reply_text(
                    "У вас нет активных записей.",
                    reply_markup=ClientKeyboards.main_menu()
                )
                return

            await update.message.reply_text(
                "Ваши записи:",
                reply_markup=ClientKeyboards.my_appointments(appointments)
            )

    async def show_appointment_detail(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Показать детали записи"""
        query = update.callback_query
        await query.answer()

        appointment_id = int(query.data.split('_')[1])

        async with async_session() as session:
            result = await session.execute(
                select(Appointment, Service, Employee).join(
                    Service, Appointment.service_id == Service.id
                ).join(
                    Employee, Appointment.employee_id == Employee.id
                ).where(Appointment.id == appointment_id)
            )
            row = result.first()

            if not row:
                await query.edit_message_text("Запись не найдена.")
                return

            appointment, service, employee = row
            info = format_appointment_info(appointment, service, employee)
            info += f"\n\n📍 Адрес: {config.SALON_INFO['address']}"

            await query.edit_message_text(
                info,
                reply_markup=ClientKeyboards.appointment_actions(appointment_id)
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
                    "✅ Запись успешно отменена."
                )

    async def show_salon_info(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Показать информацию о салоне"""
        info = (
            f"🏢 Салон красоты «{config.SALON_INFO['name']}»\n\n"
            f"📍 Адрес:\n{config.SALON_INFO['address']}\n\n"
            f"📞 Телефон: {config.SALON_INFO['phone']}\n\n"
            f"🕐 Режим работы:\n{config.SALON_INFO['schedule']}"
        )

        await update.message.reply_text(info, reply_markup=ClientKeyboards.main_menu())

    async def show_contacts(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Показать контакты"""
        contacts = (
            f"📞 Контакты салона «{config.SALON_INFO['name']}»\n\n"
            f"Телефон: {config.SALON_INFO['phone']}\n\n"
            f"Адрес:\n{config.SALON_INFO['address']}\n\n"
            f"Режим работы:\n{config.SALON_INFO['schedule']}"
        )

        await update.message.reply_text(contacts, reply_markup=ClientKeyboards.main_menu())

    async def handle_back_button(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Универсальный обработчик кнопки Назад для клиентов"""
        query = update.callback_query
        await query.answer()

        data = query.data

        # Назад к главному меню
        if data == "back_to_main":
            try:
                await query.message.delete()
            except:
                pass
            await query.message.reply_text(
                f"Добро пожаловать в салон красоты «{config.SALON_INFO['name']}»! 💆‍♀️\n\n"
                f"Используйте меню ниже для навигации:",
                reply_markup=ClientKeyboards.main_menu()
            )

        # Назад к категориям
        elif data == "back_to_categories":
            async with async_session() as session:
                result = await session.execute(
                    select(Service.category).distinct().where(Service.is_active == True)
                )
                categories = [row[0] for row in result.all()]

            await query.edit_message_text(
                "Выберите категорию услуг:",
                reply_markup=ClientKeyboards.services_categories(categories)
            )

        # Назад к списку услуг
        elif data == "back_to_services":
            # Получаем категорию из контекста (если есть)
            await query.edit_message_text(
                "Выберите услугу или категорию:",
            )
            # Показываем категории
            async with async_session() as session:
                result = await session.execute(
                    select(Service.category).distinct().where(Service.is_active == True)
                )
                categories = [row[0] for row in result.all()]

            await query.edit_message_text(
                "Выберите категорию услуг:",
                reply_markup=ClientKeyboards.services_categories(categories)
            )

        # Назад к списку записей
        elif data == "back_to_appointments":
            user_id = update.effective_user.id

            async with async_session() as session:
                result = await session.execute(
                    select(User).where(User.telegram_id == user_id)
                )
                user = result.scalars().first()

                result = await session.execute(
                    select(Appointment).where(
                        Appointment.user_id == user.id,
                        Appointment.status == 'scheduled',
                        Appointment.appointment_date >= datetime.now()
                    ).order_by(Appointment.appointment_date)
                )
                appointments = result.scalars().all()

                if not appointments:
                    await query.edit_message_text("У вас нет активных записей.")
                    return

                await query.edit_message_text(
                    "Ваши записи:",
                    reply_markup=ClientKeyboards.my_appointments(appointments)
                )
