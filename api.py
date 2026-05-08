import os
import json
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
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
    
    async def event_generator():
        input_data = None if request.is_approval else {"messages": [("user", request.message)]}
        
        try:
            async for event in my_agent.astream_events(input_data, config=config, version="v2"):
                kind = event["event"]

                if kind == "on_chat_model_stream" and event["metadata"].get("langgraph_node") == "chatbot":
                    chunk = event["data"]["chunk"].content
                    if isinstance(chunk, str) and chunk:
                        yield f"data: {json.dumps({'type': 'token', 'content': chunk})}\n\n"
                        
        except Exception as e:
            yield f"data: {json.dumps({'type': 'error', 'content': str(e)})}\n\n"

        etat_courant = my_agent.get_state(config)
        if etat_courant.next and etat_courant.next[0] == "ask_human":
            dernier_message = etat_courant.values["messages"][-1]
            outils_demandes = [tc["name"] for tc in dernier_message.tool_calls]
            noms_outils = ", ".join(outils_demandes)
            
            msg_approbation = f"\n\n⚠️ **Authorization required** : I want to use `[{noms_outils}]`. Type 'yes' to accept."
            yield f"data: {json.dumps({'type': 'approval', 'content': msg_approbation})}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")