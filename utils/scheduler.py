from datetime import datetime, timedelta
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from sqlalchemy import select, and_
from database.models import Appointment, User, Service, Employee
from database.database import async_session
import config


class NotificationScheduler:
    """Планировщик уведомлений"""

    def __init__(self, bot):
        self.bot = bot
        self.scheduler = AsyncIOScheduler()

    def start(self):
        """Запуск планировщика"""
        # Проверка напоминаний каждые 10 минут
        self.scheduler.add_job(
            self.check_reminders,
            IntervalTrigger(minutes=10),
            id='check_reminders',
            replace_existing=True
        )
        self.scheduler.start()

    async def check_reminders(self):
        """Проверка и отправка напоминаний"""
        async with async_session() as session:
            now = datetime.now()

            # Получаем все активные записи
            result = await session.execute(
                select(Appointment, User, Service, Employee).join(
                    User, Appointment.user_id == User.id
                ).join(
                    Service, Appointment.service_id == Service.id
                ).join(
                    Employee, Appointment.employee_id == Employee.id
                ).where(
                    Appointment.status == 'scheduled'
                )
            )

            appointments = result.all()

            for appointment, user, service, employee in appointments:
                time_diff = appointment.appointment_date - now

                # Напоминание за 24 часа
                if not appointment.reminder_sent_24h:
                    if timedelta(hours=23, minutes=50) <= time_diff <= timedelta(hours=24, minutes=10):
                        await self.send_reminder(user, appointment, service, employee, "24 часа")
                        appointment.reminder_sent_24h = True
                        await session.commit()

                # Напоминание за 3 часа
                if not appointment.reminder_sent_3h:
                    if timedelta(hours=2, minutes=50) <= time_diff <= timedelta(hours=3, minutes=10):
                        await self.send_reminder(user, appointment, service, employee, "3 часа")
                        appointment.reminder_sent_3h = True
                        await session.commit()

                        # Отправляем уведомление сотруднику
                        await self.send_employee_reminder(employee, appointment, service, user)

    async def send_reminder(self, user: User, appointment: Appointment, service: Service, employee: Employee, time_before: str):
        """Отправка напоминания клиенту"""
        date_str = appointment.appointment_date.strftime('%d.%m.%Y в %H:%M')

        message = (
            f"🔔 Напоминание о записи через {time_before}!\n\n"
            f"📅 Дата: {date_str}\n"
            f"💆 Услуга: {service.name}\n"
            f"👤 Мастер: {employee.name}\n"
            f"📍 Адрес: {config.SALON_INFO['address']}\n\n"
            f"Ждём вас! 😊"
        )

        try:
            await self.bot.send_message(chat_id=user.telegram_id, text=message)
        except Exception as e:
            print(f"Error sending reminder to user {user.telegram_id}: {e}")

    async def send_employee_reminder(self, employee: Employee, appointment: Appointment, service: Service, user: User):
        """Отправка напоминания сотруднику"""
        date_str = appointment.appointment_date.strftime('%d.%m.%Y в %H:%M')

        client_name = f"{user.first_name} {user.last_name or ''}".strip()
        if user.phone:
            client_info = f"{client_name} ({user.phone})"
        else:
            client_info = client_name

        message = (
            f"🔔 Напоминание о записи через 3 часа!\n\n"
            f"📅 Дата: {date_str}\n"
            f"💆 Услуга: {service.name}\n"
            f"👤 Клиент: {client_info}\n\n"
            f"Подготовьтесь к приёму! 💪"
        )

        try:
            if employee.user:
                await self.bot.send_message(chat_id=employee.user.telegram_id, text=message)
        except Exception as e:
            print(f"Error sending reminder to employee {employee.id}: {e}")

    async def notify_new_appointment(self, appointment: Appointment, user: User, service: Service, employee: Employee):
        """Уведомление о новой записи"""
        date_str = appointment.appointment_date.strftime('%d.%m.%Y в %H:%M')

        # Уведомление клиенту
        client_message = (
            f"✅ Ваша запись успешно создана!\n\n"
            f"📅 Дата: {date_str}\n"
            f"💆 Услуга: {service.name}\n"
            f"💰 Цена: {service.price} ₽\n"
            f"👤 Мастер: {employee.name}\n"
            f"📍 Адрес: {config.SALON_INFO['address']}\n\n"
            f"Мы отправим вам напоминание за 24 часа и за 3 часа до визита."
        )

        try:
            await self.bot.send_message(chat_id=user.telegram_id, text=client_message)
        except Exception as e:
            print(f"Error sending notification to user {user.telegram_id}: {e}")

        # Уведомление сотруднику
        client_name = f"{user.first_name} {user.last_name or ''}".strip()
        employee_message = (
            f"📝 Новая запись!\n\n"
            f"📅 Дата: {date_str}\n"
            f"💆 Услуга: {service.name}\n"
            f"👤 Клиент: {client_name}\n"
            f"📞 Телефон: {user.phone or 'не указан'}"
        )

        try:
            if employee.user:
                await self.bot.send_message(chat_id=employee.user.telegram_id, text=employee_message)
        except Exception as e:
            print(f"Error sending notification to employee {employee.id}: {e}")

        # Уведомление администратору
        admin_message = (
            f"📝 Новая запись в системе!\n\n"
            f"📅 Дата: {date_str}\n"
            f"💆 Услуга: {service.name}\n"
            f"👤 Мастер: {employee.name}\n"
            f"👤 Клиент: {client_name}\n"
            f"📞 Телефон: {user.phone or 'не указан'}"
        )

        try:
            await self.bot.send_message(chat_id=config.ADMIN_ID, text=admin_message)
        except Exception as e:
            print(f"Error sending notification to admin: {e}")

    async def notify_appointment_cancelled(self, appointment: Appointment, user: User, service: Service, employee: Employee, cancelled_by: str):
        """Уведомление об отмене записи"""
        date_str = appointment.appointment_date.strftime('%d.%m.%Y в %H:%M')
        client_name = f"{user.first_name} {user.last_name or ''}".strip()

        # Уведомление клиенту (если отменил не клиент)
        if cancelled_by != 'client':
            client_message = (
                f"❌ Ваша запись отменена\n\n"
                f"📅 Дата: {date_str}\n"
                f"💆 Услуга: {service.name}\n"
                f"👤 Мастер: {employee.name}\n\n"
                f"Для новой записи обратитесь к администратору."
            )
            try:
                await self.bot.send_message(chat_id=user.telegram_id, text=client_message)
            except Exception as e:
                print(f"Error sending cancellation notification to user {user.telegram_id}: {e}")

        # Уведомление сотруднику (если отменил не сотрудник)
        if cancelled_by != 'employee':
            employee_message = (
                f"❌ Запись отменена\n\n"
                f"📅 Дата: {date_str}\n"
                f"💆 Услуга: {service.name}\n"
                f"👤 Клиент: {client_name}\n"
                f"📞 Телефон: {user.phone or 'не указан'}"
            )
            try:
                if employee.user:
                    await self.bot.send_message(chat_id=employee.user.telegram_id, text=employee_message)
            except Exception as e:
                print(f"Error sending cancellation notification to employee {employee.id}: {e}")

        # Уведомление администратору
        admin_message = (
            f"❌ Запись отменена ({cancelled_by})\n\n"
            f"📅 Дата: {date_str}\n"
            f"💆 Услуга: {service.name}\n"
            f"👤 Мастер: {employee.name}\n"
            f"👤 Клиент: {client_name}\n"
            f"📞 Телефон: {user.phone or 'не указан'}"
        )
        try:
            await self.bot.send_message(chat_id=config.ADMIN_ID, text=admin_message)
        except Exception as e:
            print(f"Error sending cancellation notification to admin: {e}")

    async def notify_appointment_completed(self, appointment: Appointment, user: User, service: Service, employee: Employee):
        """Уведомление о выполнении записи"""
        date_str = appointment.appointment_date.strftime('%d.%m.%Y в %H:%M')
        client_name = f"{user.first_name} {user.last_name or ''}".strip()

        # Уведомление администратору
        admin_message = (
            f"✅ Запись выполнена!\n\n"
            f"📅 Дата: {date_str}\n"
            f"💆 Услуга: {service.name}\n"
            f"👤 Мастер: {employee.name}\n"
            f"👤 Клиент: {client_name}\n"
            f"💰 Сумма: {service.price} ₽"
        )
        try:
            await self.bot.send_message(chat_id=config.ADMIN_ID, text=admin_message)
        except Exception as e:
            print(f"Error sending completion notification to admin: {e}")

    async def notify_appointment_edited(self, appointment: Appointment, user: User, service: Service, employee: Employee, edited_by: str):
        """Уведомление об изменении записи"""
        date_str = appointment.appointment_date.strftime('%d.%m.%Y в %H:%M')
        client_name = f"{user.first_name} {user.last_name or ''}".strip()

        # Уведомление клиенту
        client_message = (
            f"✏️ Ваша запись изменена\n\n"
            f"📅 Новая дата: {date_str}\n"
            f"💆 Услуга: {service.name}\n"
            f"👤 Мастер: {employee.name}\n"
            f"📍 Адрес: {config.SALON_INFO['address']}"
        )
        try:
            await self.bot.send_message(chat_id=user.telegram_id, text=client_message)
        except Exception as e:
            print(f"Error sending edit notification to user {user.telegram_id}: {e}")

        # Уведомление сотруднику (если редактировал не он)
        if edited_by != 'employee':
            employee_message = (
                f"✏️ Запись изменена\n\n"
                f"📅 Новая дата: {date_str}\n"
                f"💆 Услуга: {service.name}\n"
                f"👤 Клиент: {client_name}\n"
                f"📞 Телефон: {user.phone or 'не указан'}"
            )
            try:
                if employee.user:
                    await self.bot.send_message(chat_id=employee.user.telegram_id, text=employee_message)
            except Exception as e:
                print(f"Error sending edit notification to employee {employee.id}: {e}")

        # Уведомление администратору
        admin_message = (
            f"✏️ Запись изменена ({edited_by})\n\n"
            f"📅 Новая дата: {date_str}\n"
            f"💆 Услуга: {service.name}\n"
            f"👤 Мастер: {employee.name}\n"
            f"👤 Клиент: {client_name}\n"
            f"📞 Телефон: {user.phone or 'не указан'}"
        )
        try:
            await self.bot.send_message(chat_id=config.ADMIN_ID, text=admin_message)
        except Exception as e:
            print(f"Error sending edit notification to admin: {e}")
