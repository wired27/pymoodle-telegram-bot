from sqlalchemy import Column, BigInteger, UniqueConstraint
from models.base import Base

class SeenAssignment(Base):
    __tablename__ = 'seen_assignments'
    telegram_id = Column(BigInteger, primary_key=True)
    assignment_id = Column(BigInteger, primary_key=True)
    __table_args__ = (UniqueConstraint('telegram_id', 'assignment_id', name='_user_assignment_uc'),)