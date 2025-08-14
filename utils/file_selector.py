"""
Smart File Selector for Model-Aware File Loading

This module provides intelligent file selection and loading based on model
capabilities, task context, and token budgets. It prioritizes relevant files
and can summarize large files when necessary.
"""

import os
import hashlib
import logging
from pathlib import Path
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any, Set, Tuple
from enum import Enum

from .model_capabilities import get_model_capabilities, default_tokenizer
from .token_budgeter import estimate_tokens_for_model

logger = logging.getLogger(__name__)


class FileRelevance(Enum):
    """File relevance levels for prioritization"""
    CRITICAL = 100    # Must include (mentioned in prompt, error file, etc.)
    HIGH = 80         # Very relevant (imported, related to task)
    MEDIUM = 60       # Somewhat relevant (same directory, similar name)
    LOW = 40          # Possibly relevant (project file)
    MINIMAL = 20      # Include if space allows


@dataclass
class FileInfo:
    """Information about a file for selection"""
    path: str
    content: Optional[str] = None
    size_bytes: int = 0
    token_count: int = 0
    relevance_score: float = 0.0
    relevance_level: FileRelevance = FileRelevance.LOW
    file_hash: Optional[str] = None
    is_summarized: bool = False
    summary: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def compute_hash(self) -> str:
        """Compute content hash for deduplication"""
        if self.content:
            return hashlib.sha256(self.content.encode()).hexdigest()[:16]
        return ""


@dataclass
class FileSelectionResult:
    """Result of file selection process"""
    selected_files: List[FileInfo]
    total_tokens: int
    total_files: int
    files_omitted: int
    files_summarized: int
    token_budget: int
    selection_strategy: str
    metadata: Dict[str, Any] = field(default_factory=dict)


class FileSelector:
    """
    Intelligent file selector that optimizes file loading based on:
    - Model token limits
    - Task relevance
    - File dependencies
    - Content deduplication
    """
    
    # File extensions by category
    CODE_EXTENSIONS = {
        '.py', '.js', '.ts', '.jsx', '.tsx', '.java', '.cpp', '.c', '.h',
        '.cs', '.go', '.rs', '.rb', '.php', '.swift', '.kt', '.scala',
        '.r', '.m', '.mm', '.sh', '.bash', '.zsh', '.fish'
    }
    
    CONFIG_EXTENSIONS = {
        '.json', '.yaml', '.yml', '.toml', '.ini', '.cfg', '.conf',
        '.env', '.properties'
    }
    
    DOC_EXTENSIONS = {
        '.md', '.rst', '.txt', '.adoc', '.tex'
    }
    
    def __init__(self, 
                 default_summarizer: Optional[callable] = None,
                 cache_summaries: bool = True):
        """
        Initialize the file selector.
        
        Args:
            default_summarizer: Function to summarize file content
            cache_summaries: Whether to cache file summaries
        """
        self.default_summarizer = default_summarizer
        self.cache_summaries = cache_summaries
        self.summary_cache = {} if cache_summaries else None
        self.file_cache = {}
    
    def select_files(
        self,
        files: List[str],
        model: str,
        task_context: Optional[str] = None,
        mentioned_files: Optional[List[str]] = None,
        error_files: Optional[List[str]] = None,
        budget_percentage: float = 0.6,
        include_dependencies: bool = True,
        strategy: str = "auto"
    ) -> FileSelectionResult:
        """
        Select most relevant files within token budget.
        
        Args:
            files: List of file paths to select from
            model: Model identifier for token limits
            task_context: Task description for relevance scoring
            mentioned_files: Files explicitly mentioned (highest priority)
            error_files: Files with errors (high priority)
            budget_percentage: Percentage of tokens to use for files (0.0-1.0)
            include_dependencies: Whether to include file dependencies
            strategy: Selection strategy ("all", "priority", "summary", "auto")
            
        Returns:
            FileSelectionResult with selected files and metadata
        """
        # Get model capabilities
        caps = get_model_capabilities(model)
        if caps:
            # Calculate file budget
            available_tokens = int(caps.max_input_tokens * (1 - caps.safety_margin_pct))
            file_budget = int(available_tokens * budget_percentage)
        else:
            # Conservative fallback
            file_budget = 60_000
        
        # Determine strategy based on model
        if strategy == "auto":
            if caps and caps.max_input_tokens >= 900_000:
                strategy = "all"  # GPT-4.1 can handle everything
            elif caps and caps.max_input_tokens >= 400_000:
                strategy = "priority"  # GPT-5 needs prioritization
            else:
                strategy = "summary"  # Smaller models need summaries
        
        # Load and score files
        file_infos = self._load_and_score_files(
            files, model, task_context,
            mentioned_files, error_files
        )
        
        # Apply selection strategy
        if strategy == "all":
            result = self._select_all_within_budget(file_infos, file_budget, model)
        elif strategy == "priority":
            result = self._select_by_priority(file_infos, file_budget, model)
        else:  # summary
            result = self._select_with_summarization(file_infos, file_budget, model)
        
        result.selection_strategy = strategy
        result.token_budget = file_budget
        
        logger.info(f"Selected {len(result.selected_files)}/{result.total_files} files "
                   f"using {result.total_tokens}/{file_budget} tokens "
                   f"(strategy: {strategy})")
        
        return result
    
    def _load_and_score_files(
        self,
        files: List[str],
        model: str,
        task_context: Optional[str],
        mentioned_files: Optional[List[str]],
        error_files: Optional[List[str]]
    ) -> List[FileInfo]:
        """Load files and calculate relevance scores."""
        file_infos = []
        mentioned_set = set(mentioned_files or [])
        error_set = set(error_files or [])
        
        for file_path in files:
            # Skip if file doesn't exist
            if not os.path.exists(file_path):
                continue
            
            # Create file info
            info = FileInfo(path=file_path)
            
            # Load content if not cached
            if file_path in self.file_cache:
                info.content = self.file_cache[file_path]
            else:
                try:
                    with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                        info.content = f.read()
                    self.file_cache[file_path] = info.content
                except Exception as e:
                    logger.warning(f"Failed to read {file_path}: {e}")
                    continue
            
            # Calculate size and tokens
            info.size_bytes = len(info.content.encode())
            info.token_count = estimate_tokens_for_model(model, info.content)
            info.file_hash = info.compute_hash()
            
            # Calculate relevance
            info.relevance_score, info.relevance_level = self._calculate_relevance(
                file_path, info.content, task_context,
                file_path in mentioned_set,
                file_path in error_set
            )
            
            file_infos.append(info)
        
        # Sort by relevance (descending)
        file_infos.sort(key=lambda x: x.relevance_score, reverse=True)
        
        return file_infos
    
    def _calculate_relevance(
        self,
        file_path: str,
        content: str,
        task_context: Optional[str],
        is_mentioned: bool,
        is_error: bool
    ) -> Tuple[float, FileRelevance]:
        """Calculate relevance score for a file."""
        score = 0.0
        level = FileRelevance.LOW
        
        # Critical files
        if is_mentioned:
            score = 100.0
            level = FileRelevance.CRITICAL
        elif is_error:
            score = 95.0
            level = FileRelevance.CRITICAL
        else:
            # Base score from file type
            path = Path(file_path)
            ext = path.suffix.lower()
            
            if ext in self.CODE_EXTENSIONS:
                score = 50.0
            elif ext in self.CONFIG_EXTENSIONS:
                score = 40.0
            elif ext in self.DOC_EXTENSIONS:
                score = 30.0
            else:
                score = 20.0
            
            # Boost score based on task context
            if task_context:
                task_lower = task_context.lower()
                file_lower = file_path.lower()
                content_lower = content.lower()[:1000]  # Check first 1000 chars
                
                # File name matches
                for keyword in task_lower.split():
                    if len(keyword) > 3:  # Skip short words
                        if keyword in file_lower:
                            score += 20.0
                        if keyword in content_lower:
                            score += 10.0
                
                # Special keywords in task
                if "test" in task_lower and "test" in file_lower:
                    score += 15.0
                if "error" in task_lower or "bug" in task_lower:
                    if "error" in content_lower or "exception" in content_lower:
                        score += 15.0
                if "config" in task_lower and ext in self.CONFIG_EXTENSIONS:
                    score += 20.0
            
            # Cap score and determine level
            score = min(score, 99.0)
            if score >= 80:
                level = FileRelevance.HIGH
            elif score >= 60:
                level = FileRelevance.MEDIUM
            elif score >= 40:
                level = FileRelevance.LOW
            else:
                level = FileRelevance.MINIMAL
        
        return score, level
    
    def _select_all_within_budget(
        self,
        file_infos: List[FileInfo],
        budget: int,
        model: str
    ) -> FileSelectionResult:
        """Select all files that fit within budget (GPT-4.1 strategy)."""
        selected = []
        total_tokens = 0
        
        for info in file_infos:
            if total_tokens + info.token_count <= budget:
                selected.append(info)
                total_tokens += info.token_count
        
        return FileSelectionResult(
            selected_files=selected,
            total_tokens=total_tokens,
            total_files=len(file_infos),
            files_omitted=len(file_infos) - len(selected),
            files_summarized=0
        )
    
    def _select_by_priority(
        self,
        file_infos: List[FileInfo],
        budget: int,
        model: str
    ) -> FileSelectionResult:
        """Select files by priority with optional summarization (GPT-5 strategy)."""
        selected = []
        total_tokens = 0
        files_summarized = 0
        
        # First pass: Include critical files (summarize if needed)
        for info in file_infos:
            if info.relevance_level != FileRelevance.CRITICAL:
                break
            
            if total_tokens + info.token_count <= budget:
                selected.append(info)
                total_tokens += info.token_count
            elif self.default_summarizer:
                # Summarize critical files that don't fit
                summary_budget = min(1000, budget - total_tokens)
                if summary_budget > 100:
                    summary = self._get_or_create_summary(info, summary_budget)
                    if summary:
                        info.content = summary
                        info.is_summarized = True
                        info.token_count = estimate_tokens_for_model(model, summary)
                        selected.append(info)
                        total_tokens += info.token_count
                        files_summarized += 1
        
        # Second pass: Include other files by priority
        for info in file_infos:
            if info.relevance_level == FileRelevance.CRITICAL:
                continue  # Already processed
            
            if total_tokens + info.token_count <= budget:
                selected.append(info)
                total_tokens += info.token_count
            elif info.relevance_level == FileRelevance.HIGH and self.default_summarizer:
                # Consider summarizing high-relevance files
                remaining = budget - total_tokens
                if remaining > 500:
                    summary_budget = min(500, remaining)
                    summary = self._get_or_create_summary(info, summary_budget)
                    if summary:
                        info.content = summary
                        info.is_summarized = True
                        info.token_count = estimate_tokens_for_model(model, summary)
                        selected.append(info)
                        total_tokens += info.token_count
                        files_summarized += 1
        
        return FileSelectionResult(
            selected_files=selected,
            total_tokens=total_tokens,
            total_files=len(file_infos),
            files_omitted=len(file_infos) - len(selected),
            files_summarized=files_summarized
        )
    
    def _select_with_summarization(
        self,
        file_infos: List[FileInfo],
        budget: int,
        model: str
    ) -> FileSelectionResult:
        """Aggressively summarize to fit more files (small model strategy)."""
        selected = []
        total_tokens = 0
        files_summarized = 0
        
        # Target summary size based on number of files
        files_to_include = min(len(file_infos), 20)  # Cap at 20 files
        tokens_per_file = budget // max(files_to_include, 1)
        
        for info in file_infos[:files_to_include]:
            if info.token_count <= tokens_per_file:
                # File fits as-is
                selected.append(info)
                total_tokens += info.token_count
            elif self.default_summarizer:
                # Summarize to fit
                summary_budget = min(tokens_per_file, 500)
                summary = self._get_or_create_summary(info, summary_budget)
                if summary:
                    info.content = summary
                    info.is_summarized = True
                    info.token_count = estimate_tokens_for_model(model, summary)
                    selected.append(info)
                    total_tokens += info.token_count
                    files_summarized += 1
        
        return FileSelectionResult(
            selected_files=selected,
            total_tokens=total_tokens,
            total_files=len(file_infos),
            files_omitted=len(file_infos) - len(selected),
            files_summarized=files_summarized
        )
    
    def _get_or_create_summary(
        self,
        file_info: FileInfo,
        target_tokens: int
    ) -> Optional[str]:
        """Get cached summary or create new one."""
        # Check cache
        cache_key = f"{file_info.file_hash}_{target_tokens}"
        if self.summary_cache and cache_key in self.summary_cache:
            return self.summary_cache[cache_key]
        
        # Create summary
        if self.default_summarizer:
            try:
                summary = self.default_summarizer(file_info.content, target_tokens)
                
                # Cache it
                if self.summary_cache is not None:
                    self.summary_cache[cache_key] = summary
                
                return summary
            except Exception as e:
                logger.error(f"Failed to summarize {file_info.path}: {e}")
        
        return None
    
    def find_dependencies(
        self,
        file_path: str,
        all_files: List[str],
        max_depth: int = 2
    ) -> Set[str]:
        """
        Find file dependencies (imports, includes, etc.).
        
        Args:
            file_path: File to find dependencies for
            all_files: List of all available files
            max_depth: Maximum depth to follow dependencies
            
        Returns:
            Set of dependent file paths
        """
        dependencies = set()
        
        # This is a simplified implementation
        # In practice, you'd use AST parsing for accurate dependency detection
        
        if not os.path.exists(file_path):
            return dependencies
        
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
            
            # Python imports
            if file_path.endswith('.py'):
                import_lines = [
                    line for line in content.split('\n')
                    if line.strip().startswith(('import ', 'from '))
                ]
                
                for line in import_lines:
                    # Extract module name
                    parts = line.split()
                    if parts[0] == 'from' and len(parts) > 1:
                        module = parts[1].split('.')[0]
                    elif parts[0] == 'import' and len(parts) > 1:
                        module = parts[1].split('.')[0]
                    else:
                        continue
                    
                    # Find matching files
                    for f in all_files:
                        if module in f and f != file_path:
                            dependencies.add(f)
            
            # JavaScript/TypeScript imports
            elif file_path.endswith(('.js', '.ts', '.jsx', '.tsx')):
                # Simple regex for imports
                import_patterns = [
                    r"import .* from ['\"](.+)['\"]",
                    r"require\(['\"](.+)['\"]\)"
                ]
                # Simplified - would need proper parsing
            
        except Exception as e:
            logger.warning(f"Failed to find dependencies for {file_path}: {e}")
        
        return dependencies


def create_file_manifest(
    files: List[FileInfo],
    include_summaries: bool = True
) -> str:
    """
    Create a manifest of selected files for context.
    
    Args:
        files: List of selected files
        include_summaries: Whether to note which files are summarized
        
    Returns:
        Formatted manifest string
    """
    if not files:
        return "No files included"
    
    lines = ["## File Manifest\n"]
    
    # Group by relevance level
    by_relevance = {}
    for f in files:
        level = f.relevance_level.name
        if level not in by_relevance:
            by_relevance[level] = []
        by_relevance[level].append(f)
    
    # Output by relevance
    for level in ["CRITICAL", "HIGH", "MEDIUM", "LOW", "MINIMAL"]:
        if level not in by_relevance:
            continue
        
        lines.append(f"\n### {level.title()} Relevance")
        for f in by_relevance[level]:
            status = " [SUMMARIZED]" if f.is_summarized else ""
            tokens = f"{f.token_count:,} tokens"
            lines.append(f"- {f.path} ({tokens}){status}")
    
    # Summary stats
    total_tokens = sum(f.token_count for f in files)
    total_summarized = sum(1 for f in files if f.is_summarized)
    
    lines.append(f"\n**Total: {len(files)} files, {total_tokens:,} tokens**")
    if total_summarized > 0:
        lines.append(f"**{total_summarized} files summarized to fit token budget**")
    
    return "\n".join(lines)