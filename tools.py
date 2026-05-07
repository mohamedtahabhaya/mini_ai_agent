import os
import requests
import pypdf
from datetime import datetime
from bs4 import BeautifulSoup
from pydantic import BaseModel, Field
from langchain_core.tools import tool
from langchain_tavily import TavilySearch

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
    """Tool to read the exact text content of a local .txt or .pdf file from anywhere on the computer."""
    expanded_path = os.path.expanduser(file_path)
    
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

my_tools = [internet_search, write_local_file, read_local_document, get_current_time, scrape_web_page]