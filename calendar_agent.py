import datetime
import os.path
import smtplib
from email.mime.text import MIMEText
from typing import Any, Dict, List, Optional

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

SCOPES = ["https://www.googleapis.com/auth/calendar"]

# SMTP configuration (replace with your credentials or use environment variables)
SMTP_USER = "testevank@gmail.com"
SMTP_PASS = "wsjl encp iocm yrav"  # The 16-character app password
SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 465

class CalendarAgent:
    def __init__(self, credentials_file: str = "credentials.json"):
        self.credentials_file = credentials_file
        self.service = self._get_google_calendar_service()

    def _get_google_calendar_service(self):
        creds = None
        if os.path.exists("token.json"):
            creds = Credentials.from_authorized_user_file("token.json", SCOPES)
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file(
                    self.credentials_file, SCOPES
                )
                creds = flow.run_local_server(port=0)
            with open("token.json", "w") as token:
                token.write(creds.to_json())

        try:
            service = build("calendar", "v3", credentials=creds)
            return service
        except HttpError as error:
            print(f"An error occurred: {error}")
            return None

    def list_upcoming_events(self) -> Dict[str, Any]:
        if not self.service:
            return {"error": "Google Calendar service not available"}
        
        try:
            now = datetime.datetime.utcnow().isoformat() + "Z"
            events_result = (
                self.service.events()
                .list(
                    calendarId="primary",
                    timeMin=now,
                    maxResults=10,
                    singleEvents=True,
                    orderBy="startTime",
                )
                .execute()
            )
            events = events_result.get("items", [])

            if not events:
                return {"message": "No upcoming events found.", "events": []}

            events_list = []
            for event in events:
                start = event["start"].get("dateTime", event["start"].get("date"))
                events_list.append({
                    "id": event["id"],
                    "summary": event["summary"],
                    "start": start
                })
            return {"message": "Upcoming events retrieved successfully", "events": events_list}

        except HttpError as error:
            return {"error": f"An error occurred: {error}"}

    def _send_meeting_email(self, to_email: str, subject: str, body: str):
        msg = MIMEText(body, "html")
        msg["Subject"] = subject
        msg["From"] = SMTP_USER
        msg["To"] = to_email
        with smtplib.SMTP_SSL(SMTP_SERVER, SMTP_PORT) as server:
            server.login(SMTP_USER, SMTP_PASS)
            server.sendmail(SMTP_USER, [to_email], msg.as_string())

    def create_calendar_event(self, summary: str, start_time: str, end_time: str, attendees: Optional[List[str]] = None, description: Optional[str] = None, add_meet_link: bool = False) -> Dict[str, Any]:
        if not self.service:
            return {"error": "Google Calendar service not available"}

        event = {
            'summary': summary,
            'description': description,
            'start': {
                'dateTime': start_time,
                'timeZone': 'America/Los_Angeles',
            },
            'end': {
                'dateTime': end_time,
                'timeZone': 'America/Los_Angeles',
            },
            'reminders': {
                'useDefault': False,
                'overrides': [
                    {'method': 'email', 'minutes': 24 * 60},
                    {'method': 'popup', 'minutes': 10},
                ],
            },
        }

        if attendees:
            event['attendees'] = [{'email': email} for email in attendees]
        if add_meet_link:
            event['conferenceData'] = {
                "createRequest": {
                    "requestId": f"meet-{datetime.datetime.utcnow().timestamp()}"
                }
            }
        try:
            event_result = self.service.events().insert(
                calendarId='primary',
                body=event,
                conferenceDataVersion=1 if add_meet_link else 0
            ).execute()
            response = {"message": "Event created successfully", "event_link": event_result.get('htmlLink')}
            meet_link = None
            if add_meet_link and 'conferenceData' in event_result and 'entryPoints' in event_result['conferenceData']:
                for ep in event_result['conferenceData']['entryPoints']:
                    if ep.get('entryPointType') == 'video':
                        meet_link = ep.get('uri')
                        response['hangoutLink'] = meet_link
            # Automatically send email to attendees
            if attendees:
                email_subject = f"Invitation: {summary}"
                email_body = f"""
                <h3>{summary}</h3>
                <p><b>Description:</b> {description or ''}</p>
                <p><b>Start:</b> {start_time}</p>
                <p><b>End:</b> {end_time}</p>
                {f'<p><b>Google Meet Link:</b> <a href="{meet_link}">{meet_link}</a></p>' if meet_link else ''}
                <p>Event Link: <a href='{event_result.get('htmlLink')}'>{event_result.get('htmlLink')}</a></p>
                """
                for attendee in attendees:
                    self._send_meeting_email(attendee, email_subject, email_body)
            return response
        except HttpError as error:
            return {"error": f"An error occurred: {error}"}

    def delete_event(self, event_id: str) -> Dict[str, Any]:
        """Delete an event from the primary calendar by event ID."""
        if not self.service:
            return {"error": "Google Calendar service not available"}
        try:
            # Fetch event details before deletion to notify attendees
            event = self.service.events().get(calendarId='primary', eventId=event_id).execute()
            attendees = [a['email'] for a in event.get('attendees', [])] if 'attendees' in event else []
            summary = event.get('summary', 'Meeting')
            start_time = event['start'].get('dateTime', event['start'].get('date', ''))
            end_time = event['end'].get('dateTime', event['end'].get('date', ''))
            description = event.get('description', '')
            # Send cancellation email
            if attendees:
                email_subject = f"CANCELLED: {summary}"
                email_body = f"""
                <h3>Meeting Cancelled: {summary}</h3>
                <p><b>Description:</b> {description or ''}</p>
                <p><b>Start:</b> {start_time}</p>
                <p><b>End:</b> {end_time}</p>
                <p>This meeting has been cancelled.</p>
                """
                for attendee in attendees:
                    self._send_meeting_email(attendee, email_subject, email_body)
            self.service.events().delete(calendarId='primary', eventId=event_id).execute()
            return {"message": f"Event with ID {event_id} deleted successfully."}
        except HttpError as error:
            return {"error": f"An error occurred: {error}"}

    def update_event(self, event_id: str, summary: Optional[str] = None, start_time: Optional[str] = None, end_time: Optional[str] = None, attendees: Optional[List[str]] = None, description: Optional[str] = None, add_meet_link: bool = False) -> Dict[str, Any]:
        """Update an event in the primary calendar by event ID."""
        if not self.service:
            return {"error": "Google Calendar service not available"}
        try:
            event = self.service.events().get(calendarId='primary', eventId=event_id).execute()
            if summary is not None:
                event['summary'] = summary
            if description is not None:
                event['description'] = description
            if start_time is not None:
                event['start']['dateTime'] = start_time
            if end_time is not None:
                event['end']['dateTime'] = end_time
            if attendees is not None:
                event['attendees'] = [{'email': email} for email in attendees]
            if add_meet_link:
                event['conferenceData'] = {
                    "createRequest": {
                        "requestId": f"meet-update-{datetime.datetime.utcnow().timestamp()}"
                    }
                }
            updated_event = self.service.events().update(
                calendarId='primary',
                eventId=event_id,
                body=event,
                conferenceDataVersion=1 if add_meet_link else 0
            ).execute()
            response = {"message": "Event updated successfully", "event_link": updated_event.get('htmlLink')}
            meet_link = None
            if add_meet_link and 'conferenceData' in updated_event and 'entryPoints' in updated_event['conferenceData']:
                for ep in updated_event['conferenceData']['entryPoints']:
                    if ep.get('entryPointType') == 'video':
                        meet_link = ep.get('uri')
                        response['hangoutLink'] = meet_link
            # Send update email to attendees
            attendees_list = [a['email'] for a in updated_event.get('attendees', [])] if 'attendees' in updated_event else []
            if attendees_list:
                email_subject = f"UPDATED: {updated_event.get('summary', 'Meeting')}"
                email_body = f"""
                <h3>Meeting Updated: {updated_event.get('summary', '')}</h3>
                <p><b>Description:</b> {updated_event.get('description', '')}</p>
                <p><b>Start:</b> {updated_event['start'].get('dateTime', updated_event['start'].get('date', ''))}</p>
                <p><b>End:</b> {updated_event['end'].get('dateTime', updated_event['end'].get('date', ''))}</p>
                {f'<p><b>Google Meet Link:</b> <a href="{meet_link}">{meet_link}</a></p>' if meet_link else ''}
                <p>Event Link: <a href='{updated_event.get('htmlLink')}'>{updated_event.get('htmlLink')}</a></p>
                """
                for attendee in attendees_list:
                    self._send_meeting_email(attendee, email_subject, email_body)
            return response
        except HttpError as error:
            return {"error": f"An error occurred: {error}"} 