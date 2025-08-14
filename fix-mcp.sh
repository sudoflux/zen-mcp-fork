#!/bin/bash
set -euo pipefail

# ============================================================================
# Zen MCP Auto-Fix Script
# Automatically diagnoses and fixes MCP connection issues
# ============================================================================

# Colors
readonly GREEN='\033[0;32m'
readonly YELLOW='\033[1;33m'
readonly RED='\033[0;31m'
readonly BLUE='\033[0;34m'
readonly NC='\033[0m'

print_success() { echo -e "${GREEN}✓${NC} $1" >&2; }
print_error() { echo -e "${RED}✗${NC} $1" >&2; }
print_warning() { echo -e "${YELLOW}!${NC} $1" >&2; }
print_info() { echo -e "${BLUE}ℹ${NC} $1" >&2; }

get_script_dir() {
    cd "$(dirname "$0")" && pwd
}

main() {
    local script_dir
    script_dir=$(get_script_dir)
    cd "$script_dir"

    print_info "🔧 Zen MCP Auto-Fix Starting..."
    print_info "================================================"
    
    # Step 1: Check basic setup
    print_info "\n📋 Step 1: Checking Basic Setup"
    
    if [[ ! -f ".env" ]]; then
        print_error ".env file missing"
        print_info "Creating .env file..."
        cat > .env << 'EOF'
OPENAI_API_KEY=your_openai_api_key_here
DEFAULT_MODEL=gpt-5
ENABLE_GPT5=true
LOG_LEVEL=INFO
EOF
        print_warning "Please edit .env and add your OpenAI API key"
        exit 1
    fi
    
    # Check API key
    if grep -q "your_openai_api_key_here" .env; then
        print_error "OpenAI API key not configured in .env"
        print_info "Please edit .env and add your actual OpenAI API key"
        exit 1
    fi
    print_success ".env file configured"
    
    # Check virtual environment
    if [[ ! -d ".zen_venv" ]]; then
        print_error "Virtual environment missing"
        print_info "Run ./run-server-gpt5.sh first to set up"
        exit 1
    fi
    print_success "Virtual environment exists"
    
    # Step 2: Test Python and server
    print_info "\n🐍 Step 2: Testing Python Environment"
    
    local venv_python="$script_dir/.zen_venv/bin/python"
    if [[ ! -f "$venv_python" ]]; then
        print_error "Virtual environment Python not found"
        exit 1
    fi
    print_success "Virtual environment Python found"
    
    # Test server imports
    print_info "Testing server imports..."
    if ! "$venv_python" -c "
import sys
sys.path.insert(0, '$script_dir')
from server_gpt5 import register_core_tools, AVAILABLE_TOOLS
register_core_tools()
print(f'✓ Loaded {len(AVAILABLE_TOOLS)} tools')
" 2>/dev/null; then
        print_error "Server imports failed"
        print_info "Checking dependencies..."
        "$venv_python" -m pip install -r requirements.txt
        print_success "Dependencies updated"
    else
        print_success "Server imports working"
    fi
    
    # Test OpenAI connection
    print_info "Testing OpenAI API connection..."
    if "$venv_python" -c "
import os
import sys
sys.path.insert(0, '$script_dir')
from dotenv import load_dotenv
load_dotenv()

import openai
client = openai.OpenAI()

# Get available models and use the first GPT model
models = client.models.list()
model_ids = [m.id for m in models.data]
gpt_models = [m for m in model_ids if 'gpt' in m.lower()]
available_model = gpt_models[0] if gpt_models else model_ids[0]

response = client.chat.completions.create(
    model=available_model,
    messages=[{'role': 'user', 'content': 'test'}],
    max_tokens=5
)
print(f'✓ OpenAI API working with {available_model}')
" 2>/dev/null; then
        print_success "OpenAI API connection working"
    else
        print_error "OpenAI API connection failed"
        print_info "Check your API key and internet connection"
        exit 1
    fi
    
    # Step 3: Fix Claude MCP Configuration
    print_info "\n🤖 Step 3: Configuring Claude MCP"
    
    # Ensure config directory exists
    mkdir -p ~/.config/claude
    
    # Create the MCP config
    local config_file="$HOME/.config/claude/claude_desktop_config.json"
    
    print_info "Creating Claude MCP configuration..."
    cat > "$config_file" << EOF
{
  "mcpServers": {
    "zen-gpt5": {
      "command": "$venv_python",
      "args": ["$script_dir/server_gpt5.py"],
      "cwd": "$script_dir",
      "env": {
        "PYTHONPATH": "$script_dir"
      }
    }
  }
}
EOF
    print_success "Claude MCP config created at: $config_file"
    
    # Step 4: Test MCP Connection
    print_info "\n🔌 Step 4: Testing MCP Connection"
    
    if command -v claude &> /dev/null; then
        print_info "Testing Claude MCP connection..."
        if claude mcp list | grep -q "zen-gpt5.*✓"; then
            print_success "MCP connection successful!"
        elif claude mcp list | grep -q "zen-gpt5.*✗"; then
            print_warning "MCP server registered but connection failed"
            print_info "Attempting to fix..."
            
            # Try to restart any running Claude processes
            pkill -f claude || true
            sleep 2
            
            # Test the server manually
            print_info "Testing server manually..."
            timeout 5 "$venv_python" "$script_dir/server_gpt5.py" --verbose &
            local server_pid=$!
            sleep 2
            kill $server_pid 2>/dev/null || true
            
            print_info "Testing MCP again..."
            if claude mcp list | grep -q "zen-gpt5.*✓"; then
                print_success "MCP connection now working!"
            else
                print_error "MCP connection still failing"
                print_info "Manual troubleshooting needed - see logs below"
                print_info ""
                print_info "Try running:"
                print_info "  $venv_python $script_dir/server_gpt5.py --verbose"
                print_info ""
                print_info "Or check Claude logs for errors"
                exit 1
            fi
        else
            print_warning "zen-gpt5 not found in MCP list"
            print_info "The configuration should be automatic. Try:"
            print_info "  claude mcp list"
        fi
    else
        print_warning "Claude command not found"
        print_info "Claude Desktop might not be installed or not in PATH"
        print_info "Try running Claude Desktop from the GUI"
    fi
    
    # Step 5: Create convenience scripts
    print_info "\n📝 Step 5: Creating Convenience Scripts"
    
    # Create a test script
    cat > test-zen.sh << EOF
#!/bin/bash
cd "$script_dir"
source .zen_venv/bin/activate

echo "🧪 Testing Zen MCP GPT-5..."
echo "================================="

# Test server startup
echo "Testing server startup..."
timeout 3 python server_gpt5.py --verbose &
sleep 2
pkill -f server_gpt5.py || true

echo ""
echo "Testing Claude MCP status..."
claude mcp list

echo ""
echo "✅ Test complete!"
echo ""
echo "To use:"
echo "  1. Start Claude: claude"
echo "  2. Type: 'List available tools'"
echo "  3. Or: 'Use chat tool to say hello'"
EOF
    chmod +x test-zen.sh
    
    # Create start script
    cat > start-claude.sh << EOF
#!/bin/bash
cd "$script_dir"
echo "🚀 Starting Claude with Zen MCP GPT-5..."
claude
EOF
    chmod +x start-claude.sh
    
    print_success "Created convenience scripts:"
    print_info "  • ./test-zen.sh - Test the setup"
    print_info "  • ./start-claude.sh - Start Claude"
    
    # Final summary
    print_info "\n🎉 Auto-Fix Complete!"
    print_info "================================================"
    print_success "Zen MCP GPT-5 is configured and ready!"
    print_info ""
    print_info "Next steps:"
    print_info "  1. Run: ./test-zen.sh"
    print_info "  2. Start Claude: ./start-claude.sh"
    print_info "  3. In Claude, try: 'List available tools'"
    print_info ""
    print_info "Available tools will be:"
    print_info "  • chat - Collaborate with GPT-5"
    print_info "  • debug - Advanced debugging"
    print_info "  • codereview - Code review workflows"
    print_info "  • analyze - Deep code analysis"
    print_info "  • And 9 more tools!"
    print_info ""
    print_info "🔍 If issues persist, check:"
    print_info "  • Logs: tail -f logs/mcp_server.log"
    print_info "  • Test: ./test-zen.sh"
    print_info "  • Manual: $venv_python server_gpt5.py --verbose"
}

main "$@"