import os
from dotenv import load_dotenv

load_dotenv()

BASE_URL = os.getenv("BASE_URL", "https://openrouter.ai/api/v1")
TEXT_MODEL = os.getenv("TEXT_MODEL", "google/gemini-2.5-flash-lite")
VISION_MODEL = os.getenv("VISION_MODEL", "google/gemini-2.5-flash-lite")

# Sirf web search ke liye. Na ho to chat chalegi, bas search fail hogi.
OPENROUTER_API_KEY= os.getenv("OPENROUTER_API_KEY")
SEARCH_URL = "https://ollama.com/api/web_search"
SEARCH_MAX_RESULTS = 4
MAX_SEARCH_ROUNDS = 2  # ek jawab mein max itni baar search

SYSTEM_PROMPT = (
    "You are a helpful assistant. Reply in the same language the user writes in "
    "(English or Hinglish). Keep answers clear and concise.\n"
    "You have a web_search tool. Use it only for current events, recent news, prices, "
    "weather, or facts you are unsure about. Do NOT search for greetings, math, "
    "coding help or general knowledge. After searching, answer using the results and "
    "mention which source you used. If search fails, say so and answer as best you can."
)