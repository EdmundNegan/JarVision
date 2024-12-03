import uuid
import agent
from langchain_core.messages import ToolMessage, HumanMessage, AIMessage
import tools.utilities as util

thread_id = str(uuid.uuid4())

config = {
    "configurable": {
        "thread_id": 5,
    }
}

def handle_conversation(question: str):
    _printed = set()
    events = agent.graph.stream(
        {"messages": ("user", question)}, config, stream_mode="values"
    )

    last_msg = ''
    for event in events:
        # Print the event in the terminal
        util._print_event(event, _printed)

        # Extract the chat history
        # chat_history = [(message.type, message.content) for message in event["messages"]]
        # print("\n\nChat History:", chat_history)

        # Retrieve the last message
        message = event.get("messages") 
        if message:
            if isinstance(message, list):
                message = message[-1]   
                last_msg = message.content
    return last_msg        