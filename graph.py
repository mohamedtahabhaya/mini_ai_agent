from langgraph.graph import StateGraph, START, END 
from langgraph.prebuilt import ToolNode
from langchain_groq import ChatGroq
from langchain_core.messages import SystemMessage 
from state import AgentState
from tools import system_tools, web_assistant_tools

llm = ChatGroq(model="openai/gpt-oss-120b", streaming=True)
tool_node = ToolNode(tools=system_tools + web_assistant_tools) 

def create_agent(llm, tools, system_prompt, agent_name):
    """Creates a specialized sub-agent with access to specific tools."""
    llm_with_tools = llm.bind_tools(tools)
    def agent_node(state: AgentState):
        messages_for_llm = [SystemMessage(content=system_prompt)] + state["messages"]
        response = llm_with_tools.invoke(messages_for_llm)
        return {"messages": [response], "sender": agent_name}
        
    return agent_node

system_prompt = """You are the System Expert for this AI team. You specialize in local computer operations like terminal commands, file management, and system navigation.
When you receive a message, be professional and helpful. If the user is just saying hello, respond naturally. 
Your primary tools allow you to "open" things, run scripts, and manage the local environment. Focus on being an efficient power-user for the local machine."""

system_agent_node = create_agent(llm, system_tools, system_prompt, "system_agent")

web_prompt = """You are the Web and Administrative Assistant for this AI team. You specialize in internet searches, email management, and calendar scheduling.
You are proactive! If a user asks to "open" a video or a specific website (like "open Iron Man wake up scene on youtube"), DO NOT just show a search page. 
Instead:
1. Use `internet_search` to find the direct URL of the video or site.
2. Use `open_item` (with is_url=True) to launch that specific URL for the user.
If you are unsure of the link, search for it first, then open the best result. Be the "face" of the team and handle small talk warmly."""

web_agent_node = create_agent(llm, web_assistant_tools, web_prompt, "web_agent")

general_prompt = """You are the General Assistant and "concierge" of this AI team. 
Your role is to handle greetings, general questions, and chitchat.
IMPORTANT: While you don't have tools yourself, your TEAMMATES do. 
- The System Expert can manage local files and the terminal.
- The Web Assistant can search the internet, read/send emails, and manage the calendar.
If a user asks what "you" (the team) can do, mention these capabilities. Be helpful, friendly, and concise."""

general_agent_node = create_agent(llm, [], general_prompt, "general_agent")

supervisor_prompt = """You are the Supervisor of an AI team. 
Your specialists are:
- system_agent: Local computer specialist (files, terminal, local system).
- web_agent: Web specialist (search, email, calendar).
- general_agent: General assistant for greetings, chitchat, and basic questions.

TASK:
Determine which specialist should handle the user's request.

ROUTING RULES:
1. If the request is a greeting, small talk, or a general question that needs no tools -> route to 'general_agent'.
2. If the user mentions: file, directory, folder, terminal, computer, local, or local read/write tasks -> route to 'system_agent'.
3. If the user mentions: web, internet, email, calendar, search, or online videos (youtube, etc.) -> route to 'web_agent'.
4. If the user asks to "open" a local file or local path, route to 'system_agent'.
5. If the user asks to "open" a URL, a website, or an online video, route to 'web_agent'.
6. If the request is fully completed, respond with 'FINISH'.

RESPOND STRICTLY AND ONLY WITH ONE OF THESE 4 WORDS:
system_agent
web_agent
general_agent
FINISH
"""

def supervisor_node(state: AgentState):
    print("[SUPERVISOR] Analyzing the request...")
    messages_for_llm = [SystemMessage(content=supervisor_prompt)] + state["messages"]

    try:
        response = llm.invoke(messages_for_llm)
        text = response.content.strip().lower()
    except Exception as e:
        print(f"[SUPERVISOR] LLM Error : {e} Forcing FINISH.")
        text = "finish"

    if "system_agent" in text:
        decision = "system_agent"
    elif "web_agent" in text:
        decision = "web_agent"
    elif "general_agent" in text:
        decision = "general_agent"
    else:
        decision = "FINISH"

    # Loop protection
    if decision == state.get("sender"):
        print(f"[ANTI-LOOP] Forcing FINISH.")
        decision = "FINISH"

    print(f"[SUPERVISOR] Route -> {decision}")
    return {"next_agent": decision, "sender": "supervisor"}

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

builder.add_edge(START, "supervisor")

builder.add_conditional_edges(
    "supervisor",
    lambda state: state["next_agent"], 
    {
        "system_agent": "system_agent",
        "web_agent": "web_agent",
        "general_agent": "general_agent",
        "FINISH": END
    }
)

builder.add_conditional_edges("system_agent", route_after_agent, {"tools": "tools", "supervisor": "supervisor"})
builder.add_conditional_edges("web_agent", route_after_agent, {"tools": "tools", "supervisor": "supervisor"})
builder.add_conditional_edges("general_agent", route_after_agent, {"tools": "tools", "supervisor": "supervisor"})
builder.add_conditional_edges("tools", route_after_tools, {"system_agent": "system_agent", "web_agent": "web_agent"})