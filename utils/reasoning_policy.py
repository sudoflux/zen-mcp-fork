"""
Reasoning Policy for GPT-5 Extended Thinking Optimization

This module provides adaptive reasoning token allocation for models that
support extended thinking (like GPT-5), optimizing reasoning depth based
on task complexity while controlling costs.
"""

import logging
from enum import Enum
from typing import Dict, Optional, Tuple
from dataclasses import dataclass

from .model_capabilities import get_model_capabilities, supports_reasoning, get_max_reasoning_tokens

logger = logging.getLogger(__name__)


class TaskKind(Enum):
    """
    Task categories for reasoning allocation.
    Each task type has different reasoning requirements.
    """
    # High complexity tasks requiring deep reasoning
    DEBUGGING = "debugging"
    PLANNING = "planning"
    ARCHITECTURE = "architecture"
    SECURITY_AUDIT = "security_audit"
    
    # Medium complexity tasks
    CODE_REVIEW = "code_review"
    REFACTORING = "refactoring"
    ANALYSIS = "analysis"
    CONSENSUS = "consensus"
    
    # Lower complexity tasks
    TESTING = "testing"
    DOCUMENTATION = "documentation"
    CHAT = "chat"
    SUMMARIZATION = "summarization"
    
    # Generic fallback
    GENERAL = "general"


class ReasoningEffort(Enum):
    """Reasoning effort levels"""
    MINIMAL = "minimal"   # 0.5% of model max
    LOW = "low"          # 8% of model max
    MEDIUM = "medium"    # 33% of model max
    HIGH = "high"        # 67% of model max
    MAX = "max"          # 100% of model max


@dataclass
class ReasoningConfig:
    """Configuration for reasoning allocation"""
    effort: ReasoningEffort
    base_tokens: int
    escalation_enabled: bool = True
    cost_limit: Optional[float] = None
    
    def to_dict(self) -> Dict[str, any]:
        """Convert to dictionary for API parameters"""
        return {
            "thinking_mode": self.effort.value,
            "reasoning_tokens": self.base_tokens,
            "escalation_enabled": self.escalation_enabled
        }


class ReasoningPolicy:
    """
    Manages reasoning token allocation for models with extended thinking.
    
    This policy helps optimize the use of reasoning tokens by:
    - Allocating tokens based on task complexity
    - Preventing excessive token usage
    - Supporting adaptive escalation on failure
    - Tracking reasoning costs
    """
    
    # Default token allocations by task kind
    DEFAULT_ALLOCATIONS = {
        # High complexity - maximum reasoning
        TaskKind.DEBUGGING: ReasoningConfig(ReasoningEffort.HIGH, 12_000),
        TaskKind.PLANNING: ReasoningConfig(ReasoningEffort.HIGH, 10_000),
        TaskKind.ARCHITECTURE: ReasoningConfig(ReasoningEffort.HIGH, 10_000),
        TaskKind.SECURITY_AUDIT: ReasoningConfig(ReasoningEffort.HIGH, 8_000),
        
        # Medium complexity - moderate reasoning
        TaskKind.CODE_REVIEW: ReasoningConfig(ReasoningEffort.MEDIUM, 6_000),
        TaskKind.REFACTORING: ReasoningConfig(ReasoningEffort.MEDIUM, 6_000),
        TaskKind.ANALYSIS: ReasoningConfig(ReasoningEffort.MEDIUM, 5_000),
        TaskKind.CONSENSUS: ReasoningConfig(ReasoningEffort.MEDIUM, 5_000),
        
        # Lower complexity - minimal reasoning
        TaskKind.TESTING: ReasoningConfig(ReasoningEffort.LOW, 3_000),
        TaskKind.DOCUMENTATION: ReasoningConfig(ReasoningEffort.LOW, 2_000),
        TaskKind.CHAT: ReasoningConfig(ReasoningEffort.LOW, 2_000),
        TaskKind.SUMMARIZATION: ReasoningConfig(ReasoningEffort.MINIMAL, 1_000),
        
        # Default
        TaskKind.GENERAL: ReasoningConfig(ReasoningEffort.LOW, 3_000),
    }
    
    # Effort to percentage mapping
    EFFORT_PERCENTAGES = {
        ReasoningEffort.MINIMAL: 0.005,  # 0.5%
        ReasoningEffort.LOW: 0.08,       # 8%
        ReasoningEffort.MEDIUM: 0.33,    # 33%
        ReasoningEffort.HIGH: 0.67,      # 67%
        ReasoningEffort.MAX: 1.0,        # 100%
    }
    
    def __init__(self, cost_per_thousand_tokens: float = 0.01):
        """
        Initialize the reasoning policy.
        
        Args:
            cost_per_thousand_tokens: Cost per 1K reasoning tokens (for budget tracking)
        """
        self.cost_per_thousand = cost_per_thousand_tokens
        self.usage_history = []
    
    def get_reasoning_params(
        self,
        model: str,
        task_kind: TaskKind,
        override_effort: Optional[ReasoningEffort] = None,
        override_tokens: Optional[int] = None
    ) -> Optional[Dict[str, any]]:
        """
        Get reasoning parameters for a model and task.
        
        Args:
            model: Model identifier
            task_kind: Type of task being performed
            override_effort: Override the default effort level
            override_tokens: Override the default token allocation
            
        Returns:
            Dictionary of reasoning parameters or None if model doesn't support reasoning
        """
        # Check if model supports reasoning
        if not supports_reasoning(model):
            logger.debug(f"Model {model} does not support reasoning tokens")
            return None
        
        # Get model's maximum reasoning tokens
        max_reasoning = get_max_reasoning_tokens(model)
        if not max_reasoning:
            logger.warning(f"Model {model} supports reasoning but max tokens unknown")
            max_reasoning = 128_000  # Default for GPT-5
        
        # Get base configuration for task
        config = self.DEFAULT_ALLOCATIONS.get(task_kind, self.DEFAULT_ALLOCATIONS[TaskKind.GENERAL])
        
        # Apply overrides
        if override_effort:
            config.effort = override_effort
        if override_tokens:
            config.base_tokens = override_tokens
        
        # Calculate actual tokens based on effort and model max
        if config.effort in self.EFFORT_PERCENTAGES:
            percentage = self.EFFORT_PERCENTAGES[config.effort]
            calculated_tokens = int(max_reasoning * percentage)
            # Use minimum of calculated and configured tokens
            actual_tokens = min(calculated_tokens, config.base_tokens, max_reasoning)
        else:
            actual_tokens = min(config.base_tokens, max_reasoning)
        
        logger.info(f"Allocating {actual_tokens} reasoning tokens for {task_kind.value} on {model}")
        
        # Track usage
        self.usage_history.append({
            "model": model,
            "task": task_kind.value,
            "tokens": actual_tokens,
            "effort": config.effort.value
        })
        
        return {
            "thinking_mode": config.effort.value,
            "reasoning_tokens": actual_tokens,
            "metadata": {
                "task_kind": task_kind.value,
                "escalation_enabled": config.escalation_enabled
            }
        }
    
    def escalate_reasoning(
        self,
        current_effort: ReasoningEffort,
        current_tokens: int
    ) -> Tuple[ReasoningEffort, int]:
        """
        Escalate reasoning effort for retry after failure.
        
        Args:
            current_effort: Current effort level
            current_tokens: Current token allocation
            
        Returns:
            Tuple of (new_effort, new_tokens)
        """
        # Effort escalation path
        escalation_path = [
            ReasoningEffort.MINIMAL,
            ReasoningEffort.LOW,
            ReasoningEffort.MEDIUM,
            ReasoningEffort.HIGH,
            ReasoningEffort.MAX
        ]
        
        try:
            current_index = escalation_path.index(current_effort)
            if current_index < len(escalation_path) - 1:
                new_effort = escalation_path[current_index + 1]
                # Increase tokens by 50%
                new_tokens = int(current_tokens * 1.5)
                logger.info(f"Escalating reasoning: {current_effort.value} -> {new_effort.value}, tokens: {current_tokens} -> {new_tokens}")
                return new_effort, new_tokens
        except ValueError:
            pass
        
        # Already at max or unknown effort
        return current_effort, current_tokens
    
    def get_adaptive_params(
        self,
        model: str,
        task_kind: TaskKind,
        attempt_number: int = 1,
        previous_failure: bool = False
    ) -> Optional[Dict[str, any]]:
        """
        Get adaptive reasoning parameters that adjust based on attempts.
        
        Args:
            model: Model identifier
            task_kind: Type of task
            attempt_number: Which attempt this is (1 = first try)
            previous_failure: Whether the previous attempt failed
            
        Returns:
            Reasoning parameters adjusted for attempt
        """
        base_params = self.get_reasoning_params(model, task_kind)
        if not base_params:
            return None
        
        # Escalate on retries
        if attempt_number > 1 or previous_failure:
            config = self.DEFAULT_ALLOCATIONS.get(task_kind, self.DEFAULT_ALLOCATIONS[TaskKind.GENERAL])
            
            # Escalate effort and tokens
            for _ in range(attempt_number - 1):
                new_effort, new_tokens = self.escalate_reasoning(
                    config.effort,
                    base_params["reasoning_tokens"]
                )
                config.effort = new_effort
                base_params["reasoning_tokens"] = new_tokens
                base_params["thinking_mode"] = new_effort.value
            
            base_params["metadata"]["attempt"] = attempt_number
            base_params["metadata"]["escalated"] = True
        
        return base_params
    
    def estimate_cost(self, tokens: int) -> float:
        """
        Estimate cost for reasoning tokens.
        
        Args:
            tokens: Number of reasoning tokens
            
        Returns:
            Estimated cost in dollars
        """
        return (tokens / 1000) * self.cost_per_thousand
    
    def get_usage_summary(self) -> Dict[str, any]:
        """
        Get summary of reasoning token usage.
        
        Returns:
            Dictionary with usage statistics
        """
        if not self.usage_history:
            return {"total_tokens": 0, "total_cost": 0, "calls": 0}
        
        total_tokens = sum(h["tokens"] for h in self.usage_history)
        total_cost = self.estimate_cost(total_tokens)
        
        # Group by task kind
        by_task = {}
        for history in self.usage_history:
            task = history["task"]
            if task not in by_task:
                by_task[task] = {"tokens": 0, "calls": 0}
            by_task[task]["tokens"] += history["tokens"]
            by_task[task]["calls"] += 1
        
        return {
            "total_tokens": total_tokens,
            "total_cost": total_cost,
            "calls": len(self.usage_history),
            "by_task": by_task,
            "average_tokens_per_call": total_tokens // len(self.usage_history) if self.usage_history else 0
        }


def get_task_kind_from_tool(tool_name: str) -> TaskKind:
    """
    Map tool name to task kind for reasoning allocation.
    
    Args:
        tool_name: Name of the tool being used
        
    Returns:
        Appropriate TaskKind
    """
    tool_mapping = {
        "debug": TaskKind.DEBUGGING,
        "planner": TaskKind.PLANNING,
        "codereview": TaskKind.CODE_REVIEW,
        "refactor": TaskKind.REFACTORING,
        "analyze": TaskKind.ANALYSIS,
        "consensus": TaskKind.CONSENSUS,
        "testgen": TaskKind.TESTING,
        "docgen": TaskKind.DOCUMENTATION,
        "chat": TaskKind.CHAT,
        "thinkdeep": TaskKind.ANALYSIS,
        "secaudit": TaskKind.SECURITY_AUDIT,
        "precommit": TaskKind.CODE_REVIEW,
        "tracer": TaskKind.ANALYSIS,
    }
    
    return tool_mapping.get(tool_name.lower(), TaskKind.GENERAL)


# Global policy instance
_global_policy = None

def get_global_reasoning_policy() -> ReasoningPolicy:
    """Get or create the global reasoning policy instance."""
    global _global_policy
    if _global_policy is None:
        _global_policy = ReasoningPolicy()
    return _global_policy