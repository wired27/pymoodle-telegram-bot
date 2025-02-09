from sqlalchemy import Column, BigInteger, Integer, String, UniqueConstraint
from sqlalchemy.orm import declarative_base

Base = declarative_base()

class User(Base):
    __tablename__ = 'users'
    telegram_id = Column(BigInteger, primary_key=True, index=True)  # BigInteger for large IDs
    api_key = Column(String, nullable=False)

class SeenAssignment(Base):
    __tablename__ = 'seen_assignments'
    telegram_id = Column(BigInteger, primary_key=True)
    assignment_id = Column(BigInteger, primary_key=True)
    __table_args__ = (UniqueConstraint('telegram_id', 'assignment_id', name='_user_assignment_uc'),)

class NotificationSetting(Base):
    __tablename__ = 'notification_settings'
    telegram_id = Column(BigInteger, primary_key=True)
    interval = Column(String, primary_key=True)
    __table_args__ = (UniqueConstraint('telegram_id', 'interval', name='_user_notification_uc'),)

class SentReminder(Base):
    __tablename__ = 'sent_reminders'
    telegram_id = Column(BigInteger, primary_key=True)
    assignment_id = Column(BigInteger, primary_key=True)
    interval = Column(String, primary_key=True)
    __table_args__ = (UniqueConstraint('telegram_id', 'assignment_id', 'interval', name='_user_assignment_interval_uc'),)
