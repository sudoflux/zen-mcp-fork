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
    local required_major="3"
    local required_minor="9"
    local python_cmd=""
    
    # Try various Python commands
    for cmd in python3.12 python3.11 python3.10 python3.9 python3 python; do
        if command -v "$cmd" &> /dev/null; then
            local version
            version=$("$cmd" -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
            local major="${version%.*}"
            local minor="${version#*.}"
            
            # Check if version meets requirements (3.9+)
            if [[ "$major" -eq "$required_major" ]] && [[ "$minor" -ge "$required_minor" ]]; then
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

check_and_install_claude() {
    print_info ""
    print_info "=== Claude Desktop Check ==="
    print_info ""
    
    # Check if Claude is installed based on OS
    local claude_installed=false
    local claude_path=""
    
    if [[ "$OSTYPE" == "darwin"* ]]; then
        # macOS
        if [[ -d "/Applications/Claude.app" ]]; then
            claude_installed=true
            claude_path="/Applications/Claude.app"
        fi
    elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
        # Linux - check for AppImage or snap
        if command -v claude &> /dev/null; then
            claude_installed=true
            claude_path=$(which claude)
        elif [[ -f "$HOME/.local/bin/claude" ]]; then
            claude_installed=true
            claude_path="$HOME/.local/bin/claude"
        elif snap list claude &> /dev/null 2>&1; then
            claude_installed=true
            claude_path="snap"
        fi
    elif [[ "$OSTYPE" == "msys" ]] || [[ "$OSTYPE" == "cygwin" ]]; then
        # Windows
        if [[ -f "$LOCALAPPDATA/Programs/claude/Claude.exe" ]]; then
            claude_installed=true
            claude_path="$LOCALAPPDATA/Programs/claude/Claude.exe"
        fi
    fi
    
    if [[ "$claude_installed" == true ]]; then
        print_success "Claude Desktop found at: $claude_path"
        return 0
    else
        print_warning "Claude Desktop not found"
        print_info ""
        print_info "Would you like to install Claude Desktop?"
        read -p "Install Claude Desktop? (y/N): " install_claude
        
        if [[ "$install_claude" == "y" ]] || [[ "$install_claude" == "Y" ]]; then
            install_claude_desktop
        else
            print_info "Skipping Claude Desktop installation"
            print_info "You can install it manually from: https://claude.ai/download"
            return 1
        fi
    fi
}

install_claude_desktop() {
    print_info "Installing Claude Desktop..."
    
    if [[ "$OSTYPE" == "darwin"* ]]; then
        # macOS installation
        print_info "Downloading Claude Desktop for macOS..."
        curl -L "https://storage.googleapis.com/osprey-downloads-c02f6a0d-347c-492b-a752-3e0651722e97/nest-win-x64/Claude-Setup.dmg" -o /tmp/Claude.dmg
        print_info "Mounting DMG..."
        hdiutil attach /tmp/Claude.dmg
        print_info "Installing Claude.app..."
        cp -R "/Volumes/Claude/Claude.app" /Applications/
        hdiutil detach "/Volumes/Claude"
        rm /tmp/Claude.dmg
        print_success "Claude Desktop installed to /Applications"
        
    elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
        # Linux installation - using AppImage
        print_info "Downloading Claude Desktop AppImage for Linux..."
        
        # Create local bin directory if it doesn't exist
        mkdir -p "$HOME/.local/bin"
        
        # Download AppImage (Note: URL may need updating)
        local download_url="https://storage.googleapis.com/osprey-downloads-c02f6a0d-347c-492b-a752-3e0651722e97/nest-linux-x64/claude-desktop.AppImage"
        
        if command -v wget &> /dev/null; then
            wget -O "$HOME/.local/bin/claude.AppImage" "$download_url"
        elif command -v curl &> /dev/null; then
            curl -L "$download_url" -o "$HOME/.local/bin/claude.AppImage"
        else
            print_error "Neither wget nor curl found. Please install one of them."
            return 1
        fi
        
        # Make it executable
        chmod +x "$HOME/.local/bin/claude.AppImage"
        
        # Create desktop entry
        cat > "$HOME/.local/share/applications/claude.desktop" << 'EOF'
[Desktop Entry]
Name=Claude
Exec=$HOME/.local/bin/claude.AppImage
Type=Application
Icon=claude
Categories=Development;
EOF
        
        print_success "Claude Desktop installed to ~/.local/bin/claude.AppImage"
        print_info "You may need to add ~/.local/bin to your PATH"
        
        # Add to PATH if not already there
        if [[ ":$PATH:" != *":$HOME/.local/bin:"* ]]; then
            echo 'export PATH="$HOME/.local/bin:$PATH"' >> "$HOME/.bashrc"
            export PATH="$HOME/.local/bin:$PATH"
            print_info "Added ~/.local/bin to PATH"
        fi
        
    elif [[ "$OSTYPE" == "msys" ]] || [[ "$OSTYPE" == "cygwin" ]]; then
        # Windows installation
        print_info "Downloading Claude Desktop for Windows..."
        curl -L "https://storage.googleapis.com/osprey-downloads-c02f6a0d-347c-492b-a752-3e0651722e97/nest-win-x64/Claude-Setup.exe" -o /tmp/Claude-Setup.exe
        print_info "Running installer..."
        /tmp/Claude-Setup.exe
        rm /tmp/Claude-Setup.exe
        print_success "Claude Desktop installer launched"
    else
        print_error "Unsupported operating system for automatic installation"
        print_info "Please download manually from: https://claude.ai/download"
        return 1
    fi
    
    print_success "Claude Desktop installed successfully!"
    print_info "Please launch Claude Desktop and sign in with your account"
}

setup_mcp_config() {
    local script_dir="$1"
    
    print_info ""
    print_info "=== MCP Configuration for Claude ==="
    print_info ""
    
    # First check if Claude is installed
    if ! check_and_install_claude; then
        print_warning "Continuing without Claude Desktop"
    fi
    
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
    
    # Create config directory if it doesn't exist
    if [[ ! -d "$config_dir" ]]; then
        print_info "Creating Claude config directory..."
        mkdir -p "$config_dir"
    fi
    
    if [[ ! -f "$config_file" ]]; then
        print_info "Creating Claude Desktop config..."
        cat > "$config_file" << EOF
{
  "mcpServers": {
    "zen-mcp-gpt5": {
      "command": "python",
      "args": ["$script_dir/server_gpt5.py"],
      "cwd": "$script_dir",
      "env": {
        "PYTHONPATH": "$script_dir"
      }
    }
  }
}
EOF
        print_success "Created Claude config at: $config_file"
        print_info "MCP server configured and ready!"
    else
        print_success "Found existing Claude Desktop config"
        print_info ""
        print_info "To add Zen MCP GPT-5, add this to your config:"
        print_info ""
        cat << EOF
"zen-mcp-gpt5": {
  "command": "python",
  "args": ["$script_dir/server_gpt5.py"],
  "cwd": "$script_dir",
  "env": {
    "PYTHONPATH": "$script_dir"
  }
}
EOF
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