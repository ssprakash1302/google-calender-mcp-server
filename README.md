## Google Calendar Agent, API, and MCP Server

### Overview
This project provides a layered Google Calendar integration that you can use directly over HTTP or as MCP tools from agent frameworks.

- **Core agent (`calendar_agent.py`)**: Handles Google OAuth, Calendar API operations, and attendee email notifications.
- **FastAPI service (`calendar_service.py`)**: Exposes the agent as HTTP endpoints.
- **MCP server (`mcp_server_streamable.py`)**: Wraps the HTTP service as MCP tools over a streamable HTTP transport.

### Features
- List upcoming Google Calendar events
- Create events with optional Google Meet links and attendee invites
- Update events (title, time, attendees, description, Meet link)
- Delete events and notify attendees of cancellation
- Automatic attendee email notifications for create/update/delete (via SMTP)

## Architecture
1. `calendar_agent.py`
   - Initializes Google OAuth2 credentials, persists `token.json`, and builds the Calendar v3 client.
   - Implements operations: `list_upcoming_events`, `create_calendar_event`, `update_event`, `delete_event`.
   - Sends HTML emails to attendees via SMTP on create/update/delete.

2. `calendar_service.py`
   - FastAPI app that initializes a single `CalendarAgent` using the provided client secret file.
   - Endpoints map 1:1 to agent methods with Pydantic validation and clear error responses.
   - Runs by default on `http://127.0.0.1:5002`.

3. `mcp_server_streamable.py`
   - Async HTTP client calls the FastAPI service.
   - Registers MCP tools: `list_upcoming_events`, `create_calendar_event`, `update_event`, `delete_event`.
   - Runs an MCP server at `http://127.0.0.1:8001/calendar` (streamable-http transport).

## Requirements
- Python 3.10+
- Google Cloud project with Calendar API enabled
- OAuth 2.0 Client (Desktop) JSON downloaded locally (client secrets)

Python packages (from `requirements.txt` plus MCP deps):
- `google-api-python-client`, `google-auth-oauthlib`, `fastapi`, `uvicorn`
- `aiohttp`, `python-dotenv`, `fastmcp` (used by the MCP server)

Install:
```bash
pip install -r requirements.txt
pip install aiohttp python-dotenv fastmcp
```

## Setup
### 1) Google OAuth and Calendar API
1. Enable Google Calendar API in your Google Cloud project.
2. Create an OAuth Client ID (Desktop).
3. Download the client secret JSON and place it in the project root. Update `CREDENTIALS_FILE` in `calendar_service.py` if the filename is different.
4. On first run, a browser window will prompt you to authorize; `token.json` will be created automatically.

### 2) SMTP for attendee emails
The agent sends HTML emails to attendees using Gmail SMTP over SSL.

- Current configuration lives in `calendar_agent.py` as constants: `SMTP_USER`, `SMTP_PASS`, `SMTP_SERVER`, `SMTP_PORT`.
- For Gmail, use a 16‑character App Password. Avoid storing secrets in code for production.

Recommended: move these to environment variables and load them with `python-dotenv`.

Example `.env` (do not commit):
```bash
SMTP_USER=you@example.com
SMTP_PASS=your-app-password
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=465
CALENDAR_SERVICE_URL=http://127.0.0.1:5002
```

### 3) Project files to keep private
- `client_secret_*.json` (OAuth client)
- `token.json` (OAuth tokens)
- Any files with credentials

Add these to `.gitignore` before publishing a repo.

## Running Locally
### Start the FastAPI service
```bash
python calendar_service.py
```

- Default host/port: `http://127.0.0.1:5002`
- Uses the client secret file set in `calendar_service.py` as `CREDENTIALS_FILE`.

### Start the MCP server (optional)
In a separate terminal:
```bash
python mcp_server_streamable.py
```

- Default host/port/path: `http://127.0.0.1:8001/calendar`
- Points to the FastAPI service via `CALENDAR_SERVICE_URL` (defaults to `http://127.0.0.1:5002`).

## API Reference (FastAPI)
Base URL: `http://127.0.0.1:5002`

### GET `/events`
List up to 10 upcoming events ordered by start time.

Response (200):
```json
{
  "message": "Upcoming events retrieved successfully",
  "events": [
    {"id": "...", "summary": "...", "start": "2025-09-16T10:00:00Z"}
  ]
}
```

### POST `/schedule`
Create a new event. Set `add_meet_link` to `true` to add a Google Meet link.

Request body:
```json
{
  "summary": "Team Sync",
  "start_time": "2025-09-16T10:00:00-07:00",
  "end_time": "2025-09-16T10:30:00-07:00",
  "attendees": ["alice@example.com", "bob@example.com"],
  "description": "Weekly updates",
  "add_meet_link": true
}
```

Response (200):
```json
{
  "message": "Event created successfully",
  "event_link": "https://www.google.com/calendar/event?eid=...",
  "hangoutLink": "https://meet.google.com/..."  
}
```

Notes:
- The agent sets the timezone to `America/Los_Angeles` when creating/updating. Provide ISO 8601 datetime strings; adjust to your timezone as needed.
- If attendees are provided, the agent sends HTML email invitations.

### PUT `/event/update`
Update an existing event. At minimum, pass `event_id` and any fields you want to modify.

Request body (examples):
```json
{"event_id": "abc123", "summary": "New Title"}
```
```json
{"event_id": "abc123", "start_time": "2025-09-16T11:00:00-07:00", "end_time": "2025-09-16T11:30:00-07:00", "add_meet_link": true}
```

Response (200):
```json
{
  "message": "Event updated successfully",
  "event_link": "https://www.google.com/calendar/event?eid=...",
  "hangoutLink": "https://meet.google.com/..."
}
```

### DELETE `/event`
Delete an event by ID.

Request body:
```json
{"event_id": "abc123"}
```

Response (200):
```json
{"message": "Event with ID abc123 deleted successfully."}
```

Behavior:
- On delete, the agent sends cancellation emails to prior attendees (if any).

## MCP Tools
The MCP server exposes these tools backed by the HTTP API:

- `list_upcoming_events()` → returns upcoming events
- `create_calendar_event(summary, start_time, end_time, attendees?, description?, add_meet_link?)`
- `update_event(event_id, summary?, start_time?, end_time?, attendees?, description?, add_meet_link?)`
- `delete_event(event_id)`

Connection details:
- Transport: `streamable-http`
- Server: `http://127.0.0.1:8001`
- Path: `/calendar`

Set `CALENDAR_SERVICE_URL` if your FastAPI service is not on the default.

## Email Notification Details
- Emails are sent as HTML via SMTP over SSL.
- Create: invitation email to each attendee.
- Update: update notification to current attendees.
- Delete: cancellation email to previous attendees.

## Troubleshooting
- "agent not initialized": Ensure your client secret JSON path in `calendar_service.py` is correct and accessible.
- OAuth window not opening: Ensure you can open a browser window; otherwise use an alternative OAuth flow (`InstalledAppFlow.run_local_server`).
- 400/500 from API calls: Inspect the response message; common causes are invalid ISO timestamps, missing fields, or insufficient OAuth scopes.
- Emails not received: Verify SMTP credentials, app password, and check spam folders.

## Security and Production Hardening
- Do not hardcode SMTP credentials; load them from environment variables or a secret manager.
- Add `client_secret_*.json` and `token.json` to `.gitignore`.
- Rotate app passwords and restrict Google Cloud OAuth consent and scopes.
- Add input validation and rate limits at the API layer if exposed publicly.
- Use a service account and domain‑wide delegation if appropriate for organizational calendars.

## Project Structure
```text
local agent calender/
├── calendar_agent.py                # Core Google Calendar + email logic
├── calendar_service.py              # FastAPI HTTP service (port 5002)
├── mcp_server_streamable.py         # MCP server (port 8001, /calendar)
├── requirements.txt                 # Base dependencies
├── token.json                       # Generated after first OAuth (do not commit)
├── client_secret_*.json             # OAuth client (do not commit)
└── README.md                        # This file
```
