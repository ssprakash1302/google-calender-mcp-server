#!/usr/bin/env python3
"""
MCP Server for Google Calendar with Streamable HTTP Transport

This server provides Google Calendar integration capabilities through MCP (Model Context Protocol)
using FastMCP with streamable HTTP transport. It communicates with the Google Calendar HTTP service
to provide event listing and scheduling functionality.
"""

import json
import logging
import os
from typing import Any, Dict, List, Optional
import aiohttp
from urllib.parse import urljoin
from fastmcp import FastMCP
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("calendar_mcp_server_streamable")

# Calendar service configuration
CALENDAR_SERVICE_URL = os.getenv('CALENDAR_SERVICE_URL', 'http://127.0.0.1:5002')

# Initialize FastMCP server
mcp = FastMCP("google-calendar-server")

class CalendarServiceClient:
    def __init__(self, base_url: str):
        self.base_url = base_url
        self.session = None
    
    async def ensure_session(self):
        if self.session is None:
            self.session = aiohttp.ClientSession()
    
    async def close(self):
        if self.session:
            await self.session.close()
            self.session = None
    
    async def list_upcoming_events(self) -> Dict[str, Any]:
        await self.ensure_session()
        async with self.session.get(
            urljoin(self.base_url, "/events")
        ) as response:
            if response.status != 200:
                error_text = await response.text()
                raise RuntimeError(f"HTTP {response.status}: {error_text}")
            return await response.json()
    
    async def create_calendar_event(
        self, 
        summary: str, 
        start_time: str, 
        end_time: str, 
        attendees: Optional[List[str]] = None, 
        description: Optional[str] = None,
        add_meet_link: Optional[bool] = False
    ) -> Dict[str, Any]:
        await self.ensure_session()
        payload = {
            "summary": summary,
            "start_time": start_time,
            "end_time": end_time
        }
        if attendees:
            payload["attendees"] = attendees
        if description:
            payload["description"] = description
        if add_meet_link:
            payload["add_meet_link"] = add_meet_link
        async with self.session.post(
            urljoin(self.base_url, "/schedule"),
            json=payload
        ) as response:
            if response.status != 200:
                error_text = await response.text()
                raise RuntimeError(f"HTTP {response.status}: {error_text}")
            return await response.json()

    async def delete_event(self, event_id: str) -> Dict[str, Any]:
        await self.ensure_session()
        payload = {"event_id": event_id}
        async with self.session.delete(
            urljoin(self.base_url, "/event"),
            json=payload
        ) as response:
            if response.status != 200:
                error_text = await response.text()
                raise RuntimeError(f"HTTP {response.status}: {error_text}")
            return await response.json()

    async def update_event(self, event_id: str, summary: Optional[str] = None, start_time: Optional[str] = None, end_time: Optional[str] = None, attendees: Optional[List[str]] = None, description: Optional[str] = None, add_meet_link: Optional[bool] = False) -> Dict[str, Any]:
        await self.ensure_session()
        payload = {"event_id": event_id}
        if summary is not None:
            payload["summary"] = summary
        if start_time is not None:
            payload["start_time"] = start_time
        if end_time is not None:
            payload["end_time"] = end_time
        if attendees is not None:
            payload["attendees"] = attendees
        if description is not None:
            payload["description"] = description
        if add_meet_link:
            payload["add_meet_link"] = add_meet_link
        async with self.session.put(
            urljoin(self.base_url, "/event/update"),
            json=payload
        ) as response:
            if response.status != 200:
                error_text = await response.text()
                raise RuntimeError(f"HTTP {response.status}: {error_text}")
            return await response.json()

# Initialize the calendar service client
calendar_client = CalendarServiceClient(CALENDAR_SERVICE_URL)

@mcp.tool()
async def list_upcoming_events() -> Dict[str, Any]:
    """List upcoming Google Calendar events."""
    try:
        result = await calendar_client.list_upcoming_events()
        return result
    except Exception as e:
        logger.error(f"Error in list_upcoming_events: {e}")
        return {"error": str(e)}

@mcp.tool()
async def create_calendar_event(
    summary: str,
    start_time: str,
    end_time: str,
    attendees: Optional[List[str]] = None,
    description: Optional[str] = None,
    add_meet_link: Optional[bool] = False
) -> Dict[str, Any]:
    """Schedule a new Google Calendar event.
    Args:
        summary: The title of the event.
        start_time: The start date and time in ISO 8601 format.
        end_time: The end date and time in ISO 8601 format.
        attendees: Optional list of email addresses for attendees.
        description: Optional description for the event.
        add_meet_link: Optional boolean to add a Google Meet link.
    Returns:
        A dictionary containing the event creation status and link.
    """
    try:
        result = await calendar_client.create_calendar_event(
            summary,
            start_time,
            end_time,
            attendees,
            description,
            add_meet_link
        )
        return result
    except Exception as e:
        logger.error(f"Error in create_calendar_event: {e}")
        return {"error": str(e)}

@mcp.tool()
async def delete_event(event_id: str) -> Dict[str, Any]:
    """Delete a Google Calendar event by event ID.
    Args:
        event_id: The ID of the event to delete.
    Returns:
        A dictionary containing the deletion status.
    """
    try:
        result = await calendar_client.delete_event(event_id)
        return result
    except Exception as e:
        logger.error(f"Error in delete_event: {e}")
        return {"error": str(e)}

@mcp.tool()
async def update_event(
    event_id: str,
    summary: Optional[str] = None,
    start_time: Optional[str] = None,
    end_time: Optional[str] = None,
    attendees: Optional[List[str]] = None,
    description: Optional[str] = None,
    add_meet_link: Optional[bool] = False
) -> Dict[str, Any]:
    """Update a Google Calendar event by event ID.
    Args:
        event_id: The ID of the event to update.
        summary: (Optional) New summary/title.
        start_time: (Optional) New start time (ISO 8601).
        end_time: (Optional) New end time (ISO 8601).
        attendees: (Optional) New list of attendees.
        description: (Optional) New description.
        add_meet_link: Optional boolean to add a Google Meet link.
    Returns:
        A dictionary containing the update status and event link.
    """
    try:
        result = await calendar_client.update_event(
            event_id,
            summary,
            start_time,
            end_time,
            attendees,
            description,
            add_meet_link
        )
        return result
    except Exception as e:
        logger.error(f"Error in update_event: {e}")
        return {"error": str(e)}

if __name__ == "__main__":
    logger.info(f"Starting Google Calendar MCP Server with streamable HTTP transport...")
    logger.info(f"Connecting to calendar service at {CALENDAR_SERVICE_URL}")
    try:
        mcp.run(
            transport="streamable-http",
            host="127.0.0.1",
            port=8001,
            path="/calendar"
        )
    except KeyboardInterrupt:
        logger.info("Server shutting down...")
    except Exception as e:
        logger.error(f"Server error: {e}")
        raise
    finally:
        import asyncio
        asyncio.run(calendar_client.close()) 