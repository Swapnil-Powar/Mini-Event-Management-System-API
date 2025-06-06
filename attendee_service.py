from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import func
from app.models import Attendee, Event
from app.schemas import AttendeeCreate, PaginatedAttendeesResponse
from fastapi import HTTPException, status
 
class AttendeeService:
    async def register_attendee(self, db: AsyncSession, event_id: int, attendee_data: AttendeeCreate) -> Attendee:
        # Check if event exists
        event_stmt = select(Event).where(Event.id == event_id)
        event_result = await db.execute(event_stmt)
        event = event_result.scalars().first()

        if not event:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Event not found")

        # Check for overbooking
        attendee_count_stmt = select(func.count(Attendee.id)).where(Attendee.event_id == event_id)
        attendee_count_result = await db.execute(attendee_count_stmt)
        current_attendee_count = attendee_count_result.scalar_one_or_none() or 0

        if current_attendee_count >= event.max_capacity:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Event is at full capacity")

        # Check for duplicate registration
        duplicate_stmt = select(Attendee).where(Attendee.event_id == event_id, Attendee.email == attendee_data.email)
        duplicate_result = await db.execute(duplicate_stmt)
        existing_attendee = duplicate_result.scalars().first() 

        if existing_attendee:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Attendee with this email already registered for this event")

        db_attendee = Attendee(
            name=attendee_data.name,
            email=attendee_data.email,
            event_id=event_id
        )
        db.add(db_attendee)
        await db.commit()
        await db.refresh(db_attendee)
        return db_attendee

    async def get_attendees_for_event(
        self, db: AsyncSession, event_id: int, page: int = 1, size: int = 10
    ) -> PaginatedAttendeesResponse:
        if page < 1:
            page = 1
        if size < 1:
            size = 10
        
        offset = (page - 1) * size

        # Check if event exists
        event_stmt = select(Event).where(Event.id == event_id)
        event_result = await db.execute(event_stmt)
        event = event_result.scalars().first()
        if not event:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Event not found")

        # Get total count of attendees for the event
        total_count_stmt = select(func.count(Attendee.id)).where(Attendee.event_id == event_id)
        total_count_result = await db.execute(total_count_stmt)
        total_attendees = total_count_result.scalar_one_or_none() or 0

        # Get paginated attendees
        attendees_stmt = (
            select(Attendee)
            .where(Attendee.event_id == event_id)
            .offset(offset)
            .limit(size)
            .order_by(Attendee.id) # Or by name, registration time etc.
        )
        attendees_result = await db.execute(attendees_stmt)
        attendees = attendees_result.scalars().all()

        total_pages = (total_attendees + size - 1) // size  # Ceiling division

        return PaginatedAttendeesResponse(
            total=total_attendees,
            page=page,
            size=size,
            pages=total_pages,
            items=[attendee for attendee in attendees] # Model instances will be converted by Pydantic
        )
    