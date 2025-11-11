from telegram import InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton


class EmployeeKeyboards:
    """Клавиатуры для сотрудников"""

    @staticmethod
    def main_menu():
        """Главное меню сотрудника"""
        keyboard = [
            [KeyboardButton("📅 Мои записи на сегодня")],
            [KeyboardButton("📆 Расписание на неделю")],
            [KeyboardButton("✅ Отметить выполнение")],
            [KeyboardButton("ℹ️ Информация о салоне")],
        ]
        return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

    @staticmethod
    def select_date_for_schedule(available_dates: list):
        """Выбор даты для просмотра расписания"""
        keyboard = []
        for date in available_dates:
            date_str = date.strftime('%d.%m.%Y (%a)')
            keyboard.append([
                InlineKeyboardButton(date_str, callback_data=f"emp_date_{date.strftime('%Y-%m-%d')}")
            ])
        keyboard.append([InlineKeyboardButton("◀️ Назад", callback_data="emp_back_to_main")])
        return InlineKeyboardMarkup(keyboard)

    @staticmethod
    def appointment_list(appointments: list):
        """Список записей"""
        keyboard = []
        for appointment in appointments:
            time_str = appointment.appointment_date.strftime('%H:%M')
            keyboard.append([
                InlineKeyboardButton(
                    f"{time_str}",
                    callback_data=f"emp_appointment_{appointment.id}"
                )
            ])
        keyboard.append([InlineKeyboardButton("◀️ Назад", callback_data="emp_back_to_main")])
        return InlineKeyboardMarkup(keyboard)

    @staticmethod
    def appointment_actions(appointment_id: int):
        """Действия с записью"""
        keyboard = [
            [InlineKeyboardButton("✅ Отметить выполненной", callback_data=f"emp_complete_{appointment_id}")],
            [InlineKeyboardButton("❌ Отменить запись", callback_data=f"emp_cancel_{appointment_id}")],
            [InlineKeyboardButton("◀️ Назад", callback_data="emp_back_to_list")],
        ]
        return InlineKeyboardMarkup(keyboard)

    @staticmethod
    def appointments_for_completion(appointments: list):
        """Список записей для отметки выполнения"""
        keyboard = []
        for appointment in appointments:
            date_str = appointment.appointment_date.strftime('%d.%m %H:%M')
            keyboard.append([
                InlineKeyboardButton(
                    f"{date_str}",
                    callback_data=f"emp_mark_complete_{appointment.id}"
                )
            ])
        keyboard.append([InlineKeyboardButton("◀️ Назад", callback_data="emp_back_to_main")])
        return InlineKeyboardMarkup(keyboard)
