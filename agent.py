# premiere version 

import os
from typing import Annotated
from typing_extensions import TypedDict
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langchain_groq import ChatGroq
from langchain_core.tools import tool
from langgraph.prebuilt import ToolNode, tools_condition
from langgraph.checkpoint.sqlite import SqliteSaver
from langchain_community.tools import DuckDuckGoSearchRun

os.environ["GROQ_API_KEY"] = "gsk_XXXXXX"

search_tool = DuckDuckGoSearchRun()

llm = ChatGroq(model="llama-3.3-70b-versatile")
tools = [search_tool]
llm_with_tools = llm.bind_tools(tools)

class AgentState(TypedDict):
    messages: Annotated[list, add_messages]

def chatbot_node(state: AgentState):
    response = llm_with_tools.invoke(state["messages"])
    return {"messages": [response]}

tool_node = ToolNode(tools=tools)

graph = StateGraph(AgentState)
graph.add_node("chatbot", chatbot_node)
graph.add_node("tools", tool_node)
graph.add_edge(START, "chatbot")
graph.add_conditional_edges("chatbot", tools_condition)
graph.add_edge("tools", "chatbot")

with SqliteSaver.from_conn_string("ma_memoire.sqlite") as memory:
    custom_agent = graph.compile(checkpointer=memory,interrupt_before=["tools"])

    config = {"configurable": {"thread_id": "taha_session_1"}}

    print("--- Agent with Breakpoint (type 'quit' to exit) ---")

    while True:
        user_input = input("\nYou: ")
        if user_input.lower() == 'quit':
            break
            
        print("Thinking...")
        for event in custom_agent.stream({"messages": [("user", user_input)]}, config=config):
            for visited_node, data in event.items():
                print(f" -> Visiting node: [{visited_node}]")
                
        current_state = custom_agent.get_state(config)
        
        if current_state.next and current_state.next[0] == "tools":
            decision = input("\n[SYSTEM] the agent wants to use a tool. Agree ? (y/n): ")
            
            if decision.strip().lower() in ["oui", "y", "yes"]:
                for event in custom_agent.stream(None, config=config):
                    for visited_node, data in event.items():
                        print(f" -> Visiting node: [{visited_node}]")
                
                final_state = custom_agent.get_state(config)
                final_response = final_state.values["messages"][-1].content
                print(f"\nAgent: {final_response}")
            else:
                print("[SYSTEM] Exécution bloquée par l'utilisateur.")
        else:
            final_response = data["messages"][-1].content
            print(f"\nAgent: {final_response}")