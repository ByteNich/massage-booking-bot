from telegram import InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton


class AdminKeyboards:
    """Клавиатуры для администратора"""

    @staticmethod
    def main_menu():
        """Главное меню администратора (inline)"""
        keyboard = [
            [InlineKeyboardButton("👥 Управление сотрудниками", callback_data="admin_employees")],
            [InlineKeyboardButton("💆 Управление услугами", callback_data="admin_services")],
            [InlineKeyboardButton("📊 Статистика", callback_data="admin_stats")],
            [InlineKeyboardButton("📅 Все записи", callback_data="admin_appointments")],
            [InlineKeyboardButton("📢 Рассылка", callback_data="admin_broadcast")],
        ]
        return InlineKeyboardMarkup(keyboard)

    @staticmethod
    def employees_menu():
        """Меню управления сотрудниками"""
        keyboard = [
            [InlineKeyboardButton("➕ Добавить сотрудника", callback_data="admin_add_employee")],
            [InlineKeyboardButton("📋 Список сотрудников", callback_data="admin_list_employees")],
            [InlineKeyboardButton("◀️ Назад", callback_data="admin_back_to_main")],
        ]
        return InlineKeyboardMarkup(keyboard)

    @staticmethod
    def employees_list(employees: list):
        """Список сотрудников"""
        keyboard = []
        for employee in employees:
            status = "✅" if employee.is_active else "❌"
            keyboard.append([
                InlineKeyboardButton(
                    f"{status} {employee.name}",
                    callback_data=f"admin_employee_{employee.id}"
                )
            ])
        keyboard.append([InlineKeyboardButton("◀️ Назад", callback_data="admin_employees_menu")])
        return InlineKeyboardMarkup(keyboard)

    @staticmethod
    def employee_actions(employee_id: int, is_active: bool):
        """Действия с сотрудником"""
        status_text = "Деактивировать" if is_active else "Активировать"
        keyboard = [
            [InlineKeyboardButton(f"🔄 {status_text}", callback_data=f"admin_toggle_employee_{employee_id}")],
            [InlineKeyboardButton("✏️ Редактировать", callback_data=f"admin_edit_employee_{employee_id}")],
            [InlineKeyboardButton("◀️ Назад", callback_data="admin_list_employees")],
        ]
        return InlineKeyboardMarkup(keyboard)

    @staticmethod
    def services_menu():
        """Меню управления услугами"""
        keyboard = [
            [InlineKeyboardButton("➕ Добавить услугу", callback_data="admin_add_service")],
            [InlineKeyboardButton("📋 Список услуг", callback_data="admin_list_services")],
            [InlineKeyboardButton("◀️ Назад", callback_data="admin_back_to_main")],
        ]
        return InlineKeyboardMarkup(keyboard)

    @staticmethod
    def services_list(services: list):
        """Список услуг"""
        keyboard = []
        for service in services:
            status = "✅" if service.is_active else "❌"
            keyboard.append([
                InlineKeyboardButton(
                    f"{status} {service.name} - {service.price} ₽",
                    callback_data=f"admin_service_{service.id}"
                )
            ])
        keyboard.append([InlineKeyboardButton("◀️ Назад", callback_data="admin_services_menu")])
        return InlineKeyboardMarkup(keyboard)

    @staticmethod
    def service_actions(service_id: int, is_active: bool):
        """Действия с услугой"""
        status_text = "Деактивировать" if is_active else "Активировать"
        keyboard = [
            [InlineKeyboardButton(f"🔄 {status_text}", callback_data=f"admin_toggle_service_{service_id}")],
            [InlineKeyboardButton("✏️ Редактировать", callback_data=f"admin_edit_service_{service_id}")],
            [InlineKeyboardButton("◀️ Назад", callback_data="admin_list_services")],
        ]
        return InlineKeyboardMarkup(keyboard)

    @staticmethod
    def statistics_menu():
        """Меню статистики"""
        keyboard = [
            [InlineKeyboardButton("📅 За сегодня", callback_data="admin_stats_today")],
            [InlineKeyboardButton("📆 За неделю", callback_data="admin_stats_week")],
            [InlineKeyboardButton("📊 За месяц", callback_data="admin_stats_month")],
            [InlineKeyboardButton("◀️ Назад", callback_data="admin_back_to_main")],
        ]
        return InlineKeyboardMarkup(keyboard)

    @staticmethod
    def all_appointments_filter():
        """Фильтр для всех записей"""
        keyboard = [
            [InlineKeyboardButton("📅 На сегодня", callback_data="admin_appointments_today")],
            [InlineKeyboardButton("📆 На неделю", callback_data="admin_appointments_week")],
            [InlineKeyboardButton("📋 Все активные", callback_data="admin_appointments_all")],
            [InlineKeyboardButton("◀️ Назад", callback_data="admin_back_to_main")],
        ]
        return InlineKeyboardMarkup(keyboard)

    @staticmethod
    def appointments_list(appointments: list):
        """Список записей"""
        keyboard = []
        for appointment in appointments:
            date_str = appointment.appointment_date.strftime('%d.%m %H:%M')
            keyboard.append([
                InlineKeyboardButton(
                    f"{date_str}",
                    callback_data=f"admin_appointment_{appointment.id}"
                )
            ])
        keyboard.append([InlineKeyboardButton("◀️ Назад", callback_data="admin_appointments_filter")])
        return InlineKeyboardMarkup(keyboard)

    @staticmethod
    def appointment_actions(appointment_id: int):
        """Действия с записью"""
        keyboard = [
            [InlineKeyboardButton("❌ Отменить запись", callback_data=f"admin_cancel_appointment_{appointment_id}")],
            [InlineKeyboardButton("◀️ Назад", callback_data="admin_back_to_appointments")],
        ]
        return InlineKeyboardMarkup(keyboard)

    @staticmethod
    def broadcast_confirm():
        """Подтверждение рассылки"""
        keyboard = [
            [InlineKeyboardButton("✅ Отправить", callback_data="admin_broadcast_send")],
            [InlineKeyboardButton("🖼 Добавить фото", callback_data="admin_broadcast_add_photo")],
            [InlineKeyboardButton("✏️ Изменить текст", callback_data="admin_broadcast_edit_text")],
            [InlineKeyboardButton("❌ Отменить", callback_data="admin_broadcast_cancel")],
        ]
        return InlineKeyboardMarkup(keyboard)

    @staticmethod
    def broadcast_with_photo_confirm():
        """Подтверждение рассылки с фото"""
        keyboard = [
            [InlineKeyboardButton("✅ Отправить", callback_data="admin_broadcast_send")],
            [InlineKeyboardButton("🗑 Удалить фото", callback_data="admin_broadcast_remove_photo")],
            [InlineKeyboardButton("✏️ Изменить текст", callback_data="admin_broadcast_edit_text")],
            [InlineKeyboardButton("❌ Отменить", callback_data="admin_broadcast_cancel")],
        ]
        return InlineKeyboardMarkup(keyboard)
