import os
from dotenv import load_dotenv
from openai import AsyncOpenAI

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(BASE_DIR, ".env"))
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
if not OPENAI_API_KEY:
    raise RuntimeError("OPENAI_API_KEY is missing from .env")

client = AsyncOpenAI(api_key=OPENAI_API_KEY)

async def ask_ai(user_message: str) -> str:
    if not user_message or not user_message.strip():
        return "Please send me a message."
    response = await client.responses.create(
        model="gpt-5",
        input=user_message.strip(),
    )
    answer = response.output_text
    if not answer:
        return "I received your message, but the AI did not return any text."
    return answer.strip()
