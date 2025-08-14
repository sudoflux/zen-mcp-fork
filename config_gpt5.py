"""
GPT-5 + Claude Specific Configuration

Tailored configuration for GPT-5 API access with Claude Desktop.
No fallbacks, no compatibility layers - just GPT-5 optimization.
"""

import os

# Version and metadata
__version__ = "5.8.5-gpt5"
__updated__ = "2025-01-08"
__author__ = "Josh's GPT-5 Fork"

# GPT-5 Only Configuration
DEFAULT_MODEL = "gpt-5"
IS_AUTO_MODE = False  # Always use GPT-5

# GPT-5 Optimized Settings
TEMPERATURE_ANALYTICAL = 0.1    # For code review, debugging
TEMPERATURE_BALANCED = 0.3      # For general chat  
TEMPERATURE_CREATIVE = 0.6      # For architecture, planning

# GPT-5 Thinking Mode (always high for complex tasks)
DEFAULT_THINKING_MODE_THINKDEEP = "high"

# GPT-5 Specific Configuration
GPT5_CONFIG = {
    "default_thinking_mode": "high",
    "max_reasoning_tokens": 12000,
    "escalation_enabled": True,
    "file_strategy": "priority",
    "conversation_strategy": "balanced",
    "context_window": 400000,
    "output_limit": 128000,
}

# Token Budget for GPT-5's 400K context
TOKEN_BUDGET_CONFIG = {
    "system": 0.02,         # 2% for system prompts (8K tokens)
    "instructions": 0.03,   # 3% for instructions (12K tokens)  
    "files": 0.65,          # 65% for file content (260K tokens)
    "conversation": 0.25,   # 25% for history (100K tokens)
    "buffer": 0.05,         # 5% safety margin (20K tokens)
}

# GPT-5 Model Preferences (no fallbacks)
MODEL_PREFERENCES = {
    "debugging": ["gpt-5"],
    "code_review": ["gpt-5"], 
    "planning": ["gpt-5"],
    "refactoring": ["gpt-5"],
    "architecture": ["gpt-5"],
    "security_audit": ["gpt-5"],
    "testing": ["gpt-5"],
    "documentation": ["gpt-5"],
    "chat": ["gpt-5"],
    "general": ["gpt-5"],
}

# MCP Protocol Limits (Claude Desktop specific)
MCP_PROMPT_SIZE_LIMIT = 100_000  # Larger for GPT-5 workflows

# Language/Locale 
LOCALE = os.getenv("LOCALE", "")

# Logging optimized for GPT-5 workflows
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")