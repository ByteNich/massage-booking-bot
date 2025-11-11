from datetime import datetime, timedelta
from telegram import Update
from telegram.ext import ContextTypes, ConversationHandler
from sqlalchemy import select, and_
from database.models import User, Service, Appointment, Employee
from database.database import async_session
from keyboards.employee import EmployeeKeyboards
from utils.helpers import format_appointment_info, get_available_time_slots
import config

# States для ConversationHandler
EMP_SELECTING_SERVICE, EMP_ENTERING_PHONE, EMP_SELECTING_DATE, EMP_SELECTING_TIME, EMP_CONFIRMING = range(5)
EMP_EDITING = range(1)[0]


class EmployeeHandlers:
    """Обработчики для сотрудников"""

    def __init__(self, scheduler=None):
        self.scheduler = scheduler
        self.new_appointment_data = {}  # Временное хранилище данных о новой записи

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

    async def handle_main_menu_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработка callback'ов главного меню"""
        query = update.callback_query
        await query.answer()
        data = query.data

        if data == "emp_today":
            await self.show_today_appointments(update, context)
        elif data == "emp_week":
            await self.show_week_schedule(update, context)
        elif data == "emp_add":
            await self.start_new_appointment(update, context)
        elif data == "emp_mark":
            await self.show_appointments_for_completion(update, context)

    async def show_today_appointments(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Показать записи на сегодня"""
        query = update.callback_query
        if query:
            await query.answer()
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
                text = "На сегодня у вас нет записей."
                if query:
                    await query.edit_message_text(text)
                else:
                    await update.message.reply_text(text)
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
            if query:
                await query.edit_message_text(
                    message,
                    reply_markup=EmployeeKeyboards.appointment_list(appointments)
                )
            else:
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
                select(Appointment, User, Service, Employee).join(
                    User, Appointment.user_id == User.id
                ).join(
                    Service, Appointment.service_id == Service.id
                ).join(
                    Employee, Appointment.employee_id == Employee.id
                ).where(Appointment.id == appointment_id)
            )
            row = result.first()

            if row:
                appointment, user, service, employee = row
                appointment.status = 'completed'
                await session.commit()

                # Отправляем уведомление
                if self.scheduler:
                    await self.scheduler.notify_appointment_completed(appointment, user, service, employee)

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
                select(Appointment, User, Service, Employee).join(
                    User, Appointment.user_id == User.id
                ).join(
                    Service, Appointment.service_id == Service.id
                ).join(
                    Employee, Appointment.employee_id == Employee.id
                ).where(Appointment.id == appointment_id)
            )
            row = result.first()

            if row:
                appointment, user, service, employee = row
                appointment.status = 'cancelled'
                await session.commit()

                # Отправляем уведомления
                if self.scheduler:
                    await self.scheduler.notify_appointment_cancelled(appointment, user, service, employee, 'employee')

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
                select(Appointment, User, Service, Employee).join(
                    User, Appointment.user_id == User.id
                ).join(
                    Service, Appointment.service_id == Service.id
                ).join(
                    Employee, Appointment.employee_id == Employee.id
                ).where(Appointment.id == appointment_id)
            )
            row = result.first()

            if row:
                appointment, user, service, employee = row
                appointment.status = 'completed'
                await session.commit()

                # Отправляем уведомление
                if self.scheduler:
                    await self.scheduler.notify_appointment_completed(appointment, user, service, employee)

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

    # === ДОБАВЛЕНИЕ НОВОЙ ЗАПИСИ ===

    async def start_new_appointment(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Начать процесс создания новой записи"""
        user_id = update.effective_user.id

        async with async_session() as session:
            # Проверяем, что это сотрудник
            result = await session.execute(
                select(Employee).join(User).where(User.telegram_id == user_id)
            )
            employee = result.scalars().first()

            if not employee:
                await update.message.reply_text("Ошибка: вы не являетесь сотрудником.")
                return ConversationHandler.END

            # Сохраняем ID сотрудника
            self.new_appointment_data[user_id] = {'employee_id': employee.id}

            # Показываем список услуг
            result = await session.execute(
                select(Service).where(Service.is_active == True).order_by(Service.category, Service.name)
            )
            services = result.scalars().all()

            await update.message.reply_text(
                "➕ Создание новой записи\n\n"
                "Шаг 1: Выберите услугу:",
                reply_markup=EmployeeKeyboards.services_list(services)
            )

        return EMP_SELECTING_SERVICE

    async def select_service_for_new(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Выбор услуги для новой записи"""
        query = update.callback_query
        await query.answer()

        service_id = int(query.data.split('_')[2])
        user_id = update.effective_user.id

        # Сохраняем service_id
        self.new_appointment_data[user_id]['service_id'] = service_id

        await query.edit_message_text(
            "Шаг 2: Введите номер телефона клиента\n\n"
            "Формат: +79991234567 или 89991234567\n\n"
            "Или отправьте /cancel для отмены"
        )

        return EMP_ENTERING_PHONE

    async def enter_client_phone(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Ввод номера телефона клиента"""
        user_id = update.effective_user.id
        phone = update.message.text

        # Очистка номера
        phone = ''.join(c for c in phone if c.isdigit() or c == '+')
        if phone.startswith('8'):
            phone = '+7' + phone[1:]
        elif phone.startswith('7'):
            phone = '+7' + phone[1:]
        elif not phone.startswith('+'):
            phone = '+' + phone

        # Сохраняем телефон
        self.new_appointment_data[user_id]['client_phone'] = phone

        # Генерируем доступные даты (следующие 14 дней)
        available_dates = []
        for i in range(14):
            date = datetime.now() + timedelta(days=i)
            if date.weekday() in config.WORK_DAYS:
                available_dates.append(date)

        await update.message.reply_text(
            f"Телефон клиента: {phone}\n\n"
            f"Шаг 3: Выберите дату:",
            reply_markup=EmployeeKeyboards.select_date_for_new(available_dates)
        )

        return EMP_SELECTING_DATE

    async def select_date_for_new(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Выбор даты для новой записи"""
        query = update.callback_query
        await query.answer()

        selected_date_str = query.data.split('_', 3)[3]
        selected_date = datetime.strptime(selected_date_str, '%Y-%m-%d')
        user_id = update.effective_user.id

        # Сохраняем дату
        self.new_appointment_data[user_id]['date'] = selected_date_str

        # Получаем employee_id и service_id
        employee_id = self.new_appointment_data[user_id]['employee_id']
        service_id = self.new_appointment_data[user_id]['service_id']

        async with async_session() as session:
            # Получаем записи на эту дату
            start_of_day = selected_date.replace(hour=0, minute=0, second=0, microsecond=0)
            end_of_day = selected_date.replace(hour=23, minute=59, second=59, microsecond=999999)

            result = await session.execute(
                select(Appointment).where(
                    Appointment.employee_id == employee_id,
                    Appointment.appointment_date >= start_of_day,
                    Appointment.appointment_date <= end_of_day,
                    Appointment.status == 'scheduled'
                )
            )
            existing_appointments = result.scalars().all()

            # Получаем длительность услуги
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
                return EMP_SELECTING_DATE

            await query.edit_message_text(
                f"Шаг 4: Выберите время на {selected_date.strftime('%d.%m.%Y')}:",
                reply_markup=EmployeeKeyboards.select_time_for_new(time_slots, selected_date_str)
            )

        return EMP_SELECTING_TIME

    async def select_time_for_new(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Выбор времени для новой записи"""
        query = update.callback_query
        await query.answer()

        parts = query.data.split('_')
        time_str = parts[-1]
        user_id = update.effective_user.id

        # Сохраняем время
        self.new_appointment_data[user_id]['time'] = time_str

        # Показываем подтверждение
        async with async_session() as session:
            service_id = self.new_appointment_data[user_id]['service_id']
            result = await session.execute(
                select(Service).where(Service.id == service_id)
            )
            service = result.scalars().first()

            date_str = self.new_appointment_data[user_id]['date']
            client_phone = self.new_appointment_data[user_id]['client_phone']

            confirmation_text = (
                "Шаг 5: Подтвердите создание записи:\n\n"
                f"📅 Дата: {date_str} в {time_str}\n"
                f"💆 Услуга: {service.name}\n"
                f"💰 Цена: {service.price} ₽\n"
                f"📞 Телефон клиента: {client_phone}\n"
                f"⏱ Длительность: {service.duration} мин"
            )

            await query.edit_message_text(
                confirmation_text,
                reply_markup=EmployeeKeyboards.confirm_new_appointment()
            )

        return EMP_CONFIRMING

    async def back_to_date_selection(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Возврат к выбору даты"""
        query = update.callback_query
        await query.answer()

        # Показываем снова выбор даты
        dates = []
        today = datetime.now().date()
        for i in range(14):  # Показываем 14 дней
            date = today + timedelta(days=i)
            if date.weekday() not in [0, 2]:  # Не понедельник и не среда
                dates.append(date)

        await query.edit_message_text(
            "Шаг 3: Выберите дату:",
            reply_markup=EmployeeKeyboards.select_date_for_new(dates)
        )

        return EMP_SELECTING_DATE

    async def confirm_new_appointment(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Подтверждение создания новой записи"""
        query = update.callback_query
        await query.answer()

        user_id = update.effective_user.id
        appointment_info = self.new_appointment_data.get(user_id)

        if not appointment_info:
            await query.edit_message_text("Ошибка: данные о записи не найдены.")
            return ConversationHandler.END

        async with async_session() as session:
            # Ищем или создаем клиента по телефону
            client_phone = appointment_info['client_phone']
            result = await session.execute(
                select(User).where(User.phone == client_phone)
            )
            client = result.scalars().first()

            if not client:
                # Создаем нового клиента
                client = User(
                    telegram_id=0,  # Временный ID, клиент еще не использовал бота
                    phone=client_phone,
                    role=config.ROLE_CLIENT
                )
                session.add(client)
                await session.commit()
                await session.refresh(client)

            # Создаём запись
            appointment_datetime = datetime.strptime(
                f"{appointment_info['date']} {appointment_info['time']}",
                '%Y-%m-%d %H:%M'
            )

            appointment = Appointment(
                user_id=client.id,
                employee_id=appointment_info['employee_id'],
                service_id=appointment_info['service_id'],
                appointment_date=appointment_datetime,
                status='scheduled'
            )

            session.add(appointment)
            await session.commit()
            await session.refresh(appointment)

            # Получаем полные данные для уведомления
            result = await session.execute(
                select(Service).where(Service.id == appointment_info['service_id'])
            )
            service = result.scalars().first()

            result = await session.execute(
                select(Employee).where(Employee.id == appointment_info['employee_id'])
            )
            employee = result.scalars().first()

            # Отправляем уведомления
            if self.scheduler:
                await self.scheduler.notify_new_appointment(appointment, client, service, employee)

        # Очищаем данные
        del self.new_appointment_data[user_id]

        await query.edit_message_text(
            "✅ Запись успешно создана!\n\n"
            "Клиент будет уведомлен, если у него есть Telegram."
        )

        return ConversationHandler.END

    async def cancel_new_appointment(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Отмена создания новой записи"""
        query = update.callback_query
        await query.answer()

        user_id = update.effective_user.id
        if user_id in self.new_appointment_data:
            del self.new_appointment_data[user_id]

        await query.edit_message_text("❌ Создание записи отменено.")
        return ConversationHandler.END

    # === РЕДАКТИРОВАНИЕ ЗАПИСИ ===

    async def start_edit_appointment(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Начать редактирование записи"""
        query = update.callback_query
        await query.answer()

        appointment_id = int(query.data.split('_')[2])
        context.user_data['editing_appointment_id'] = appointment_id

        async with async_session() as session:
            result = await session.execute(
                select(Appointment, Service, User).join(
                    Service, Appointment.service_id == Service.id
                ).join(
                    User, Appointment.user_id == User.id
                ).where(Appointment.id == appointment_id)
            )
            row = result.first()

            if not row:
                await query.edit_message_text("Запись не найдена.")
                return ConversationHandler.END

            appointment, service, user = row
            date_str = appointment.appointment_date.strftime('%d.%m.%Y %H:%M')

            await query.edit_message_text(
                f"✏️ Редактирование записи\n\n"
                f"Текущие данные:\n"
                f"📅 Дата и время: {date_str}\n"
                f"💆 Услуга: {service.name}\n"
                f"👤 Клиент: {user.phone}\n\n"
                f"Что хотите изменить?\n\n"
                f"Отправьте:\n"
                f"• дата: 2024-12-25 15:00\n"
                f"• отмена - для отмены редактирования"
            )

        return EMP_EDITING

    async def process_appointment_edit(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработка редактирования записи"""
        appointment_id = context.user_data.get('editing_appointment_id')

        if not appointment_id:
            await update.message.reply_text("Ошибка: запись не выбрана")
            return ConversationHandler.END

        text = update.message.text

        if text.lower() in ['отмена', '/cancel']:
            await update.message.reply_text("Редактирование отменено")
            context.user_data.pop('editing_appointment_id', None)
            return ConversationHandler.END

        if text.lower() == '/done':
            await update.message.reply_text("✅ Редактирование завершено")
            context.user_data.pop('editing_appointment_id', None)
            return ConversationHandler.END

        # Парсинг команды
        if ':' not in text:
            await update.message.reply_text(
                "❌ Неверный формат!\n\n"
                "Используйте:\n"
                "дата: 2024-12-25 15:00"
            )
            return EMP_EDITING

        field, value = text.split(':', 1)
        field = field.strip().lower()
        value = value.strip()

        async with async_session() as session:
            result = await session.execute(
                select(Appointment, User, Service, Employee).join(
                    User, Appointment.user_id == User.id
                ).join(
                    Service, Appointment.service_id == Service.id
                ).join(
                    Employee, Appointment.employee_id == Employee.id
                ).where(Appointment.id == appointment_id)
            )
            row = result.first()

            if not row:
                await update.message.reply_text("Ошибка: запись не найдена")
                return ConversationHandler.END

            appointment, user, service, employee = row

            try:
                if field in ['дата', 'date', 'время', 'time']:
                    # Парсим новую дату и время
                    new_datetime = datetime.strptime(value, '%Y-%m-%d %H:%M')
                    appointment.appointment_date = new_datetime
                    await session.commit()

                    # Отправляем уведомления
                    if self.scheduler:
                        await self.scheduler.notify_appointment_edited(appointment, user, service, employee, 'employee')

                    await update.message.reply_text(
                        f"✅ Дата и время изменены на: {new_datetime.strftime('%d.%m.%Y %H:%M')}"
                    )
                else:
                    await update.message.reply_text(
                        f"❌ Неизвестное поле: {field}\n"
                        f"Доступные поля: дата"
                    )
            except ValueError:
                await update.message.reply_text(
                    f"❌ Неверный формат даты!\n"
                    f"Используйте: 2024-12-25 15:00"
                )

        await update.message.reply_text("Отправьте еще изменения или /done для завершения")
        return EMP_EDITING

    async def handle_back_button(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработка кнопок 'Назад'"""
        query = update.callback_query
        await query.answer()
        data = query.data

        if data == "emp_back_to_main":
            # Возврат в главное меню
            await query.message.edit_text(
                "Главное меню сотрудника",
                reply_markup=None
            )
            await query.message.reply_text(
                f"Используйте меню ниже:",
                reply_markup=EmployeeKeyboards.main_menu()
            )
        elif data == "emp_back_to_list":
            # Возврат к списку записей на сегодня
            user_id = update.effective_user.id

            async with async_session() as session:
                # Получаем сотрудника
                result = await session.execute(
                    select(Employee).join(User).where(User.telegram_id == user_id)
                )
                employee = result.scalars().first()

                if not employee:
                    await query.message.edit_text("Ошибка: сотрудник не найден.")
                    return

                # Получаем записи на сегодня
                today = datetime.now().date()
                result = await session.execute(
                    select(Appointment)
                    .where(
                        and_(
                            Appointment.employee_id == employee.id,
                            Appointment.appointment_date >= datetime.combine(today, datetime.min.time()),
                            Appointment.appointment_date < datetime.combine(today, datetime.max.time()),
                            Appointment.status.in_(['pending', 'confirmed'])
                        )
                    )
                    .order_by(Appointment.appointment_date)
                )
                appointments = result.scalars().all()

                if not appointments:
                    await query.message.edit_text(
                        "📅 На сегодня нет записей",
                        reply_markup=None
                    )
                    return

                await query.message.edit_text(
                    f"📅 Записи на сегодня ({today.strftime('%d.%m.%Y')}):\n"
                    f"Выберите запись для просмотра:",
                    reply_markup=EmployeeKeyboards.appointment_list(appointments)
                )
