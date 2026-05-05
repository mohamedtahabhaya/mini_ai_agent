import os
from dotenv import load_dotenv
load_dotenv()

from pymongo import MongoClient
from langgraph.checkpoint.mongodb import MongoDBSaver
from graph import builder

URI_MONGODB = "mongodb://localhost:27017"
client = MongoClient(URI_MONGODB)

memory = MongoDBSaver(client)
mon_agent = builder.compile(checkpointer=memory)

config = {"configurable": {"thread_id": "session_taha_mongo"}}

print("--- Agent ---")
print("Tapez 'quit' pour quitter le terminal.\n")

while True:
    user_input = input("You: ")
    if user_input.lower() == 'quit':
        break
        
    print("Thinking...")
    for event in mon_agent.stream({"messages": [("user", user_input)]}, config=config):
        for visited_node, data in event.items():
            print(f" -> Visiting node: [{visited_node}]")

    final_state = mon_agent.get_state(config)
    final_response = final_state.values["messages"][-1].content
    print(f"\nAgent: {final_response}\n")