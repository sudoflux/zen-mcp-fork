# NEXT_AGENT.md

Purpose
This document orients the next engineer working on the GPT-5 + Claude edition of Zen MCP. It explains the design constraints, fixes already applied, pitfalls to avoid, and targeted opportunities for incremental improvements.

Project Goal (non-negotiable)
- Single-provider focus: OpenAI GPT-5 only.
- Primary user workflow: Claude Desktop + GPT-5 for planning, code review, and troubleshooting.
- Minimize complexity; no multi-provider adapters or fallbacks.

Key Artifacts
- server_gpt5_pure.py — entry-point MCP server optimized exclusively for GPT-5.
- setup-gpt5-claude.sh — one-command setup, .env creation, MCP config, and sanity checks.
- README_GPT5.md — user-facing quick start and docs.
- .env — stores OPENAI_API_KEY and GPT-5 settings (created/updated by setup script).
- tools/* — GPT-5-aware tools (chat, thinkdeep, analyze, codereview, debug, refactor, planner, testgen, docgen, secaudit, precommit, tracer, consensus).
- providers/* — provider registry and OpenAI-only provider.

Changes Made (and rationale)
- De-scoped to single provider (OpenAI GPT-5).
  Rationale: Less surface area, fewer failure modes, and clearer optimizations.
- Fixed missing setup_logging by inlining logging.basicConfig in server_gpt5_pure.py.
  Rationale: Remove implicit dependency and simplify boot.
- API parameter correction for GPT-5.
  Rationale: Avoid 400 errors by using the correct token parameter for the chosen API path.
- Automated setup via setup-gpt5-claude.sh.
  Rationale: Consistent developer experience (venv, deps, .env, MCP config).
- Corrected Claude Desktop MCP connection.
  Rationale: Point at the correct server entry point using absolute paths and venv python.

Important Inconsistencies To Verify (line-precise)
1) server path in README and setup script vs actual file name
   - README_GPT5.md lines 29-31 currently reference server_gpt5.py, but the provided entry-point file is server_gpt5_pure.py.
   - setup-gpt5-claude.sh lines 134-141 currently:
     "args": ["$script_dir/server_gpt5.py"],
     "cwd": "$script_dir"
   Action: Use server_gpt5_pure.py consistently across README and setup.

2) GPT-5 token parameter on the OpenAI client
   - server_gpt5_pure.py lines 69-72 currently:
     response = client.chat.completions.create(
       model="gpt-5",
       messages=[{"role": "user", "content": "Hello"}],
       max_tokens=5
     )
   - setup-gpt5-claude.sh test snippet lines 89-95:
     client.chat.completions.create(..., max_completion_tokens=10)
   Action: Pick one parameter and use it consistently (prefer whatever actually succeeds in your environment). If using Chat Completions API, keep it consistent and validated with a live request. If migrating to the Responses API, use max_output_tokens. Update test and server together.

3) Verbose logging switch
   - server_gpt5_pure.py lines 243-251 provide a --verbose option. Consider reflecting this in README, along with log file locations.

Server Overview
- Boot sequence: startup() registers the OpenAI provider, validates GPT-5 access with a test call, registers tools, and logs GPT-5 config.
  - server_gpt5_pure.py lines 198-223:
    "Initialize GPT-5 server on startup..." and "Register tools"
- Tool routing: All tools are registered in register_gpt5_tools() and exposed via list_tools()/call_tool().
  - server_gpt5_pure.py lines 88-133: registration
  - server_gpt5_pure.py lines 138-153: list_tools() with "[GPT-5] ..." descriptions
  - server_gpt5_pure.py lines 155-193: call_tool() forcing model=gpt-5 as default and elevating thinking_mode for complex tools

What Was Broken (and how we avoided it)
- Missing setup_logging: replaced with logging.basicConfig to avoid import errors.
  - server_gpt5_pure.py lines 33-37 show basicConfig usage.
- Wrong token parameter for GPT-5: caused 400s.
  - Verified by a minimal client call (setup script includes a quick test).
- MCP config pointed to the wrong server entry file.
  - Fixed by writing absolute paths in setup-gpt5-claude.sh.
- Virtual environment path issues:
  - We ensure command uses .zen_venv/bin/python and set PYTHONPATH to the project root.

Operational Guidance

Run locally
- Preferred path:
  - ./setup-gpt5-claude.sh
  - ./start-claude.sh (launches Claude; MCP connects automatically)
- Direct run (for debugging):
  - ./.zen_venv/bin/python server_gpt5_pure.py --verbose

Environment
- .env keys:
  - OPENAI_API_KEY (required)
  - DEFAULT_MODEL (default gpt-5)
  - ENABLE_GPT5=true
  - GPT5_DEFAULT_THINKING_MODE=high
  - GPT5_MAX_REASONING_TOKENS=12000
  - LOG_LEVEL=INFO
- Load via python-dotenv; server imports load_dotenv at module import.

MCP (Claude Desktop)
- Config path varies by OS:
  - macOS: ~/Library/Application Support/Claude/claude_desktop_config.json
  - Windows: %APPDATA%\Claude\claude_desktop_config.json
  - Linux: ~/.config/claude/claude_desktop_config.json
- Use absolute paths for command, args, and cwd to avoid path resolution issues.
- Use venv python: .zen_venv/bin/python
- Ensure executable permissions for scripts on Linux/macOS.

Sanity checks
- Verify OpenAI connectivity and GPT-5 access:
  - setup-gpt5-claude.sh performs a test chat.completions call.
- Quick tool ping:
  - python3 test-gpt5.py
- If Claude shows no tools:
  - Check config path, ensure absolute paths, restart Claude Desktop, and tail logs/mcp_server.log.

Edge Cases and Failure Modes
- Token limit exceeded:
  - Lower reasoning budgets, reduce file set, or use summarization.
- Rate limiting / 429:
  - Add exponential backoff in the provider layer (future work).
- Long-running tool executions:
  - Consider timeouts per tool and graceful cancellation policy.
- OS path differences:
  - Always prefer absolute paths; avoid ~ expansions inside JSON.

Recommended Code Spot-Fixes (safe, incremental)
1) Unify GPT-5 token parameter
   - In server_gpt5_pure.py:
     Replace (lines 69-72):
       response = client.chat.completions.create(..., max_tokens=5)
     With:
       response = client.chat.completions.create(..., max_completion_tokens=5)
   - Ensure setup-gpt5-claude.sh uses the same param for the same endpoint (it currently uses max_completion_tokens).

2) Setup script config file target
   - setup-gpt5-claude.sh lines 134-141:
     "args": ["$script_dir/server_gpt5.py"]
   - Update to:
     "args": ["$script_dir/server_gpt5_pure.py"]

Observability & Quality (next steps)
- Logging:
  - Current: basicConfig; LOG_LEVEL from .env.
  - Improvement: structured logging (JSON) behind a flag for easier parsing.
- Tool telemetry:
  - Record per-tool cost estimation and token usage to logs/mcp_activity.log.
- Retries:
  - Add simple jittered exponential backoff for 429/5xx at provider boundary.
- Streaming:
  - Consider enabling streaming (where supported) to improve UX for long outputs.
- Caching:
  - Optional: memoize expensive analyze/codereview runs keyed by file hash windows.

De-scoped by design (avoid re-introducing)
- Multi-provider compatibility.
- Provider auto-discovery or dynamic registry bootstrapping.
- Complex plugin loading systems.

Release Checklist
- [ ] setup-gpt5-claude.sh writes correct server filename and absolute paths
- [ ] server_gpt5_pure.py uses the same GPT-5 token param as the setup test
- [ ] README_GPT5.md matches actual scripts, file names, and instructions
- [ ] tools register successfully; list_tools returns expected set
- [ ] Claude shows tools after full restart
- [ ] logs/mcp_server.log contains clean startup header and no exceptions

Contact Points in Code (for quick navigation)
- Providers registration:
  - server_gpt5_pure.py lines 59-67:
    ModelProviderRegistry.register_provider(...) and OpenAI test call
- Tool registration:
  - server_gpt5_pure.py lines 106-122 (class list) and 123-133 (loop)
- Tool dispatch:
  - server_gpt5_pure.py lines 155-193 (call_tool)
- Startup/shutdown:
  - server_gpt5_pure.py lines 198-223 (startup), 224-238 (shutdown)
- CLI entry:
  - server_gpt5_pure.py lines 243-272 (click main and serve)

Final Notes
- Keep it simple and aligned with the single-provider mandate.
- Any new feature must justify itself against the project's clarity and reliability goals.
- If you need to change token parameters or endpoints, update both the setup test and server to match, and document it in README_GPT5.md.