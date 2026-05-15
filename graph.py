from langgraph.graph import StateGraph, START, END 
from langgraph.prebuilt import ToolNode
from langchain_groq import ChatGroq
from langchain_core.messages import SystemMessage, RemoveMessage
from state import AgentState
from tools import system_tools, web_assistant_tools

llm = ChatGroq(model="openai/gpt-oss-120b", streaming=True)
tool_node = ToolNode(tools=system_tools + web_assistant_tools) 

def create_agent(llm, tools, system_prompt, agent_name):
    """Creates a specialized sub-agent with access to specific tools."""
    llm_with_tools = llm.bind_tools(tools)
    def agent_node(state: AgentState):
        summary = state.get("summary", "")
        if summary:
            full_prompt = f"{system_prompt}\n\nCONTEXT FROM PREVIOUS CONVERSATION: {summary}"
        else:
            full_prompt = system_prompt
            
        messages_for_llm = [SystemMessage(content=full_prompt)] + state["messages"]
        response = llm_with_tools.invoke(messages_for_llm)
        return {"messages": [response], "sender": agent_name}
        
    return agent_node

system_prompt = """You are the System Expert for this AI team. You specialize in local computer operations.
You can execute terminal commands, read/write files, and navigate directories.
Be professional and helpful. If the user is just saying hello, respond naturally. 
Your primary tools allow you to "open" things, run scripts, and manage the local environment."""

web_prompt = """You are the Web and Administrative Assistant for this AI team. You specialize in internet searches, emails, and calendar.
You are proactive! If a user asks to "open" a specific video or website, use your search tools to find the URL and then open it immediately.
Be warm and helpful. You are an expert in finding information online."""

general_prompt = """You are the General Assistant and "concierge" of this AI team. 
Your role is to handle greetings, general questions, and chitchat.
IMPORTANT: While you don't have tools yourself, your TEAMMATES do:
- System Expert: Manages local files and the terminal.
- Web Assistant: Searches the internet, reads/sends emails, and manages the calendar.
If a user asks what we can do, mention these capabilities. Be friendly and concise."""

supervisor_prompt = """You are the Supervisor of an AI team. 
Specialists:
- system_agent: Local computer tasks (files, terminal).
- web_agent: Web tasks (search, email, calendar).
- general_agent: Greetings, chitchat, and general questions.

ROUTING RULES:
1. Greetings/General talk -> route to 'general_agent'.
2. Local files/Terminal -> route to 'system_agent'.
3. Web/Email/Calendar/YouTube -> route to 'web_agent'.
4. To "open" a local file -> route to 'system_agent'. To "open" a URL/video -> route to 'web_agent'.
5. If the request is completed -> route to 'FINISH'.

RESPOND ONLY WITH ONE WORD: system_agent, web_agent, general_agent, or FINISH."""

system_agent_node = create_agent(llm, system_tools, system_prompt, "system_agent")
web_agent_node = create_agent(llm, web_assistant_tools, web_prompt, "web_agent")
general_agent_node = create_agent(llm, [], general_prompt, "general_agent")

def supervisor_node(state: AgentState):
    print("[SUPERVISOR] Analyzing the request...")
    summary = state.get("summary", "")
    full_prompt = supervisor_prompt
    if summary:
        full_prompt += f"\n\nCONTEXT FROM PREVIOUS CONVERSATION: {summary}"
        
    messages_for_llm = [SystemMessage(content=full_prompt)] + state["messages"]

    try:
        response = llm.invoke(messages_for_llm)
        text = response.content.strip().lower()
    except Exception as e:
        print(f"[SUPERVISOR] Error: {e}")
        text = "finish"

    if "system_agent" in text:
        decision = "system_agent"
    elif "web_agent" in text:
        decision = "web_agent"
    elif "general_agent" in text:
        decision = "general_agent"
    else:
        decision = "FINISH"

    if decision == state.get("sender"):
        decision = "FINISH"

    print(f"[SUPERVISOR] Route -> {decision}")
    return {"next_agent": decision, "sender": "supervisor"}

def summarize_conversation(state: AgentState):
    """Summarizes the conversation history to save tokens."""
    print("[MEMORY] Summarizing old messages...")
    summary = state.get("summary", "")
    
    if summary:
        summary_prompt = f"Current summary: {summary}\n\nExtend this summary with the following new messages:"
    else:
        summary_prompt = "Summarize the following conversation history concisely:"

    messages = state["messages"]
    messages_to_summarize = messages[:-4]
    
    if not messages_to_summarize:
        return {}

    response = llm.invoke([SystemMessage(content=summary_prompt)] + messages_to_summarize)
    
    prune_commands = [RemoveMessage(id=m.id) for m in messages_to_summarize if hasattr(m, "id") and m.id]
    
    return {
        "summary": response.content,
        "messages": prune_commands
    }

def route_after_supervisor(state: AgentState):
    decision = state["next_agent"]
    if decision == "FINISH":
        if len(state["messages"]) > 10:
            return "summarize"
        return END
    return decision

def route_after_agent(state: AgentState):
    """Did the agent call a tool, or is it done talking?"""
    last_message = state["messages"][-1]
    if hasattr(last_message, "tool_calls") and last_message.tool_calls:
        print(f"[{state['sender']}] is entering the tool room...")
        return "tools"
    
    print(f"[{state['sender']}] has finished, returning to the Supervisor.")
    return "supervisor"

def route_after_tools(state: AgentState):
    """The tool is done, which agent should we return the result to?"""
    return state["sender"]

builder = StateGraph(AgentState)

builder.add_node("supervisor", supervisor_node) 
builder.add_node("system_agent", system_agent_node)
builder.add_node("web_agent", web_agent_node)
builder.add_node("general_agent", general_agent_node)
builder.add_node("tools", tool_node)
builder.add_node("summarize", summarize_conversation)

builder.add_edge(START, "supervisor")

builder.add_conditional_edges(
    "supervisor",
    route_after_supervisor, 
    {
        "system_agent": "system_agent",
        "web_agent": "web_agent",
        "general_agent": "general_agent",
        "summarize": "summarize",
        END: END
    }
)

builder.add_edge("summarize", END)

builder.add_conditional_edges("system_agent", route_after_agent, {"tools": "tools", "supervisor": "supervisor"})
builder.add_conditional_edges("web_agent", route_after_agent, {"tools": "tools", "supervisor": "supervisor"})
builder.add_conditional_edges("general_agent", route_after_agent, {"tools": "tools", "supervisor": "supervisor"})
builder.add_conditional_edges("tools", route_after_tools, {"system_agent": "system_agent", "web_agent": "web_agent"})

builder = builder
