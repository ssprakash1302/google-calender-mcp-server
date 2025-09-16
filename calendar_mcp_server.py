#!/usr/bin/env python3
"""
MCP Server for Google Calendar

This server provides Google Calendar integration capabilities through MCP (Model Context Protocol).
It communicates with the Google Calendar HTTP service to provide event listing and scheduling functionality.
"""

import asyncio
import json
import sys
from typing import Any, Dict, List, Optional, Sequence
import logging
from pathlib import Path
import os
import aiohttp
from urllib.parse import urljoin
import base64

# MCP imports
from mcp.server import Server
from mcp.server.models import InitializationOptions
import mcp.server.stdio
import mcp.types as types

# Add the current directory to Python path to import our modules
current_dir = Path(__file__).parent
sys.path.insert(0, str(current_dir))

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("calendar_mcp_server")

# Calendar service configuration
CALENDAR_SERVICE_URL = "http://127.0.0.1:5002"

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

# Create MCP server
server = Server("google-calendar-server")

@server.list_tools()
async def handle_list_tools() -> List[types.Tool]:
    """List available Google Calendar tools"""
    tools = [
        types.Tool(
            name="list_upcoming_events",
            description="List upcoming Google Calendar events.",
            inputSchema={
                "type": "object",
                "properties": {}
            }
        ),
        types.Tool(
            name="create_calendar_event",
            description="Schedule a new Google Calendar event.\n\nArgs:\n    summary: The title of the event.\n    start_time: The start date and time in ISO 8601 format (e.g., '2024-08-01T10:00:00-07:00').\n    end_time: The end date and time in ISO 8601 format (e.g., '2024-08-01T11:00:00-07:00').\n    attendees: Optional list of email addresses for attendees.\n    description: Optional description for the event.\n    add_meet_link: Optional boolean to add a Google Meet link.\n\nReturns:\n    A dictionary containing the event creation status and link.",
            inputSchema={
                "type": "object",
                "properties": {
                    "summary": {"type": "string"},
                    "start_time": {"type": "string"},
                    "end_time": {"type": "string"},
                    "attendees": {"type": "array", "items": {"type": "string"}, "nullable": True},
                    "description": {"type": "string", "nullable": True},
                    "add_meet_link": {"type": "boolean", "nullable": True}
                },
                "required": ["summary", "start_time", "end_time"]
            }
        ),
        types.Tool(
            name="delete_event",
            description="Delete a Google Calendar event by event ID.\n\nArgs:\n    event_id: The ID of the event to delete.\n\nReturns:\n    A dictionary containing the deletion status.",
            inputSchema={
                "type": "object",
                "properties": {
                    "event_id": {"type": "string"}
                },
                "required": ["event_id"]
            }
        ),
        types.Tool(
            name="update_event",
            description="Update a Google Calendar event by event ID.\n\nArgs:\n    event_id: The ID of the event to update.\n    summary: (Optional) New summary/title.\n    start_time: (Optional) New start time (ISO 8601).\n    end_time: (Optional) New end time (ISO 8601).\n    attendees: (Optional) New list of attendees.\n    description: (Optional) New description.\n    add_meet_link: Optional boolean to add a Google Meet link.\n\nReturns:\n    A dictionary containing the update status and event link.",
            inputSchema={
                "type": "object",
                "properties": {
                    "event_id": {"type": "string"},
                    "summary": {"type": "string", "nullable": True},
                    "start_time": {"type": "string", "nullable": True},
                    "end_time": {"type": "string", "nullable": True},
                    "attendees": {"type": "array", "items": {"type": "string"}, "nullable": True},
                    "description": {"type": "string", "nullable": True},
                    "add_meet_link": {"type": "boolean", "nullable": True}
                },
                "required": ["event_id"]
            }
        )
    ]
    
    return tools

@server.call_tool()
async def handle_call_tool(name: str, arguments: dict) -> Sequence[types.TextContent]:
    """Handle tool calls by forwarding to the calendar service"""
    try:
        if name == "list_upcoming_events":
            result = await calendar_client.list_upcoming_events()
        elif name == "create_calendar_event":
            result = await calendar_client.create_calendar_event(
                arguments["summary"],
                arguments["start_time"],
                arguments["end_time"],
                arguments.get("attendees"),
                arguments.get("description"),
                arguments.get("add_meet_link", False)
            )
        elif name == "delete_event":
            result = await calendar_client.delete_event(arguments["event_id"])
        elif name == "update_event":
            result = await calendar_client.update_event(
                arguments["event_id"],
                arguments.get("summary"),
                arguments.get("start_time"),
                arguments.get("end_time"),
                arguments.get("attendees"),
                arguments.get("description"),
                arguments.get("add_meet_link", False)
            )
        else:
            raise ValueError(f"Unknown tool: {name}")
        
        # Return the result as formatted JSON text
        return [
            types.TextContent(
                type="text",
                text=json.dumps(result, indent=2, default=str)
            )
        ]
        
    except Exception as e:
        logger.error(f"Error calling tool {name}: {e}")
        raise RuntimeError(str(e))

async def main():
    """Main function to run the MCP server"""
    logger.info("Starting Google Calendar MCP Server...")
    logger.info(f"Connecting to calendar service at {CALENDAR_SERVICE_URL}")
    
    try:
        # Run the server using stdio transport
        async with mcp.server.stdio.stdio_server() as (read_stream, write_stream):
            await server.run(
                read_stream, 
                write_stream, 
                InitializationOptions(
                    server_name="google-calendar-server",
                    server_version="1.0.0",
                    capabilities={
                        "tools": {
                            "enabled": True,
                            "supported_tools": [
                                "list_upcoming_events", 
                                "create_calendar_event",
                                "delete_event",
                                "update_event"
                            ]
                        },
                        "streaming": False
                    }
                )
            )
    except KeyboardInterrupt:
        logger.info("Server shutting down...")
    except Exception as e:
        logger.error(f"Server error: {e}")
        raise
    finally:
        # Clean up the HTTP client session
        await calendar_client.close()

if __name__ == "__main__":
    asyncio.run(main()) 