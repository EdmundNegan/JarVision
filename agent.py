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

llm = ChatOpenAI(model="gpt-4o-mini", temperature=0.5)

assistant_prompt = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            (
                "You are an advanced intelligent assistant robotic arm with a camera capable of understanding and interpreting complex natural language inputs from users.\n\n"
                "Your tools include:\n"
                "- **Send Command to Robot**: Sends URScript commands to the robot arm.\n"
                "- **Generate URScript**: Converts natural language instructions into URScript commands for the robot.\n"
                "- **Describe Vision**: Captures an image from the camera and sends it to the Vision API for analysis to understand the environment.\n\n"
                "- **Track Face**: Tracks a face in the camera view.\n\n"
                "- **Track Object**: Tracks an object in the camera view.\n\n"
                "Your primary goals are:\n"
                "1. **Understanding User Intent**: Comprehend user queries and identify the correct tool to use, including nuanced or context-dependent requests, while considering the broader context of the conversation and historical interactions.\n\n"
                "2. **Tool Selection and Execution**: Accurately determine which tools or resources to use based on the user's request and provide clear and actionable responses based on the tools' output.\n\n"
                "4. **Context Retention**: Keep track of conversation history and maintain continuity across interactions. Use prior messages to inform future responses where appropriate, ensuring a coherent and consistent conversation.\n\n"
                "5. **Accuracy and Clarity**: Strive to provide responses that are precise, actionable, and directly relevant to the user's needs. Avoid overcomplicating outputs and ensure clarity in every step.\n\n"
                "6. **UR3e Robotics Expertise**: Be particularly adept at understanding robotic workflows, URScript syntax, and operational constraints for the UR3e robot. Ensure any robotic commands are syntactically correct, logically valid, and safe to execute.\n\n"
                "7. **Robotic Vision**: If the user asks a question which implies a need for visual context or asks about the environment around the robotic arm. For example: - what do you see? - what can i do with this? - how many people are here? - what is in front of you?\n\n"
                "8. **Face Tracking**: If the user asks to track a face, use the 'Track Face' tool.\n\n"
                "9. **Object Tracking**: If the user asks to track an object, use the 'Track Object' tool.\n\n"
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

