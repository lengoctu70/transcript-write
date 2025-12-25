"""Tests for output validator"""
import pytest
from src.validator import (
    ValidationSeverity,
    ValidationIssue,
    ValidationResult,
    OutputValidator
)
from src.llm_processor import ProcessedChunk


class TestValidationIssue:
    """Test ValidationIssue dataclass"""

    def test_validation_issue_creation(self):
        """Create ValidationIssue with all fields"""
        issue = ValidationIssue(
            severity=ValidationSeverity.ERROR,
            rule="test_rule",
            message="Test error message",
            chunk_index=0,
            snippet="Error context here"
        )
        assert issue.severity == ValidationSeverity.ERROR
        assert issue.rule == "test_rule"
        assert issue.message == "Test error message"
        assert issue.chunk_index == 0
        assert issue.snippet == "Error context here"

    def test_validation_issue_without_optional_fields(self):
        """Create ValidationIssue without optional fields"""
        issue = ValidationIssue(
            severity=ValidationSeverity.WARNING,
            rule="test_warning",
            message="Test warning"
        )
        assert issue.chunk_index is None
        assert issue.snippet is None


class TestValidationResult:
    """Test ValidationResult dataclass"""

    def test_empty_result(self):
        """Create empty ValidationResult"""
        result = ValidationResult()
        assert len(result.issues) == 0
        assert not result.has_errors
        assert not result.has_warnings
        assert result.error_count == 0
        assert result.warning_count == 0

    def test_result_with_errors(self):
        """Result with error issues"""
        result = ValidationResult()
        result.issues.append(ValidationIssue(
            severity=ValidationSeverity.ERROR,
            rule="error_1",
            message="Error 1"
        ))
        result.issues.append(ValidationIssue(
            severity=ValidationSeverity.WARNING,
            rule="warning_1",
            message="Warning 1"
        ))

        assert result.has_errors
        assert result.has_warnings
        assert result.error_count == 1
        assert result.warning_count == 1

    def test_result_to_dict(self):
        """Convert result to dictionary"""
        result = ValidationResult()
        result.issues.append(ValidationIssue(
            severity=ValidationSeverity.ERROR,
            rule="test_error",
            message="Test error",
            chunk_index=0,
            snippet="Test snippet"
        ))

        data = result.to_dict()
        assert data["total_issues"] == 1
        assert data["errors"] == 1
        assert data["warnings"] == 0
        assert len(data["issues"]) == 1
        assert data["issues"][0]["severity"] == "error"
        assert data["issues"][0]["rule"] == "test_error"
        assert data["issues"][0]["chunk"] == 0


class TestOutputValidator:
    """Test OutputValidator class"""

    def test_validate_clean_text_no_issues(self):
        """Validate clean text with no issues"""
        validator = OutputValidator()
        issues = validator.validate_chunk(
            original="This is the original text.",
            cleaned="This is the cleaned text.",
            chunk_index=0
        )
        assert len(issues) == 0

    def test_detect_filler_words(self):
        """Detect common filler words"""
        validator = OutputValidator()
        issues = validator.validate_chunk(
            original="Original content",
            cleaned="You know, this is basically like, um, important.",
            chunk_index=0
        )

        # Should detect filler words (warnings)
        filler_issues = [i for i in issues if i.rule == "filler_detected"]
        assert len(filler_issues) > 0
        assert all(i.severity == ValidationSeverity.WARNING for i in filler_issues)

    def test_detect_context_markers(self):
        """Detect context markers as errors"""
        validator = OutputValidator()

        # Test each context marker
        markers = [
            "[CONTEXT FROM PREVIOUS SECTION]",
            "[NEW CONTENT TO PROCESS]",
            "[VIDEO INFO]",
            "[TRANSCRIPT TO PROCESS]"
        ]

        for marker in markers:
            issues = validator.validate_chunk(
                original="Original",
                cleaned=f"Cleaned text {marker} more text",
                chunk_index=0
            )
            context_errors = [i for i in issues if i.rule == "context_marker_in_output"]
            assert len(context_errors) > 0
            assert context_errors[0].severity == ValidationSeverity.ERROR

    def test_valid_timestamp_format(self):
        """Accept valid timestamp formats"""
        validator = OutputValidator()
        issues = validator.validate_chunk(
            original="Original",
            cleaned="[00:01:30] This is valid content.\n[00:02:45] More content.",
            chunk_index=0
        )
        timestamp_issues = [i for i in issues if i.rule == "invalid_timestamp_format"]
        assert len(timestamp_issues) == 0

    def test_invalid_timestamp_format(self):
        """Detect invalid timestamp formats"""
        validator = OutputValidator()
        issues = validator.validate_chunk(
            original="Original",
            cleaned="[00:01:30.500] Invalid millisecond format.\n[1:30] Missing leading zero.",
            chunk_index=0
        )
        timestamp_issues = [i for i in issues if i.rule == "invalid_timestamp_format"]
        assert len(timestamp_issues) > 0

    def test_excessive_truncation_warning(self):
        """Warn when cleaned text is too short compared to original"""
        validator = OutputValidator()
        issues = validator.validate_chunk(
            original="A" * 1000,  # Long original
            cleaned="Short text",  # Very short cleaned
            chunk_index=0
        )
        truncation_warnings = [i for i in issues if i.rule == "excessive_truncation"]
        assert len(truncation_warnings) > 0

    def test_content_expansion_warning(self):
        """Warn when cleaned text is much longer than original"""
        validator = OutputValidator()
        issues = validator.validate_chunk(
            original="Short text",
            cleaned="A" * 1000,  # Much longer cleaned
            chunk_index=0
        )
        expansion_warnings = [i for i in issues if i.rule == "content_expansion"]
        assert len(expansion_warnings) > 0

    def test_detect_many_questions(self):
        """Detect when there are too many questions"""
        validator = OutputValidator()
        questions_text = " ".join([f"Question {i}?" for i in range(5)])
        issues = validator.validate_chunk(
            original="Original",
            cleaned=questions_text,
            chunk_index=0
        )
        question_issues = [i for i in issues if i.rule == "many_questions"]
        assert len(question_issues) > 0
        assert question_issues[0].severity == ValidationSeverity.INFO

    def test_few_questions_no_warning(self):
        """Don't warn for small number of questions"""
        validator = OutputValidator()
        issues = validator.validate_chunk(
            original="Original",
            cleaned="Is this good? Yes. What about that? Fine.",
            chunk_index=0
        )
        question_issues = [i for i in issues if i.rule == "many_questions"]
        assert len(question_issues) == 0

    def test_validate_all_chunks(self):
        """Validate multiple processed chunks"""
        validator = OutputValidator()

        chunks = [
            ProcessedChunk(
                chunk_index=0,
                original_text="Original text with filler words like, you know, um.",
                cleaned_text="Cleaned text with problems.",
                input_tokens=50,
                output_tokens=40,
                cost=0.001,
                model="claude-3-5-sonnet-20241022"
            ),
            ProcessedChunk(
                chunk_index=1,
                original_text="Original content that is reasonably long to avoid expansion warning",
                cleaned_text="[CONTEXT FROM PREVIOUS SECTION] Invalid content",
                input_tokens=30,
                output_tokens=25,
                cost=0.0005,
                model="claude-3-5-sonnet-20241022"
            )
        ]

        result = validator.validate_all(chunks)
        assert len(result.issues) > 0
        assert result.has_errors  # Context marker is an error

    def test_validate_clean_transcript(self):
        """Validate transcript that passes all checks"""
        validator = OutputValidator()

        chunk = ProcessedChunk(
            chunk_index=0,
            original_text="[00:00:00] Hello world this is reasonably long original text",
            cleaned_text="[00:00:00] This is clean and properly formatted content.",
            input_tokens=20,
            output_tokens=15,
            cost=0.0003,
            model="claude-3-5-sonnet-20241022"
        )

        result = validator.validate_all([chunk])
        assert not result.has_errors
        assert not result.has_warnings
        assert result.error_count == 0

    def test_fillers_list_patterns(self):
        """Verify filler patterns are regex compatible"""
        validator = OutputValidator()
        import re

        # All filler patterns should be valid regex
        for pattern in validator.FILLERS:
            try:
                re.compile(pattern, re.IGNORECASE)
            except re.error:
                pytest.fail(f"Invalid regex pattern: {pattern}")

    def test_snippet_generation_in_filler_detection(self):
        """Verify snippet generation includes context"""
        validator = OutputValidator()
        issues = validator.validate_chunk(
            original="Original",
            cleaned="This is a very long sentence that basically contains the word basically in the middle of it for testing purposes.",
            chunk_index=0
        )

        filler_issues = [i for i in issues if i.rule == "filler_detected"]
        if filler_issues:
            assert filler_issues[0].snippet is not None
            assert "..." in filler_issues[0].snippet

    def test_case_insensitive_filler_detection(self):
        """Detect filler words regardless of case"""
        validator = OutputValidator()
        issues = validator.validate_chunk(
            original="Original",
            cleaned="This is Basically and Actually and REALLY with different cases.",
            chunk_index=0
        )
        filler_issues = [i for i in issues if i.rule == "filler_detected"]
        assert len(filler_issues) > 0
