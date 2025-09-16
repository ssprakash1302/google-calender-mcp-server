from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
import uvicorn
import os

from calendar_agent import CalendarAgent

# Initialize FastAPI app
app = FastAPI(
    title="Google Calendar Service",
    description="HTTP API wrapper for Google Calendar agent",
    version="1.0.0"
)

# Initialize the calendar agent
# Use the exact filename for your client secret
CREDENTIALS_FILE = "client_secret_967453579177-m12llc81j87fa3dhjb1uphcit2dfkq33.apps.googleusercontent.com.json"

try:
    agent = CalendarAgent(credentials_file=CREDENTIALS_FILE)
    print("Calendar Agent initialized successfully")
except Exception as e:
    print(f"Failed to initialize Calendar Agent: {str(e)}")
    agent = None

# Pydantic models for request validation
class CreateEventRequest(BaseModel):
    summary: str
    start_time: str
    end_time: str
    attendees: Optional[List[str]] = None
    description: Optional[str] = None
    add_meet_link: Optional[bool] = False

class DeleteEventRequest(BaseModel):
    event_id: str

class UpdateEventRequest(BaseModel):
    event_id: str
    summary: Optional[str] = None
    start_time: Optional[str] = None
    end_time: Optional[str] = None
    attendees: Optional[List[str]] = None
    description: Optional[str] = None
    add_meet_link: Optional[bool] = False

# Health check endpoint
@app.get("/")
async def root():
    return {
        "service": "Google Calendar Service",
        "status": "running",
        "agent_loaded": agent is not None
    }

@app.get("/health")
async def health_check():
    return {
        "status": "healthy" if agent is not None else "unhealthy",
        "agent_status": "loaded" if agent is not None else "not loaded"
    }

# Main calendar endpoints
@app.get("/events")
async def list_events() -> Dict[str, Any]:
    """List upcoming Google Calendar events"""
    if agent is None:
        raise HTTPException(status_code=500, detail="Calendar agent not initialized")
    
    result = agent.list_upcoming_events()
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    return result

@app.post("/schedule")
async def schedule_event(request: CreateEventRequest) -> Dict[str, Any]:
    """Schedule a new Google Calendar event. Set add_meet_link=True to add a Google Meet link."""
    if agent is None:
        raise HTTPException(status_code=500, detail="Calendar agent not initialized")
    
    try:
        result = agent.create_calendar_event(
            request.summary,
            request.start_time,
            request.end_time,
            request.attendees,
            request.description,
            request.add_meet_link
        )
        if "error" in result:
            raise HTTPException(status_code=400, detail=result["error"])
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to schedule event: {str(e)}")

@app.delete("/event")
async def delete_event(request: DeleteEventRequest) -> Dict[str, Any]:
    """Delete a Google Calendar event by event ID"""
    if agent is None:
        raise HTTPException(status_code=500, detail="Calendar agent not initialized")
    result = agent.delete_event(request.event_id)
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    return result

@app.put("/event/update")
async def update_event(request: UpdateEventRequest) -> Dict[str, Any]:
    """Update a Google Calendar event by event ID. Set add_meet_link=True to add a Google Meet link."""
    if agent is None:
        raise HTTPException(status_code=500, detail="Calendar agent not initialized")
    result = agent.update_event(
        event_id=request.event_id,
        summary=request.summary,
        start_time=request.start_time,
        end_time=request.end_time,
        attendees=request.attendees,
        description=request.description,
        add_meet_link=request.add_meet_link
    )
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    return result

if __name__ == "__main__":
    print(f"Starting Google Calendar Service...")
    print(f"Using credentials file: {CREDENTIALS_FILE}")
    uvicorn.run(
        "calendar_service:app",
        host="127.0.0.1",
        port=5002, # Using a different port to avoid conflict with sentiment service
        log_level="info",
        reload=True,
        workers=1,
        loop="asyncio",
        timeout_keep_alive=30
    ) 