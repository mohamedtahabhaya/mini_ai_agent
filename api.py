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
from typing import Optional

app = FastAPI(title="My AI Agent") 

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
    session_id: str = "agent01" 
    is_approval: bool = False
    image_data: Optional[str] = None

@app.post("/chat")
async def chat_endpoint(request: ChatRequest):
    config = {"configurable": {"thread_id": request.session_id}}
    
    async def event_generator():
        if request.is_approval:
            input_data = None
        else:
            message_content = [{"type": "text", "text": request.message}]
            
            if request.image_data:
                message_content.append({
                    "type": "image_url",
                    "image_url": {"url": request.image_data}
                })
                
            input_data = {"messages": [("user", message_content)]}
        
        try:
            async for event in my_agent.astream_events(input_data, config=config, version="v2"):
                kind = event["event"]
                node_name = event["metadata"].get("langgraph_node")

                if kind == "on_chat_model_stream" and node_name in ["system_agent", "web_agent", "general_agent"]:
                    chunk = event["data"]["chunk"].content 
                    if isinstance(chunk, str) and chunk:
                        yield f"data: {json.dumps({'type': 'token', 'content': chunk})}\n\n"

                elif kind == "on_chain_end" and node_name == "supervisor":
                    output = event["data"].get("output")
                    if output and "messages" in output:
                        for msg in output["messages"]:
                            content = msg[1] if isinstance(msg, tuple) else getattr(msg, 'content', str(msg))
                            yield f"data: {json.dumps({'type': 'token', 'content': content})}\n\n"
                        
        except Exception as e:
            yield f"data: {json.dumps({'type': 'error', 'content': str(e)})}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")