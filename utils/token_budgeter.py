"""
Token Budgeter for Model-Aware Context Management

This module provides intelligent token allocation and context building
based on model capabilities, ensuring optimal use of available context
windows while respecting token limits and safety margins.
"""

import logging
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any, Callable
from enum import Enum

from .model_capabilities import (
    get_model_capabilities,
    calculate_token_overhead,
    get_effective_token_limit,
    default_tokenizer
)

logger = logging.getLogger(__name__)


class ContextPriority(Enum):
    """Priority levels for context parts"""
    CRITICAL = 100  # Never drop (system prompts, instructions)
    HIGH = 90       # Keep if possible (recent findings, key files)
    MEDIUM = 70     # Include when space allows (conversation history)
    LOW = 50        # First to drop (older context, auxiliary files)
    OPTIONAL = 30   # Nice to have (examples, verbose explanations)


@dataclass
class ContextPart:
    """
    Represents a part of the context to be included in the prompt.
    
    Attributes:
        id: Unique identifier for this part
        priority: Priority level (higher = keep longer)
        content: The actual text content
        hard_required: If True, never drop this part
        summarizer: Optional function to summarize if space is tight
        metadata: Additional metadata about this part
    """
    id: str
    priority: int
    content: str
    hard_required: bool = False
    summarizer: Optional[Callable[[str, int], str]] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    @property
    def token_count(self) -> int:
        """Estimate token count for this part"""
        return default_tokenizer(self.content)


@dataclass
class BuiltContext:
    """Result of context building operation"""
    final_text: str
    parts_included: List[str]
    parts_summarized: List[str]
    parts_dropped: List[str]
    tokens_used: int
    tokens_available: int
    metadata: Dict[str, Any] = field(default_factory=dict)


class TokenBudgeter:
    """
    Manages token allocation and context building for different models.
    
    This class provides intelligent context management by:
    - Respecting model-specific token limits
    - Prioritizing content based on importance
    - Summarizing when necessary
    - Maintaining safety margins
    """
    
    def __init__(self, default_summarizer: Optional[Callable] = None):
        """
        Initialize the TokenBudgeter.
        
        Args:
            default_summarizer: Default summarization function to use
        """
        self.default_summarizer = default_summarizer
        self.tokenizer = default_tokenizer
    
    def build_context(
        self,
        model: str,
        parts: List[ContextPart],
        tools_enabled: bool = False,
        tool_count: int = 0,
        json_mode: bool = False,
        reserve_output_tokens: Optional[int] = None
    ) -> BuiltContext:
        """
        Build optimized context for model respecting token limits.
        
        Args:
            model: Model identifier
            parts: List of context parts to include
            tools_enabled: Whether tools/functions are enabled
            tool_count: Number of tools/functions
            json_mode: Whether JSON response mode is enabled
            reserve_output_tokens: Tokens to reserve for output (if None, uses model default)
            
        Returns:
            BuiltContext object with final text and metadata
        """
        caps = get_model_capabilities(model)
        
        # Calculate available tokens
        if caps:
            max_tokens = get_effective_token_limit(model, tools_enabled, tool_count, json_mode)
            
            # Reserve tokens for output if specified
            if reserve_output_tokens:
                max_tokens -= min(reserve_output_tokens, caps.max_output_tokens)
        else:
            # Conservative fallback
            max_tokens = 100_000
            logger.warning(f"No capabilities found for model {model}, using conservative limit")
        
        # Sort parts by priority (descending) and hard_required flag
        sorted_parts = sorted(
            parts,
            key=lambda p: (p.hard_required, p.priority),
            reverse=True
        )
        
        included_parts = []
        summarized_parts = []
        dropped_parts = []
        total_tokens = 0
        
        for part in sorted_parts:
            part_tokens = part.token_count
            
            # Try to include the part as-is
            if total_tokens + part_tokens <= max_tokens:
                included_parts.append(part)
                total_tokens += part_tokens
                logger.debug(f"Including part {part.id} ({part_tokens} tokens)")
            
            # If it doesn't fit and is hard required, try summarizing
            elif part.hard_required:
                if part.summarizer or self.default_summarizer:
                    summarizer = part.summarizer or self.default_summarizer
                    
                    # Calculate target size for summary
                    remaining_tokens = max_tokens - total_tokens
                    target_tokens = min(
                        int(remaining_tokens * 0.5),  # Use at most half of remaining
                        500  # But no more than 500 tokens for a summary
                    )
                    
                    if target_tokens > 50:  # Only summarize if we have reasonable space
                        try:
                            summarized_content = summarizer(part.content, target_tokens)
                            summarized_part = ContextPart(
                                id=f"{part.id}_summarized",
                                priority=part.priority,
                                content=summarized_content,
                                hard_required=True,
                                metadata={**part.metadata, "original_id": part.id}
                            )
                            
                            if summarized_part.token_count <= remaining_tokens:
                                included_parts.append(summarized_part)
                                summarized_parts.append(part.id)
                                total_tokens += summarized_part.token_count
                                logger.info(f"Summarized part {part.id} ({part_tokens} -> {summarized_part.token_count} tokens)")
                            else:
                                dropped_parts.append(part.id)
                                logger.warning(f"Dropped hard-required part {part.id} - even summary too large")
                        except Exception as e:
                            logger.error(f"Failed to summarize part {part.id}: {e}")
                            dropped_parts.append(part.id)
                    else:
                        dropped_parts.append(part.id)
                        logger.warning(f"Dropped hard-required part {part.id} - no space for summary")
                else:
                    dropped_parts.append(part.id)
                    logger.warning(f"Dropped hard-required part {part.id} - no summarizer available")
            
            # Optional part that doesn't fit - drop it
            else:
                dropped_parts.append(part.id)
                logger.debug(f"Dropping optional part {part.id} ({part_tokens} tokens)")
        
        # Build final text
        final_text = "\n\n".join([p.content for p in included_parts])
        
        return BuiltContext(
            final_text=final_text,
            parts_included=[p.id for p in included_parts],
            parts_summarized=summarized_parts,
            parts_dropped=dropped_parts,
            tokens_used=total_tokens,
            tokens_available=max_tokens,
            metadata={
                "model": model,
                "tools_enabled": tools_enabled,
                "tool_count": tool_count,
                "json_mode": json_mode
            }
        )
    
    def allocate_token_budget(
        self,
        model: str,
        budget_allocation: Dict[str, float],
        tools_enabled: bool = False,
        tool_count: int = 0
    ) -> Dict[str, int]:
        """
        Allocate token budget across different context categories.
        
        Args:
            model: Model identifier
            budget_allocation: Dictionary of category -> percentage (0.0-1.0)
            tools_enabled: Whether tools are enabled
            tool_count: Number of tools
            
        Returns:
            Dictionary of category -> token count
            
        Example:
            allocate_token_budget("gpt-5", {
                "system": 0.02,    # 2% for system prompt
                "files": 0.60,     # 60% for file content
                "conversation": 0.30,  # 30% for conversation history
                "buffer": 0.08     # 8% safety buffer
            })
        """
        # Validate allocations sum to <= 1.0
        total_allocation = sum(budget_allocation.values())
        if total_allocation > 1.0:
            raise ValueError(f"Budget allocations sum to {total_allocation}, must be <= 1.0")
        
        # Get total available tokens
        total_tokens = get_effective_token_limit(model, tools_enabled, tool_count)
        
        # Allocate tokens per category
        allocations = {}
        for category, percentage in budget_allocation.items():
            allocations[category] = int(total_tokens * percentage)
        
        # Add unallocated tokens to buffer
        allocated = sum(allocations.values())
        if allocated < total_tokens:
            if "buffer" in allocations:
                allocations["buffer"] += (total_tokens - allocated)
            else:
                allocations["unallocated"] = total_tokens - allocated
        
        return allocations
    
    def create_priority_context_parts(
        self,
        system_prompt: str,
        instructions: Optional[str] = None,
        conversation: Optional[str] = None,
        files: Optional[List[Dict[str, str]]] = None,
        findings: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> List[ContextPart]:
        """
        Create standard context parts with appropriate priorities.
        
        Args:
            system_prompt: System prompt (always included)
            instructions: User instructions
            conversation: Conversation history
            files: List of file dictionaries with 'path' and 'content'
            findings: Current findings or analysis
            metadata: Additional metadata
            
        Returns:
            List of ContextPart objects
        """
        parts = []
        
        # System prompt - always critical
        if system_prompt:
            parts.append(ContextPart(
                id="system",
                priority=ContextPriority.CRITICAL.value,
                content=system_prompt,
                hard_required=True
            ))
        
        # Instructions - critical
        if instructions:
            parts.append(ContextPart(
                id="instructions",
                priority=ContextPriority.CRITICAL.value,
                content=instructions,
                hard_required=True
            ))
        
        # Findings - high priority
        if findings:
            parts.append(ContextPart(
                id="findings",
                priority=ContextPriority.HIGH.value,
                content=findings,
                hard_required=False,
                summarizer=self.default_summarizer
            ))
        
        # Conversation - medium priority
        if conversation:
            parts.append(ContextPart(
                id="conversation",
                priority=ContextPriority.MEDIUM.value,
                content=conversation,
                hard_required=False,
                summarizer=self.default_summarizer
            ))
        
        # Files - prioritized by order
        if files:
            for i, file_info in enumerate(files):
                # First few files get higher priority
                priority = ContextPriority.HIGH.value if i < 3 else ContextPriority.MEDIUM.value
                
                parts.append(ContextPart(
                    id=f"file_{file_info.get('path', i)}",
                    priority=priority,
                    content=file_info.get('content', ''),
                    hard_required=False,
                    summarizer=self.default_summarizer,
                    metadata={"path": file_info.get('path')}
                ))
        
        # Metadata - optional
        if metadata:
            parts.append(ContextPart(
                id="metadata",
                priority=ContextPriority.OPTIONAL.value,
                content=str(metadata),
                hard_required=False
            ))
        
        return parts


def estimate_tokens_for_model(model: str, text: str) -> int:
    """
    Estimate token count for a specific model.
    
    Args:
        model: Model identifier
        text: Text to estimate tokens for
        
    Returns:
        Estimated token count
    """
    caps = get_model_capabilities(model)
    if caps and caps.tokenizer:
        return caps.tokenizer(text)
    return default_tokenizer(text)


def can_fit_in_context(
    model: str,
    text: str,
    tools_enabled: bool = False,
    tool_count: int = 0,
    reserve_output: bool = True
) -> bool:
    """
    Check if text can fit in model's context window.
    
    Args:
        model: Model identifier
        text: Text to check
        tools_enabled: Whether tools are enabled
        tool_count: Number of tools
        reserve_output: Whether to reserve space for output
        
    Returns:
        True if text fits, False otherwise
    """
    caps = get_model_capabilities(model)
    if not caps:
        return False
    
    available = get_effective_token_limit(model, tools_enabled, tool_count)
    
    if reserve_output:
        # Reserve 20% or max output tokens, whichever is smaller
        output_reserve = min(
            int(available * 0.2),
            caps.max_output_tokens
        )
        available -= output_reserve
    
    text_tokens = estimate_tokens_for_model(model, text)
    return text_tokens <= available