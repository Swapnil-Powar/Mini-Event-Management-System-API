from fastapi import APIRouter, Depends, HTTPException, status, Query, Header
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional
from app import schemas, models
from app.database import get_db
from app.services.event_service import EventService
from app.services.attendee_service import AttendeeService
import pytz

router = APIRouter(
    prefix="/events",
    tags=["events"],
)

@router.post("/", response_model=schemas.EventResponse, status_code=status.HTTP_201_CREATED)
async def create_event(
    event: schemas.EventCreate,  
    db: AsyncSession = Depends(get_db),
    event_service: EventService = Depends() 
):
    """
    Creates a new event.
    - **name**: Name of the event
    - **location**: Location of the event
    - **start_time**: Start time of the event (ISO 8601 format, e.g., "2023-10-26T10:00:00+05:30" or "2023-10-26T10:00:00Z")
    - **end_time**: End time of the event (ISO 8601 format)
    - **max_capacity**: Maximum number of attendees
    """
    db_event = await event_service.create_event(db=db, event_data=event)
    # Convert to a default timezone for response, e.g., IST or client's preference
    # For simplicity, let's assume client wants IST if not specified.
    # The model's to_dict handles this if we pass the timezone.
    # However, Pydantic handles serialization based on schema.
    # The schema validator already ensures timezone awareness.
    return db_event # Pydantic will serialize using EventResponse

@router.get("/", response_model=List[schemas.EventResponse])
async def read_events(
    skip: int = 0, 
    limit: int = 10, 
    db: AsyncSession = Depends(get_db),
    event_service: EventService = Depends(),
    x_timezone: Optional[str] = Header(default="UTC", alias="X-Timezone")
):
    """
    Lists all upcoming events.
    Events are returned with times converted to the timezone specified in the `X-Timezone` header (defaults to UTC).
    """
    try:
        pytz.timezone(x_timezone) # Validate timezone string
    except pytz.exceptions.UnknownTimeZoneError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid X-Timezone header value.")
        
    events = await event_service.get_events(db=db, skip=skip, limit=limit)
    # Convert event times to the requested timezone for the response
    # Pydantic will use the schema's json_encoders or the model's representation
    # We need to ensure the EventResponse schema can handle this or do it manually.
    # The Event model's to_dict can be used if we construct dicts manually.
    # For now, let's rely on Pydantic and the model's structure.
    # The schema's `json_encoders` for datetime will output ISO format.
    # The `start_time` and `end_time` in `EventResponse` are `datetime` objects.
    # If they are timezone-aware, FastAPI/Pydantic should serialize them correctly with timezone info.
    
    # To ensure correct timezone in response, we can transform the event objects
    # before returning them if Pydantic doesn't handle it as expected.
    # For now, assuming Pydantic handles timezone-aware datetimes correctly.
    # The `EventResponse` schema inherits from `EventBase` which has datetime fields.
    # The `Event` model stores times in UTC. When fetched, they are UTC-aware.
    # Pydantic should serialize these as ISO 8601 strings with UTC offset (Z).
    # If client needs a specific timezone, they should handle conversion or we can add a utility.
    
    # Let's adjust the response to reflect the X-Timezone
    response_events = []
    for event_model in events:
        # Create EventResponse Pydantic model from the SQLAlchemy model
        # This ensures that Pydantic's serialization logic is used.
        # The `orm_mode = True` in the schema's Config helps with this.
        # However, to explicitly convert timezones for the response:
        target_tz = pytz.timezone(x_timezone)
        response_event_data = {
            "id": event_model.id,
            "name": event_model.name,
            "location": event_model.location,
            "start_time": event_model.start_time.astimezone(target_tz),
            "end_time": event_model.end_time.astimezone(target_tz),
            "max_capacity": event_model.max_capacity,
        }
        response_events.append(schemas.EventResponse(**response_event_data))
    return response_events


@router.post("/{event_id}/register", response_model=schemas.AttendeeResponse, status_code=status.HTTP_201_CREATED)
async def register_for_event(
    event_id: int, 
    attendee: schemas.AttendeeCreate, 
    db: AsyncSession = Depends(get_db),
    attendee_service: AttendeeService = Depends()
):
    """
    Registers an attendee for a specific event.
    - Prevents overbooking.
    - Prevents duplicate registrations for the same email.
    """
    return await attendee_service.register_attendee(db=db, event_id=event_id, attendee_data=attendee)

@router.get("/{event_id}/attendees", response_model=schemas.PaginatedAttendeesResponse)
async def get_event_attendees(
    event_id: int, 
    page: int = Query(1, ge=1, description="Page number"),
    size: int = Query(10, ge=1, le=100, description="Number of items per page"),
    db: AsyncSession = Depends(get_db),
    attendee_service: AttendeeService = Depends()
):
    """
    Returns all registered attendees for an event with pagination.
    """
    return await attendee_service.get_attendees_for_event(db=db, event_id=event_id, page=page, size=size)
