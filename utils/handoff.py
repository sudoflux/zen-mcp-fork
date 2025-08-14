"""
Cross-Model Handoff System

This module provides a structured handoff mechanism for transferring context
between different models in multi-stage workflows, ensuring continuity and
minimizing context loss.
"""

import json
import logging
from dataclasses import dataclass, field, asdict
from typing import List, Dict, Optional, Any
from datetime import datetime

logger = logging.getLogger(__name__)


@dataclass
class FileReference:
    """Reference to a file in the handoff"""
    path: str
    hash: str
    ranges: Optional[List[str]] = None  # Line ranges if partial file
    relevance: str = "related"  # critical, important, related
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {k: v for k, v in asdict(self).items() if v is not None}


@dataclass
class HandoffEnvelope:
    """
    Structured envelope for cross-model context handoff.
    
    This envelope ensures that when switching between models (e.g., GPT-5 to GPT-4.1),
    the essential context is preserved without overwhelming token limits.
    """
    
    # Core identification (required fields first)
    stage_id: str
    source_model: str
    target_model: str
    task_summary: str
    task_kind: str  # debugging, planning, code_review, etc.
    
    # Optional/defaulted fields
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    
    # Key information
    key_constraints: List[str] = field(default_factory=list)
    requirements: List[str] = field(default_factory=list)
    
    # Work products
    findings: List[str] = field(default_factory=list)
    working_hypotheses: List[str] = field(default_factory=list)
    decisions_made: List[str] = field(default_factory=list)
    
    # Outstanding items
    unresolved_questions: List[str] = field(default_factory=list)
    action_items: List[str] = field(default_factory=list)
    
    # Next steps
    next_instructions: str = "Continue analysis based on findings"
    suggested_approach: Optional[str] = None
    
    # File context
    file_refs: List[FileReference] = field(default_factory=list)
    
    # Memory and conversation
    memory_state_id: Optional[str] = None
    conversation_id: Optional[str] = None
    
    # Context anchors for validation
    context_start_text: Optional[str] = None  # First 100 chars of original context
    context_end_text: Optional[str] = None    # Last 100 chars of original context
    
    # Metadata
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_context(self, include_files: bool = True) -> str:
        """
        Convert envelope to context string for next model.
        
        Args:
            include_files: Whether to include file references
            
        Returns:
            Formatted context string
        """
        sections = []
        
        # Header
        sections.append(f"## Handoff from {self.source_model} to {self.target_model}")
        sections.append(f"Stage: {self.stage_id} | Task Type: {self.task_kind}")
        sections.append(f"Timestamp: {self.timestamp}\n")
        
        # Task Summary
        sections.append("### Task Summary")
        sections.append(self.task_summary)
        
        # Key Constraints and Requirements
        if self.key_constraints:
            sections.append("\n### Key Constraints")
            for constraint in self.key_constraints:
                sections.append(f"- {constraint}")
        
        if self.requirements:
            sections.append("\n### Requirements")
            for req in self.requirements:
                sections.append(f"- {req}")
        
        # Findings and Decisions
        if self.findings:
            sections.append("\n### Key Findings")
            for finding in self.findings[:10]:  # Limit to top 10
                sections.append(f"- {finding}")
            if len(self.findings) > 10:
                sections.append(f"... and {len(self.findings) - 10} more findings")
        
        if self.decisions_made:
            sections.append("\n### Decisions Made")
            for decision in self.decisions_made:
                sections.append(f"- {decision}")
        
        # Working Hypotheses
        if self.working_hypotheses:
            sections.append("\n### Working Hypotheses")
            for hypothesis in self.working_hypotheses:
                sections.append(f"- {hypothesis}")
        
        # Outstanding Items
        if self.unresolved_questions:
            sections.append("\n### Unresolved Questions")
            for question in self.unresolved_questions:
                sections.append(f"- {question}")
        
        if self.action_items:
            sections.append("\n### Action Items")
            for item in self.action_items:
                sections.append(f"- {item}")
        
        # Next Steps
        sections.append("\n### Next Steps")
        sections.append(self.next_instructions)
        if self.suggested_approach:
            sections.append(f"\nSuggested Approach: {self.suggested_approach}")
        
        # File References
        if include_files and self.file_refs:
            sections.append("\n### Relevant Files")
            for ref in self.file_refs[:20]:  # Limit to 20 files
                range_info = f" (lines {', '.join(ref.ranges)})" if ref.ranges else ""
                sections.append(f"- [{ref.relevance}] {ref.path}{range_info}")
            if len(self.file_refs) > 20:
                sections.append(f"... and {len(self.file_refs) - 20} more files")
        
        # Memory Reference
        if self.memory_state_id or self.conversation_id:
            sections.append("\n### Context References")
            if self.memory_state_id:
                sections.append(f"Memory State: {self.memory_state_id}")
            if self.conversation_id:
                sections.append(f"Conversation: {self.conversation_id}")
        
        return "\n".join(sections)
    
    def to_json(self) -> str:
        """Serialize envelope to JSON."""
        data = asdict(self)
        # Convert FileReference objects
        data["file_refs"] = [ref.to_dict() for ref in self.file_refs]
        return json.dumps(data, indent=2)
    
    @classmethod
    def from_json(cls, json_str: str) -> "HandoffEnvelope":
        """Deserialize envelope from JSON."""
        data = json.loads(json_str)
        # Convert file_refs back to FileReference objects
        if "file_refs" in data:
            data["file_refs"] = [FileReference(**ref) for ref in data["file_refs"]]
        return cls(**data)
    
    def validate(self) -> List[str]:
        """
        Validate the envelope for completeness.
        
        Returns:
            List of validation errors (empty if valid)
        """
        errors = []
        
        if not self.stage_id:
            errors.append("Missing stage_id")
        if not self.source_model:
            errors.append("Missing source_model")
        if not self.target_model:
            errors.append("Missing target_model")
        if not self.task_summary:
            errors.append("Missing task_summary")
        if not self.task_kind:
            errors.append("Missing task_kind")
        
        # Warn if envelope is too large
        context_size = len(self.to_context())
        if context_size > 10000:  # ~2500 tokens
            errors.append(f"Envelope context too large ({context_size} chars)")
        
        return errors


class HandoffManager:
    """
    Manages handoff envelopes between models in workflows.
    
    This manager helps create, validate, and optimize handoffs for
    different model transitions.
    """
    
    def __init__(self):
        """Initialize the handoff manager."""
        self.handoff_history = []
    
    def create_handoff(
        self,
        source_model: str,
        target_model: str,
        stage_id: str,
        task_kind: str,
        task_summary: str,
        **kwargs
    ) -> HandoffEnvelope:
        """
        Create a new handoff envelope.
        
        Args:
            source_model: Model creating the handoff
            target_model: Model receiving the handoff
            stage_id: Current stage identifier
            task_kind: Type of task (debugging, planning, etc.)
            task_summary: Summary of the task
            **kwargs: Additional envelope fields
            
        Returns:
            HandoffEnvelope instance
        """
        envelope = HandoffEnvelope(
            source_model=source_model,
            target_model=target_model,
            stage_id=stage_id,
            task_kind=task_kind,
            task_summary=task_summary,
            **kwargs
        )
        
        # Validate
        errors = envelope.validate()
        if errors:
            logger.warning(f"Handoff validation warnings: {errors}")
        
        # Track history
        self.handoff_history.append({
            "timestamp": envelope.timestamp,
            "source": source_model,
            "target": target_model,
            "stage": stage_id
        })
        
        logger.info(f"Created handoff: {source_model} -> {target_model} for {stage_id}")
        
        return envelope
    
    def optimize_for_target(
        self,
        envelope: HandoffEnvelope,
        target_model: str
    ) -> HandoffEnvelope:
        """
        Optimize envelope for target model's capabilities.
        
        Args:
            envelope: Original envelope
            target_model: Target model identifier
            
        Returns:
            Optimized envelope
        """
        from .model_capabilities import get_model_capabilities
        
        caps = get_model_capabilities(target_model)
        if not caps:
            return envelope
        
        # For large context models (GPT-4.1), include more details
        if caps.max_input_tokens >= 900_000:
            # Can include all findings and files
            pass
        
        # For medium context models (GPT-5), balance detail
        elif caps.max_input_tokens >= 400_000:
            # Limit findings to top 20
            if len(envelope.findings) > 20:
                envelope.findings = envelope.findings[:20]
                envelope.metadata["findings_truncated"] = True
            
            # Limit file refs to critical and important only
            envelope.file_refs = [
                ref for ref in envelope.file_refs
                if ref.relevance in ["critical", "important"]
            ]
        
        # For smaller context models, aggressive summarization
        else:
            # Keep only top 5 findings
            envelope.findings = envelope.findings[:5]
            # Keep only critical files
            envelope.file_refs = [
                ref for ref in envelope.file_refs
                if ref.relevance == "critical"
            ]
            # Limit constraints and requirements
            envelope.key_constraints = envelope.key_constraints[:3]
            envelope.requirements = envelope.requirements[:3]
        
        return envelope
    
    def create_continuation_handoff(
        self,
        model: str,
        stage_id: str,
        partial_output: str,
        continuation_number: int
    ) -> HandoffEnvelope:
        """
        Create a handoff for output continuation (e.g., GPT-4.1 hitting 32K limit).
        
        Args:
            model: Model that needs continuation
            stage_id: Current stage
            partial_output: Output generated so far
            continuation_number: Which continuation this is
            
        Returns:
            Continuation handoff envelope
        """
        # Extract key points from partial output
        lines = partial_output.split('\n')
        last_complete_section = ""
        
        # Find last complete section
        for i in range(len(lines) - 1, -1, -1):
            if lines[i].startswith('#') or lines[i].startswith('##'):
                last_complete_section = '\n'.join(lines[i:min(i+10, len(lines))])
                break
        
        return self.create_handoff(
            source_model=model,
            target_model=model,  # Same model continues
            stage_id=f"{stage_id}_cont_{continuation_number}",
            task_kind="continuation",
            task_summary=f"Continue output from part {continuation_number}",
            next_instructions=f"CONTINUE from where you left off. Last section was:\n{last_complete_section}",
            metadata={
                "continuation_number": continuation_number,
                "partial_output_length": len(partial_output),
                "output_truncated_at": partial_output[-200:] if len(partial_output) > 200 else partial_output
            }
        )
    
    def get_handoff_chain(self, conversation_id: str) -> List[Dict[str, Any]]:
        """
        Get the chain of handoffs for a conversation.
        
        Args:
            conversation_id: Conversation identifier
            
        Returns:
            List of handoff summaries
        """
        # Filter by conversation (would need to track this in real implementation)
        return self.handoff_history


# Global handoff manager instance
_global_manager = None

def get_global_handoff_manager() -> HandoffManager:
    """Get or create the global handoff manager instance."""
    global _global_manager
    if _global_manager is None:
        _global_manager = HandoffManager()
    return _global_manager