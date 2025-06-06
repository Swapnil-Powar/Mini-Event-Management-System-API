from pydantic import BaseModel, EmailStr, validator
from typing import List, Optional
from datetime import datetime
import pytz

class EventBase(BaseModel):
    name: str
    location: str
    start_time: datetime
    end_time: datetime
    max_capacity: int

    @validator('start_time', 'end_time', pre=True, always=True)
    def ensure_timezone_awareness(cls, v):
        if isinstance(v, str):
            v = datetime.fromisoformat(v)
        if v.tzinfo is None: 
            # Assuming IST if no timezone is provided, as per requirement
            # However, it's generally better to expect UTC or timezone-aware strings from clients
            return pytz.timezone('Asia/Kolkata').localize(v)
        return v

    @validator('end_time') 
    def end_time_must_be_after_start_time(cls, v, values):
        if 'start_time' in values and v <= values['start_time']:
            raise ValueError('End time must be after start time')
        return v

    class Config: 
        orm_mode = True
        json_encoders = {
            datetime: lambda dt: dt.isoformat()
        }

class EventCreate(EventBase):
    pass

class EventResponse(EventBase):
    id: int

class AttendeeBase(BaseModel):
    name: str
    email: EmailStr

class AttendeeCreate(AttendeeBase):
    pass

class AttendeeResponse(AttendeeBase):
    id: int
    event_id: int

    class Config:
        orm_mode = True

class EventWithAttendeesResponse(EventResponse):
    attendees: List[AttendeeResponse] = []

class PaginatedAttendeesResponse(BaseModel):
    total: int
    page: int
    size: int
    pages: int
    items: List[AttendeeResponse]
    