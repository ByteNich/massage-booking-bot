from datetime import datetime
from sqlalchemy import select
from database.models import User, Appointment, Service, Employee
import config


async def get_user_role(telegram_id: int, session) -> str:
    """Получить роль пользователя"""
    if telegram_id == config.ADMIN_ID:
        return config.ROLE_ADMIN

    if telegram_id in config.EMPLOYEE_IDS:
        return config.ROLE_EMPLOYEE

    return config.ROLE_CLIENT


async def get_or_create_user(telegram_id: int, username: str, first_name: str, last_name: str, session) -> User:
    """Получить или создать пользователя"""
    result = await session.execute(
        select(User).where(User.telegram_id == telegram_id)
    )
    user = result.scalars().first()

    if not user:
        role = await get_user_role(telegram_id, session)
        user = User(
            telegram_id=telegram_id,
            username=username,
            first_name=first_name,
            last_name=last_name,
            role=role
        )
        session.add(user)
        await session.commit()
        await session.refresh(user)

    return user


def format_appointment_info(appointment: Appointment, service: Service, employee: Employee) -> str:
    """Форматирование информации о записи"""
    date_str = appointment.appointment_date.strftime('%d.%m.%Y в %H:%M')

    return (
        f"📅 Запись на {date_str}\n"
        f"💆 Услуга: {service.name}\n"
        f"💰 Цена: {service.price} ₽\n"
        f"👤 Мастер: {employee.name}\n"
        f"⏱ Длительность: {service.duration} мин"
    )


def format_service_info(service: Service) -> str:
    """Форматирование информации об услуге"""
    info = f"💆 {service.name}\n"
    info += f"💰 Цена: {service.price} ₽\n"
    info += f"⏱ Длительность: {service.duration} мин\n"
    info += f"📁 Категория: {service.category}\n"

    if service.description:
        info += f"\n{service.description}"

    return info


def get_available_time_slots(date: datetime, existing_appointments: list, duration: int) -> list:
    """Получить доступные временные слоты"""
    slots = []
    current_hour = config.WORK_START

    while current_hour < config.WORK_END:
        slot_time = date.replace(hour=current_hour, minute=0, second=0, microsecond=0)

        # Проверяем, не занят ли слот
        is_available = True
        for appointment in existing_appointments:
            if appointment.appointment_date == slot_time:
                is_available = False
                break

        if is_available and slot_time > datetime.now():
            slots.append(slot_time)

        current_hour += 1

    return slots


def format_phone_number(phone: str) -> str:
    """Форматирование номера телефона"""
    # Удаляем все символы кроме цифр и +
    cleaned = ''.join(c for c in phone if c.isdigit() or c == '+')

    # Если начинается с 8, заменяем на +7
    if cleaned.startswith('8'):
        cleaned = '+7' + cleaned[1:]
    elif cleaned.startswith('7'):
        cleaned = '+7' + cleaned[1:]
    elif not cleaned.startswith('+'):
        cleaned = '+' + cleaned

    return cleaned
