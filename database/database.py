from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import sessionmaker
from database.models import Base, Service, Employee, User
import config

# Create async engine
engine = create_async_engine(
    config.DATABASE_URL,
    echo=False,
    future=True
)

# Create async session factory
async_session = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False
)


async def init_db():
    """Инициализация базы данных"""
    async with engine.begin() as conn:
        # Создание всех таблиц
        await conn.run_sync(Base.metadata.create_all)

    # Добавление начальных данных
    await add_initial_data()


async def add_initial_data():
    """Добавление начальных данных (услуги)"""
    async with async_session() as session:
        # Проверяем, есть ли уже услуги
        from sqlalchemy import select
        result = await session.execute(select(Service))
        if result.scalars().first():
            return  # Данные уже есть

        # Добавляем услуги
        services = [
            Service(
                name='Массаж вакуумными банками и стоун терапия',
                price=2500,
                category='Уходы по телу',
                duration=90
            ),
            Service(
                name='Альгинатная маска',
                price=600,
                category='Уход за лицом',
                description='Глубокое увлажнение и детокс, разглаживание мелких морщин',
                duration=30
            ),
            Service(
                name='Лифтинг-массаж лица',
                price=1100,
                category='Уход за лицом',
                description='Улучшает контур лица, активирует лимфоток, придаёт коже свежесть',
                duration=45
            ),
            Service(
                name='Скрабирование + антицеллюлитное обёртывание + крем',
                price=2300,
                category='Уходы по телу',
                description='Комплекс для упругости и детокса: прогревание в термоодеяле',
                duration=90
            ),
            Service(
                name='Скраб-массаж + увлажняющий крем',
                price=1500,
                category='Уходы по телу',
                description='Мягкое отшелушивание и питание кожи, возвращает ей бархатистость',
                duration=60
            ),
            Service(
                name='Массаж бамбуковыми вениками',
                price=1200,
                category='Авторские техники',
                description='Экзотическая техника с вениками из бамбука — тонизирует тело',
                duration=60
            ),
            Service(
                name='Моделирующий массаж',
                price=2500,
                category='Классические массажи',
                description='Контурирующий массаж для упругости и выразительных форм',
                duration=75
            ),
            Service(
                name='Лимфодренажный массаж',
                price=1900,
                category='Классические массажи',
                description='Мягкая техника для выведения лишней жидкости и снятия отёков',
                duration=60
            ),
            Service(
                name='Лечебный массаж',
                price=1300,
                category='Классические массажи',
                description='Глубокое прорабатывание мышц, снятие напряжения и восстановление',
                duration=60
            ),
        ]

        session.add_all(services)
        await session.commit()


async def get_session():
    """Получение сессии базы данных"""
    async with async_session() as session:
        yield session
