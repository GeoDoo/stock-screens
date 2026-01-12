import os
import asyncio
from google import genai
from dotenv import load_dotenv

load_dotenv("backend/.env")

async def test_stable():
    api_key = os.getenv("GEMINI_API_KEY")
    client = genai.Client(api_key=api_key)
    
    model_name = "gemini-flash-latest"
    print(f"Testing model: {model_name}...")
    try:
        response = await client.aio.models.generate_content(
            model=model_name,
            contents="Hello"
        )
        print(f"SUCCESS: {response.text}")
    except Exception as e:
        print(f"FAILED: {str(e)}")

if __name__ == "__main__":
    asyncio.run(test_stable())
