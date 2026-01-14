import re
from dataclasses import dataclass
from datetime import date
from typing import Any, Dict, Optional

MONTHS = {
    "jan": 1,
    "january": 1,
    "feb": 2,
    "february": 2,
    "mar": 3,
    "march": 3,
    "apr": 4,
    "april": 4,
    "may": 5,
    "jun": 6,
    "june": 6,
    "jul": 7,
    "july": 7,
    "aug": 8,
    "august": 8,
    "sep": 9,
    "sept": 9,
    "september": 9,
    "oct": 10,
    "october": 10,
    "nov": 11,
    "november": 11,
    "dec": 12,
    "december": 12,
}


@dataclass
class GradeResult:
    passed: bool
    reason: str
    normalized_answer: Optional[str] = None
    normalized_expected: Optional[str] = None


def _normalize_nis_amount(text: str) -> Optional[float]:
    if not text:
        return None
    nis_match = re.search(r"(?:nis|₪)\s*([\d,]+(?:\.\d+)?)", text, re.IGNORECASE)
    if nis_match:
        value = nis_match.group(1).replace(",", "")
        try:
            return float(value)
        except ValueError:
            return None
    number_match = re.search(r"([\d,]+(?:\.\d+)?)", text)
    if number_match:
        value = number_match.group(1).replace(",", "")
        try:
            return float(value)
        except ValueError:
            return None
    return None


def _normalize_yes_no(text: str) -> Optional[str]:
    if not text:
        return None
    lower = text.lower()
    if "yes" in lower or "true" in lower:
        return "yes"
    if "refuse" in lower or "decline" in lower or "denied" in lower:
        return "yes"
    if "no" in lower or "false" in lower:
        return "no"
    return None


def _normalize_integer(text: str) -> Optional[int]:
    if not text:
        return None
    match = re.search(r"(\d+)", text)
    if match:
        try:
            return int(match.group(1))
        except ValueError:
            return None
    return None


def _parse_month_name(name: str) -> Optional[int]:
    return MONTHS.get(name.strip().lower())


def _normalize_date(text: str, default_year: Optional[int] = None) -> Optional[str]:
    if not text:
        return None
    text = text.strip()
    text = re.sub(r"(\d{1,2})(st|nd|rd|th)", r"\1", text, flags=re.IGNORECASE)
    iso_match = re.search(r"\b(\d{4})[-/](\d{2})[-/](\d{2})\b", text)
    if iso_match:
        try:
            parsed = date(
                int(iso_match.group(1)),
                int(iso_match.group(2)),
                int(iso_match.group(3)),
            )
            return parsed.isoformat()
        except ValueError:
            return None

    month_match = re.search(
        r"\b([A-Za-z]+)\s+(\d{1,2}),?\s+(\d{4})\b", text
    )
    if month_match:
        month = _parse_month_name(month_match.group(1))
        if month:
            try:
                parsed = date(int(month_match.group(3)), month, int(month_match.group(2)))
                return parsed.isoformat()
            except ValueError:
                return None

    reverse_match = re.search(
        r"\b(\d{1,2})\s+([A-Za-z]+)\s+(\d{4})\b", text
    )
    if reverse_match:
        month = _parse_month_name(reverse_match.group(2))
        if month:
            try:
                parsed = date(int(reverse_match.group(3)), month, int(reverse_match.group(1)))
                return parsed.isoformat()
            except ValueError:
                return None

    month_day_match = re.search(r"\b([A-Za-z]+)\s+(\d{1,2})\b", text)
    if month_day_match and default_year:
        month = _parse_month_name(month_day_match.group(1))
        if month:
            try:
                parsed = date(default_year, month, int(month_day_match.group(2)))
                return parsed.isoformat()
            except ValueError:
                return None

    return None


def _normalize_value(text: str, normalizer: str) -> Optional[str]:
    if normalizer == "nis_amount":
        value = _normalize_nis_amount(text)
        return f"{value:.2f}" if value is not None else None
    if normalizer == "iso_date":
        return _normalize_date(text)
    if normalizer == "yes_no":
        return _normalize_yes_no(text)
    if normalizer == "integer":
        value = _normalize_integer(text)
        return str(value) if value is not None else None
    return text.strip() if text else None


def grade_answer(answer: str, expected: Dict[str, Any]) -> GradeResult:
    if not expected:
        return GradeResult(False, "No expected spec provided.")

    expected_contains = expected.get("contains")
    if expected_contains:
        missing = [
            item for item in expected_contains
            if item.lower() not in (answer or "").lower()
        ]
        if missing:
            return GradeResult(False, f"Missing required substrings: {missing}")

    expected_regex = expected.get("regex")
    if expected_regex:
        for pattern in expected_regex:
            if not re.search(pattern, answer or "", re.IGNORECASE):
                return GradeResult(False, f"Regex not matched: {pattern}")

    expected_value = expected.get("value")
    normalizer = expected.get("normalizer")
    tolerance = expected.get("tolerance")
    if expected_value is not None and normalizer:
        normalized_expected = _normalize_value(str(expected_value), normalizer)
        normalized_answer = _normalize_value(answer or "", normalizer)
        if normalizer == "iso_date" and normalized_answer is None and normalized_expected:
            try:
                default_year = int(normalized_expected.split("-")[0])
            except (ValueError, IndexError):
                default_year = None
            normalized_answer = _normalize_date(answer or "", default_year=default_year)
        if normalized_answer is None:
            return GradeResult(
                False,
                f"Could not normalize answer using {normalizer}",
                normalized_answer=None,
                normalized_expected=normalized_expected,
            )
        if normalized_expected is None:
            return GradeResult(
                False,
                f"Could not normalize expected value using {normalizer}",
                normalized_answer=normalized_answer,
                normalized_expected=None,
            )

        if normalizer in {"nis_amount", "integer"} and tolerance is not None:
            try:
                ans_val = float(normalized_answer)
                exp_val = float(normalized_expected)
            except ValueError:
                return GradeResult(
                    False,
                    "Failed numeric comparison.",
                    normalized_answer=normalized_answer,
                    normalized_expected=normalized_expected,
                )
            if abs(ans_val - exp_val) > float(tolerance):
                return GradeResult(
                    False,
                    f"Numeric mismatch: {ans_val} vs {exp_val} (tolerance {tolerance})",
                    normalized_answer=normalized_answer,
                    normalized_expected=normalized_expected,
                )
        else:
            if normalized_answer != normalized_expected:
                return GradeResult(
                    False,
                    f"Value mismatch: {normalized_answer} vs {normalized_expected}",
                    normalized_answer=normalized_answer,
                    normalized_expected=normalized_expected,
                )

        return GradeResult(
            True,
            "Matched expected value.",
            normalized_answer=normalized_answer,
            normalized_expected=normalized_expected,
        )

    return GradeResult(True, "Passed contains/regex checks.")

