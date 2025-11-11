from datetime import datetime
from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, ForeignKey, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship

Base = declarative_base()


class User(Base):
    """Модель пользователя"""
    __tablename__ = 'users'

    id = Column(Integer, primary_key=True)
    telegram_id = Column(Integer, unique=True, nullable=False)
    username = Column(String(255), nullable=True)
    first_name = Column(String(255), nullable=True)
    last_name = Column(String(255), nullable=True)
    phone = Column(String(20), nullable=True)
    role = Column(String(20), default='client')  # client, employee, admin
    created_at = Column(DateTime, default=datetime.now)

    # Relationships
    appointments = relationship('Appointment', back_populates='user', foreign_keys='Appointment.user_id')


class Employee(Base):
    """Модель сотрудника"""
    __tablename__ = 'employees'

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'), unique=True)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.now)

    # Relationships
    user = relationship('User', foreign_keys=[user_id])
    appointments = relationship('Appointment', back_populates='employee')
    work_schedule = relationship('WorkSchedule', back_populates='employee')


class Service(Base):
    """Модель услуги"""
    __tablename__ = 'services'

    id = Column(Integer, primary_key=True)
    name = Column(String(255), nullable=False)
    price = Column(Float, nullable=False)
    category = Column(String(255), nullable=True)
    description = Column(Text, nullable=True)
    duration = Column(Integer, default=60)  # Длительность в минутах
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.now)

    # Relationships
    appointments = relationship('Appointment', back_populates='service')


class Appointment(Base):
    """Модель записи на услугу"""
    __tablename__ = 'appointments'

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    employee_id = Column(Integer, ForeignKey('employees.id'), nullable=False)
    service_id = Column(Integer, ForeignKey('services.id'), nullable=False)
    appointment_date = Column(DateTime, nullable=False)
    status = Column(String(20), default='scheduled')  # scheduled, completed, cancelled
    notes = Column(Text, nullable=True)
    reminder_sent_24h = Column(Boolean, default=False)
    reminder_sent_3h = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.now)

    # Relationships
    user = relationship('User', back_populates='appointments', foreign_keys=[user_id])
    employee = relationship('Employee', back_populates='appointments')
    service = relationship('Service', back_populates='appointments')


class WorkSchedule(Base):
    """Модель рабочего расписания сотрудника"""
    __tablename__ = 'work_schedule'

    id = Column(Integer, primary_key=True)
    employee_id = Column(Integer, ForeignKey('employees.id'), nullable=False)
    date = Column(DateTime, nullable=False)
    start_time = Column(String(5), nullable=False)  # HH:MM
    end_time = Column(String(5), nullable=False)    # HH:MM
    is_available = Column(Boolean, default=True)

    # Relationships
    employee = relationship('Employee', back_populates='work_schedule')
