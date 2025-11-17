from telegram import InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton
from utils.helpers import format_date_russian


class ClientKeyboards:
    """Клавиатуры для клиентов"""

    @staticmethod
    def main_menu():
        """Главное меню клиента (inline)"""
        keyboard = [
            [InlineKeyboardButton("📅 Записаться на процедуру", callback_data="client_booking")],
            [InlineKeyboardButton("💬 Задать вопрос AI-ассистенту", callback_data="client_ai_chat")],
            [InlineKeyboardButton("📝 Мои записи", callback_data="client_my_appointments")],
            [InlineKeyboardButton("ℹ️ Информация о салоне", callback_data="client_info")],
        ]
        return InlineKeyboardMarkup(keyboard)

    @staticmethod
    def services_categories(categories: list):
        """Категории услуг"""
        keyboard = []
        for category in categories:
            keyboard.append([InlineKeyboardButton(category, callback_data=f"category_{category}")])
        keyboard.append([InlineKeyboardButton("◀️ Назад", callback_data="back_to_main")])
        return InlineKeyboardMarkup(keyboard)

    @staticmethod
    def services_list(services: list):
        """Список услуг"""
        keyboard = []
        for service in services:
            keyboard.append([
                InlineKeyboardButton(
                    f"{service.name} - {service.price} ₽",
                    callback_data=f"service_{service.id}"
                )
            ])
        keyboard.append([InlineKeyboardButton("◀️ Назад", callback_data="back_to_categories")])
        return InlineKeyboardMarkup(keyboard)

    @staticmethod
    def service_actions(service_id: int):
        """Действия с услугой"""
        keyboard = [
            [InlineKeyboardButton("📅 Записаться", callback_data=f"book_{service_id}")],
            [InlineKeyboardButton("◀️ Назад к списку", callback_data="back_to_services")],
        ]
        return InlineKeyboardMarkup(keyboard)

    @staticmethod
    def select_date(available_dates: list):
        """Выбор даты"""
        keyboard = []
        for date in available_dates:
            date_str = format_date_russian(date, include_weekday=True)
            keyboard.append([
                InlineKeyboardButton(date_str, callback_data=f"date_{date.strftime('%Y-%m-%d')}")
            ])
        keyboard.append([InlineKeyboardButton("◀️ Отмена", callback_data="cancel_booking")])
        return InlineKeyboardMarkup(keyboard)

    @staticmethod
    def select_time(time_slots: list, selected_date: str):
        """Выбор времени"""
        keyboard = []
        for slot in time_slots:
            time_str = slot.strftime('%H:%M')
            keyboard.append([
                InlineKeyboardButton(time_str, callback_data=f"time_{selected_date}_{time_str}")
            ])
        keyboard.append([InlineKeyboardButton("◀️ Назад", callback_data="back_to_date")])
        return InlineKeyboardMarkup(keyboard)

    @staticmethod
    def confirm_booking():
        """Подтверждение записи"""
        keyboard = [
            [InlineKeyboardButton("✅ Подтвердить", callback_data="confirm_booking")],
            [InlineKeyboardButton("❌ Отменить", callback_data="cancel_booking")],
        ]
        return InlineKeyboardMarkup(keyboard)

    @staticmethod
    def my_appointments(appointments: list):
        """Список записей клиента"""
        keyboard = []
        for appointment in appointments:
            date_str = appointment.appointment_date.strftime('%d.%m %H:%M')
            keyboard.append([
                InlineKeyboardButton(
                    f"{date_str}",
                    callback_data=f"appointment_{appointment.id}"
                )
            ])
        keyboard.append([InlineKeyboardButton("◀️ Назад", callback_data="back_to_main")])
        return InlineKeyboardMarkup(keyboard)

    @staticmethod
    def appointment_actions(appointment_id: int):
        """Действия с записью"""
        keyboard = [
            [InlineKeyboardButton("❌ Отменить запись", callback_data=f"cancel_appointment_{appointment_id}")],
            [InlineKeyboardButton("◀️ Назад к списку", callback_data="back_to_appointments")],
        ]
        return InlineKeyboardMarkup(keyboard)

    @staticmethod
    def request_phone():
        """Запрос номера телефона"""
        keyboard = [
            [KeyboardButton("📱 Отправить номер телефона", request_contact=True)],
        ]
        return ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=True)

    @staticmethod
    def salon_info_with_map():
        """Информация о салоне с картой"""
        keyboard = [
            [InlineKeyboardButton("📍 Открыть в Яндекс.Картах", url="https://yandex.ru/maps/-/CLCOeWmw")],
            [InlineKeyboardButton("◀️ Назад", callback_data="back_to_main")],
        ]
        return InlineKeyboardMarkup(keyboard)

    @staticmethod
    def ai_chat_menu():
        """Меню AI-чата"""
        keyboard = [
            [InlineKeyboardButton("📅 Записаться на процедуру", callback_data="ai_chat_go_booking")],
            [InlineKeyboardButton("❌ Завершить диалог", callback_data="ai_chat_end")],
        ]
        return InlineKeyboardMarkup(keyboard)
