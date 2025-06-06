from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from app.routers import events
from app.database import create_tables, engine, SessionLocal # Added SessionLocal
from contextlib import asynccontextmanager
from app.services.event_service import EventService # Added
from app.services.attendee_service import AttendeeService # Added
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting up...")
    logger.info("Creating database tables...") 
    
    await create_tables()
    logger.info("Database tables created.") 
    yield
    logger.info("Shutting down...")
    await engine.dispose()
    logger.info("Database engine disposed.")
 
app = FastAPI(
    lifespan=lifespan,
    title="Mini Event Management System API",
    description="API for managing events and attendees, with timezone support and pagination.",
    version="0.1.0", 
    docs_url="/docs",  # Customize Swagger UI URL
    redoc_url="/redoc" # Customize ReDoc URL
)

# Dependency injection for services
def get_event_service():
    return EventService()

def get_attendee_service():
    return AttendeeService()

app.dependency_overrides[EventService] = get_event_service
app.dependency_overrides[AttendeeService] = get_attendee_service


# Custom exception handler for validation errors
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={"detail": exc.errors(), "body": exc.body},
    )

# Include routers
app.include_router(events.router, prefix="/api/v1") # Added prefix for versioning

@app.get("/", tags=["Root"])
async def read_root():
    return {"message": "Welcome to the Mini Event Management System API!"}

if __name__ == "__main__":
    import uvicorn
    # Ensure the app is run with the correct reload and app string for Uvicorn
    # Example: uvicorn main:app --reload
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
    