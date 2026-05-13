from langgraph.graph import StateGraph, START, END
from langgraph.prebuilt import ToolNode
from langchain_groq import ChatGroq
from langchain_core.messages import SystemMessage
from state import AgentState
from tools import system_tools, web_assistant_tools
from pydantic import BaseModel
from typing import Literal

llm = ChatGroq(model="meta-llama/llama-4-scout-17b-16e-instruct", streaming=True)
all_tools = system_tools + web_assistant_tools
tool_node = ToolNode(tools=all_tools)

def create_agent(llm, tools, system_prompt, agent_name) :
    """function factory to create specialized sub-agents."""
    llm_with_tools = llm.bind_tools(tools)
    def agent_node(state: AgentState):
        message_for_llm = [SystemMessage(content=system_prompt)] + state["messages"]
        response = llm_with_tools.invoke(message_for_llm)
        return {"messages": [response], "sender": agent_name}
    return agent_node

system_prompt = """You are the System Expert. Your sole role is to interact with the local computer. You can execute terminal commands, read/write files, and navigate folders. If asked a question that requires internet searching or email management, simply respond: "I am not qualified for that, ask the Web Assistant." """
system_agent_node = create_agent(llm, system_tools, system_prompt, "system_agent")

web_prompt = """You are the Web and Administrative Assistant. Your sole role is to search for information on the internet via Tavily, read/send emails, and manage Google Calendar. If asked to modify a local file or run a terminal command, simply respond: "I am not qualified for that, ask the System Expert." """
web_agent_node = create_agent(llm, web_assistant_tools, web_prompt, "web_agent")

class Route(BaseModel):
    next_agent: Literal["system_agent", "web_agent", "FIN"]

supervisor_prompt = """ You are the Supervisor of an AI team.
Your employees are:
- system_agent: Specialist in local computer tasks (files, terminal, folders, permissions).
- web_agent: Specialist in external tasks (internet search, emails, Google Calendar).
Analyze the user's request or the ongoing conversation.
Decide which expert to hand over to.
If an expert has just responded to the user satisfactorily, or if there is nothing left to do, you MUST choose 'FIN'."""

supervisor_chain = llm.with_structured_output(Route)

def supervisor_node(state: AgentState):
    print("[SUPERVISOR] Analyzing...")
    messages_for_llm = [SystemMessage(content=supervisor_prompt)] + state["messages"]
    decision = supervisor_chain.invoke(messages_for_llm)
    print(f"[SUPERVISOR] Decision made -> Handing over to: {decision.next_agent}")
    return {"next_agent": decision.next_agent, "sender": "supervisor"}

def route_after_agent(state: AgentState):
    """ Did the agent call a tool, or did it finish speaking? """
    last_message = state["messages"][-1]
    if hasattr(last_message, "tool_calls") and last_message.tool_calls:
        print(f"[{state['sender']}] called tools: {[tc.name for tc in last_message.tool_calls]}")
        return "tools"
    print(f"[{state['sender']}] finished responding, routing to supervisor for next decision.")
    return "supervisor"

def route_after_tools(state: AgentState):
    """ The tool has finished, which agent should we send the result back to? """
    return state["sender"]

builder = StateGraph(AgentState)
builder.add_node("supervisor", supervisor_node)
builder.add_node("system_agent", system_agent_node)
builder.add_node("web_agent", web_agent_node)
builder.add_node("tools", tool_node)

builder.add_edge(START, "supervisor")
builder.add_conditional_edges(
    "supervisor",
    lambda state: [state["next_agent"]],
    { "system_agent": "system_agent", "web_agent": "web_agent", "FIN": END}
)

builder.add_conditional_edges("system_agent", route_after_agent, {"tools": "tools", "supervisor": "supervisor"})
builder.add_conditional_edges("web_agent", route_after_agent, {"tools": "tools", "supervisor": "supervisor"})
builder.add_conditional_edges("tools", route_after_tools, {"system_agent": "system_agent", "web_agent": "web_agent"})