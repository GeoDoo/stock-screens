import os
import asyncio
from google import genai
from dotenv import load_dotenv

# Load .env from backend directory
load_dotenv("backend/.env")

async def test_key():
    api_key = os.getenv("GEMINI_API_KEY")
    print(f"Using API Key: {api_key[:10]}...")
    
    client = genai.Client(api_key=api_key)
    
    # Try multiple common model names to find which one works
    models = ["gemini-1.5-flash", "gemini-2.0-flash-exp", "gemini-2.0-flash"]
    
    for model_name in models:
        print(f"\nTesting model: {model_name}...")
        try:
            response = await client.aio.models.generate_content(
                model=model_name,
                contents="Hello, are you working?"
            )
            print(f"SUCCESS with {model_name}: {response.text}")
            return
        except Exception as e:
            print(f"FAILED with {model_name}: {str(e)}")

if __name__ == "__main__":
    asyncio.run(test_key())
