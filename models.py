from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship
from app.database import Base
import datetime
import pytz

class Event(Base):
    __tablename__ = "events"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True, nullable=False)
    location = Column(String, nullable=False)
    start_time = Column(DateTime(timezone=True), nullable=False)
    end_time = Column(DateTime(timezone=True), nullable=False)
    max_capacity = Column(Integer, nullable=False) 

    attendees = relationship("Attendee", back_populates="event")

    def to_dict(self, timezone_str: str = "UTC"):
        target_tz = pytz.timezone(timezone_str) 
        return {
            "id": self.id,
            "name": self.name,
            "location": self.location,
            "start_time": self.start_time.astimezone(target_tz).isoformat() if self.start_time else None,
            "end_time": self.end_time.astimezone(target_tz).isoformat() if self.end_time else None,
            "max_capacity": self.max_capacity,
        }


class Attendee(Base):
    __tablename__ = "attendees"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    email = Column(String, index=True, nullable=False)
    event_id = Column(Integer, ForeignKey("events.id"), nullable=False)

    event = relationship("Event", back_populates="attendees")

    __table_args__ = (UniqueConstraint('email', 'event_id', name='_email_event_uc'),)

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "email": self.email,
            "event_id": self.event_id
        }
    