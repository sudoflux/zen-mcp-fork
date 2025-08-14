"""
Unit tests for GPT-5 and Opus 4.1 optimization components.

This test suite validates the new model-aware features including:
- Model capabilities registry
- Token budgeting
- Reasoning policy
- Handoff system
- File selection
- Model-aware conversation memory
"""

import pytest
import os
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from utils.model_capabilities import (
    get_model_capabilities,
    calculate_token_overhead,
    get_effective_token_limit,
    get_optimal_models_for_task,
    supports_reasoning,
    get_max_reasoning_tokens
)

from utils.token_budgeter import (
    TokenBudgeter,
    ContextPart,
    ContextPriority,
    estimate_tokens_for_model,
    can_fit_in_context
)

from utils.reasoning_policy import (
    ReasoningPolicy,
    TaskKind,
    ReasoningEffort,
    get_task_kind_from_tool
)

from utils.handoff import (
    HandoffEnvelope,
    HandoffManager,
    FileReference
)

from utils.file_selector import (
    FileSelector,
    FileRelevance,
    FileInfo,
    create_file_manifest
)


class TestModelCapabilities:
    """Test model capabilities registry."""
    
    def test_gpt5_capabilities(self):
        """Test GPT-5 model capabilities."""
        caps = get_model_capabilities("gpt-5")
        assert caps is not None
        assert caps.max_input_tokens == 400_000
        assert caps.max_output_tokens == 128_000
        assert caps.supports_reasoning is True
        assert caps.reasoning_max_tokens == 128_000
    
    def test_gpt41_capabilities(self):
        """Test GPT-4.1 (Opus) capabilities."""
        caps = get_model_capabilities("gpt-4.1")
        assert caps is not None
        assert caps.max_input_tokens == 1_000_000
        assert caps.max_output_tokens == 32_768
        assert caps.supports_reasoning is False
    
    def test_token_overhead_calculation(self):
        """Test token overhead calculation."""
        overhead = calculate_token_overhead("gpt-5", tools_enabled=True, tool_count=5)
        assert overhead > 0
        assert overhead == 200 + 300 + (80 * 5)  # system + tool_base + per_tool * count
    
    def test_effective_token_limit(self):
        """Test effective token limit calculation."""
        limit = get_effective_token_limit("gpt-5", tools_enabled=True, tool_count=3)
        assert limit > 0
        assert limit < 400_000  # Less than max due to overhead and safety margin
    
    def test_optimal_models_for_task(self):
        """Test model selection for tasks."""
        models = get_optimal_models_for_task("debugging")
        assert "gpt-5" in models
        
        models = get_optimal_models_for_task("refactoring")
        assert "gpt-4.1" in models
    
    def test_reasoning_support(self):
        """Test reasoning support detection."""
        assert supports_reasoning("gpt-5") is True
        assert supports_reasoning("gpt-4.1") is False
        assert get_max_reasoning_tokens("gpt-5") == 128_000


class TestTokenBudgeter:
    """Test token budgeting system."""
    
    def test_context_building(self):
        """Test basic context building."""
        budgeter = TokenBudgeter()
        
        parts = [
            ContextPart("system", 100, "System prompt", hard_required=True),
            ContextPart("instructions", 90, "User instructions", hard_required=True),
            ContextPart("files", 70, "File content " * 1000, hard_required=False),
            ContextPart("history", 50, "Conversation history", hard_required=False),
        ]
        
        result = budgeter.build_context("gpt-5", parts)
        
        assert result.final_text is not None
        assert len(result.parts_included) > 0
        assert result.tokens_used <= result.tokens_available
    
    def test_priority_ordering(self):
        """Test that higher priority parts are included first."""
        budgeter = TokenBudgeter()
        
        parts = [
            ContextPart("low", 30, "Low priority", hard_required=False),
            ContextPart("high", 90, "High priority", hard_required=False),
            ContextPart("medium", 60, "Medium priority", hard_required=False),
        ]
        
        result = budgeter.build_context("gpt-5", parts)
        
        # High priority should be included first
        if len(result.parts_included) > 0:
            assert "high" in result.parts_included
    
    def test_hard_required_parts(self):
        """Test that hard required parts are always included."""
        budgeter = TokenBudgeter()
        
        parts = [
            ContextPart("optional", 50, "Optional content" * 10000, hard_required=False),
            ContextPart("required", 100, "Required content", hard_required=True),
        ]
        
        result = budgeter.build_context("gpt-5", parts)
        
        assert "required" in result.parts_included
    
    def test_token_allocation(self):
        """Test token budget allocation."""
        budgeter = TokenBudgeter()
        
        allocations = budgeter.allocate_token_budget(
            "gpt-5",
            {"system": 0.1, "files": 0.6, "conversation": 0.3}
        )
        
        assert "system" in allocations
        assert "files" in allocations
        assert "conversation" in allocations
        total = sum(allocations.values())
        assert total > 0


class TestReasoningPolicy:
    """Test reasoning policy for GPT-5."""
    
    def test_reasoning_allocation(self):
        """Test reasoning token allocation."""
        policy = ReasoningPolicy()
        
        # GPT-5 should get reasoning tokens
        params = policy.get_reasoning_params("gpt-5", TaskKind.DEBUGGING)
        assert params is not None
        assert "thinking_mode" in params
        assert "reasoning_tokens" in params
        assert params["reasoning_tokens"] > 0
        
        # GPT-4.1 should not get reasoning tokens
        params = policy.get_reasoning_params("gpt-4.1", TaskKind.DEBUGGING)
        assert params is None
    
    def test_task_specific_allocation(self):
        """Test different allocations for different tasks."""
        policy = ReasoningPolicy()
        
        debug_params = policy.get_reasoning_params("gpt-5", TaskKind.DEBUGGING)
        chat_params = policy.get_reasoning_params("gpt-5", TaskKind.CHAT)
        
        assert debug_params["reasoning_tokens"] > chat_params["reasoning_tokens"]
    
    def test_reasoning_escalation(self):
        """Test reasoning escalation on retry."""
        policy = ReasoningPolicy()
        
        new_effort, new_tokens = policy.escalate_reasoning(
            ReasoningEffort.LOW, 3000
        )
        
        assert new_effort != ReasoningEffort.LOW
        assert new_tokens > 3000
    
    def test_adaptive_params(self):
        """Test adaptive parameters based on attempts."""
        policy = ReasoningPolicy()
        
        first_attempt = policy.get_adaptive_params("gpt-5", TaskKind.DEBUGGING, 1)
        second_attempt = policy.get_adaptive_params("gpt-5", TaskKind.DEBUGGING, 2)
        
        if first_attempt and second_attempt:
            assert second_attempt["reasoning_tokens"] >= first_attempt["reasoning_tokens"]
    
    def test_task_kind_mapping(self):
        """Test tool to task kind mapping."""
        assert get_task_kind_from_tool("debug") == TaskKind.DEBUGGING
        assert get_task_kind_from_tool("planner") == TaskKind.PLANNING
        assert get_task_kind_from_tool("chat") == TaskKind.CHAT


class TestHandoffSystem:
    """Test cross-model handoff system."""
    
    def test_handoff_creation(self):
        """Test creating a handoff envelope."""
        manager = HandoffManager()
        
        envelope = manager.create_handoff(
            source_model="gpt-5",
            target_model="gpt-4.1",
            stage_id="analysis_1",
            task_kind="debugging",
            task_summary="Analyzing bug in authentication",
            findings=["Found SQL injection vulnerability"],
            file_refs=[FileReference("auth.py", "abc123")]
        )
        
        assert envelope.source_model == "gpt-5"
        assert envelope.target_model == "gpt-4.1"
        assert len(envelope.findings) == 1
        assert len(envelope.file_refs) == 1
    
    def test_handoff_context_generation(self):
        """Test generating context from handoff."""
        envelope = HandoffEnvelope(
            stage_id="test_1",
            source_model="gpt-5",
            target_model="gpt-4.1",
            task_summary="Test task",
            task_kind="testing",
            findings=["Finding 1", "Finding 2"],
            next_instructions="Continue analysis"
        )
        
        context = envelope.to_context()
        
        assert "Test task" in context
        assert "Finding 1" in context
        assert "Continue analysis" in context
    
    def test_handoff_validation(self):
        """Test handoff validation."""
        envelope = HandoffEnvelope(
            stage_id="",  # Invalid - empty
            source_model="gpt-5",
            target_model="gpt-4.1",
            task_summary="",  # Invalid - empty
            task_kind="testing"
        )
        
        errors = envelope.validate()
        assert len(errors) > 0
        assert any("stage_id" in e for e in errors)
        assert any("task_summary" in e for e in errors)
    
    def test_continuation_handoff(self):
        """Test continuation handoff for output limits."""
        manager = HandoffManager()
        
        envelope = manager.create_continuation_handoff(
            model="gpt-4.1",
            stage_id="review_1",
            partial_output="## Part 1\nThis is the beginning...",
            continuation_number=2
        )
        
        assert "cont_2" in envelope.stage_id
        assert envelope.task_kind == "continuation"
        assert "CONTINUE" in envelope.next_instructions


class TestFileSelector:
    """Test smart file selection."""
    
    def test_file_relevance_scoring(self):
        """Test file relevance scoring."""
        selector = FileSelector()
        
        # Create mock files
        files = [
            "/project/test_auth.py",
            "/project/auth.py",
            "/project/readme.md",
            "/project/config.json"
        ]
        
        # Score files for debugging task
        score1, level1 = selector._calculate_relevance(
            "/project/auth.py",
            "def authenticate():",
            "debug authentication error",
            is_mentioned=False,
            is_error=True
        )
        
        score2, level2 = selector._calculate_relevance(
            "/project/readme.md",
            "# Project README",
            "debug authentication error",
            is_mentioned=False,
            is_error=False
        )
        
        assert score1 > score2
        assert level1 == FileRelevance.CRITICAL
    
    def test_file_selection_strategies(self):
        """Test different file selection strategies."""
        selector = FileSelector()
        
        # Mock file info
        files = []
        for i in range(10):
            info = FileInfo(
                path=f"/file_{i}.py",
                content=f"content {i}" * 100,
                token_count=100,
                relevance_score=90 - i * 5
            )
            files.append(info)
        
        # Test "all" strategy (GPT-4.1)
        result = selector._select_all_within_budget(files, 500, "gpt-4.1")
        assert len(result.selected_files) == 5  # 5 files * 100 tokens = 500
        
        # Test "priority" strategy (GPT-5)
        result = selector._select_by_priority(files, 300, "gpt-5")
        assert len(result.selected_files) == 3  # Top 3 files by relevance
    
    def test_file_manifest_creation(self):
        """Test creating file manifest."""
        files = [
            FileInfo(
                path="/critical.py",
                token_count=1000,
                relevance_level=FileRelevance.CRITICAL,
                is_summarized=False
            ),
            FileInfo(
                path="/helper.py",
                token_count=500,
                relevance_level=FileRelevance.LOW,
                is_summarized=True
            )
        ]
        
        manifest = create_file_manifest(files)
        
        assert "critical.py" in manifest
        assert "CRITICAL" in manifest
        assert "[SUMMARIZED]" in manifest


if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v"])