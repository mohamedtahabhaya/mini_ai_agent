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

my_tools = [internet_search]