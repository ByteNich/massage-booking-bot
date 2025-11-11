from telegram import InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton


class EmployeeKeyboards:
    """Клавиатуры для сотрудников"""

    @staticmethod
    def main_menu():
        """Главное меню сотрудника"""
        keyboard = [
            [KeyboardButton("📅 Мои записи на сегодня")],
            [KeyboardButton("📆 Расписание на неделю")],
            [KeyboardButton("➕ Добавить запись")],
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
            [InlineKeyboardButton("✏️ Редактировать", callback_data=f"emp_edit_{appointment_id}")],
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

    @staticmethod
    def services_list(services: list):
        """Список услуг для создания записи"""
        keyboard = []
        for service in services:
            keyboard.append([
                InlineKeyboardButton(
                    f"{service.name} - {service.price} ₽",
                    callback_data=f"emp_service_{service.id}"
                )
            ])
        keyboard.append([InlineKeyboardButton("❌ Отмена", callback_data="emp_cancel_new")])
        return InlineKeyboardMarkup(keyboard)

    @staticmethod
    def select_date_for_new(available_dates: list):
        """Выбор даты для новой записи"""
        keyboard = []
        for date in available_dates:
            date_str = date.strftime('%d.%m.%Y (%a)')
            keyboard.append([
                InlineKeyboardButton(date_str, callback_data=f"emp_new_date_{date.strftime('%Y-%m-%d')}")
            ])
        keyboard.append([InlineKeyboardButton("❌ Отмена", callback_data="emp_cancel_new")])
        return InlineKeyboardMarkup(keyboard)

    @staticmethod
    def select_time_for_new(time_slots: list, selected_date: str):
        """Выбор времени для новой записи"""
        keyboard = []
        for slot in time_slots:
            time_str = slot.strftime('%H:%M')
            keyboard.append([
                InlineKeyboardButton(time_str, callback_data=f"emp_new_time_{selected_date}_{time_str}")
            ])
        keyboard.append([InlineKeyboardButton("◀️ Назад", callback_data="emp_back_to_date")])
        return InlineKeyboardMarkup(keyboard)

    @staticmethod
    def confirm_new_appointment():
        """Подтверждение новой записи"""
        keyboard = [
            [InlineKeyboardButton("✅ Подтвердить", callback_data="emp_confirm_new")],
            [InlineKeyboardButton("❌ Отменить", callback_data="emp_cancel_new")],
        ]
        return InlineKeyboardMarkup(keyboard)
