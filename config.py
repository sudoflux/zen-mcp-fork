"""
Configuration and constants for Zen MCP Server

This module centralizes all configuration settings for the Zen MCP Server.
It defines model configurations, token limits, temperature defaults, and other
constants used throughout the application.

Configuration values can be overridden by environment variables where appropriate.
"""

import os

# Version and metadata
# These values are used in server responses and for tracking releases
# IMPORTANT: This is the single source of truth for version and author info
# Semantic versioning: MAJOR.MINOR.PATCH
__version__ = "5.8.5"
# Last update date in ISO format
__updated__ = "2025-08-08"
# Primary maintainer
__author__ = "Fahad Gilani"

# Model configuration
# DEFAULT_MODEL: The default model used for all AI operations
# This should be a stable, high-performance model suitable for code analysis
# Can be overridden by setting DEFAULT_MODEL environment variable
# Special value "auto" means Claude should pick the best model for each task
DEFAULT_MODEL = os.getenv("DEFAULT_MODEL", "auto")

# Auto mode detection - when DEFAULT_MODEL is "auto", Claude picks the model
IS_AUTO_MODE = DEFAULT_MODEL.lower() == "auto"

# Each provider (gemini.py, openai_provider.py, xai.py) defines its own SUPPORTED_MODELS
# with detailed descriptions. Tools use ModelProviderRegistry.get_available_model_names()
# to get models only from enabled providers (those with valid API keys).
#
# This architecture ensures:
# - No namespace collisions (models only appear when their provider is enabled)
# - API key-based filtering (prevents wrong models from being shown to Claude)
# - Proper provider routing (models route to the correct API endpoint)
# - Clean separation of concerns (providers own their model definitions)


# Temperature defaults for different tool types
# Temperature controls the randomness/creativity of model responses
# Lower values (0.0-0.3) produce more deterministic, focused responses
# Higher values (0.7-1.0) produce more creative, varied responses

# TEMPERATURE_ANALYTICAL: Used for tasks requiring precision and consistency
# Ideal for code review, debugging, and error analysis where accuracy is critical
TEMPERATURE_ANALYTICAL = 0.2  # For code review, debugging

# TEMPERATURE_BALANCED: Middle ground for general conversations
# Provides a good balance between consistency and helpful variety
TEMPERATURE_BALANCED = 0.5  # For general chat

# TEMPERATURE_CREATIVE: Higher temperature for exploratory tasks
# Used when brainstorming, exploring alternatives, or architectural discussions
TEMPERATURE_CREATIVE = 0.7  # For architecture, deep thinking

# Thinking Mode Defaults
# DEFAULT_THINKING_MODE_THINKDEEP: Default thinking depth for extended reasoning tool
# Higher modes use more computational budget but provide deeper analysis
DEFAULT_THINKING_MODE_THINKDEEP = os.getenv("DEFAULT_THINKING_MODE_THINKDEEP", "high")

# Consensus Tool Defaults
# Consensus timeout and rate limiting settings
DEFAULT_CONSENSUS_TIMEOUT = 120.0  # 2 minutes per model
DEFAULT_CONSENSUS_MAX_INSTANCES_PER_COMBINATION = 2

# NOTE: Consensus tool now uses sequential processing for MCP compatibility
# Concurrent processing was removed to avoid async pattern violations

# Model Preferences for GPT-5 & Opus 4.1 Optimizations
# These preferences guide automatic model selection based on task type
MODEL_PREFERENCES = {
    "planning": ["gpt-4.1", "gpt-5"],  # GPT-4.1 for large context, GPT-5 for reasoning
    "code_review": ["gpt-5", "gpt-4.1"],  # GPT-5 for deep analysis, GPT-4.1 for coverage
    "debugging": ["gpt-5", "o3"],  # GPT-5 for reasoning, O3 as fallback
    "refactoring": ["gpt-4.1", "gpt-5"],  # GPT-4.1 for entire codebase understanding
    "architecture": ["gpt-5", "gpt-4.1"],  # Both excellent for architecture
    "security_audit": ["gpt-5", "o3"],  # GPT-5 for comprehensive analysis
    "testing": ["gpt-5", "gpt-5-mini"],  # GPT-5 for test generation
    "documentation": ["gpt-5-mini", "gpt-5"],  # Mini for speed, full for quality
    "chat": ["gpt-5-mini", "gpt-5-nano", "gpt-5"],  # Fast models for chat
    "general": ["gpt-5", "gpt-4.1", "o3"],  # General fallback order
}

# GPT-5 Specific Configuration
GPT5_CONFIG = {
    "default_thinking_mode": os.getenv("GPT5_DEFAULT_THINKING_MODE", "medium"),
    "max_reasoning_tokens": int(os.getenv("GPT5_MAX_REASONING_TOKENS", "12000")),
    "escalation_enabled": os.getenv("GPT5_ESCALATION_ENABLED", "true").lower() == "true",
    "file_strategy": os.getenv("GPT5_FILE_STRATEGY", "priority"),  # all, priority, summary
    "conversation_strategy": os.getenv("GPT5_CONVERSATION_STRATEGY", "balanced"),  # full, balanced, summary
}

# GPT-4.1 (Opus) Specific Configuration  
GPT4_1_CONFIG = {
    "auto_continue": os.getenv("GPT4_1_AUTO_CONTINUE", "true").lower() == "true",
    "max_output_tokens": int(os.getenv("GPT4_1_MAX_OUTPUT", "32000")),
    "file_strategy": os.getenv("GPT4_1_FILE_STRATEGY", "all"),  # all, priority, summary
    "conversation_strategy": os.getenv("GPT4_1_CONVERSATION_STRATEGY", "full"),  # full, balanced, summary
}

# Token Budget Allocation (as percentages of available tokens)
TOKEN_BUDGET_CONFIG = {
    "system": float(os.getenv("TOKEN_BUDGET_SYSTEM", "0.02")),  # 2% for system prompts
    "instructions": float(os.getenv("TOKEN_BUDGET_INSTRUCTIONS", "0.03")),  # 3% for instructions
    "files": float(os.getenv("TOKEN_BUDGET_FILES", "0.60")),  # 60% for file content
    "conversation": float(os.getenv("TOKEN_BUDGET_CONVERSATION", "0.27")),  # 27% for history
    "buffer": float(os.getenv("TOKEN_BUDGET_BUFFER", "0.08")),  # 8% safety margin
}

# Validate budget allocations
_budget_total = sum(TOKEN_BUDGET_CONFIG.values())
if _budget_total > 1.0:
    import warnings
    warnings.warn(f"Token budget allocations sum to {_budget_total:.2f}, should be <= 1.0")

# MCP Protocol Transport Limits
#
# IMPORTANT: This limit ONLY applies to the Claude CLI ↔ MCP Server transport boundary.
# It does NOT limit internal MCP Server operations like system prompts, file embeddings,
# conversation history, or content sent to external models (Gemini/OpenAI/OpenRouter).
#
# MCP Protocol Architecture:
# Claude CLI ←→ MCP Server ←→ External Model (Gemini/OpenAI/etc.)
#     ↑                              ↑
#     │                              │
# MCP transport                Internal processing
# (token limit from MAX_MCP_OUTPUT_TOKENS)    (No MCP limit - can be 1M+ tokens)
#
# MCP_PROMPT_SIZE_LIMIT: Maximum character size for USER INPUT crossing MCP transport
# The MCP protocol has a combined request+response limit controlled by MAX_MCP_OUTPUT_TOKENS.
# To ensure adequate space for MCP Server → Claude CLI responses, we limit user input
# to roughly 60% of the total token budget converted to characters. Larger user prompts
# must be sent as prompt.txt files to bypass MCP's transport constraints.
#
# Token to character conversion ratio: ~4 characters per token (average for code/text)
# Default allocation: 60% of tokens for input, 40% for response
#
# What IS limited by this constant:
# - request.prompt field content (user input from Claude CLI)
# - prompt.txt file content (alternative user input method)
# - Any other direct user input fields
#
# What is NOT limited by this constant:
# - System prompts added internally by tools
# - File content embedded by tools
# - Conversation history loaded from storage
# - Web search instructions or other internal additions
# - Complete prompts sent to external models (managed by model-specific token limits)
#
# This ensures MCP transport stays within protocol limits while allowing internal
# processing to use full model context windows (200K-1M+ tokens).


def _calculate_mcp_prompt_limit() -> int:
    """
    Calculate MCP prompt size limit based on MAX_MCP_OUTPUT_TOKENS environment variable.

    Returns:
        Maximum character count for user input prompts
    """
    # Check for Claude's MAX_MCP_OUTPUT_TOKENS environment variable
    max_tokens_str = os.getenv("MAX_MCP_OUTPUT_TOKENS")

    if max_tokens_str:
        try:
            max_tokens = int(max_tokens_str)
            # Allocate 60% of tokens for input, convert to characters (~4 chars per token)
            input_token_budget = int(max_tokens * 0.6)
            character_limit = input_token_budget * 4
            return character_limit
        except (ValueError, TypeError):
            # Fall back to default if MAX_MCP_OUTPUT_TOKENS is not a valid integer
            pass

    # Default fallback: 60,000 characters (equivalent to ~15k tokens input of 25k total)
    return 60_000


MCP_PROMPT_SIZE_LIMIT = _calculate_mcp_prompt_limit()

# Language/Locale Configuration
# LOCALE: Language/locale specification for AI responses
# When set, all AI tools will respond in the specified language while
# maintaining their analytical capabilities
# Examples: "fr-FR", "en-US", "zh-CN", "zh-TW", "ja-JP", "ko-KR", "es-ES",
# "de-DE", "it-IT", "pt-PT"
# Leave empty for default language (English)
LOCALE = os.getenv("LOCALE", "")

# Threading configuration
# Simple in-memory conversation threading for stateless MCP environment
# Conversations persist only during the Claude session
