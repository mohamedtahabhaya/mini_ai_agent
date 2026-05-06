import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv
load_dotenv()
from pymongo import MongoClient
from langgraph.checkpoint.mongodb import MongoDBSaver

from graph import builder



app = FastAPI(title="My AI Agent API", description="API powered by LangGraph and FastAPI")

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

my_agent = builder.compile(checkpointer=memory)

class ChatRequest(BaseModel):
    message: str
    session_id: str = "session_taha_api"

@app.post("/chat")
async def chat_endpoint(request: ChatRequest):
    config = {"configurable": {"thread_id": request.session_id}}
    
    final_state = my_agent.invoke(
        {"messages": [("user", request.message)]}, config=config)
    
    final_response = final_state["messages"][-1].content
    
    return {"reponse": final_response}