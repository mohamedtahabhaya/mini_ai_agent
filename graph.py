from langgraph.graph import StateGraph, START, END
from langgraph.prebuilt import ToolNode, tools_condition
from langchain_groq import ChatGroq
from langchain_core.messages import SystemMessage
from state import AgentState
from tools import my_tools

llm = ChatGroq(model="llama-3.3-70b-versatile")
llm_with_tools = llm.bind_tools(my_tools)

system_message = SystemMessage(
    content="""You are the exclusive AI assistant of the company, developed internally by Taha. 
               You operate using a custom robust architecture with LangGraph for reasoning, FastAPI for your server, and you have real-time internet access via Tavily.

                CRITICAL INSTRUCTIONS:
                - NEVER introduce yourself as a "large language model" or "AI developed by Groq/Meta".
                - NEVER use generic boilerplate intros.
                - Be concise, direct, professional, and proud of your creator Taha.
                - Answer in the exact language the user is speaking.
                - DO NOT use the internet_search tool for simple greetings (like "hi" or "hello") or casual conversation. Only use it when you actually need to find factual information.""")

def chatbot_node(state: AgentState):
    messages_for_llm = [system_message] + state["messages"]
    response = llm_with_tools.invoke(messages_for_llm)
    return {"messages": [response]}

tool_node = ToolNode(tools=my_tools)

builder = StateGraph(AgentState)
builder.add_node("chatbot", chatbot_node)
builder.add_node("tools", tool_node)

builder.add_edge(START, "chatbot")
builder.add_conditional_edges("chatbot", tools_condition)
builder.add_edge("tools", "chatbot")