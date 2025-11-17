"""
AI сервис для общения с клиентами через Google Gemini
"""
import logging
from typing import Optional
import google.generativeai as genai
import config

logger = logging.getLogger(__name__)


class AIService:
    """Сервис для работы с AI (Google Gemini)"""

    def __init__(self):
        """Инициализация AI сервиса"""
        self.api_key = config.GEMINI_API_KEY
        self.model_name = config.GEMINI_MODEL
        self.model = None
        self.chat_sessions = {}  # {user_id: chat_session}

        if self.api_key:
            try:
                genai.configure(api_key=self.api_key)
                self.model = genai.GenerativeModel(
                    model_name=self.model_name,
                    system_instruction=self._get_system_prompt()
                )
                logger.info(f"AI Service initialized with model: {self.model_name}")
            except Exception as e:
                logger.error(f"Failed to initialize AI service: {e}")
        else:
            logger.warning("GEMINI_API_KEY not set. AI chat will not work.")

    def _get_system_prompt(self) -> str:
        """Системный промпт для AI-ассистента"""
        return f"""Ты - дружелюбный AI-ассистент салона красоты "{config.SALON_INFO['name']}".

ИНФОРМАЦИЯ О САЛОНЕ:
Название: {config.SALON_INFO['name']}
Адрес: {config.SALON_INFO['address']}
Телефон: {config.SALON_INFO['phone']}
Режим работы: {config.SALON_INFO['schedule']}

ТВОЯ РОЛЬ:
- Отвечай на вопросы о салоне, услугах, ценах, расположении
- Рассказывай о пользе массажа и SPA-процедур
- Консультируй клиентов профессионально и дружелюбно
- Постепенно "прогревай" клиента к записи на процедуру
- Когда клиент готов записаться, предложи нажать кнопку "📅 Записаться на процедуру"

СТИЛЬ ОБЩЕНИЯ:
- Обращайся на "Вы"
- Используй эмодзи, но умеренно (не больше 2-3 в сообщении)
- Будь профессиональным, но теплым и дружелюбным
- Отвечай кратко и по делу (не более 3-4 предложений)
- Если не знаешь точного ответа, честно признайся и предложи позвонить в салон

ОСНОВНЫЕ КАТЕГОРИИ УСЛУГ:
- Массаж (классический, лечебный, расслабляющий, антицеллюлитный)
- SPA-процедуры
- Косметология

ВАЖНО:
- НЕ придумывай конкретные цены - скажи, что они зависят от вида процедуры
- НЕ записывай клиентов сам - только предлагай нажать кнопку записи
- При вопросах о свободных датах/времени - предлагай использовать функцию записи в боте
- Не давай медицинских советов - только общую информацию о пользе процедур

Отвечай на русском языке."""

    async def get_response(self, user_id: int, message: str) -> Optional[str]:
        """
        Получить ответ от AI

        Args:
            user_id: ID пользователя Telegram
            message: Сообщение от пользователя

        Returns:
            Ответ от AI или None в случае ошибки
        """
        if not self.model:
            return "Извините, AI-ассистент временно недоступен. Пожалуйста, используйте меню бота для записи."

        try:
            # Получаем или создаем чат-сессию для пользователя
            if user_id not in self.chat_sessions:
                self.chat_sessions[user_id] = self.model.start_chat(history=[])

            chat = self.chat_sessions[user_id]

            # Отправляем сообщение и получаем ответ
            response = chat.send_message(message)

            return response.text

        except Exception as e:
            logger.error(f"Error getting AI response for user {user_id}: {e}")
            return "Извините, произошла ошибка. Попробуйте еще раз или воспользуйтесь меню бота."

    def clear_history(self, user_id: int):
        """Очистить историю чата для пользователя"""
        if user_id in self.chat_sessions:
            del self.chat_sessions[user_id]
            logger.info(f"Cleared chat history for user {user_id}")

    def is_available(self) -> bool:
        """Проверить, доступен ли AI сервис"""
        return self.model is not None
