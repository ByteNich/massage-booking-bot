import os
from dotenv import load_dotenv

load_dotenv()

# Telegram Bot
BOT_TOKEN = os.getenv('BOT_TOKEN')
ADMIN_ID = int(os.getenv('ADMIN_ID', 0))
EMPLOYEE_IDS = [int(id.strip()) for id in os.getenv('EMPLOYEE_IDS', '').split(',') if id.strip()]

# Database
# Получаем DATABASE_URL и конвертируем в async версию если нужно
_db_url = os.getenv('DATABASE_URL', 'sqlite+aiosqlite:///massage_bot.db')

# Replit может предоставить postgres:// вместо postgresql://
if _db_url.startswith('postgres://'):
    _db_url = _db_url.replace('postgres://', 'postgresql://', 1)

# Конвертируем синхронные драйверы в асинхронные
if 'postgresql://' in _db_url and 'asyncpg' not in _db_url:
    _db_url = _db_url.replace('postgresql://', 'postgresql+asyncpg://')
elif 'sqlite:///' in _db_url and 'aiosqlite' not in _db_url:
    _db_url = _db_url.replace('sqlite:///', 'sqlite+aiosqlite:///')

DATABASE_URL = _db_url

# Salon Info
SALON_INFO = {
    'name': os.getenv('SALON_NAME', 'VOLGA SPA'),
    'address': os.getenv('SALON_ADDRESS', 'Приволжский федеральный округ, Нижегородская область, городской округ Нижний Новгород, Нижний Новгород, Советская улица, 12 этаж 4, офис 436'),
    'phone': os.getenv('SALON_PHONE', '+7 (987) 530-91-00'),
    'schedule': os.getenv('SALON_SCHEDULE', 'вт,чт-сб 8:00-20:00'),
}

# Working hours
WORK_DAYS = [1, 3, 4, 5]  # вт(1), чт(3), пт(4), сб(5)
WORK_START = 8  # 8:00
WORK_END = 20   # 20:00

# Notification settings (hours before appointment)
REMINDER_HOURS = [int(h) for h in os.getenv('REMINDER_HOURS', '24,3').split(',')]

# User roles
ROLE_CLIENT = 'client'
ROLE_EMPLOYEE = 'employee'
ROLE_ADMIN = 'admin'

# Google Gemini API
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY', '')
GEMINI_MODEL = os.getenv('GEMINI_MODEL', 'gemini-1.5-flash')  # бесплатная версия
