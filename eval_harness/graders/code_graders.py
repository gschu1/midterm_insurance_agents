"""
Code-based graders: fast, objective checks on answer text and context.
"""
import re
from typing import Any, Dict, List, Optional

from ..types import GradeResult


def regex_match_grader(
    answer: str,
    expected_regex: str,
    case_sensitive: bool = False
) -> GradeResult:
    """Check if answer matches expected regex pattern."""
    flags = 0 if case_sensitive else re.IGNORECASE
    pattern = re.compile(expected_regex, flags)
    matched = bool(pattern.search(answer))
    
    return GradeResult(
        passed=matched,
        evidence=f"Regex '{expected_regex}' {'matched' if matched else 'did not match'} answer",
        failure_reason=None if matched else f"Answer did not match pattern: {expected_regex}",
        details={"pattern": expected_regex, "matched": matched}
    )


def exact_substring_grader(
    answer: str,
    expected_substring: str,
    case_sensitive: bool = False
) -> GradeResult:
    """Check if answer contains expected substring."""
    if case_sensitive:
        found = expected_substring in answer
    else:
        found = expected_substring.lower() in answer.lower()
    
    return GradeResult(
        passed=found,
        evidence=f"Substring '{expected_substring}' {'found' if found else 'not found'} in answer",
        failure_reason=None if found else f"Answer did not contain: {expected_substring}",
        details={"substring": expected_substring, "found": found}
    )


def forbidden_pattern_grader(
    answer: str,
    forbidden_regexes: List[str],
    case_sensitive: bool = False
) -> GradeResult:
    """Check if answer contains any forbidden patterns."""
    flags = 0 if case_sensitive else re.IGNORECASE
    violations = []
    
    for pattern in forbidden_regexes:
        regex = re.compile(pattern, flags)
        if regex.search(answer):
            violations.append(pattern)
    
    passed = len(violations) == 0
    
    return GradeResult(
        passed=passed,
        evidence=f"{len(violations)} forbidden pattern(s) {'found' if violations else 'not found'}",
        failure_reason=None if passed else f"Forbidden patterns found: {', '.join(violations)}",
        details={"violations": violations, "patterns_checked": forbidden_regexes}
    )


def context_hit_grader(
    answer: str,
    sources: List[Dict[str, Any]],
    ground_truth: str,
    threshold: float = 0.7
) -> GradeResult:
    """Check if ground truth appears in retrieved context."""
    if not sources:
        return GradeResult(
            passed=False,
            evidence="No sources available to check",
            failure_reason="No retrieved context available",
            details={"sources_count": 0}
        )
    
    # Concatenate all source text
    context_text = "\n\n".join(
        s.get("text", "") for s in sources if s.get("text")
    )
    
    # Normalize for comparison
    def normalize(t: str) -> str:
        return re.sub(r'[^\w\s]', '', t.lower())
    
    norm_context = normalize(context_text)
    norm_ground = normalize(ground_truth)
    
    # For short ground truths, check exact substring
    if len(norm_ground) < 20:
        found = norm_ground in norm_context
    else:
        # For longer, check word overlap
        ground_words = set(norm_ground.split())
        context_words = set(norm_context.split())
        if len(ground_words) > 0:
            overlap = len(ground_words & context_words) / len(ground_words)
            found = overlap >= threshold
        else:
            found = False
    
    return GradeResult(
        passed=found,
        evidence=f"Ground truth {'found' if found else 'not found'} in retrieved context",
        failure_reason=None if found else "Ground truth not present in retrieved context",
        details={
            "ground_truth": ground_truth,
            "sources_count": len(sources),
            "context_length": len(context_text),
            "found": found
        }
    )


def source_type_grader(
    sources: List[Dict[str, Any]],
    required_type: str
) -> GradeResult:
    """Check if at least one source has the required node_type."""
    if not sources:
        return GradeResult(
            passed=False,
            evidence="No sources available",
            failure_reason="No retrieved context available",
            details={"required_type": required_type, "sources_count": 0}
        )
    
    # Check if any source has the required type
    # Note: sources from agents have node_id, score, text
    # We need to check if we can infer node_type from metadata
    # For now, we'll check if the text contains hints or if metadata is available
    found = False
    matching_sources = []
    
    for source in sources:
        # Check if source has metadata with node_type
        if isinstance(source, dict):
            metadata = source.get("metadata", {})
            if metadata.get("node_type") == required_type:
                found = True
                matching_sources.append(source.get("node_id", "unknown"))
            # Also check if text suggests the type (for table_row, might have structured format)
            text = source.get("text", "")
            if required_type == "table_row" and ":" in text and "," in text:
                # Heuristic: table rows often have "Key: value, Key: value" format
                found = True
                matching_sources.append(source.get("node_id", "unknown"))
    
    return GradeResult(
        passed=found,
        evidence=f"Required source type '{required_type}' {'found' if found else 'not found'}",
        failure_reason=None if found else f"No sources with type '{required_type}' found",
        details={
            "required_type": required_type,
            "sources_count": len(sources),
            "matching_sources": matching_sources,
            "found": found
        }
    )


def grade_code_task(
    task_spec: Dict[str, Any],
    answer: str,
    sources: List[Dict[str, Any]],
    ground_truth: Optional[str] = None
) -> Dict[str, Any]:
    """
    Grade a code task using all applicable graders.
    
    Returns a dict with all grader results.
    """
    results = {}
    
    # Regex match
    if task_spec.get("expected_regex"):
        results["regex_match"] = regex_match_grader(
            answer,
            task_spec["expected_regex"]
        )
    
    # Exact substring
    if task_spec.get("expected_substring"):
        results["exact_substring"] = exact_substring_grader(
            answer,
            task_spec["expected_substring"]
        )
    
    # Forbidden patterns
    if task_spec.get("forbidden_regexes"):
        results["forbidden_pattern"] = forbidden_pattern_grader(
            answer,
            task_spec["forbidden_regexes"]
        )
    
    # Context hit (if ground truth provided)
    if ground_truth:
        results["context_hit"] = context_hit_grader(
            answer,
            sources,
            ground_truth
        )
    
    # Source type requirement
    if task_spec.get("requires_source_type"):
        results["source_type"] = source_type_grader(
            sources,
            task_spec["requires_source_type"]
        )
    
    # Overall pass: all applicable graders must pass
    all_passed = all(r.passed for r in results.values()) if results else False
    
    return {
        "overall_passed": all_passed,
        "graders": {k: {
            "passed": v.passed,
            "evidence": v.evidence,
            "failure_reason": v.failure_reason,
            "details": v.details
        } for k, v in results.items()}
    }

