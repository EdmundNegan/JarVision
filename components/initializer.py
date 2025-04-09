import os

# initialize ip address of robot
HOST = os.getenv("HOST")
PORT = os.getenv("PORT")

# initialize OpenAI
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
DEFAULT_CHAT_MODEL = "gpt-4o"

# initialize Tavily 
TAVILY_API_KEY = os.getenv("TAVILY_API_KEY")

# initialize Vosk
VOSK_MODEL = os.getenv("VOSK_MODEL")

