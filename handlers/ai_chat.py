"""
Обработчик AI-чата с клиентами
"""
from telegram import Update
from telegram.ext import ContextTypes, ConversationHandler
from keyboards.client import ClientKeyboards
import config

# State для ConversationHandler
AI_CHATTING = range(1)[0]


class AIChatHandlers:
    """Обработчики для AI-чата"""

    def __init__(self, ai_service):
        """
        Инициализация обработчика AI-чата

        Args:
            ai_service: Экземпляр AIService для работы с AI
        """
        self.ai_service = ai_service
        self.active_chats = set()  # Пользователи, находящиеся в режиме AI-чата

    async def start_ai_chat(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Начать AI-чат"""
        query = update.callback_query
        if query:
            await query.answer()

        user_id = update.effective_user.id

        if not self.ai_service.is_available():
            text = (
                "😔 К сожалению, AI-ассистент сейчас недоступен.\n\n"
                "Пожалуйста, воспользуйтесь меню для записи или позвоните нам:\n"
                f"📞 {config.SALON_INFO['phone']}"
            )
            if query:
                await query.edit_message_text(text, reply_markup=ClientKeyboards.main_menu())
            else:
                await update.message.reply_text(text, reply_markup=ClientKeyboards.main_menu())
            return ConversationHandler.END

        # Очищаем предыдущую историю чата
        self.ai_service.clear_history(user_id)
        self.active_chats.add(user_id)

        welcome_text = (
            f"🤖 Здравствуйте! Я AI-ассистент салона {config.SALON_INFO['name']}.\n\n"
            "Я могу помочь вам:\n"
            "• Узнать об услугах и процедурах\n"
            "• Получить информацию о салоне\n"
            "• Ответить на вопросы о массаже и SPA\n"
            "• Подобрать подходящую процедуру\n\n"
            "💬 Просто напишите свой вопрос, и я отвечу!\n\n"
            "Для завершения диалога нажмите кнопку ниже."
        )

        if query:
            await query.edit_message_text(
                welcome_text,
                reply_markup=ClientKeyboards.ai_chat_menu()
            )
        else:
            await update.message.reply_text(
                welcome_text,
                reply_markup=ClientKeyboards.ai_chat_menu()
            )

        return AI_CHATTING

    async def handle_ai_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработать сообщение в AI-чате"""
        user_id = update.effective_user.id
        user_message = update.message.text

        # Отправляем индикатор набора текста
        await update.message.chat.send_action(action="typing")

        # Получаем ответ от AI
        ai_response = await self.ai_service.get_response(user_id, user_message)

        if ai_response:
            # Отправляем ответ с кнопками
            await update.message.reply_text(
                ai_response,
                reply_markup=ClientKeyboards.ai_chat_menu()
            )
        else:
            await update.message.reply_text(
                "Извините, произошла ошибка. Попробуйте еще раз.",
                reply_markup=ClientKeyboards.ai_chat_menu()
            )

        return AI_CHATTING

    async def end_ai_chat(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Завершить AI-чат"""
        query = update.callback_query
        if query:
            await query.answer()

        user_id = update.effective_user.id

        # Удаляем пользователя из активных чатов
        self.active_chats.discard(user_id)

        # Очищаем историю
        self.ai_service.clear_history(user_id)

        farewell_text = (
            "👋 Спасибо за общение!\n\n"
            f"Буду рад помочь вам снова в салоне {config.SALON_INFO['name']}.\n\n"
            "Используйте меню ниже для записи на процедуру."
        )

        if query:
            await query.edit_message_text(
                farewell_text,
                reply_markup=ClientKeyboards.main_menu()
            )
        else:
            await update.message.reply_text(
                farewell_text,
                reply_markup=ClientKeyboards.main_menu()
            )

        return ConversationHandler.END

    async def go_to_booking_from_chat(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Перейти к записи из AI-чата"""
        query = update.callback_query
        if query:
            await query.answer()

        user_id = update.effective_user.id

        # Завершаем AI-чат
        self.active_chats.discard(user_id)
        self.ai_service.clear_history(user_id)

        # Показываем главное меню
        text = (
            "Отлично! Давайте запишем вас на процедуру! 📅\n\n"
            "Нажмите кнопку ниже для выбора услуги."
        )

        if query:
            await query.edit_message_text(
                text,
                reply_markup=ClientKeyboards.main_menu()
            )
        else:
            await update.message.reply_text(
                text,
                reply_markup=ClientKeyboards.main_menu()
            )

        return ConversationHandler.END
