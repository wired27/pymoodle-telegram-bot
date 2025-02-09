from sqlalchemy import select
from models.assignment import SeenAssignment
from core.database import async_session

class AssignmentRepository:
    def __init__(self):
        pass

    async def insert_seen(self, telegram_id: int, assignment_id: int):
        async with async_session() as session:
            # Using insert with on_conflict_do_nothing style may require additional dialect-specific code.
            stmt = SeenAssignment.__table__.insert().values(telegram_id=telegram_id, assignment_id=assignment_id)
            try:
                await session.execute(stmt)
            except Exception:
                # On conflict, ignore
                pass
            await session.commit()

    async def get_seen_assignments(self, telegram_id: int):
        async with async_session() as session:
            result = await session.execute(select(SeenAssignment.assignment_id).where(SeenAssignment.telegram_id == telegram_id))
            return [row[0] for row in result.all()]