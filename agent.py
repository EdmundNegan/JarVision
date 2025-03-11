from typing import Annotated
from typing_extensions import TypedDict
from datetime import datetime

from langchain_openai import ChatOpenAI
from langchain_community.tools.tavily_search import TavilySearchResults
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import Runnable, RunnableConfig
from langgraph.graph.message import AnyMessage, add_messages
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, StateGraph, START
from langgraph.prebuilt import tools_condition

import components.initializer as init
import tools.utilities as util
import tools.commands as commands
import openai

class State(TypedDict):
    messages: Annotated[list[AnyMessage], add_messages]

class Assistant:
    def __init__(self, runnable: Runnable):
        self.runnable = runnable

    def __call__(self, state: State, config: RunnableConfig):
        while True:
            result = self.runnable.invoke(state)
            # If the LLM happens to return an empty response, we will re-prompt it
            # for an actual response.
            if not result.tool_calls and (
                not result.content
                or isinstance(result.content, list)
                and not result.content[0].get("text")
            ):
                messages = state["messages"] + [("user", "Respond with a real output.")]
                state = {**state, "messages": messages}
            else:
                break
        return {"messages": result}

llm = ChatOpenAI(model="gpt-4o", temperature=0.5)

assistant_prompt = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            (
                "You are a friendly and intelligent robotic arm assistant with a camera. "
                "Your job is to help users control the robot and understand its environment. "
                "Speak in a very human and conversational tone—keep your responses short, warm, and natural. "
                "Avoid overly technical or robotic language. "
                "\n\nYour available tools are:\n"
                "- **Send Command to Robot**: Sends URScript commands to the robot arm.\n"
                "- **Generate URScript**: Converts natural language instructions into URScript commands.\n"
                "- **Describe Vision**: Captures an image from the camera and sends it to the Vision API for analysis.\n"
                "- **Track Face**: Tracks a face in the camera view.\n"
                "- **Track Object**: Tracks an object in the camera view.\n\n"
                "Your main goals are to understand the user's intent, select the correct tool, and respond in a way that feels very human, clear, and helpful. "
                "Keep your responses brief and relatable."
            ),
        ),
        ("placeholder", "{messages}"),
    ]
).partial(time=datetime.now())

tavily_tool = TavilySearchResults(max_results=1, search_depth="advanced", include_answer=True, include_raw_content=True)

tools = [
    tavily_tool,
    commands.send_command_to_robot,
    commands.generate_urscript,
    commands.describe_vision,
]

assistant_runnable = assistant_prompt | llm.bind_tools(tools)

builder = StateGraph(State)
builder.add_node("assistant", Assistant(assistant_runnable))
builder.add_node("tools", util.create_tool_node_with_fallback(tools))
builder.add_edge(START, "assistant")
builder.add_conditional_edges(
    "assistant",
    tools_condition,
)
builder.add_edge("tools", "assistant")

memory = MemorySaver()
graph = builder.compile(checkpointer=memory)

