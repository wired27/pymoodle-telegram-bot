from sqlalchemy import Column, BigInteger, String
from .base import Base

class User(Base):
    __tablename__ = 'users'
    telegram_id = Column(BigInteger, primary_key=True, index=True)
    api_key = Column(String, nullable=False)
