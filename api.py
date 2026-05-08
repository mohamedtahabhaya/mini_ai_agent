import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv
load_dotenv()
from pymongo import MongoClient
from langgraph.checkpoint.mongodb import MongoDBSaver

from graph import builder



app = FastAPI(title="My AI Agent API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

mongodb_uri = os.getenv("URI_MONGODB")
client = MongoClient(mongodb_uri)
memory = MongoDBSaver(client)

my_agent = builder.compile(checkpointer=memory, interrupt_before=["ask_human"])

class ChatRequest(BaseModel):
    message: str
    session_id: str = "agent_securise_1" 
    is_approval: bool = False

@app.post("/chat")
async def chat_endpoint(request: ChatRequest):
    config = {"configurable": {"thread_id": request.session_id}}
    
    if request.is_approval:
        final_state = my_agent.invoke(None, config=config)
    else:
        final_state = my_agent.invoke(
            {"messages": [("user", request.message)]}, config=config)
   
    etat_courant = my_agent.get_state(config)
    
    if etat_courant.next and etat_courant.next[0] == "ask_human":
        dernier_message = final_state["messages"][-1]
        outils_demandes = [tc["name"] for tc in dernier_message.tool_calls]
        noms_outils = ", ".join(outils_demandes)
        
        return {
            "response": f"⚠️ **Autorization required** : I want to use the tool `[{noms_outils}]`. Type 'yes' to accept.",
            "requires_approval": True
        }

    final_response = final_state["messages"][-1].content
    return {
        "response": final_response,
        "requires_approval": False
    }