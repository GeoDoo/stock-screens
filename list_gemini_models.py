import os
import asyncio
from google import genai
from dotenv import load_dotenv

load_dotenv("backend/.env")

async def list_models():
    api_key = os.getenv("GEMINI_API_KEY")
    client = genai.Client(api_key=api_key)
    
    print("Available Models:")
    try:
        # The new SDK models.list() returns a list, not an iterator
        models = await client.aio.models.list()
        for model in models:
            print(f" - {model.name}: {model.supported_actions}")
    except Exception as e:
        print(f"Error listing models: {str(e)}")

if __name__ == "__main__":
    asyncio.run(list_models())
