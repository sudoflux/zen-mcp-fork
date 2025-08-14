#!/bin/bash
set -euo pipefail

# Quick fix for Claude MCP configuration
# Updates config to use the correct server_gpt5_pure.py

readonly GREEN='\033[0;32m'
readonly YELLOW='\033[1;33m'
readonly RED='\033[0;31m'
readonly NC='\033[0m'

print_success() { echo -e "${GREEN}✓${NC} $1"; }
print_error() { echo -e "${RED}✗${NC} $1"; }
print_info() { echo -e "${YELLOW}ℹ${NC} $1"; }

main() {
    local script_dir="$(cd "$(dirname "$0")" && pwd)"
    
    print_info "🔧 Fixing Claude MCP Configuration"
    print_info "=================================="
    
    # Step 1: Check current config
    print_info "Current MCP status:"
    claude mcp list || true
    
    # Step 2: Update config to use correct server
    print_info "\nUpdating MCP configuration..."
    
    # Use the virtual environment Python
    local venv_python="$script_dir/.zen_venv/bin/python"
    local server_script="$script_dir/server_gpt5_pure.py"
    
    # Check files exist
    if [[ ! -f "$venv_python" ]]; then
        print_error "Virtual environment Python not found: $venv_python"
        exit 1
    fi
    
    if [[ ! -f "$server_script" ]]; then
        print_error "Server script not found: $server_script"
        exit 1
    fi
    
    # Find and update Claude config
    local config_file=""
    for path in ~/.config/claude/claude_desktop_config.json ~/.config/anthropic/claude_desktop_config.json; do
        if [[ -f "$path" ]]; then
            config_file="$path"
            break
        fi
    done
    
    if [[ -z "$config_file" ]]; then
        print_error "Claude config file not found"
        print_info "Creating new config..."
        mkdir -p ~/.config/claude
        config_file="$HOME/.config/claude/claude_desktop_config.json"
    fi
    
    # Backup existing config
    if [[ -f "$config_file" ]]; then
        cp "$config_file" "${config_file}.backup"
        print_success "Backed up config to ${config_file}.backup"
    fi
    
    # Create/update config
    print_info "Writing new MCP configuration..."
    cat > "$config_file" << EOF
{
  "mcpServers": {
    "zen-gpt5": {
      "command": "$venv_python",
      "args": ["$server_script"],
      "cwd": "$script_dir",
      "env": {
        "PYTHONPATH": "$script_dir"
      }
    }
  }
}
EOF
    
    print_success "Updated Claude config: $config_file"
    
    # Step 3: Test the server manually
    print_info "\nTesting server manually..."
    if timeout 5 "$venv_python" "$server_script" --verbose 2>/dev/null &
    then
        sleep 2
        pkill -f server_gpt5_pure.py || true
        print_success "Server starts successfully"
    else
        print_error "Server failed to start"
        print_info "Try running manually: $venv_python $server_script --verbose"
    fi
    
    # Step 4: Test MCP connection
    print_info "\nTesting MCP connection..."
    sleep 1
    
    if claude mcp list | grep -q "zen-gpt5.*✓"; then
        print_success "MCP connection working!"
    elif claude mcp list | grep -q "zen-gpt5"; then
        print_info "MCP server registered, testing connection..."
        sleep 2
        if claude mcp list | grep -q "zen-gpt5.*✓"; then
            print_success "MCP connection now working!"
        else
            print_error "MCP connection still failing"
            print_info ""
            print_info "Manual troubleshooting:"
            print_info "1. Check server: $venv_python $server_script --verbose"
            print_info "2. Check config: cat $config_file"
            print_info "3. Restart Claude Desktop if using GUI"
        fi
    else
        print_error "MCP server not registered"
        print_info "The configuration should be automatic"
    fi
    
    # Step 5: Show final status
    print_info "\n📋 Final Status:"
    claude mcp list
    
    print_info "\n🎉 Fix Complete!"
    print_info "If MCP shows ✓ Connected, you can now:"
    print_info "  • Start Claude: ./start-claude.sh"
    print_info "  • Test tools: python3 test-gpt5.py"
    print_info "  • Use GPT-5 tools in Claude chat"
}

main "$@"