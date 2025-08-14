#!/bin/bash
set -euo pipefail

# ============================================================================
# GPT-5 + Claude Setup Script
# Specifically tailored for GPT-5 API access with Claude Desktop
# ============================================================================

readonly GREEN='\033[0;32m'
readonly YELLOW='\033[1;33m'
readonly RED='\033[0;31m'
readonly BLUE='\033[0;34m'
readonly NC='\033[0m'

print_success() { echo -e "${GREEN}✓${NC} $1" >&2; }
print_error() { echo -e "${RED}✗${NC} $1" >&2; }
print_warning() { echo -e "${YELLOW}!${NC} $1" >&2; }
print_info() { echo -e "${BLUE}ℹ${NC} $1" >&2; }

main() {
    local script_dir="$(cd "$(dirname "$0")" && pwd)"
    cd "$script_dir"

    print_info "🚀 GPT-5 + Claude Setup"
    print_info "=========================="
    print_info "Tailored for GPT-5 API access with Claude Desktop"
    print_info ""

    # Step 1: Python setup
    print_info "Step 1: Setting up Python environment"
    local python_cmd="python3"
    
    if ! command -v python3 &> /dev/null; then
        print_error "Python 3 not found. Install with: sudo apt install python3 python3-pip python3-venv"
        exit 1
    fi
    
    # Create virtual environment
    if [[ ! -d ".zen_venv" ]]; then
        $python_cmd -m venv .zen_venv
        print_success "Created virtual environment"
    fi
    
    source .zen_venv/bin/activate
    pip install --upgrade pip > /dev/null 2>&1
    pip install -r requirements.txt > /dev/null 2>&1
    print_success "Dependencies installed"

    # Step 2: Configure for GPT-5
    print_info "\nStep 2: GPT-5 Configuration"
    
    if [[ ! -f ".env" ]]; then
        cat > .env << 'EOF'
# GPT-5 Configuration
OPENAI_API_KEY=your_openai_api_key_here
DEFAULT_MODEL=gpt-5
ENABLE_GPT5=true
GPT5_DEFAULT_THINKING_MODE=high
GPT5_MAX_REASONING_TOKENS=12000
LOG_LEVEL=INFO
EOF
        print_warning "Created .env file - please add your OpenAI API key"
    fi
    
    # Check API key
    if grep -q "your_openai_api_key_here" .env; then
        print_info ""
        read -p "Enter your OpenAI API key (sk-proj-...): " api_key
        if [[ -n "$api_key" ]]; then
            sed -i "s/OPENAI_API_KEY=.*/OPENAI_API_KEY=$api_key/" .env
            print_success "API key configured"
        fi
    fi
    
    # Test GPT-5 connection
    print_info "Testing GPT-5 connection..."
    if python3 -c "
import os
import sys
sys.path.insert(0, '$script_dir')
from dotenv import load_dotenv
load_dotenv('$script_dir/.env')
import openai
api_key = os.getenv('OPENAI_API_KEY')
if not api_key:
    print('No API key found')
    exit(1)
client = openai.OpenAI(api_key=api_key)
response = client.chat.completions.create(
    model='gpt-5',
    messages=[{'role': 'user', 'content': 'Hello GPT-5'}],
    max_completion_tokens=10
)
print('GPT-5 Response:', response.choices[0].message.content)
" 2>/dev/null; then
        print_success "GPT-5 connection working!"
    else
        print_error "GPT-5 connection failed. Check your API key."
        exit 1
    fi

    # Step 3: Claude Desktop setup
    print_info "\nStep 3: Claude Desktop Configuration"
    
    # Check if Claude is installed
    if ! command -v claude &> /dev/null; then
        print_info "Installing Claude Desktop..."
        
        # Download and install Claude AppImage for Linux
        mkdir -p ~/.local/bin
        curl -L "https://storage.googleapis.com/osprey-downloads-c02f6a0d-347c-492b-a752-3e0651722e97/nest-linux-x64/claude-desktop.AppImage" \
             -o ~/.local/bin/claude.AppImage 2>/dev/null
        chmod +x ~/.local/bin/claude.AppImage
        ln -sf ~/.local/bin/claude.AppImage ~/.local/bin/claude
        
        # Add to PATH
        if [[ ":$PATH:" != *":$HOME/.local/bin:"* ]]; then
            echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.bashrc
            export PATH="$HOME/.local/bin:$PATH"
        fi
        
        print_success "Claude Desktop installed"
    else
        print_success "Claude Desktop found"
    fi

    # Step 4: Configure MCP
    print_info "\nStep 4: MCP Configuration"
    
    mkdir -p ~/.config/claude
    cat > ~/.config/claude/claude_desktop_config.json << EOF
{
  "mcpServers": {
    "gpt5": {
      "command": "$script_dir/.zen_venv/bin/python",
      "args": ["$script_dir/server_gpt5.py"],
      "cwd": "$script_dir",
      "env": {
        "PYTHONPATH": "$script_dir"
      }
    }
  }
}
EOF
    print_success "MCP configured for GPT-5 server"

    # Create convenience scripts
    cat > start-claude.sh << 'EOF'
#!/bin/bash
cd "$(dirname "$0")"
echo "🚀 Starting Claude with GPT-5 tools..."
claude
EOF
    chmod +x start-claude.sh

    cat > test-gpt5.py << 'EOF'
#!/usr/bin/env python3
import asyncio
import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

async def test_tools():
    from tools.chat import ChatTool
    tool = ChatTool()
    result = await tool.execute({
        "prompt": "List 3 key features of GPT-5",
        "model": "gpt-5"
    })
    print("✅ GPT-5 tools working!")
    print("Response:", result[0]["text"][:100] + "...")

if __name__ == "__main__":
    asyncio.run(test_tools())
EOF
    chmod +x test-gpt5.py

    # Final summary
    print_info "\n🎉 Setup Complete!"
    print_info "=================="
    print_success "GPT-5 + Claude configured and ready!"
    print_info ""
    print_info "Quick start:"
    print_info "  1. Start Claude: ./start-claude.sh"
    print_info "  2. Test tools: python3 test-gpt5.py"
    print_info ""
    print_info "In Claude, try:"
    print_info '  "Use chat to analyze this Python code structure"'
    print_info '  "Use debug to help troubleshoot this error"'
    print_info '  "Use codereview with GPT-5 reasoning mode"'
    print_info ""
    print_info "Available GPT-5 optimized tools:"
    print_info "  • chat - GPT-5 collaborative thinking"
    print_info "  • debug - Advanced debugging with 12K reasoning tokens"
    print_info "  • codereview - Deep code analysis"
    print_info "  • analyze - Full codebase understanding"
    print_info "  • refactor - Intelligent restructuring"
    print_info "  • planner - Complex project planning"
    print_info ""
    print_success "All tools configured for GPT-5's 400K context + 128K output!"
}

main "$@"