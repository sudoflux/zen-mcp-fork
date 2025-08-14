# Zen MCP - GPT-5 + Claude Edition

A streamlined MCP server that gives Claude Desktop access to GPT-5's advanced capabilities with zero multi-provider complexity.

Requirements:
- Claude Desktop Pro/Team
- OpenAI API key with GPT-5 access

Why a single-provider design?
- Reliability: Fewer code paths and no adapters for other providers = fewer edge cases.
- Simplicity: One set of models, one set of parameters, one set of optimizations.
- Performance: GPT-5-specific token, reasoning, and context strategies without generic fallbacks.

What's different from the original Zen MCP?
- Removed multi-provider support; OpenRouter/Gemini/etc. are not included.
- GPT-5-first parameter handling and reasoning controls.
- Simplified setup via setup-gpt5-claude.sh.
- Claude Desktop MCP configuration corrected and validated.

## Quick Start (about 5 minutes)

1) Clone and run setup
```bash
git clone https://github.com/sudoflux/zen-mcp-fork.git
cd zen-mcp-fork
./setup-gpt5-claude.sh
```

2) Add your OpenAI API key
The setup will prompt for your key and write it to .env:
```env
OPENAI_API_KEY=sk-proj-xxxxx
```

3) Claude Desktop MCP configuration
The setup script writes ~/.config/claude/claude_desktop_config.json with an entry similar to:
```json
{
  "mcpServers": {
    "gpt5": {
      "command": "/absolute/path/to/zen-mcp-fork/.zen_venv/bin/python",
      "args": ["/absolute/path/to/zen-mcp-fork/server_gpt5_pure.py"],
      "cwd": "/absolute/path/to/zen-mcp-fork",
      "env": {
        "PYTHONPATH": "/absolute/path/to/zen-mcp-fork"
      }
    }
  }
}
```

4) Start Claude
```bash
./start-claude.sh
```
The GPT-5 tools will appear in Claude automatically.

## What This Server Enables

Claude can leverage GPT-5's strengths for planning, code review, and troubleshooting:
- 400K context window for large repos
- Up to 128K output tokens for comprehensive docs
- Reasoning-oriented workflows (2K–12K token budgets)
- Model-aware token and file-selection strategies

## Available Tools (high level)

Core
- chat: Collaborate with GPT-5 on any topic
- thinkdeep: Extended reasoning for complex problems
- debug: Advanced debugging with reasoning
- codereview: End-to-end code review workflows
- analyze: Deep code analysis with large context

Development
- refactor: Refactoring recommendations
- planner: Break down complex tasks
- testgen: Generate test suites
- docgen: Documentation generation

Validation
- secaudit: Security checks (OWASP-oriented)
- precommit: Pre-commit style checks
- consensus: Multiple GPT-5 perspectives

Note: All tools route to GPT-5 or your configured default model.

## Configuration

Environment variables (.env)
```env
# Required
OPENAI_API_KEY=sk-proj-xxxxx

# Optional GPT-5 settings
DEFAULT_MODEL=gpt-5
ENABLE_GPT5=true
GPT5_DEFAULT_THINKING_MODE=high    # low/medium/high/max
GPT5_MAX_REASONING_TOKENS=12000
LOG_LEVEL=INFO
```

Model selection
- DEFAULT_MODEL=auto lets tools choose (still GPT-5 biased).
- Use gpt-5-mini for faster/cheaper iterations when acceptable.

## GPT-5 Optimizations

Token management
- Smart budgeting prioritizes critical content.
- Automatic summarization to fit more context when needed.
- Safety margin buffer to avoid overflows.

Adaptive reasoning
- Debugging: ~12k reasoning tokens
- Planning: ~10k reasoning tokens
- Code Review: ~6k reasoning tokens
- Chat: ~3k reasoning tokens

File selection strategies
- Priority-based and relevance scoring
- Strategy tuned to task type (analysis vs. refactor etc.)

## Monitoring

Logs
- Main logs: logs/mcp_server.log
- Tool-only activity: logs/mcp_activity.log

Tail logs
```bash
tail -f logs/mcp_server.log
```

Increase verbosity at runtime
```bash
python ./.zen_venv/bin/python server_gpt5_pure.py --verbose
```

## Troubleshooting

OpenAI API issues
```bash
curl https://api.openai.com/v1/models \
  -H "Authorization: Bearer $OPENAI_API_KEY"
```
- Ensure your key has GPT-5 access.

Claude cannot find tools
- Verify ~/.config/claude/claude_desktop_config.json references absolute paths.
- Confirm venv python path is correct.
- Fully quit and restart Claude Desktop.

Token limit errors
- Narrow the file set or target specific directories.
- Use summarization or reduce reasoning token budgets.
- Consider gpt-5-mini for iterative steps.

## Performance Tips

- Large repos: analyze with directory scoping for better signal.
- Fast loops: gpt-5-mini + reduced reasoning budgets.
- Hard bugs: thinkdeep at high mode for maximal reasoning.
- Cost control: cap reasoning token budgets per tool call.

## Security Notes

- API keys stay local; not sent to Claude.
- File access is read-only by default.
- Only requests to OpenAI are made; no additional telemetry.

## License

Apache 2.0 — see LICENSE.

## Credits

Based on the original Zen MCP by the Zen team; this fork is optimized for GPT-5 + Claude workflows.