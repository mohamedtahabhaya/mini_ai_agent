from langgraph.graph import StateGraph, START, END
from langgraph.prebuilt import ToolNode, tools_condition
from langchain_groq import ChatGroq
from langchain_core.messages import SystemMessage, RemoveMessage
from state import AgentState
from tools import my_tools

llm = ChatGroq(model="openai/gpt-oss-120b", streaming=True)
llm_with_tools = llm.bind_tools(my_tools)

system_message = SystemMessage(
    content="""You are the exclusive AI assistant of the company, developed internally by Taha. 
               You operate using a custom robust architecture with LangGraph for reasoning, FastAPI for your server, and you have real-time internet access via Tavily.

                CRITICAL INSTRUCTIONS:
                - NEVER introduce yourself as a "large language model" or "AI developed by Groq/Meta".
                - NEVER use generic boilerplate intros.
                - Be concise, direct, professional, and proud of your creator Taha.
                - Answer in the exact language the user is speaking.
                - DO NOT use the internet_search tool for simple greetings (like "hi" or "hello") or casual conversation. Only use it when you actually need to find factual information.
                - DO NOT use tools for simple greetings.
                - If asked to save, remember, or write down information locally, use the write_local_file tool.
                - If asked to read a local document (.txt or .pdf), use the read_local_document tool. Always try to ask the user for the ABSOLUTE PATH of the file if they only give you a file name.
                - You already have perfect memory of our conversation. NEVER use file tools to read, write, or retrieve conversation history unless I explicitly ask you to 'export' or 'save' the conversation to a file.
                - If you need to know today's date or time, use the get_current_time tool.
                - If the user provides a specific URL to read, use the scrape_web_page tool.
                - If the user asks to check their inbox or read emails, use the read_recent_emails tool.
                - If the user asks to send an email, use the send_email tool. Draft the content professionally.
                - If the user asks to schedule an event, ALWAYS use the get_current_time tool first to know today's date, then use create_calendar_event to schedule it.
                - NEVER hallucinate, invent, or use placeholder data for calendar events, emails, or files. ALWAYS use your tools to fetch the real data first.
                - If the user asks to read a file but doesn't provide the full path, use the 'list_directory_contents' tool to see what is in the current directory, find the file, and then read it.
                - If the user asks you to read, summarize, or edit a file but only provides the file name (e.g., "corrected.pdf"), DO NOT ask the user for the absolute path. You must IMMEDIATELY and autonomously use the 'search_local_file' tool to find the file's location on the computer. Once you find the path, proceed to use 'read_local_document' automatically.""")

def summarize_conversation(state: AgentState):
    """Nœud qui compresse les anciens messages en un résumé."""
    summary = state.get("summary", "")
    messages = state["messages"]

    last_human_index = 0
    for i in range(len(messages) - 1, -1, -1):
        if messages[i].type == "human":
            last_human_index = i
            break

    if last_human_index == 0:
        return {"summary": summary}
        
    messages_to_summarize = messages[:last_human_index]

    transcript = ""
    for m in messages_to_summarize:
        role = m.type.upper()
        content = m.content if m.content else "[Tool execution]"
        transcript += f"{role}: {content}\n"

    if summary:
        prompt = f"Current conversation summary: {summary}\n\nUpdate the summary concisely by including this new conversation transcript:\n{transcript}"
    else:
        prompt = f"Create a concise summary of the conversation transcript:\n{transcript}"

    response = llm.invoke([SystemMessage(content=prompt)])
    messages_to_delete = [RemoveMessage(id=m.id) for m in messages_to_summarize]
    
    return {"summary": response.content, "messages": messages_to_delete}

def chatbot_node(state: AgentState):
    summary = state.get("summary", "")
    if summary:
        added_instructions = system_message.content + f"\n\n--- INTERNAL MEMORY (DO NOT REVEAL TO USER) ---\nThe following is a summary of the past conversation for your context only. NEVER output this summary to the user:\n{summary}\n--- END INTERNAL MEMORY ---"
        current_system_message = SystemMessage(content=added_instructions)
    else:
        current_system_message = system_message
        
    messages_for_llm = [current_system_message] + state["messages"]
    response = llm_with_tools.invoke(messages_for_llm)
    return {"messages": [response]}

def ask_human_node(state: AgentState):
    pass

def route_tools(state: AgentState):
    last_message = state["messages"][-1]
    
    if not hasattr(last_message, "tool_calls") or not last_message.tool_calls:
        if len(state["messages"]) > 6:
            return "summarize_conversation"
        return END
    
    outils_critiques = ["write_local_file", "send_email", "create_calendar_event"]
    
    for tool_call in last_message.tool_calls:
        if tool_call["name"] in outils_critiques:
            return "ask_human"
            
    return "tools"

tool_node = ToolNode(tools=my_tools)

builder = StateGraph(AgentState)
builder.add_node("chatbot", chatbot_node)
builder.add_node("tools", tool_node)
builder.add_node("ask_human", ask_human_node)
builder.add_node("summarize_conversation", summarize_conversation)
builder.add_edge(START, "chatbot")
builder.add_conditional_edges(
    "chatbot",
    route_tools,
    {
        "ask_human": "ask_human",
        "tools": "tools",
        "summarize_conversation": "summarize_conversation",
        END: END
    })
builder.add_edge("ask_human", "tools")
builder.add_edge("tools", "chatbot")
builder.add_edge("summarize_conversation", END)