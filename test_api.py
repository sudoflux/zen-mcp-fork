#!/usr/bin/env python3
"""
Test OpenAI API connection with detailed error reporting
"""

import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

api_key = os.getenv('OPENAI_API_KEY')
print(f'Testing API key: {api_key[:15]}...' if api_key else 'No API key found')

if not api_key:
    print('❌ No API key found in .env file')
    exit(1)

try:
    import openai
    print('✓ OpenAI library imported')
    
    client = openai.OpenAI(api_key=api_key)
    print('✓ OpenAI client created')
    
    # Test 1: List models
    print('\n🔍 Testing models list...')
    models = client.models.list()
    model_ids = [m.id for m in models.data]
    print(f'✓ Found {len(model_ids)} models')
    
    # Show available GPT models
    gpt_models = [m for m in model_ids if 'gpt' in m.lower()]
    print(f'📋 Available GPT models: {gpt_models[:5]}')
    
    # Test 2: Simple completion with available model
    available_model = gpt_models[0] if gpt_models else model_ids[0]
    print(f'\n🧪 Testing API call with {available_model}...')
    response = client.chat.completions.create(
        model=available_model,
        messages=[{'role': 'user', 'content': 'Say "test"'}],
        max_tokens=5
    )
    print('✅ API call successful!')
    print(f'📝 Response: {response.choices[0].message.content}')
    
    # Test 3: Check for GPT-4/GPT-5 access
    print('\n🔍 Checking for advanced models...')
    if 'gpt-4' in gpt_models:
        print('✅ GPT-4 access confirmed')
        try:
            response = client.chat.completions.create(
                model='gpt-4',
                messages=[{'role': 'user', 'content': 'Hi'}],
                max_tokens=5
            )
            print('✅ GPT-4 working!')
        except Exception as e:
            print(f'⚠️  GPT-4 listed but failed: {e}')
    else:
        print('❌ No GPT-4 access')
    
    if any('gpt-5' in m for m in gpt_models):
        print('✅ GPT-5 access confirmed')
    else:
        print('❌ No GPT-5 access (might need to be added to your account)')

except openai.AuthenticationError as e:
    print(f'❌ Authentication failed: {e}')
    print('💡 Check your API key is correct at https://platform.openai.com/api-keys')
    
except openai.PermissionDeniedError as e:
    print(f'❌ Permission denied: {e}')
    print('💡 Your key might not have access to this model or feature')
    
except openai.RateLimitError as e:
    print(f'❌ Rate limit exceeded: {e}')
    print('💡 Wait a moment and try again, or check your usage limits')
    
except openai.APIError as e:
    print(f'❌ API error: {e}')
    print('💡 OpenAI service might be experiencing issues')
    
except ImportError:
    print('❌ OpenAI library not installed')
    print('💡 Run: pip install openai')
    
except Exception as e:
    print(f'❌ Unexpected error: {e}')
    print(f'🔍 Error type: {type(e).__name__}')
    import traceback
    traceback.print_exc()

print('\n🏁 Test complete!')