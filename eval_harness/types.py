"""
Data types for the evaluation harness.

Defines explicit data models for tasks, trials, graders, transcripts, and outcomes.
"""
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
from datetime import datetime


@dataclass
class TaskSpec:
    """A single evaluation task specification."""
    task_id: str
    suite: str  # "code", "model", or "hitl"
    question: str
    # Code grader fields
    expected_regex: Optional[str] = None
    expected_substring: Optional[str] = None
    forbidden_regexes: List[str] = field(default_factory=list)
    requires_source_type: Optional[str] = None  # e.g., "table_row"
    # Model judge fields
    rubric: Optional[str] = None
    # HITL fields
    rubric_fields: List[str] = field(default_factory=list)
    # Metadata
    notes: Optional[str] = None
    ground_truth: Optional[str] = None  # For reference, not used by graders


@dataclass
class TrialResult:
    """Result of a single trial (one attempt at a task)."""
    task_id: str
    suite: str
    trial_index: int
    timestamp: str
    git_commit: Optional[str]
    
    # Input
    question: str
    answer: str  # Output from the system - required field
    
    # Optional fields with defaults
    input_payload: Dict[str, Any] = field(default_factory=dict)
    chosen_agent: Optional[str] = None
    sources: List[Dict[str, Any]] = field(default_factory=list)
    
    # Outcome checks (pass/fail for code graders)
    outcome_checks: Dict[str, bool] = field(default_factory=dict)
    
    # Grader outputs
    code_grade: Optional[Dict[str, Any]] = None
    model_judge_grade: Optional[Dict[str, Any]] = None
    hitl_label: Optional[Dict[str, Any]] = None
    
    # Model/provider metadata
    model_metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class GradeResult:
    """Result from a grader."""
    passed: bool
    score: Optional[float] = None  # For model judge: 1-5
    evidence: Optional[str] = None
    uncertainty_flag: bool = False
    failure_reason: Optional[str] = None
    details: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Transcript:
    """Record of inputs/outputs/sources/tooling/log pointers."""
    question: str
    answer: str
    sources: List[Dict[str, Any]]
    chosen_agent: Optional[str] = None
    tool_used: Optional[str] = None
    log_pointers: List[str] = field(default_factory=list)


@dataclass
class Outcome:
    """Final state checks (if any) separate from transcript."""
    checks: Dict[str, bool] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)

