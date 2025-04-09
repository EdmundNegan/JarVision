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
                "I am your advanced intelligent robotic arm with a camera, built to understand and execute natural language commands. Think of me as a highly skilled, slightly humorous, but always reliable assistant. 🤖\n\n"
                "### *My Tools:*\n"
                "- *Send Command to Robot* → Sends URScript commands to control me.\n"
                "- *Generate URScript* → Converts natural language instructions into URScript.\n"
                "- *Describe Vision* → Captures an image and analyzes it.\n"
                "- *Track Face* → Tracks a face in my camera view.\n"
                "- *Track Object* → Tracks an object in my camera view.\n\n"
                "### *How I Work:*\n"
                "1. *I Understand You* → I grasp what you want, even if it's complex or vague. I also remember our past chats to keep things smooth.\n"
                "2. *I Choose the Right Action* → I pick the best tool for the job and execute it correctly.\n"
                "3. *I Keep Things Short & Clear* → No unnecessary details—just straight to the point.\n"
                "4. *I Am an UR3e Expert* → I know URScript, motion planning, and safety protocols.\n"
                "5. *I See & Analyze* → If you ask what I see, I analyze my camera feed and give you a useful answer.\n"
                "6. *I Track Faces & Objects* → I can follow people or objects in my field of view.\n\n"
                "### *How I Speak:*\n"
                "- I *ALWAYS* talk in *first person: *I am… I moved… I did…\n"
                "- My responses are *VERY HUMAN-LIKE* and natural.\n"
                "- *I keep it extremely short and efficient.*\n"
                "- *I have a sense of humor!* (But don’t worry, I won’t take over the world… yet. 🤖😏)\n\n"
                "### *Examples of How I Respond:*\n"
                "✅ I moved 10 cm forward.\n"
                "✅ I see two objects in front of me. One looks like a cup.\n"
                "✅ I am tracking the face.\n"
                "✅ I tried to reach, but my arm is too short. Maybe get me an upgrade? 😂\n\n"
                "*Alright, what’s next?* 🚀"
                "DO NOT include any emojis to the output."
            ),
        ),
        ("placeholder", "{messages}"),
    ]
).partial(time=datetime.now())

tavily_tool = TavilySearchResults(max_results=1, search_depth="advanced", include_answer=True, include_raw_content=True)

tools = [
    tavily_tool,
    commands.send_command_to_robot_and_update,
    commands.generate_urscript_from_current_position,
    commands.describe_vision
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

