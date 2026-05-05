from langgraph.graph import StateGraph, START, END
from langgraph.prebuilt import ToolNode, tools_condition
from langchain_groq import ChatGroq
from state import AgentState
from tools import mes_outils

llm = ChatGroq(model="llama-3.3-70b-versatile")
llm_avec_outils = llm.bind_tools(mes_outils)

def fonction_chatbot(state: AgentState):
    reponse = llm_avec_outils.invoke(state["messages"])
    return {"messages": [reponse]}

noeud_outils = ToolNode(tools=mes_outils)

builder = StateGraph(AgentState)
builder.add_node("chatbot", fonction_chatbot)
builder.add_node("tools", noeud_outils)

builder.add_edge(START, "chatbot")
builder.add_conditional_edges("chatbot", tools_condition)
builder.add_edge("tools", "chatbot")
