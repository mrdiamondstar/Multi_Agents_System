from typing import TypedDict, List
from langgraph.graph import StateGraph, END
from langchain_groq import ChatGroq
from langchain_core.messages import HumanMessage, SystemMessage
import os
from dotenv import load_dotenv

load_dotenv()

# Groq LLM configuration
llm = ChatGroq(
    model="llama-3.1-8b-instant",
    temperature=0,
    max_tokens=1000,
    api_key=os.getenv("GROQ_API_KEY")
)

# Prompt templates
MANAGER_PROMPT = "Route to planner, researcher, coder, reviewer, or end only."

PLANNER_PROMPT = """
You are a Senior System Architect.
Create a clear, implementation-ready plan.
"""

RESEARCHER_PROMPT = """
You are a Senior Research Engineer.
Expand the plan with best practices and risks.
"""

CODER_PROMPT = """
You are a Principal Software Engineer.
Output ONLY runnable production code.
"""

REVIEWER_PROMPT = """
You are a Senior Code Reviewer.
Evaluate correctness, security, performance, readability.
"""

# Shared agent state
class AgentState(TypedDict):
    user_task: str
    plan: str
    research: str
    code: str
    review: str
    next: str
    messages: List[str]

# LLM call wrapper
def call_llm(system_prompt: str, user_prompt: str) -> str:
    response = llm.invoke([
        SystemMessage(content=system_prompt),
        HumanMessage(content=user_prompt)
    ])
    return response.content

# Manager agent (deterministic routing)
def manager(state: AgentState) -> AgentState:
    if not state.get("plan"):
        state["next"] = "planner"
    elif not state.get("research"):
        state["next"] = "researcher"
    elif not state.get("code"):
        state["next"] = "coder"
    elif not state.get("review"):
        state["next"] = "reviewer"
    else:
        state["next"] = END
    return state

# Planner agent
def planner(state: AgentState) -> AgentState:
    state["plan"] = call_llm(PLANNER_PROMPT, state["user_task"])
    state["messages"].append("Planner completed")
    return state

# Researcher agent
def researcher(state: AgentState) -> AgentState:
    state["research"] = call_llm(RESEARCHER_PROMPT, state["plan"])
    state["messages"].append("Research completed")
    return state

# Coder agent
def coder(state: AgentState) -> AgentState:
    state["code"] = call_llm(
        CODER_PROMPT,
        f"PLAN:\n{state['plan']}\n\nRESEARCH:\n{state['research']}"
    )
    state["messages"].append("Code completed")
    return state

# Reviewer agent
def reviewer(state: AgentState) -> AgentState:
    state["review"] = call_llm(REVIEWER_PROMPT, state["code"])
    state["messages"].append("Review completed")
    return state

# Routing function
def route(state: AgentState) -> str:
    return state["next"]

# Graph construction
graph = StateGraph(AgentState)
graph.add_node("manager", manager)
graph.add_node("planner", planner)
graph.add_node("researcher", researcher)
graph.add_node("coder", coder)
graph.add_node("reviewer", reviewer)
graph.set_entry_point("manager")

# Conditional routing
graph.add_conditional_edges(
    "manager",
    route,
    {
        "planner": "planner",
        "researcher": "researcher",
        "coder": "coder",
        "reviewer": "reviewer",
        END: END
    }
)

# Return edges
graph.add_edge("planner", "manager")
graph.add_edge("researcher", "manager")
graph.add_edge("coder", "manager")
graph.add_edge("reviewer", "manager")

app = graph.compile()

# Execution
if __name__ == "__main__":
    result = app.invoke({
        "user_task": "write code to add two number in python",
        "plan": "",
        "research": "",
        "code": "",
        "review": "",
        "next": "",
        "messages": []
    })

    print("PLAN:\n", result["plan"])
    print("RESEARCH:\n", result["research"])
    print("CODE:\n", result["code"])
    print("REVIEW:\n", result["review"])
