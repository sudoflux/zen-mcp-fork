#!/usr/bin/env python3
"""
GPT-5 Parameter Patch

Fixes parameter differences between GPT-4 and GPT-5 API calls.
GPT-5 uses max_completion_tokens instead of max_tokens.
"""

import os
import re

def patch_openai_files():
    """Patch OpenAI-related files to use GPT-5 parameters correctly."""
    
    files_to_patch = [
        "providers/openai_compatible.py",
        "test_api.py",
        "server_gpt5_pure.py",
    ]
    
    print("🔧 Patching files for GPT-5 compatibility...")
    
    for file_path in files_to_patch:
        if os.path.exists(file_path):
            print(f"  Patching {file_path}...")
            
            with open(file_path, 'r') as f:
                content = f.read()
            
            # Replace max_tokens with max_completion_tokens for GPT-5
            # But only in GPT-5 specific contexts
            original_content = content
            
            # Pattern 1: Direct max_tokens parameter
            content = re.sub(
                r'(model=[\'"](gpt-5[^\'"]*)[\'"],[^}]*?)max_tokens=',
                r'\1max_completion_tokens=',
                content
            )
            
            # Pattern 2: In parameter dictionaries
            content = re.sub(
                r'("max_tokens":\s*\d+)',
                r'"max_completion_tokens": \1'.replace('"max_tokens": ', ''),
                content
            )
            
            if content != original_content:
                with open(file_path, 'w') as f:
                    f.write(content)
                print(f"    ✓ Patched {file_path}")
            else:
                print(f"    - No changes needed in {file_path}")
    
    print("✅ GPT-5 parameter patching complete!")

def create_gpt5_wrapper():
    """Create a wrapper that handles GPT-5 parameter differences."""
    
    wrapper_code = '''
def gpt5_chat_completion(client, **kwargs):
    """Wrapper for GPT-5 chat completions with correct parameters."""
    
    # Convert max_tokens to max_completion_tokens for GPT-5
    if "model" in kwargs and "gpt-5" in kwargs["model"]:
        if "max_tokens" in kwargs:
            kwargs["max_completion_tokens"] = kwargs.pop("max_tokens")
    
    return client.chat.completions.create(**kwargs)
'''
    
    with open("gpt5_utils.py", "w") as f:
        f.write(wrapper_code)
    
    print("✅ Created gpt5_utils.py wrapper")

if __name__ == "__main__":
    patch_openai_files()
    create_gpt5_wrapper()
    print("\n🎉 GPT-5 compatibility patches applied!")
    print("You can now run: python3 quick-test-gpt5.py")