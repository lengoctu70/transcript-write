"""Rule-based validation for cleaned transcript output"""
import re
from dataclasses import dataclass, field
from typing import List, Optional
from enum import Enum


class ValidationSeverity(Enum):
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"


@dataclass
class ValidationIssue:
    """Single validation issue"""
    severity: ValidationSeverity
    rule: str
    message: str
    chunk_index: Optional[int] = None
    snippet: Optional[str] = None


@dataclass
class ValidationResult:
    """Validation result for all chunks"""
    issues: List[ValidationIssue] = field(default_factory=list)

    @property
    def has_errors(self) -> bool:
        return any(i.severity == ValidationSeverity.ERROR for i in self.issues)

    @property
    def has_warnings(self) -> bool:
        return any(i.severity == ValidationSeverity.WARNING for i in self.issues)

    @property
    def error_count(self) -> int:
        return sum(1 for i in self.issues if i.severity == ValidationSeverity.ERROR)

    @property
    def warning_count(self) -> int:
        return sum(1 for i in self.issues if i.severity == ValidationSeverity.WARNING)

    def to_dict(self) -> dict:
        return {
            "total_issues": len(self.issues),
            "errors": self.error_count,
            "warnings": self.warning_count,
            "issues": [
                {
                    "severity": i.severity.value,
                    "rule": i.rule,
                    "message": i.message,
                    "chunk": i.chunk_index,
                    "snippet": i.snippet
                }
                for i in self.issues
            ]
        }


class OutputValidator:
    """Validate cleaned transcript against rules"""

    FILLERS = [
        r"\buh\b", r"\bum\b", r"\bah\b", r"\ber\b",
        r"\byou know\b", r"\blike\b(?!\s+this|\s+that)",
        r"\bokay\b", r"\bso\b(?=\s*,)",
        r"\bbasically\b", r"\bactually\b", r"\breally\b",
        r"\bthe thing is\b", r"\bwhat I'm trying to say\b"
    ]

    CONTEXT_MARKERS = [
        r"\[CONTEXT FROM PREVIOUS SECTION\]",
        r"\[NEW CONTENT TO PROCESS\]",
        r"\[VIDEO INFO\]",
        r"\[TRANSCRIPT TO PROCESS\]"
    ]

    def validate_chunk(
        self,
        original: str,
        cleaned: str,
        chunk_index: int
    ) -> List[ValidationIssue]:
        """Validate single cleaned chunk"""
        issues = []
        issues.extend(self._check_fillers(cleaned, chunk_index))
        issues.extend(self._check_context_markers(cleaned, chunk_index))
        issues.extend(self._check_timestamp_format(cleaned, chunk_index))
        issues.extend(self._check_content_length(original, cleaned, chunk_index))
        issues.extend(self._check_questions(cleaned, chunk_index))
        return issues

    def validate_all(
        self,
        processed_chunks: list
    ) -> ValidationResult:
        """Validate all processed chunks"""
        result = ValidationResult()

        for chunk in processed_chunks:
            issues = self.validate_chunk(
                original=chunk.original_text,
                cleaned=chunk.cleaned_text,
                chunk_index=chunk.chunk_index
            )
            result.issues.extend(issues)

        return result

    def _check_fillers(
        self, text: str, chunk_index: int
    ) -> List[ValidationIssue]:
        """Check for remaining filler words"""
        issues = []
        text_lower = text.lower()

        for pattern in self.FILLERS:
            matches = list(re.finditer(pattern, text_lower, re.IGNORECASE))
            if matches:
                for match in matches[:3]:
                    start = max(0, match.start() - 20)
                    end = min(len(text), match.end() + 20)
                    snippet = "..." + text[start:end] + "..."

                    issues.append(ValidationIssue(
                        severity=ValidationSeverity.WARNING,
                        rule="filler_detected",
                        message=f"Possible filler word: '{match.group()}'",
                        chunk_index=chunk_index,
                        snippet=snippet
                    ))

        return issues

    def _check_context_markers(
        self, text: str, chunk_index: int
    ) -> List[ValidationIssue]:
        """Check for context markers that shouldn't appear in output"""
        issues = []

        for pattern in self.CONTEXT_MARKERS:
            if re.search(pattern, text):
                issues.append(ValidationIssue(
                    severity=ValidationSeverity.ERROR,
                    rule="context_marker_in_output",
                    message=f"Context marker found in output: {pattern}",
                    chunk_index=chunk_index
                ))

        return issues

    def _check_timestamp_format(
        self, text: str, chunk_index: int
    ) -> List[ValidationIssue]:
        """Check timestamp format is correct [HH:MM:SS]"""
        issues = []
        timestamps = re.findall(r"\[[\d:\.]+\]", text)

        for ts in timestamps:
            if not re.match(r"\[\d{2}:\d{2}:\d{2}\]|\[\d{2}:\d{2}\]", ts):
                issues.append(ValidationIssue(
                    severity=ValidationSeverity.WARNING,
                    rule="invalid_timestamp_format",
                    message=f"Invalid timestamp format: {ts}",
                    chunk_index=chunk_index
                ))

        return issues

    def _check_content_length(
        self,
        original: str,
        cleaned: str,
        chunk_index: int
    ) -> List[ValidationIssue]:
        """Check that output isn't too short (over-truncated)"""
        issues = []

        original_len = len(original)
        cleaned_len = len(cleaned)

        ratio = cleaned_len / original_len if original_len > 0 else 0

        if ratio < 0.3:
            issues.append(ValidationIssue(
                severity=ValidationSeverity.WARNING,
                rule="excessive_truncation",
                message=f"Output too short ({ratio:.0%} of original). May have lost content.",
                chunk_index=chunk_index
            ))
        elif ratio > 1.2:
            issues.append(ValidationIssue(
                severity=ValidationSeverity.WARNING,
                rule="content_expansion",
                message=f"Output longer than original ({ratio:.0%}). LLM may have added content.",
                chunk_index=chunk_index
            ))

        return issues

    def _check_questions(
        self, text: str, chunk_index: int
    ) -> List[ValidationIssue]:
        """Check for questions (should be converted to statements)"""
        issues = []
        questions = re.findall(r"[^.!?]*\?", text)

        if len(questions) > 2:
            issues.append(ValidationIssue(
                severity=ValidationSeverity.INFO,
                rule="many_questions",
                message=f"Found {len(questions)} questions. Consider if they should be statements.",
                chunk_index=chunk_index
            ))

        return issues
