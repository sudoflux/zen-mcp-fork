#!/usr/bin/env python3
"""Quick GPT-5 test"""

import os
from dotenv import load_dotenv

# Load the .env file from current directory
load_dotenv()

api_key = os.getenv('OPENAI_API_KEY')
print(f"API Key found: {api_key[:20]}..." if api_key else "No API key")

if api_key:
    try:
        import openai
        client = openai.OpenAI(api_key=api_key)
        
        print("Testing GPT-5...")
        response = client.chat.completions.create(
            model='gpt-5',
            messages=[{'role': 'user', 'content': 'Say "GPT-5 working!"'}],
            max_tokens=10
        )
        print(f"✅ Success: {response.choices[0].message.content}")
        
    except Exception as e:
        print(f"❌ Error: {e}")
else:
    print("❌ No API key configured in .env")