from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import func, or_
from app.models import Event, Attendee
from app.schemas import EventCreate
from datetime import datetime
import pytz

class EventService:
    async def create_event(self, db: AsyncSession, event_data: EventCreate) -> Event:
        # Ensure start_time and end_time are timezone-aware (UTC) for storage
        utc_start_time = event_data.start_time.astimezone(pytz.utc)
        utc_end_time = event_data.end_time.astimezone(pytz.utc)

        db_event = Event(  
            name=event_data.name,
            location=event_data.location,
            start_time=utc_start_time,
            end_time=utc_end_time,
            max_capacity=event_data.max_capacity
        )
        db.add(db_event) 
        await db.commit()
        await db.refresh(db_event)
        return db_event

    async def get_events(self, db: AsyncSession, skip: int = 0, limit: int = 100, timezone_str: str = "UTC") -> list[Event]:
        """
        Retrieves upcoming events.
        Events are considered upcoming if their end_time is in the future.
        """
        now_utc = datetime.now(pytz.utc)
        stmt = select(Event).where(Event.end_time > now_utc).offset(skip).limit(limit).order_by(Event.start_time)
        result = await db.execute(stmt)
        events = result.scalars().all()
        # The to_dict method in the model will handle timezone conversion for display
        return events

    async def get_event_by_id(self, db: AsyncSession, event_id: int) -> Event | None:
        stmt = select(Event).where(Event.id == event_id)
        result = await db.execute(stmt)
        return result.scalars().first()

    async def get_event_attendee_count(self, db: AsyncSession, event_id: int) -> int:
        stmt = select(func.count(Attendee.id)).where(Attendee.event_id == event_id)
        result = await db.execute(stmt)
        return result.scalar_one_or_none() or 0
    