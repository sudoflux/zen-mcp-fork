"""
Model Capabilities Registry for GPT-5 and Opus 4.1 Optimizations

This module provides a centralized registry of model capabilities including
token limits, reasoning support, and overhead calculations. It enables
model-aware token management and optimization strategies.
"""

from dataclasses import dataclass, field
from typing import Dict, Optional, Callable
from enum import Enum


class ModelProvider(Enum):
    """Supported model providers"""
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    GOOGLE = "google"
    CUSTOM = "custom"


@dataclass
class ModelCapabilities:
    """
    Comprehensive model capability definition
    
    Attributes:
        model_id: Unique identifier for the model
        provider: Model provider
        max_input_tokens: Maximum input context window
        max_output_tokens: Maximum output tokens
        supports_reasoning: Whether model supports extended thinking/reasoning
        reasoning_max_tokens: Maximum reasoning tokens if supported
        tokenizer: Function to estimate token count (defaults to char/4)
        overhead_tokens: Token overhead for system prompts, tools, etc.
        safety_margin_pct: Safety margin to avoid hitting limits (0.07 = 7%)
        supports_vision: Whether model supports image inputs
        supports_function_calling: Whether model supports function/tool calling
        supports_json_mode: Whether model supports JSON response format
        temperature_range: Supported temperature range (min, max)
        optimal_for: List of task types this model excels at
    """
    model_id: str
    provider: ModelProvider
    max_input_tokens: int
    max_output_tokens: int
    supports_reasoning: bool
    reasoning_max_tokens: Optional[int] = None
    tokenizer: Optional[Callable[[str], int]] = None
    overhead_tokens: Dict[str, int] = field(default_factory=lambda: {
        "system": 200,
        "tool_base": 300,
        "per_tool": 80,
        "json_mode": 200
    })
    safety_margin_pct: float = 0.07
    supports_vision: bool = True
    supports_function_calling: bool = True
    supports_json_mode: bool = True
    temperature_range: tuple[float, float] = (0.0, 1.0)
    optimal_for: list[str] = field(default_factory=list)


def default_tokenizer(text: str) -> int:
    """
    Default token estimation using character-based approximation.
    Roughly 1 token ≈ 4 characters for English text.
    """
    return len(text) // 4


# Model Capabilities Registry
CAPABILITIES = {
    "gpt-5": ModelCapabilities(
        model_id="gpt-5",
        provider=ModelProvider.OPENAI,
        max_input_tokens=400_000,
        max_output_tokens=128_000,
        supports_reasoning=True,
        reasoning_max_tokens=128_000,
        tokenizer=default_tokenizer,
        overhead_tokens={
            "system": 200,
            "tool_base": 300,
            "per_tool": 80,
            "json_mode": 200
        },
        safety_margin_pct=0.07,
        supports_vision=True,
        supports_function_calling=True,
        supports_json_mode=True,
        temperature_range=(0.0, 1.0),
        optimal_for=["debugging", "code_review", "complex_reasoning", "planning"]
    ),
    
    "gpt-5-mini": ModelCapabilities(
        model_id="gpt-5-mini",
        provider=ModelProvider.OPENAI,
        max_input_tokens=400_000,
        max_output_tokens=128_000,
        supports_reasoning=True,
        reasoning_max_tokens=64_000,
        tokenizer=default_tokenizer,
        safety_margin_pct=0.07,
        optimal_for=["chat", "quick_analysis", "summarization"]
    ),
    
    "gpt-5-nano": ModelCapabilities(
        model_id="gpt-5-nano",
        provider=ModelProvider.OPENAI,
        max_input_tokens=400_000,
        max_output_tokens=128_000,
        supports_reasoning=True,
        reasoning_max_tokens=32_000,
        tokenizer=default_tokenizer,
        safety_margin_pct=0.07,
        optimal_for=["chat", "quick_responses", "classification"]
    ),
    
    "gpt-4.1": ModelCapabilities(
        model_id="gpt-4.1",
        provider=ModelProvider.OPENAI,
        max_input_tokens=1_000_000,
        max_output_tokens=32_768,
        supports_reasoning=False,
        tokenizer=default_tokenizer,
        overhead_tokens={
            "system": 200,
            "tool_base": 300,
            "per_tool": 80,
            "json_mode": 200
        },
        safety_margin_pct=0.07,
        supports_vision=True,
        supports_function_calling=True,
        supports_json_mode=True,
        temperature_range=(0.0, 2.0),
        optimal_for=["large_codebase_analysis", "refactoring", "comprehensive_review", "planning"]
    ),
    
    "o3": ModelCapabilities(
        model_id="o3",
        provider=ModelProvider.OPENAI,
        max_input_tokens=200_000,
        max_output_tokens=65_536,
        supports_reasoning=False,
        tokenizer=default_tokenizer,
        safety_margin_pct=0.07,
        temperature_range=(1.0, 1.0),  # Fixed temperature
        optimal_for=["logical_problems", "systematic_analysis"]
    ),
    
    "o3-mini": ModelCapabilities(
        model_id="o3-mini",
        provider=ModelProvider.OPENAI,
        max_input_tokens=200_000,
        max_output_tokens=65_536,
        supports_reasoning=False,
        tokenizer=default_tokenizer,
        safety_margin_pct=0.07,
        temperature_range=(1.0, 1.0),
        optimal_for=["balanced_analysis", "moderate_complexity"]
    ),
}


def get_model_capabilities(model_id: str) -> Optional[ModelCapabilities]:
    """
    Get capabilities for a specific model.
    
    Args:
        model_id: Model identifier
        
    Returns:
        ModelCapabilities object or None if not found
    """
    # Check direct match
    if model_id in CAPABILITIES:
        return CAPABILITIES[model_id]
    
    # Check aliases (handle gpt5, gpt-5, etc.)
    normalized = model_id.lower().replace("-", "").replace(".", "")
    for key, caps in CAPABILITIES.items():
        if key.lower().replace("-", "").replace(".", "") == normalized:
            return caps
    
    return None


def calculate_token_overhead(
    model_id: str,
    tools_enabled: bool = False,
    tool_count: int = 0,
    json_mode: bool = False
) -> int:
    """
    Calculate token overhead for a model based on configuration.
    
    Args:
        model_id: Model identifier
        tools_enabled: Whether tools/functions are enabled
        tool_count: Number of tools/functions
        json_mode: Whether JSON response mode is enabled
        
    Returns:
        Total token overhead
    """
    caps = get_model_capabilities(model_id)
    if not caps:
        # Conservative default overhead
        return 500
    
    overhead = caps.overhead_tokens.get("system", 200)
    
    if tools_enabled:
        overhead += caps.overhead_tokens.get("tool_base", 300)
        overhead += caps.overhead_tokens.get("per_tool", 80) * tool_count
    
    if json_mode:
        overhead += caps.overhead_tokens.get("json_mode", 200)
    
    return overhead


def get_effective_token_limit(
    model_id: str,
    tools_enabled: bool = False,
    tool_count: int = 0,
    json_mode: bool = False
) -> int:
    """
    Get effective token limit after accounting for overhead and safety margin.
    
    Args:
        model_id: Model identifier
        tools_enabled: Whether tools/functions are enabled
        tool_count: Number of tools/functions
        json_mode: Whether JSON response mode is enabled
        
    Returns:
        Effective token limit for user content
    """
    caps = get_model_capabilities(model_id)
    if not caps:
        # Conservative fallback
        return 100_000
    
    overhead = calculate_token_overhead(model_id, tools_enabled, tool_count, json_mode)
    available = caps.max_input_tokens * (1 - caps.safety_margin_pct)
    
    return int(available - overhead)


def get_optimal_models_for_task(task_type: str) -> list[str]:
    """
    Get list of models optimal for a specific task type.
    
    Args:
        task_type: Type of task (e.g., "debugging", "refactoring")
        
    Returns:
        List of model IDs sorted by preference
    """
    models = []
    for model_id, caps in CAPABILITIES.items():
        if task_type in caps.optimal_for:
            models.append(model_id)
    
    # Sort by token limits (prefer larger context for most tasks)
    models.sort(key=lambda m: CAPABILITIES[m].max_input_tokens, reverse=True)
    
    return models


def supports_reasoning(model_id: str) -> bool:
    """Check if model supports extended thinking/reasoning."""
    caps = get_model_capabilities(model_id)
    return caps.supports_reasoning if caps else False


def get_max_reasoning_tokens(model_id: str) -> Optional[int]:
    """Get maximum reasoning tokens for model if supported."""
    caps = get_model_capabilities(model_id)
    if caps and caps.supports_reasoning:
        return caps.reasoning_max_tokens
    return None