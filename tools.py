import os
import requests
import pypdf
import imaplib
import smtplib
import email
import os.path
import subprocess
import json
import shlex
import webbrowser
import sys
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.header import decode_header
from datetime import datetime
from bs4 import BeautifulSoup
from pydantic import BaseModel, Field
from langchain_core.tools import tool
from langchain_tavily import TavilySearch
from dotenv import load_dotenv
load_dotenv()
from typing import Union

class SearchSchema(BaseModel):
    query: str = Field(description="The exact search query to type on the Internet")

tavily_client = TavilySearch(max_results=3)

@tool(args_schema=SearchSchema)
def internet_search(query: str) -> str:
    """Tool to search for recent information on the Internet."""
    return tavily_client.invoke({"query": query, "topic": "general"})

class WriteFileSchema(BaseModel):
    filename: str = Field(description="The name of the file to write to (e.g., 'notes.txt')")
    content: str = Field(description="The exact text content to write inside the file")

@tool(args_schema=WriteFileSchema)
def write_local_file(filename: str, content: str) -> str:
    """Tool to create or overwrite a local text file with specific content."""
    try:
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(content)
        return f"Success: The file '{filename}' was successfully written and saved on the local computer."
    except Exception as e:
        return f"Error: Could not write to file. {str(e)}"
    
class ReadDocSchema(BaseModel):
    file_path: str = Field(description="The absolute path to the local file to read (can be .txt or .pdf)")

@tool(args_schema=ReadDocSchema)
def read_local_document(file_path: str) -> str:
    """Tool to read the exact text content of a local .txt or .pdf file from anywhere on the computer. You can pass just the file name (e.g., 'README.md') if it is in the current directory."""
    expanded_path = os.path.abspath(os.path.expanduser(file_path))
    
    if not os.path.exists(expanded_path):
        return f"Error: The file '{expanded_path}' does not exist on the local computer."
    
    try:
        if expanded_path.lower().endswith('.pdf'):
            text = ""
            with open(expanded_path, 'rb') as f:
                reader = pypdf.PdfReader(f)
                for page in reader.pages:
                    page_text = page.extract_text()
                    if page_text:
                        text += page_text + "\n"
            return f"Content of PDF '{expanded_path}':\n{text[:10000]}..." 
            
        else:
            with open(expanded_path, 'r', encoding='utf-8') as f:
                content = f.read()
            return f"Content of '{expanded_path}':\n{content[:10000]}..."
            
    except Exception as e:
        return f"Error: Could not read the file. {str(e)}"
    
class TimeSchema(BaseModel):
    empty: str = Field(default="", description="Empty field")

@tool(args_schema=TimeSchema)
def get_current_time(empty: str = "") -> str:
    """Tool to get the current exact date and time."""
    now = datetime.now()
    return f"The current date and time is: {now.strftime('%Y-%m-%d %H:%M:%S')}"

class ScrapeSchema(BaseModel):
    url: str = Field(description="The exact URL of the web page to read")

@tool(args_schema=ScrapeSchema)
def scrape_web_page(url: str) -> str:
    """Tool to read and extract the text content from a specific web page URL."""
    try:
        headers = {'User-Agent': 'Mozilla/5.0'}
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
        
        text = soup.get_text(separator=' ', strip=True)
        return f"Content of {url}:\n{text[:4000]}..."
    except Exception as e:
        return f"Error: Could not read the web page. {str(e)}"

class ReadEmailSchema(BaseModel):
    limit: int = Field(default=3, description="The number of recent emails to fetch (default is 3)")

@tool(args_schema=ReadEmailSchema)
def read_recent_emails(limit: int = 3) -> str:
    """Tool to read the most recent emails from the user's Gmail inbox."""
    email_user = os.getenv("EMAIL_ADDRESS")
    email_pass = os.getenv("EMAIL_PASSWORD")

    if not email_user or not email_pass:
        return "Error: EMAIL_ADDRESS or EMAIL_PASSWORD not found in .env file."

    try:
        mail = imaplib.IMAP4_SSL("imap.gmail.com")
        mail.login(email_user, email_pass)
        mail.select("inbox")

        status, messages = mail.search(None, "ALL")
        email_ids = messages[0].split()

        if not email_ids:
            return "The inbox is empty."

        latest_email_ids = email_ids[-limit:]
        
        email_summaries = []
        for e_id in reversed(latest_email_ids):
            status, msg_data = mail.fetch(e_id, "(RFC822)")
            for response_part in msg_data:
                if isinstance(response_part, tuple):
                    msg = email.message_from_bytes(response_part[1])
                    
                    subject, encoding = decode_header(msg["Subject"])[0]
                    if isinstance(subject, bytes):
                        subject = subject.decode(encoding if encoding else "utf-8", errors="ignore")
                    
                    from_sender = msg.get("From")
                    
                    body = ""
                    if msg.is_multipart():
                        for part in msg.walk():
                            if part.get_content_type() == "text/plain":
                                try:
                                    body = part.get_payload(decode=True).decode(errors="ignore")
                                    break
                                except:
                                    pass
                    else:
                        try:
                            body = msg.get_payload(decode=True).decode(errors="ignore")
                        except:
                            pass
                    clean_body = body.strip().replace('\n', ' ')[:300]
                    email_summaries.append(f"FROM: {from_sender}\nSUBJECT: {subject}\nPREVIEW: {clean_body}...\n")
        
        mail.logout()
        return "Recent Emails:\n\n" + "\n---\n".join(email_summaries)

    except Exception as e:
        return f"Error: Could not read emails. Detailed error: {str(e)}"
    
class SendEmailSchema(BaseModel):
    to_email: str = Field(description="The exact email address of the recipient")
    subject: str = Field(description="The subject line of the email")
    body: str = Field(description="The main text content of the email")

@tool(args_schema=SendEmailSchema)
def send_email(to_email: str, subject: str, body: str) -> str:
    """Tool to send an email from the user's Gmail account to a specific recipient."""
    email_user = os.getenv("EMAIL_ADDRESS")
    email_pass = os.getenv("EMAIL_PASSWORD")

    if not email_user or not email_pass:
        return "Error: EMAIL_ADDRESS or EMAIL_PASSWORD not found in .env file."

    try:
        msg = MIMEMultipart()
        msg['From'] = email_user
        msg['To'] = to_email
        msg['Subject'] = subject
        msg.attach(MIMEText(body, 'plain', 'utf-8'))
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(email_user, email_pass)
        server.send_message(msg)
        server.quit()
        
        return f"Success: Email was successfully sent to {to_email}."
    except Exception as e:
        return f"Error: Could not send the email. Detailed error: {str(e)}"
SCOPES = ['https://www.googleapis.com/auth/calendar']

def get_calendar_service():
    """Fonction utilitaire pour gérer l'authentification OAuth2"""
    creds = None
    if os.path.exists('token.json'):
        creds = Credentials.from_authorized_user_file('token.json', SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file('credentials.json', SCOPES)
            creds = flow.run_local_server(port=0)
        with open('token.json', 'w') as token:
            token.write(creds.to_json())
    return build('calendar', 'v3', credentials=creds)

class ReadCalendarSchema(BaseModel):
    max_results: int = Field(default=5, description="Number of upcoming events to retrieve")

@tool(args_schema=ReadCalendarSchema)
def read_upcoming_events(max_results: int = 5) -> str:
    """Tool to read the user's upcoming events from Google Calendar."""
    try:
        service = get_calendar_service()
        now = datetime.utcnow().isoformat() + 'Z'
        events_result = service.events().list(calendarId='primary', timeMin=now,
                                              maxResults=max_results, singleEvents=True,
                                              orderBy='startTime').execute()
        events = events_result.get('items', [])
        if not events:
            return "No upcoming events found in the calendar."
        
        res = "Upcoming Events:\n"
        for event in events:
            start = event['start'].get('dateTime', event['start'].get('date'))
            res += f"- {start}: {event['summary']}\n"
        return res
    except Exception as e:
        return f"Error reading calendar: {str(e)}"

class CreateEventSchema(BaseModel):
    summary: str = Field(description="Title of the event")
    start_time: str = Field(description="Start time in ISO format (e.g., 2026-05-10T09:00:00+01:00)")
    end_time: str = Field(description="End time in ISO format (e.g., 2026-05-10T10:00:00+01:00)")
    description: str = Field(default="", description="Optional description of the event")

@tool(args_schema=CreateEventSchema)
def create_calendar_event(summary: str, start_time: str, end_time: str, description: str = "") -> str:
    """Tool to create a new event in the user's Google Calendar."""
    try:
        service = get_calendar_service()
        event = {
          'summary': summary,
          'description': description,
          'start': {'dateTime': start_time},
          'end': {'dateTime': end_time},
        }
        event = service.events().insert(calendarId='primary', body=event).execute()
        return f"Success: Event created! Link: {event.get('htmlLink')}"
    except Exception as e:
        return f"Error creating event: {str(e)}"
    
@tool
def list_directory_contents(directory_path: str = ".") -> str:
    """
    Lists the files and folders in the specified directory.
    If no directory is provided, it defaults to the current working directory (like the 'ls' command).
    Use this to find the exact names of files before trying to read them.
    """
    try:
        abs_path = os.path.abspath(directory_path)
        items = os.listdir(abs_path)
        
        if not items:
            return f"The directory '{abs_path}' is empty."
        
        result = f"Contents of {abs_path}:\n"
        for item in items:
            result += f"- {item}\n"
        return result
        
    except Exception as e:
        return f"Error reading directory '{directory_path}': {str(e)}"
    
class SearchFileSchema(BaseModel):
    filename: str = Field(description="The exact name of the file to search for (e.g., 'README.md' or 'corrected.pdf')")

@tool(args_schema=SearchFileSchema)
def search_local_file(filename: str) -> str:
    """
    Tool to globally search for a file on the computer and return its absolute path.
    Used when the file is not in the current working directory.
    """

    if sys.platform == "darwin":
        try:
            result = subprocess.run(["mdfind", "-name", filename], capture_output=True, text=True, timeout=5)
            paths = result.stdout.strip().split("\n")
            
            if paths and paths[0]:
                for path in paths:
                    if "Library" not in path and path.endswith(filename):
                        return f"Success: File found at {path}"
                return f"Success: File found at {paths[0]}"
        except Exception:
            pass

    search_dirs = [
        os.path.expanduser("~/Documents"), 
        os.path.expanduser("~/Downloads"), 
        os.path.expanduser("~/Desktop"),
        os.getcwd()
    ]
    
    exclude_dirs = {'node_modules', '.venv', '.git', 'Library', 'AppData', '__pycache__', '.idea', '.vscode'}

    for search_dir in search_dirs:
        if not os.path.exists(search_dir):
            continue
            
        for root, dirs, files in os.walk(search_dir):
            dirs[:] = [d for d in dirs if d not in exclude_dirs]
            
            if filename in files:
                return f"Success: File found at {os.path.join(root, filename)}"
                
    return f"Error: Could not find '{filename}' on the computer."
    
class ExecSchema(BaseModel):
    command: str = Field(description="The exact terminal shell command to execute")

@tool(args_schema=ExecSchema)
def execute_shell_command(command: str) -> str:
    """
    Tool to execute a terminal/shell command on the local machine.
    Use this to run scripts, check the system environment, or install packages.
    """
    try:
        with open("permissions.json", "r", encoding="utf-8") as f:
            permissions = json.load(f)

        parsed_args = shlex.split(command)
        if not parsed_args:
            return "Error: Empty command."
            
        base_cmd = parsed_args[0]
        if base_cmd in permissions.get("forbidden_prefixes", []):
            return f"SECURITY ERROR: The command '{base_cmd}' is blacklisted and strictly forbidden. Do not try again."

        if base_cmd in permissions.get("auto_approved", []):
            result = subprocess.run(command, shell=True, capture_output=True, text=True, timeout=15)
            if result.returncode == 0:
                return f"Success:\n{result.stdout}"
            else:
                return f"Command failed (Exit code {result.returncode}):\n{result.stderr}"
            
        return (f"ACTION BLOCKED: The command '{base_cmd}' is not in the auto-approved list in 'permissions.json'. "
                "Ask the user if they authorize this command. If they do, ask them to manually add it to 'permissions.json' so you can run it.")

    except FileNotFoundError:
        return "Error: 'permissions.json' file not found. System locked."
    except Exception as e:
        return f"Execution error: {str(e)}"
    
class AddWhitelistSchema(BaseModel):
    new_command: str = Field(description="The exact command prefix to add to the auto_approved list (e.g., 'docker' or 'systemctl')")

@tool(args_schema=AddWhitelistSchema)
def add_to_whitelist(new_command: str) -> str:
    """
    Tool to safely add a new command to the 'auto_approved' list in the permissions.json file.
    Use this tool ONLY when the user explicitly gives you permission to whitelist a new command.
    """
    try:
        with open("permissions.json", "r", encoding="utf-8") as f:
            permissions = json.load(f)

        if new_command in permissions.get("forbidden_prefixes", []):
             return f"Error: Cannot whitelist '{new_command}' because it is in the forbidden list."
             
        if new_command not in permissions.get("auto_approved", []):
            permissions.setdefault("auto_approved", []).append(new_command)
            with open("permissions.json", "w", encoding="utf-8") as f:
                json.dump(permissions, f, indent=4)
            return f"Success: '{new_command}' has been added to the whitelist. You can now execute it."
        else:
            return f"Info: '{new_command}' is already in the whitelist."
            
    except Exception as e:
        return f"Error updating permissions.json: {str(e)}"
    
class OpenItemSchema(BaseModel):
    target: str = Field(description="The exact URL of the website or the absolute path of the local file to open.")
    is_url: Union[bool, str] = Field(description="MUST be a strict boolean (true/false). Set to true if the target is a web link, false if it is a local file.")

@tool(args_schema=OpenItemSchema)
def open_item(target: str, is_url: bool) -> str:
    """
    Tool to open a website in the default browser or open a local file in its default desktop application.
    Use this when the user explicitly asks to "open" or "play" something on their screen.
    """
    if isinstance(is_url, str):
        is_url = is_url.lower() in ['true', 'yes', '1', 'y', 't']
    try:
        if is_url:
            webbrowser.open(target)
            return f"Success: Opened web page {target} in the browser."
        else:
            if not os.path.exists(target):
                return f"Error: The file {target} does not exist. You may need to search for it first."
            if sys.platform == "darwin":
                subprocess.run(["open", target])
            elif sys.platform == "win32":
                os.startfile(target)
            else:
                subprocess.run(["xdg-open", target])
                
            return f"Success: Opened local file {target} on the screen."
            
    except Exception as e:
        return f"Error opening item: {str(e)}"
    
my_tools = [internet_search, write_local_file, read_local_document, get_current_time, scrape_web_page, read_recent_emails, send_email, read_upcoming_events, create_calendar_event, list_directory_contents, search_local_file, execute_shell_command, add_to_whitelist, open_item]