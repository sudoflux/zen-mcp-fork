#!/bin/bash
set -euo pipefail

# ============================================================================
# Zen MCP Server Setup Script - GPT-5 + Claude Edition
#
# Simplified setup for GPT-5 via OpenAI API with Claude orchestration
# ============================================================================

# ----------------------------------------------------------------------------
# Constants and Configuration
# ----------------------------------------------------------------------------

# Colors for output
readonly GREEN='\033[0;32m'
readonly YELLOW='\033[1;33m'
readonly RED='\033[0;31m'
readonly NC='\033[0m' # No Color

# Configuration
readonly VENV_PATH=".zen_venv"
readonly LOG_DIR="logs"
readonly LOG_FILE="mcp_server.log"

# ----------------------------------------------------------------------------
# Utility Functions
# ----------------------------------------------------------------------------

print_success() {
    echo -e "${GREEN}✓${NC} $1" >&2
}

print_error() {
    echo -e "${RED}✗${NC} $1" >&2
}

print_warning() {
    echo -e "${YELLOW}!${NC} $1" >&2
}

print_info() {
    echo -e "${YELLOW}$1${NC}" >&2
}

# Get the script's directory
get_script_dir() {
    cd "$(dirname "$0")" && pwd
}

# Extract version from config.py
get_version() {
    grep -E '^__version__ = ' config.py 2>/dev/null | sed 's/__version__ = "\(.*\)"/\1/' || echo "unknown"
}

# Clear Python cache files
clear_python_cache() {
    print_info "Clearing Python cache files..."
    find . -name "*.pyc" -delete 2>/dev/null || true
    find . -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null || true
    print_success "Python cache cleared"
}

# ----------------------------------------------------------------------------
# Python Setup Functions
# ----------------------------------------------------------------------------

find_python() {
    local required_version="3.9"
    local python_cmd=""
    
    # Try various Python commands
    for cmd in python3.12 python3.11 python3.10 python3.9 python3 python; do
        if command -v "$cmd" &> /dev/null; then
            local version
            version=$("$cmd" -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
            if [[ $(echo "$version >= $required_version" | bc -l) -eq 1 ]]; then
                python_cmd="$cmd"
                break
            fi
        fi
    done
    
    if [[ -z "$python_cmd" ]]; then
        print_error "Python 3.9+ not found"
        print_info "Please install Python 3.9 or higher"
        exit 1
    fi
    
    echo "$python_cmd"
}

setup_venv() {
    local python_cmd="$1"
    
    if [[ -d "$VENV_PATH" ]]; then
        print_info "Virtual environment already exists"
        # Check if it's valid
        if [[ -f "$VENV_PATH/bin/python" ]] || [[ -f "$VENV_PATH/Scripts/python.exe" ]]; then
            print_success "Using existing virtual environment"
        else
            print_warning "Virtual environment appears corrupted, recreating..."
            rm -rf "$VENV_PATH"
            "$python_cmd" -m venv "$VENV_PATH"
            print_success "Virtual environment recreated"
        fi
    else
        print_info "Creating virtual environment..."
        "$python_cmd" -m venv "$VENV_PATH"
        print_success "Virtual environment created"
    fi
}

activate_venv() {
    if [[ -f "$VENV_PATH/bin/activate" ]]; then
        source "$VENV_PATH/bin/activate"
    elif [[ -f "$VENV_PATH/Scripts/activate" ]]; then
        source "$VENV_PATH/Scripts/activate"
    else
        print_error "Failed to activate virtual environment"
        exit 1
    fi
}

install_dependencies() {
    print_info "Installing dependencies..."
    
    # Upgrade pip first
    pip install --upgrade pip &> /dev/null
    
    # Install requirements
    if [[ -f "requirements.txt" ]]; then
        pip install -r requirements.txt &> /dev/null
        print_success "Dependencies installed"
    else
        print_error "requirements.txt not found"
        exit 1
    fi
}

# ----------------------------------------------------------------------------
# Configuration Functions
# ----------------------------------------------------------------------------

setup_env_file() {
    if [[ ! -f ".env" ]]; then
        print_info "Creating .env file for GPT-5 configuration..."
        
        # Create minimal .env with only OpenAI
        cat > .env << 'EOF'
# GPT-5 Configuration (via OpenAI API)
OPENAI_API_KEY=your_openai_api_key_here

# Optional: Specify default model
DEFAULT_MODEL=gpt-5

# Optional: Feature flags for GPT-5 optimizations
ENABLE_GPT5=true
GPT5_DEFAULT_THINKING_MODE=medium
GPT5_MAX_REASONING_TOKENS=12000

# Logging
LOG_LEVEL=INFO
EOF
        print_success ".env file created"
        print_warning "Please edit .env and add your OpenAI API key"
        return 1
    else
        # Check if OpenAI key is configured
        if grep -q "OPENAI_API_KEY=your_openai_api_key_here" .env 2>/dev/null; then
            print_warning "OpenAI API key not configured in .env"
            return 1
        fi
        print_success ".env file exists with configuration"
        return 0
    fi
}

prompt_for_api_key() {
    print_info ""
    print_info "=== GPT-5 Setup ==="
    print_info "This server uses GPT-5 via OpenAI API for enhanced capabilities"
    print_info ""
    
    read -p "Enter your OpenAI API key (or press Enter to skip): " api_key
    
    if [[ -n "$api_key" ]]; then
        # Update .env file
        if [[ -f ".env" ]]; then
            sed -i.bak "s/OPENAI_API_KEY=.*/OPENAI_API_KEY=$api_key/" .env
            rm -f .env.bak
        else
            echo "OPENAI_API_KEY=$api_key" > .env
        fi
        print_success "OpenAI API key configured"
        return 0
    else
        print_warning "Skipping API key configuration"
        print_info "You can add it later by editing the .env file"
        return 1
    fi
}

setup_mcp_config() {
    local script_dir="$1"
    
    print_info ""
    print_info "=== MCP Configuration for Claude ==="
    print_info ""
    
    # Detect Claude config location
    local config_dir=""
    if [[ "$OSTYPE" == "darwin"* ]]; then
        config_dir="$HOME/Library/Application Support/Claude"
    elif [[ "$OSTYPE" == "msys" ]] || [[ "$OSTYPE" == "cygwin" ]] || [[ "$OSTYPE" == "win32" ]]; then
        config_dir="$APPDATA/Claude"
    else
        config_dir="$HOME/.config/claude"
    fi
    
    local config_file="$config_dir/claude_desktop_config.json"
    
    if [[ ! -f "$config_file" ]]; then
        print_warning "Claude Desktop config not found at: $config_file"
        print_info "Please ensure Claude Desktop is installed"
        print_info ""
        print_info "You'll need to manually add this to your Claude config:"
        print_info ""
        cat << EOF
{
  "mcpServers": {
    "zen-mcp-gpt5": {
      "command": "python",
      "args": ["$script_dir/server.py"],
      "cwd": "$script_dir",
      "env": {
        "PYTHONPATH": "$script_dir"
      }
    }
  }
}
EOF
        return 1
    else
        print_success "Found Claude Desktop config"
        print_info "MCP server will be available in Claude after restart"
    fi
}

# ----------------------------------------------------------------------------
# Log Management
# ----------------------------------------------------------------------------

setup_logs() {
    if [[ ! -d "$LOG_DIR" ]]; then
        mkdir -p "$LOG_DIR"
        print_success "Created log directory"
    fi
    
    # Create/clear log file
    > "$LOG_DIR/$LOG_FILE"
    print_success "Log file ready: $LOG_DIR/$LOG_FILE"
}

show_logs() {
    if [[ "$1" == "-f" ]] || [[ "$1" == "--follow" ]]; then
        print_info "Following logs (Ctrl+C to stop)..."
        tail -f "$LOG_DIR/$LOG_FILE"
    else
        print_info "Recent logs:"
        tail -n 50 "$LOG_DIR/$LOG_FILE"
    fi
}

# ----------------------------------------------------------------------------
# Main Setup Flow
# ----------------------------------------------------------------------------

main() {
    local script_dir
    script_dir=$(get_script_dir)
    cd "$script_dir"
    
    # Check for log viewing mode
    if [[ "${1:-}" == "-f" ]] || [[ "${1:-}" == "--follow" ]] || [[ "${1:-}" == "-l" ]] || [[ "${1:-}" == "--logs" ]]; then
        show_logs "$1"
        exit 0
    fi
    
    print_info "================================================"
    print_info " Zen MCP Server - GPT-5 + Claude Edition"
    print_info " Version: $(get_version)"
    print_info "================================================"
    print_info ""
    
    # Step 1: Python setup
    print_info "Step 1: Python Setup"
    python_cmd=$(find_python)
    print_success "Found Python: $python_cmd"
    
    setup_venv "$python_cmd"
    activate_venv
    
    # Step 2: Dependencies
    print_info ""
    print_info "Step 2: Installing Dependencies"
    install_dependencies
    
    # Step 3: Configuration
    print_info ""
    print_info "Step 3: Configuration"
    
    setup_logs
    
    if ! setup_env_file; then
        prompt_for_api_key
    fi
    
    # Step 4: MCP Setup
    setup_mcp_config "$script_dir"
    
    # Clear cache to prevent import issues
    clear_python_cache
    
    # Final message
    print_info ""
    print_info "================================================"
    print_success " Setup Complete!"
    print_info "================================================"
    print_info ""
    print_info "Next steps:"
    print_info "1. Ensure your OpenAI API key is set in .env"
    print_info "2. Restart Claude Desktop to load the MCP server"
    print_info "3. Use 'zen-mcp-gpt5' tools in Claude"
    print_info ""
    print_info "To view logs:"
    print_info "  $0 -f    # Follow logs in real-time"
    print_info "  $0 -l    # Show recent logs"
    print_info ""
    print_info "GPT-5 Features:"
    print_info "  • 400K context window"
    print_info "  • 128K output tokens"
    print_info "  • Advanced reasoning (2K-12K tokens)"
    print_info "  • Optimized for debugging & code review"
    print_info ""
}

# Run main function
main "$@"