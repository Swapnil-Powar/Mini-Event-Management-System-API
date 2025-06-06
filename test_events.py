import pytest
from httpx import AsyncClient
from fastapi import status
from datetime import datetime, timedelta
import pytz

# Assuming your main app is in 'main.py' and schemas in 'app.schemas'
# Adjust imports based on your project structure if necessary
from app.schemas import EventResponse

@pytest.mark.asyncio
async def test_create_event(client: AsyncClient):
    """
    Test creating a new event. 
    """
    start_time_naive = datetime.now() + timedelta(days=1)
    # Make start_time timezone-aware (e.g., IST)
    ist = pytz.timezone('Asia/Kolkata') 
    start_time_aware = ist.localize(start_time_naive)
    end_time_aware = start_time_aware + timedelta(hours=2)

    event_data = {
        "name": "Tech Conference 2025",
        "location": "Bangalore International Exhibition Centre",
        "start_time": start_time_aware.isoformat(), # Send as ISO string
        "end_time": end_time_aware.isoformat(),   # Send as ISO string
        "max_capacity": 500
    }

    response = await client.post("/api/v1/events/", json=event_data)

    assert response.status_code == status.HTTP_201_CREATED
    
    response_data = response.json()
    
    # Validate against the Pydantic schema if possible, or check fields
    # For now, let's check key fields
    assert response_data["name"] == event_data["name"]
    assert response_data["location"] == event_data["location"]
    assert response_data["max_capacity"] == event_data["max_capacity"]
    assert "id" in response_data

    # Validate start_time and end_time
    # The response times should be ISO formatted strings.
    # Pydantic models in FastAPI usually serialize datetime objects to ISO 8601 strings.
    # The EventResponse schema uses datetime objects, which FastAPI serializes.
    
    # Parse the response datetimes
    response_start_time = datetime.fromisoformat(response_data["start_time"])
    response_end_time = datetime.fromisoformat(response_data["end_time"])

    # The times in the response should match the input times,
    # potentially converted to UTC or another consistent timezone by the backend.
    # Our service stores them as UTC. The EventResponse schema doesn't explicitly convert
    # them back to a specific timezone for the /create endpoint response, so they might be UTC.
    # Let's check if they are equivalent to the input times.

    # Convert original aware times to UTC for comparison, as DB stores in UTC
    start_time_utc = start_time_aware.astimezone(pytz.utc)
    end_time_utc = end_time_aware.astimezone(pytz.utc)

    assert response_start_time == start_time_utc
    assert response_end_time == end_time_utc

    # Verify that the response can be parsed by the EventResponse schema
    try:
        EventResponse(**response_data)
    except Exception as e:
        pytest.fail(f"Response data does not match EventResponse schema: {e}")

@pytest.mark.asyncio
async def test_create_event_invalid_payload_missing_field(client: AsyncClient):
    """
    Test creating an event with a missing required field (e.g., name).
    """
    start_time_naive = datetime.now() + timedelta(days=2)
    ist = pytz.timezone('Asia/Kolkata')
    start_time_aware = ist.localize(start_time_naive)
    end_time_aware = start_time_aware + timedelta(hours=2)

    event_data = {
        # "name": "Missing Name Event", # Name is missing
        "location": "Some Location",
        "start_time": start_time_aware.isoformat(),
        "end_time": end_time_aware.isoformat(),
        "max_capacity": 100
    }
    response = await client.post("/api/v1/events/", json=event_data)
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

@pytest.mark.asyncio
async def test_create_event_invalid_dates_end_before_start(client: AsyncClient):
    """
    Test creating an event where end_time is before start_time.
    """
    start_time_naive = datetime.now() + timedelta(days=3)
    ist = pytz.timezone('Asia/Kolkata')
    start_time_aware = ist.localize(start_time_naive)
    # End time is before start time
    end_time_aware = start_time_aware - timedelta(hours=1) 

    event_data = {
        "name": "Invalid Dates Event",
        "location": "Chronos Venue",
        "start_time": start_time_aware.isoformat(),
        "end_time": end_time_aware.isoformat(),
        "max_capacity": 50
    }
    response = await client.post("/api/v1/events/", json=event_data)
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    # Check for specific error message if your validator provides one
    response_json = response.json()
    assert any("End time must be after start time" in error.get("msg", "") for error in response_json.get("detail", []))


@pytest.mark.asyncio
async def test_get_events_empty(client: AsyncClient):
    """
    Test getting events when no events exist.
    """
    response = await client.get("/api/v1/events/")
    assert response.status_code == status.HTTP_200_OK
    assert response.json() == []

@pytest.mark.asyncio
async def test_get_events_with_data_and_timezone_conversion(client: AsyncClient):
    """
    Test getting events after creating one, and check timezone conversion.
    """
    # 1. Create an event first
    start_time_naive = datetime.now() + timedelta(days=1)
    ist = pytz.timezone('Asia/Kolkata')
    start_time_ist = ist.localize(start_time_naive) # Event created in IST
    end_time_ist = start_time_ist + timedelta(hours=2)

    event_data_create = {
        "name": "Timezone Test Event",
        "location": "Global Village",
        "start_time": start_time_ist.isoformat(),
        "end_time": end_time_ist.isoformat(),
        "max_capacity": 100
    }
    create_response = await client.post("/api/v1/events/", json=event_data_create)
    assert create_response.status_code == status.HTTP_201_CREATED
    created_event_id = create_response.json()["id"]

    # 2. Get events, requesting EST timezone
    est = pytz.timezone('America/New_York')
    response_est = await client.get("/api/v1/events/", headers={"X-Timezone": "America/New_York"})
    assert response_est.status_code == status.HTTP_200_OK
    events_est = response_est.json()
    
    assert len(events_est) >= 1
    retrieved_event_est = next((e for e in events_est if e["id"] == created_event_id), None)
    assert retrieved_event_est is not None

    # Verify times are in EST
    response_start_time_est = datetime.fromisoformat(retrieved_event_est["start_time"])
    response_end_time_est = datetime.fromisoformat(retrieved_event_est["end_time"])

    # Convert original IST time to EST for comparison
    expected_start_time_est = start_time_ist.astimezone(est)
    expected_end_time_est = end_time_ist.astimezone(est)

    assert response_start_time_est.isoformat() == expected_start_time_est.isoformat()
    assert response_end_time_est.isoformat() == expected_end_time_est.isoformat()
    assert response_start_time_est.tzinfo is not None
    assert response_start_time_est.tzinfo.utcoffset(response_start_time_est) == est.utcoffset(expected_start_time_est)


    # 3. Get events, requesting UTC timezone (default or explicit)
    utc = pytz.utc
    response_utc = await client.get("/api/v1/events/", headers={"X-Timezone": "UTC"})
    assert response_utc.status_code == status.HTTP_200_OK
    events_utc = response_utc.json()

    assert len(events_utc) >= 1
    retrieved_event_utc = next((e for e in events_utc if e["id"] == created_event_id), None)
    assert retrieved_event_utc is not None

    # Verify times are in UTC
    response_start_time_utc = datetime.fromisoformat(retrieved_event_utc["start_time"])
    response_end_time_utc = datetime.fromisoformat(retrieved_event_utc["end_time"])
    
    expected_start_time_utc = start_time_ist.astimezone(utc)
    expected_end_time_utc = end_time_ist.astimezone(utc)

    assert response_start_time_utc.isoformat() == expected_start_time_utc.isoformat()
    assert response_end_time_utc.isoformat() == expected_end_time_utc.isoformat()
    assert response_start_time_utc.tzinfo is not None
    assert response_start_time_utc.tzinfo.utcoffset(response_start_time_utc) == utc.utcoffset(expected_start_time_utc)


@pytest.mark.asyncio
async def test_get_events_invalid_timezone_header(client: AsyncClient):
    """
    Test getting events with an invalid X-Timezone header.
    """
    response = await client.get("/api/v1/events/", headers={"X-Timezone": "Invalid/Timezone"})
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert response.json()["detail"] == "Invalid X-Timezone header value."


@pytest.mark.asyncio
async def test_register_attendee_for_event(client: AsyncClient):
    """
    Test successfully registering an attendee for an event.
    """
    # 1. Create an event first
    start_time = (datetime.now(pytz.utc) + timedelta(days=5)).isoformat()
    end_time = (datetime.now(pytz.utc) + timedelta(days=5, hours=3)).isoformat()
    event_data = {
        "name": "Community Meetup",
        "location": "Local Hall",
        "start_time": start_time,
        "end_time": end_time,
        "max_capacity": 2
    }
    event_response = await client.post("/api/v1/events/", json=event_data)
    assert event_response.status_code == status.HTTP_201_CREATED
    event_id = event_response.json()["id"]

    # 2. Register an attendee
    attendee_data = {"name": "John Doe", "email": "john.doe@example.com"}
    register_response = await client.post(f"/api/v1/events/{event_id}/register", json=attendee_data)
    
    assert register_response.status_code == status.HTTP_201_CREATED
    response_data = register_response.json()
    assert response_data["name"] == attendee_data["name"]
    assert response_data["email"] == attendee_data["email"]
    assert response_data["event_id"] == event_id
    assert "id" in response_data

@pytest.mark.asyncio
async def test_register_attendee_for_non_existent_event(client: AsyncClient):
    """
    Test registering an attendee for an event that does not exist.
    """
    attendee_data = {"name": "Jane Doe", "email": "jane.doe@example.com"}
    non_existent_event_id = 99999
    response = await client.post(f"/api/v1/events/{non_existent_event_id}/register", json=attendee_data)
    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response.json()["detail"] == "Event not found"

@pytest.mark.asyncio
async def test_register_attendee_event_at_full_capacity(client: AsyncClient):
    """
    Test registering an attendee when the event is at full capacity.
    """
    # 1. Create an event with max_capacity = 1
    start_time = (datetime.now(pytz.utc) + timedelta(days=6)).isoformat()
    end_time = (datetime.now(pytz.utc) + timedelta(days=6, hours=1)).isoformat()
    event_data = {
        "name": "Limited Slot Workshop",
        "location": "Small Room",
        "start_time": start_time,
        "end_time": end_time,
        "max_capacity": 1
    }
    event_response = await client.post("/api/v1/events/", json=event_data)
    assert event_response.status_code == status.HTTP_201_CREATED
    event_id = event_response.json()["id"]

    # 2. Register one attendee (fills capacity)
    attendee1_data = {"name": "First User", "email": "first@example.com"}
    await client.post(f"/api/v1/events/{event_id}/register", json=attendee1_data)

    # 3. Attempt to register a second attendee
    attendee2_data = {"name": "Second User", "email": "second@example.com"}
    response = await client.post(f"/api/v1/events/{event_id}/register", json=attendee2_data)
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert response.json()["detail"] == "Event is at full capacity"

@pytest.mark.asyncio
async def test_register_attendee_duplicate_email(client: AsyncClient):
    """
    Test registering an attendee with an email that is already registered for the event.
    """
    # 1. Create an event
    start_time = (datetime.now(pytz.utc) + timedelta(days=7)).isoformat()
    end_time = (datetime.now(pytz.utc) + timedelta(days=7, hours=2)).isoformat()
    event_data = {
        "name": "Duplicate Email Test Event",
        "location": "Conference Room B",
        "start_time": start_time,
        "end_time": end_time,
        "max_capacity": 5
    }
    event_response = await client.post("/api/v1/events/", json=event_data)
    assert event_response.status_code == status.HTTP_201_CREATED
    event_id = event_response.json()["id"]

    # 2. Register an attendee
    attendee_data = {"name": "Unique User", "email": "unique.user@example.com"}
    await client.post(f"/api/v1/events/{event_id}/register", json=attendee_data)

    # 3. Attempt to register the same email again
    duplicate_attendee_data = {"name": "Another Name", "email": "unique.user@example.com"}
    response = await client.post(f"/api/v1/events/{event_id}/register", json=duplicate_attendee_data)
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert response.json()["detail"] == "Attendee with this email already registered for this event"

@pytest.mark.asyncio
async def test_register_attendee_invalid_email_format(client: AsyncClient):
    """
    Test registering an attendee with an invalid email format.
    """
    # 1. Create an event
    start_time = (datetime.now(pytz.utc) + timedelta(days=8)).isoformat()
    end_time = (datetime.now(pytz.utc) + timedelta(days=8, hours=1)).isoformat()
    event_data = {
        "name": "Email Validation Test",
        "location": "Tech Hub",
        "start_time": start_time,
        "end_time": end_time,
        "max_capacity": 10
    }
    event_response = await client.post("/api/v1/events/", json=event_data)
    assert event_response.status_code == status.HTTP_201_CREATED
    event_id = event_response.json()["id"]

    # 2. Attempt to register with an invalid email
    invalid_attendee_data = {"name": "Invalid Email User", "email": "invalid-email"}
    response = await client.post(f"/api/v1/events/{event_id}/register", json=invalid_attendee_data)
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    # Pydantic's EmailStr validation should trigger this
    response_json = response.json()
    assert any("value is not a valid email address" in error.get("msg", "") for error in response_json.get("detail", []))


@pytest.mark.asyncio
async def test_get_event_attendees_empty(client: AsyncClient):
    """
    Test getting attendees for an event that has no attendees.
    """
    # 1. Create an event
    start_time = (datetime.now(pytz.utc) + timedelta(days=9)).isoformat()
    end_time = (datetime.now(pytz.utc) + timedelta(days=9, hours=2)).isoformat()
    event_data = {
        "name": "Empty Attendees Event",
        "location": "Quiet Place",
        "start_time": start_time,
        "end_time": end_time,
        "max_capacity": 10
    }
    event_response = await client.post("/api/v1/events/", json=event_data)
    assert event_response.status_code == status.HTTP_201_CREATED
    event_id = event_response.json()["id"]

    # 2. Get attendees
    response = await client.get(f"/api/v1/events/{event_id}/attendees")
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["total"] == 0
    assert data["page"] == 1
    assert data["size"] == 10 # Default size
    assert data["pages"] == 0
    assert data["items"] == []

@pytest.mark.asyncio
async def test_get_event_attendees_with_pagination(client: AsyncClient):
    """
    Test getting attendees for an event with pagination.
    """
    # 1. Create an event
    start_time = (datetime.now(pytz.utc) + timedelta(days=10)).isoformat()
    end_time = (datetime.now(pytz.utc) + timedelta(days=10, hours=3)).isoformat()
    event_data = {
        "name": "Paginated Attendees Event",
        "location": "Large Auditorium",
        "start_time": start_time,
        "end_time": end_time,
        "max_capacity": 25
    }
    event_response = await client.post("/api/v1/events/", json=event_data)
    assert event_response.status_code == status.HTTP_201_CREATED
    event_id = event_response.json()["id"]

    # 2. Register 12 attendees
    registered_attendees = []
    for i in range(12):
        attendee_data = {"name": f"Attendee {i+1}", "email": f"attendee{i+1}@example.com"}
        reg_response = await client.post(f"/api/v1/events/{event_id}/register", json=attendee_data)
        assert reg_response.status_code == status.HTTP_201_CREATED
        registered_attendees.append(reg_response.json())

    # 3. Get attendees - Page 1, Size 5
    response_page1 = await client.get(f"/api/v1/events/{event_id}/attendees?page=1&size=5")
    assert response_page1.status_code == status.HTTP_200_OK
    data_page1 = response_page1.json()
    assert data_page1["total"] == 12
    assert data_page1["page"] == 1
    assert data_page1["size"] == 5
    assert data_page1["pages"] == 3 # 12 items, size 5 -> 5, 5, 2 -> 3 pages
    assert len(data_page1["items"]) == 5
    assert data_page1["items"][0]["email"] == "attendee1@example.com"
    assert data_page1["items"][4]["email"] == "attendee5@example.com"

    # 4. Get attendees - Page 2, Size 5
    response_page2 = await client.get(f"/api/v1/events/{event_id}/attendees?page=2&size=5")
    assert response_page2.status_code == status.HTTP_200_OK
    data_page2 = response_page2.json()
    assert data_page2["total"] == 12
    assert data_page2["page"] == 2
    assert data_page2["size"] == 5
    assert data_page2["pages"] == 3
    assert len(data_page2["items"]) == 5
    assert data_page2["items"][0]["email"] == "attendee6@example.com"
    assert data_page2["items"][4]["email"] == "attendee10@example.com"

    # 5. Get attendees - Page 3, Size 5
    response_page3 = await client.get(f"/api/v1/events/{event_id}/attendees?page=3&size=5")
    assert response_page3.status_code == status.HTTP_200_OK
    data_page3 = response_page3.json()
    assert data_page3["total"] == 12
    assert data_page3["page"] == 3
    assert data_page3["size"] == 5
    assert data_page3["pages"] == 3
    assert len(data_page3["items"]) == 2 # Remaining 2 attendees
    assert data_page3["items"][0]["email"] == "attendee11@example.com"
    assert data_page3["items"][1]["email"] == "attendee12@example.com"

    # 6. Get attendees - Page 1, Size 15 (larger than total)
    response_large_size = await client.get(f"/api/v1/events/{event_id}/attendees?page=1&size=15")
    assert response_large_size.status_code == status.HTTP_200_OK
    data_large_size = response_large_size.json()
    assert data_large_size["total"] == 12
    assert data_large_size["page"] == 1
    assert data_large_size["size"] == 15
    assert data_large_size["pages"] == 1
    assert len(data_large_size["items"]) == 12

@pytest.mark.asyncio
async def test_get_event_attendees_for_non_existent_event(client: AsyncClient):
    """
    Test getting attendees for an event that does not exist.
    """
    non_existent_event_id = 88888
    response = await client.get(f"/api/v1/events/{non_existent_event_id}/attendees")
    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response.json()["detail"] == "Event not found"
    