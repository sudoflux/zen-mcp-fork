# Zen MCP - GPT-5 + Claude Edition

A streamlined MCP server that gives Claude Desktop access to GPT-5's advanced capabilities.

> **Requirements:** [Claude Desktop](https://claude.ai/download) with Pro/Team subscription + OpenAI API key with GPT-5 access

## 🚀 Quick Start (5 minutes)

### 1. Clone and Setup
```bash
git clone https://github.com/sudoflux/zen-mcp-fork.git
cd zen-mcp-fork
./run-server-gpt5.sh
```

### 2. Add your OpenAI API key
Edit `.env`:
```env
OPENAI_API_KEY=sk-proj-xxxxx  # Your actual key here
```

### 3. Configure Claude Desktop
Add to `claude_desktop_config.json`:
```json
{
  "mcpServers": {
    "zen-gpt5": {
      "command": "python",
      "args": ["/path/to/zen-mcp-fork/server_gpt5.py"],
      "cwd": "/path/to/zen-mcp-fork"
    }
  }
}
```

### 4. Restart Claude Desktop
The tools will appear automatically!

## 🎯 What This Does

This server lets Claude leverage GPT-5's unique strengths:
- **400K context window** - Analyze entire codebases
- **128K output tokens** - Generate comprehensive documentation
- **Advanced reasoning** - 2K-12K tokens of deep thinking for complex problems
- **Optimized workflows** - Smart token management and model-aware strategies

## 🛠️ Available Tools

### Core Analysis Tools
- **`chat`** - Collaborate with GPT-5 on any topic
- **`thinkdeep`** - Extended reasoning for complex problems
- **`debug`** - Advanced debugging with reasoning capabilities
- **`codereview`** - Comprehensive code review workflows
- **`analyze`** - Deep code analysis with full context

### Development Tools
- **`refactor`** - Intelligent refactoring suggestions
- **`planner`** - Break down complex tasks
- **`testgen`** - Generate comprehensive test suites
- **`docgen`** - Create detailed documentation

### Security & Validation
- **`secaudit`** - Security analysis with OWASP checks
- **`precommit`** - Pre-commit validation
- **`consensus`** - Get multiple perspectives (using different GPT-5 modes)

## 💡 Example Workflows

### Debug a Complex Issue
```
Use debug to investigate the authentication bug in auth.py, 
use GPT-5's reasoning to trace through the logic
```

### Comprehensive Code Review
```
Perform a codereview on the src/ directory focusing on security and performance,
then create a planner task to address the findings
```

### Refactor Legacy Code
```
Use analyze to understand the payment module, then refactor it 
for better maintainability, and finally testgen to ensure coverage
```

## ⚙️ Configuration

### Environment Variables (.env)
```env
# Required
OPENAI_API_KEY=sk-proj-xxxxx

# Optional GPT-5 Settings
DEFAULT_MODEL=gpt-5                    # Default model to use
ENABLE_GPT5=true                       # Enable GPT-5 features
GPT5_DEFAULT_THINKING_MODE=medium      # low/medium/high/max
GPT5_MAX_REASONING_TOKENS=12000        # Max reasoning tokens
```

### Model Selection
- **Auto mode**: Set `DEFAULT_MODEL=auto` to let the system pick
- **Specific model**: Set `DEFAULT_MODEL=gpt-5` or `DEFAULT_MODEL=gpt-5-mini`

## 📊 GPT-5 Optimizations

### Token Management
- **Smart budgeting**: Prioritizes important content
- **Automatic summarization**: Fits more context when needed
- **Safety margins**: 7% buffer to prevent errors

### Adaptive Reasoning
| Task Type | Reasoning Tokens | Use Case |
|-----------|-----------------|----------|
| Debugging | 12,000 | Complex logic errors |
| Planning | 10,000 | Architecture decisions |
| Code Review | 6,000 | Quality analysis |
| Chat | 3,000 | General discussion |

### File Selection Strategies
- **Priority-based**: Most relevant files first
- **Relevance scoring**: Automatic importance detection
- **Model-aware**: Different strategies for different contexts

## 🔍 Monitoring

### View Logs
```bash
# Follow logs in real-time
./run-server-gpt5.sh -f

# View recent logs
tail -n 100 logs/mcp_server.log

# Check for errors
grep ERROR logs/mcp_server.log
```

### Log Files
- `logs/mcp_server.log` - Main server activity
- `logs/mcp_activity.log` - Tool executions only

## 🚧 Troubleshooting

### OpenAI API Issues
```bash
# Test your API key
curl https://api.openai.com/v1/models \
  -H "Authorization: Bearer $OPENAI_API_KEY"
```

### Claude Not Finding Tools
1. Check Claude config path:
   - Mac: `~/Library/Application Support/Claude/claude_desktop_config.json`
   - Windows: `%APPDATA%\Claude\claude_desktop_config.json`
   - Linux: `~/.config/claude/claude_desktop_config.json`

2. Verify server path is absolute in config
3. Restart Claude Desktop completely

### Token Limit Errors
- Reduce file count in requests
- Use specific file paths instead of directories
- Enable summarization in settings

## 📈 Performance Tips

1. **For large codebases**: Use `analyze` tool with specific directories
2. **For quick iterations**: Use `gpt-5-mini` for faster responses
3. **For complex debugging**: Use `thinkdeep` with high reasoning mode
4. **For cost optimization**: Set token limits in configuration

## 🔒 Security Notes

- API keys are never sent to Claude
- All processing happens locally
- File access is read-only by default
- No data is stored or transmitted except to OpenAI

## 📝 License

Apache 2.0 - See LICENSE file

## 🤝 Credits

Based on the original Zen MCP by the Zen team, streamlined for GPT-5 focus.

---

*Built for developers who want GPT-5's power with Claude's interface.*