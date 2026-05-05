from pydantic import BaseModel, Field
from langchain_core.tools import tool
from langchain_tavily import TavilySearch

class SchemaRecherche(BaseModel):
    query: str = Field(description="La recherche exacte à taper sur Internet")

tavily_client = TavilySearch(max_results=3)

@tool(args_schema=SchemaRecherche)
def outil_recherche(query: str) -> str:
    """Outil pour chercher des informations récentes sur Internet."""
    return tavily_client.invoke({"query": query, "topic": "general"})

mes_outils = [outil_recherche]