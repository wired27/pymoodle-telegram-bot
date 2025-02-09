from sqlalchemy import Column, BigInteger, String, UniqueConstraint
from db.base import Base

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
