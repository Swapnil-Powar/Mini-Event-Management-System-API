# Mini Event Management System API

## Objective
This project implements a backend API for a simplified Event Management System. So, the users can create events, register attendees for events, and view attendee lists per event, focusing on clean architecture, scalability, data integrity, and timezone management.

## Features
- Create new events with details like name, location, start/end times, and capacity.
- List all upcoming events, with times convertible to a client-specified timezone.
- Register attendees for specific events, preventing overbooking and duplicate registrations.
- List all registered attendees for an event, with support for pagination.
- Timezone-aware event times: Events can be created specifying a timezone (defaults to IST if naive), are stored in UTC, and can be retrieved in a client-specified timezone.
- Automatic API documentation via Swagger UI and ReDoc. 

## Tech Stack 
- Python 3.10+
- FastAPI: For building the asynchronous API.
- Uvicorn: ASGI server for FastAPI.
- SQLAlchemy: For ORM and asynchronous database interaction. 
- `aiosqlite`: Async driver for SQLite.
- Pydantic: For data validation and settings management.
- `python-dateutil` & `pytz`: For robust timezone handling.
- Pytest: For running automated tests.
- HTTPX: For asynchronous HTTP requests in tests.

## Project Structure
```
.
├── app/                  # Core application module
│   ├── __init__.py
│   ├── database.py       # Database setup, engine, session
│   ├── models.py         # SQLAlchemy ORM models (Event, Attendee)
│   ├── schemas.py        # Pydantic schemas for request/response validation
│   ├── routers/          # API routers (endpoints)
│   │   ├── __init__.py
│   │   └── events.py     # Router for event and attendee operations
│   └── services/         # Business logic services
│       ├── __init__.py
│       ├── attendee_service.py
│       └── event_service.py
├── tests/                # Automated tests
│   ├── __init__.py
│   ├── conftest.py       # Pytest fixtures and test setup
│   └── test_events.py    # Tests for the event and attendee APIs
├── main.py               # FastAPI application entry point
├── requirements.txt      # Project dependencies
├── test.db               # SQLite database file for the application (auto-created)
└── README.md             # This file
```

## Setup Instructions

### Prerequisites
- Python 3.10 or higher.
- `pip` for package installation.

### Installation
1.  **Create and activate a virtual environment:**
    ```bash
    python -m venv venv
    # On Windows
    venv\Scripts\activate
    ```

2.  **Install dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

### Database Setup
We are using SQLite for this application. The database file (`test.db` for the main application and `test_db.sqlite` for tests) will be automatically created in the project root directory when the application or tests are first run. No manual database setup is required.

### Running the Application
To start the development server:
```bash
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```
The API will be accessible at `http://localhost:8000`.
- Swagger UI documentation: `http://localhost:8000/docs`
- ReDoc documentation: `http://localhost:8000/redoc`

### Running Tests
To run the automated tests:
```bash
pytest
```

## API Endpoints Documentation

All API endpoints are prefixed with `/api/v1`.

---

### 1. Create a New Event
-   **Endpoint:** `POST /api/v1/events/`
-   **Description:** Creates a new event. Input `start_time` and `end_time` should be ISO 8601 formatted strings. If they are naive (no timezone offset), they are assumed to be in 'Asia/Kolkata' (IST). They are stored in UTC.
-   **Request Body:**
    ```json
    {
        "name": "Annual Tech Summit",
        "location": "Conference Center Hall A",
        "start_time": "2025-12-01T09:00:00+05:30",
        "end_time": "2025-12-01T17:00:00+05:30",
        "max_capacity": 300
    }
    ```
-   **Sample cURL Request:**
    ```bash
    curl -X POST "http://localhost:8000/api/v1/events/" \
    -H "Content-Type: application/json" \
    -d '{
        "name": "Annual Tech Summit",
        "location": "Conference Center Hall A",
        "start_time": "2025-12-01T09:00:00+05:30",
        "end_time": "2025-12-01T17:00:00+05:30",
        "max_capacity": 300
    }'
    ```
-   **Successful Response (201 Created):**
    ```json
    {
        "name": "Annual Tech Summit",
        "location": "Conference Center Hall A",
        "start_time": "2025-12-01T03:30:00+00:00", // Stored and returned in UTC by default from this endpoint
        "end_time": "2025-12-01T11:30:00+00:00",   // Stored and returned in UTC
        "max_capacity": 300,
        "id": 1
    }
    ```
-   **Error Responses:**
    -   `422 Unprocessable Entity`: If validation fails (e.g., missing fields, invalid date format, end_time before start_time).
        ```json
        {
            "detail": [
                {
                    "loc": ["body", "end_time"],
                    "msg": "End time must be after start time",
                    "type": "value_error"
                }
            ]
        }
        ```

---

### 2. List All Upcoming Events
-   **Endpoint:** `GET /api/v1/events/`
-   **Description:** Lists all upcoming events (events whose `end_time` is in the future). Event times are converted to the timezone specified in the `X-Timezone` header (defaults to "UTC").
-   **Query Parameters:**
    -   `skip` (int, optional, default: 0): Number of events to skip for pagination.
    -   `limit` (int, optional, default: 10): Maximum number of events to return.
-   **Headers:**
    -   `X-Timezone` (string, optional, default: "UTC"): Target timezone for event times in the response (e.g., "America/New_York", "Asia/Kolkata").
-   **Sample cURL Request (requesting times in EST):**
    ```bash
    curl -X GET "http://localhost:8000/api/v1/events/?skip=0&limit=5" \
    -H "X-Timezone: America/New_York"
    ```
-   **Successful Response (200 OK):**
    ```json
    [
        {
            "name": "Annual Tech Summit",
            "location": "Conference Center Hall A",
            "start_time": "2025-11-30T22:30:00-05:00", // Example: Converted to EST
            "end_time": "2025-12-01T06:30:00-05:00",   // Example: Converted to EST
            "max_capacity": 300,
            "id": 1
        }
        // ... other events
    ]
    ```
-   **Error Responses:**
    -   `400 Bad Request`: If `X-Timezone` header is invalid.
        ```json
        {
            "detail": "Invalid X-Timezone header value."
        }
        ```

---

### 3. Register an Attendee for an Event
-   **Endpoint:** `POST /api/v1/events/{event_id}/register`
-   **Description:** Registers an attendee for a specific event. Prevents overbooking and duplicate registrations (same email for the same event).
-   **Path Parameters:**
    -   `event_id` (int): The ID of the event.
-   **Request Body:**
    ```json
    {
        "name": "John Doe",
        "email": "john.doe@example.com"
    }
    ```
-   **Sample cURL Request:**
    ```bash
    curl -X POST "http://localhost:8000/api/v1/events/1/register" \
    -H "Content-Type: application/json" \
    -d '{
        "name": "John Doe",
        "email": "john.doe@example.com"
    }'
    ```
-   **Successful Response (201 Created):**
    ```json
    {
        "name": "John Doe",
        "email": "john.doe@example.com",
        "id": 1,
        "event_id": 1
    }
    ```
-   **Error Responses:**
    -   `404 Not Found`: If the `event_id` does not exist.
        ```json
        { "detail": "Event not found" }
        ```
    -   `400 Bad Request`:
        -   If the event is at full capacity: `{ "detail": "Event is at full capacity" }`
        -   If the email is already registered for this event: `{ "detail": "Attendee with this email already registered for this event" }`
    -   `422 Unprocessable Entity`: If request body validation fails (e.g., invalid email format).

---

### 4. Get Attendees for an Event
-   **Endpoint:** `GET /api/v1/events/{event_id}/attendees`
-   **Description:** Returns a paginated list of all registered attendees for a specific event.
-   **Path Parameters:**
    -   `event_id` (int): The ID of the event.
-   **Query Parameters:**
    -   `page` (int, optional, default: 1, min: 1): Page number for pagination.
    -   `size` (int, optional, default: 10, min: 1, max: 100): Number of items per page.
-   **Sample cURL Request:**
    ```bash
    curl -X GET "http://localhost:8000/api/v1/events/1/attendees?page=1&size=5"
    ```
-   **Successful Response (200 OK):**
    ```json
    {
        "total": 50,    // Total number of attendees for the event
        "page": 1,
        "size": 5,
        "pages": 10,    // Total number of pages
        "items": [
            {
                "name": "John Doe",
                "email": "john.doe@example.com",
                "id": 1,
                "event_id": 1
            }
            // ... other attendees on this page
        ]
    }
    ```
-   **Error Responses:**
    -   `404 Not Found`: If the `event_id` does not exist.
        ```json
        { "detail": "Event not found" }
        ```

## Assumptions
-   **Event Time Input:** When creating an event, if `start_time` or `end_time` are provided as ISO 8601 strings without a timezone offset, they are assumed to be in the 'Asia/Kolkata' (IST) timezone. The Pydantic schema validator handles this.
-   **Storage Timezone:** The database converts all event `start_time` and `end_time` values to and stores them in UTC.
-   **Event Listing Timezone:** The `GET /api/v1/events/` endpoint defaults to returning event times in UTC if the `X-Timezone` header is not provided.
-   **Database:** SQLite is used for simplicity. The database file `test.db` is created automatically.
-   **Upcoming Events:** An event is considered "upcoming" if its `end_time` (in UTC) is after the current UTC.

## Database Schema
The database schema is defined by SQLAlchemy models in `app/models.py` and created automatically when the application starts.

### `events` table:
-   `id` (Integer, Primary Key)
-   `name` (String, Not Null)
-   `location` (String, Not Null)
-   `start_time` (DateTime with Timezone, Not Null) - Stored in UTC
-   `end_time` (DateTime with Timezone, Not Null) - Stored in UTC
-   `max_capacity` (Integer, Not Null)

### `attendees` table:
-   `id` (Integer, Primary Key)
-   `name` (String, Not Null)
-   `email` (String, Not Null, Indexed)
-   `event_id` (Integer, Foreign Key to `events.id`, Not Null)
-   **Unique Constraint:** (`email`, `event_id`) - an email can only register once per event.

## Bonus Features Implemented
-   **Pagination:** Implemented for the `GET /events/{event_id}/attendees` endpoint.
-   **Unit Tests:** Comprehensive unit and integration tests are written using `pytest` and `HTTPX`. They cover various scenarios, including edge cases and timezone conversions. They are located in the `tests/` directory.
-   **Swagger Documentation:** Automatically generated by FastAPI and available at:
    -   Swagger UI: `/docs`
    -   ReDoc: `/redoc`
    The API endpoints in `app/routers/events.py` include docstrings that enhance this documentation.
