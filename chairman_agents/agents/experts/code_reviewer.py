"""Code Reviewer Agent Module.

This module implements a specialized code review expert agent that performs
comprehensive code quality analysis, identifies issues, and provides
actionable improvement suggestions.

Key Features:
    - Code quality assessment with scoring system
    - Design pattern recognition and verification
    - Naming convention validation
    - Cyclomatic complexity analysis
    - Refactoring suggestions with priority ranking

Classes:
    ReviewContext: Context information for code review
    NamingIssue: Issue found in naming conventions
    ComplexityReport: Code complexity analysis report
    RefactoringSuggestion: Suggested code refactoring
    PatternViolation: Design pattern violation
    CodeReview: Comprehensive code review result
    BaseExpertAgent: Base class for all expert agents
    CodeReviewerAgent: Code review specialist agent

Example:
    >>> agent = CodeReviewerAgent(profile, llm_client, memory)
    >>> review = await agent.review_code(code, context)
    >>> print(f"Quality Score: {review.overall_score}")
"""

from __future__ import annotations

import ast
import logging
import re
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING, Protocol, runtime_checkable

from ...core.exceptions import TaskExecutionError
from ...core.protocols import LLMClientProtocol
from ...core.types import (
    AgentCapability,
    AgentId,
    AgentProfile,
    AgentRole,
    Artifact,
    ArtifactType,
    ExpertiseLevel,
    ReviewComment,
    Task,
    TaskResult,
    TaskStatus,
    generate_id,
)

if TYPE_CHECKING:
    from typing import Any

    from ...cognitive.memory import MemorySystem
    from ...cognitive.reasoning import ReasoningEngine


# =============================================================================
# Logging Configuration
# =============================================================================

logger = logging.getLogger(__name__)


# =============================================================================
# Enums
# =============================================================================


class ReviewSeverity(Enum):
    """Severity levels for review findings."""

    INFO = "info"
    """Informational note, no action required"""

    SUGGESTION = "suggestion"
    """Minor improvement suggestion"""

    WARNING = "warning"
    """Should be addressed"""

    ERROR = "error"
    """Must be fixed before merge"""

    CRITICAL = "critical"
    """Blocking issue, immediate action required"""


class ReviewCategory(Enum):
    """Categories for review findings."""

    NAMING = "naming"
    """Naming convention issues"""

    STYLE = "style"
    """Code style issues"""

    LOGIC = "logic"
    """Logic or algorithm issues"""

    SECURITY = "security"
    """Security vulnerabilities"""

    PERFORMANCE = "performance"
    """Performance concerns"""

    MAINTAINABILITY = "maintainability"
    """Maintainability issues"""

    COMPLEXITY = "complexity"
    """Code complexity issues"""

    PATTERN = "pattern"
    """Design pattern violations"""

    DOCUMENTATION = "documentation"
    """Documentation issues"""

    TESTING = "testing"
    """Testing related issues"""


# =============================================================================
# Data Classes
# =============================================================================


@dataclass
class ReviewContext:
    """Context information for code review.

    Provides context about the code being reviewed including
    project standards, related files, and specific focus areas.

    Attributes:
        language: Programming language of the code
        framework: Framework being used (if any)
        coding_standards: Project coding standards
        focus_areas: Specific areas to focus review on
        related_files: Related files for context
        skip_rules: Rules to skip during review
        max_issues: Maximum number of issues to report
    """

    language: str = "python"
    """Programming language of the code"""

    framework: str | None = None
    """Framework being used (e.g., 'fastapi', 'django')"""

    coding_standards: dict[str, Any] = field(default_factory=dict)
    """Project coding standards and conventions"""

    focus_areas: list[ReviewCategory] = field(default_factory=list)
    """Specific areas to focus the review on"""

    related_files: list[str] = field(default_factory=list)
    """Paths to related files for context"""

    skip_rules: list[str] = field(default_factory=list)
    """Rule IDs to skip during review"""

    max_issues: int = 50
    """Maximum number of issues to report"""


@dataclass
class NamingIssue:
    """Issue found in naming conventions.

    Represents a naming convention violation with location
    and suggested fix.

    Attributes:
        id: Unique issue identifier
        name: The problematic name
        issue_type: Type of naming issue
        line_number: Line where the issue occurs
        expected_pattern: Expected naming pattern
        suggestion: Suggested replacement name
        severity: Issue severity level
        explanation: Explanation of the issue
    """

    id: str = field(default_factory=lambda: generate_id("naming"))
    """Unique issue identifier"""

    name: str = ""
    """The problematic name"""

    issue_type: str = ""
    """Type: class_name, function_name, variable_name, constant, etc."""

    line_number: int = 0
    """Line where the issue occurs"""

    expected_pattern: str = ""
    """Expected naming pattern (e.g., 'snake_case', 'PascalCase')"""

    suggestion: str = ""
    """Suggested replacement name"""

    severity: ReviewSeverity = ReviewSeverity.SUGGESTION
    """Issue severity level"""

    explanation: str = ""
    """Explanation of why this is an issue"""


@dataclass
class ComplexityReport:
    """Code complexity analysis report.

    Contains detailed metrics about code complexity including
    cyclomatic complexity, cognitive complexity, and nesting depth.

    Attributes:
        overall_score: Overall complexity score (0-10, lower is better)
        cyclomatic_complexity: Cyclomatic complexity value
        cognitive_complexity: Cognitive complexity value
        max_nesting_depth: Maximum nesting depth
        loc: Lines of code
        sloc: Source lines of code (non-blank, non-comment)
        function_complexities: Per-function complexity breakdown
        hotspots: Most complex code sections
        recommendations: Complexity reduction recommendations
    """

    overall_score: float = 0.0
    """Overall complexity score (0-10, lower is better)"""

    cyclomatic_complexity: int = 0
    """McCabe cyclomatic complexity"""

    cognitive_complexity: int = 0
    """Cognitive complexity (Sonar style)"""

    max_nesting_depth: int = 0
    """Maximum nesting depth in the code"""

    loc: int = 0
    """Total lines of code"""

    sloc: int = 0
    """Source lines of code (excluding blanks/comments)"""

    function_complexities: dict[str, int] = field(default_factory=dict)
    """Per-function cyclomatic complexity"""

    hotspots: list[dict[str, Any]] = field(default_factory=list)
    """Most complex code sections with locations"""

    recommendations: list[str] = field(default_factory=list)
    """Recommendations for reducing complexity"""


@dataclass
class RefactoringSuggestion:
    """Suggested code refactoring.

    Represents a refactoring opportunity with before/after
    code examples and impact assessment.

    Attributes:
        id: Unique suggestion identifier
        title: Short title for the refactoring
        description: Detailed description of the refactoring
        category: Refactoring category
        priority: Priority level (1-5, 1 is highest)
        line_start: Starting line of code to refactor
        line_end: Ending line of code to refactor
        original_code: Original code snippet
        suggested_code: Suggested refactored code
        estimated_impact: Estimated impact on maintainability
        effort: Estimated effort (low, medium, high)
        pattern: Design pattern to apply (if applicable)
    """

    id: str = field(default_factory=lambda: generate_id("refactor"))
    """Unique suggestion identifier"""

    title: str = ""
    """Short title for the refactoring"""

    description: str = ""
    """Detailed description of the refactoring"""

    category: str = ""
    """Category: extract_method, rename, simplify, etc."""

    priority: int = 3
    """Priority level (1-5, 1 is highest)"""

    line_start: int = 0
    """Starting line of code to refactor"""

    line_end: int = 0
    """Ending line of code to refactor"""

    original_code: str = ""
    """Original code snippet"""

    suggested_code: str = ""
    """Suggested refactored code"""

    estimated_impact: str = ""
    """Estimated impact: 'minor', 'moderate', 'significant'"""

    effort: str = "medium"
    """Estimated effort: 'low', 'medium', 'high'"""

    pattern: str | None = None
    """Design pattern to apply (if applicable)"""


@dataclass
class PatternViolation:
    """Design pattern violation.

    Represents a violation of established design patterns
    or architectural principles.

    Attributes:
        id: Unique violation identifier
        pattern_name: Name of the violated pattern
        violation_type: Type of violation
        location: Location in code (file:line)
        description: Description of the violation
        severity: Violation severity
        suggested_fix: How to fix the violation
        references: References to pattern documentation
    """

    id: str = field(default_factory=lambda: generate_id("pattern"))
    """Unique violation identifier"""

    pattern_name: str = ""
    """Name of the violated pattern (e.g., 'Single Responsibility')"""

    violation_type: str = ""
    """Type: missing, incorrect_implementation, anti_pattern"""

    location: str = ""
    """Location in code (file:line)"""

    description: str = ""
    """Description of the violation"""

    severity: ReviewSeverity = ReviewSeverity.WARNING
    """Violation severity"""

    suggested_fix: str = ""
    """Suggested fix for the violation"""

    references: list[str] = field(default_factory=list)
    """References to pattern documentation"""


@dataclass
class QualityScores:
    """Quality assessment scores.

    Provides detailed quality scores across multiple dimensions.

    Attributes:
        readability: Code readability score (0.0-1.0)
        maintainability: Maintainability score (0.0-1.0)
        performance: Performance score (0.0-1.0)
        security: Security score (0.0-1.0)
        testability: Testability score (0.0-1.0)
        documentation: Documentation score (0.0-1.0)
    """

    readability: float = 0.0
    """Code readability score (0.0-1.0)"""

    maintainability: float = 0.0
    """Maintainability score (0.0-1.0)"""

    performance: float = 0.0
    """Performance score (0.0-1.0)"""

    security: float = 0.0
    """Security score (0.0-1.0)"""

    testability: float = 0.0
    """Testability score (0.0-1.0)"""

    documentation: float = 0.0
    """Documentation quality score (0.0-1.0)"""

    @property
    def overall(self) -> float:
        """Calculate overall weighted quality score."""
        weights = {
            "readability": 0.20,
            "maintainability": 0.25,
            "performance": 0.15,
            "security": 0.20,
            "testability": 0.10,
            "documentation": 0.10,
        }
        return sum(
            getattr(self, attr) * weight
            for attr, weight in weights.items()
        )


@dataclass
class CodeReview:
    """Comprehensive code review result.

    Contains the complete results of a code review including
    all findings, scores, and recommendations.

    Attributes:
        id: Unique review identifier
        reviewer_id: ID of the reviewing agent
        reviewed_at: When the review was performed
        comments: List of review comments
        naming_issues: Naming convention issues found
        complexity_report: Complexity analysis report
        refactoring_suggestions: Suggested refactorings
        pattern_violations: Pattern violations found
        quality_scores: Quality assessment scores
        overall_score: Overall quality score (0.0-1.0)
        summary: Summary of the review
        approval_status: Approval status
        blocking_issues: Number of blocking issues
    """

    id: str = field(default_factory=lambda: generate_id("review"))
    """Unique review identifier"""

    reviewer_id: AgentId = ""
    """ID of the reviewing agent"""

    reviewed_at: datetime = field(default_factory=datetime.now)
    """When the review was performed"""

    # Findings
    comments: list[ReviewComment] = field(default_factory=list)
    """List of review comments"""

    naming_issues: list[NamingIssue] = field(default_factory=list)
    """Naming convention issues found"""

    complexity_report: ComplexityReport | None = None
    """Complexity analysis report"""

    refactoring_suggestions: list[RefactoringSuggestion] = field(default_factory=list)
    """Suggested refactorings"""

    pattern_violations: list[PatternViolation] = field(default_factory=list)
    """Pattern violations found"""

    # Scores
    quality_scores: QualityScores = field(default_factory=QualityScores)
    """Quality assessment scores"""

    overall_score: float = 0.0
    """Overall quality score (0.0-1.0)"""

    # Summary
    summary: str = ""
    """Summary of the review"""

    approval_status: str = "pending"
    """Status: pending, approved, request_changes, rejected"""

    blocking_issues: int = 0
    """Number of blocking issues found"""

    def get_issues_by_severity(self, severity: ReviewSeverity) -> list[ReviewComment]:
        """Get all issues of a specific severity."""
        return [c for c in self.comments if c.severity == severity.value]

    def get_issues_by_category(self, category: ReviewCategory) -> list[ReviewComment]:
        """Get all issues of a specific category."""
        return [c for c in self.comments if c.category == category.value]


# =============================================================================
# Base Expert Agent
# =============================================================================


class BaseExpertAgent(ABC):
    """Base class for all expert agents.

    Provides common functionality for expert agents including
    profile management, reasoning integration, and memory access.

    Attributes:
        profile: Agent's profile and capabilities
        reasoning: Reasoning engine for decision making
        memory: Memory system for context
        role: Agent's role (to be set by subclasses)
    """

    role: AgentRole = AgentRole.BACKEND_ENGINEER

    def __init__(
        self,
        profile: AgentProfile,
        llm_client: LLMClientProtocol,
        memory: MemorySystem,
    ) -> None:
        """Initialize the expert agent.

        Args:
            profile: Agent's profile and capabilities
            llm_client: LLM client for reasoning
            memory: Memory system for context
        """
        self.profile = profile
        self._llm_client = llm_client
        self.memory = memory
        self._reasoning: ReasoningEngine | None = None

        logger.info(
            "Initialized %s agent: id=%s, name=%s",
            self.__class__.__name__, profile.id, profile.name
        )

    @property
    def id(self) -> AgentId:
        """Get agent ID."""
        return self.profile.id

    @property
    def name(self) -> str:
        """Get agent name."""
        return self.profile.name

    @property
    def reasoning(self) -> ReasoningEngine:
        """Get or create reasoning engine."""
        if self._reasoning is None:
            from ...cognitive.reasoning import ReasoningEngine
            self._reasoning = ReasoningEngine(self._llm_client)
        return self._reasoning

    @abstractmethod
    async def execute(self, task: Task) -> TaskResult:
        """Execute a task.

        Args:
            task: The task to execute

        Returns:
            Result of task execution
        """
        ...

    async def receive_message(self, message: Any) -> None:
        """Receive and process a message.

        Args:
            message: The message to process
        """
        logger.debug("Agent %s received message: %s", self.id, type(message).__name__)


# =============================================================================
# Code Reviewer Agent
# =============================================================================


class CodeReviewerAgent(BaseExpertAgent):
    """Code review specialist agent.

    Expert in code quality assessment, design pattern recognition,
    and providing actionable improvement suggestions.

    Capabilities:
        - Comprehensive code quality evaluation
        - Naming convention validation
        - Cyclomatic complexity analysis
        - Design pattern verification
        - Refactoring suggestions
    """

    role = AgentRole.CODE_REVIEWER

    # Naming patterns for Python
    NAMING_PATTERNS = {
        "class": re.compile(r"^[A-Z][a-zA-Z0-9]*$"),
        "function": re.compile(r"^[a-z_][a-z0-9_]*$"),
        "variable": re.compile(r"^[a-z_][a-z0-9_]*$"),
        "constant": re.compile(r"^[A-Z][A-Z0-9_]*$"),
        "module": re.compile(r"^[a-z][a-z0-9_]*$"),
    }

    def __init__(
        self,
        profile: AgentProfile,
        llm_client: LLMClientProtocol,
        memory: MemorySystem,
    ) -> None:
        """Initialize the code reviewer agent."""
        super().__init__(profile, llm_client, memory)

        # Ensure proper capabilities
        if AgentCapability.CODE_REVIEW not in profile.capabilities:
            profile.capabilities.append(AgentCapability.CODE_REVIEW)

    async def execute(self, task: Task) -> TaskResult:
        """Execute a code review task.

        Args:
            task: The code review task

        Returns:
            TaskResult containing the review
        """
        start_time = time.time()

        try:
            task.status = TaskStatus.IN_PROGRESS
            task.started_at = datetime.now()

            # Extract code from task context
            code = task.context.get("code", "")
            if not code:
                raise TaskExecutionError(
                    "No code provided for review",
                    task_id=task.id,
                    agent_id=self.id,
                )

            # Create review context
            context = ReviewContext(
                language=task.context.get("language", "python"),
                framework=task.context.get("framework"),
                focus_areas=[
                    ReviewCategory(area)
                    for area in task.context.get("focus_areas", [])
                ],
            )

            # Perform the review
            review = await self.review_code(code, context)

            # Create artifact
            artifact = Artifact(
                type=ArtifactType.REVIEW_REPORT,
                name=f"Code Review: {task.title}",
                content=review.summary,
                created_by=self.id,
                quality_score=review.overall_score,
                review_comments=review.comments,
            )

            execution_time = time.time() - start_time

            return TaskResult(
                task_id=task.id,
                success=True,
                artifacts=[artifact],
                confidence_score=0.9,
                quality_score=review.overall_score,
                execution_time_seconds=execution_time,
                metrics={
                    "readability": review.quality_scores.readability,
                    "maintainability": review.quality_scores.maintainability,
                    "performance": review.quality_scores.performance,
                    "issues_found": len(review.comments),
                    "blocking_issues": review.blocking_issues,
                },
            )

        except Exception as e:
            logger.error("Code review failed for task %s: %s", task.id, str(e))
            return TaskResult(
                task_id=task.id,
                success=False,
                error_message=str(e),
                error_type=type(e).__name__,
                execution_time_seconds=time.time() - start_time,
            )

    async def review_code(
        self,
        code: str,
        context: ReviewContext,
    ) -> CodeReview:
        """Perform comprehensive code review.

        Args:
            code: Source code to review
            context: Review context information

        Returns:
            Complete code review result
        """
        review = CodeReview(reviewer_id=self.id)

        # Run all analysis methods
        naming_issues = await self.check_naming(code)
        complexity_report = await self.analyze_complexity(code)
        refactoring_suggestions = await self.suggest_refactoring(code)
        pattern_violations = await self.verify_patterns(code)

        # Populate review
        review.naming_issues = naming_issues
        review.complexity_report = complexity_report
        review.refactoring_suggestions = refactoring_suggestions
        review.pattern_violations = pattern_violations

        # Convert findings to review comments
        for issue in naming_issues:
            review.comments.append(ReviewComment(
                reviewer_id=self.id,
                line_start=issue.line_number,
                comment=issue.explanation,
                severity=issue.severity.value,
                category=ReviewCategory.NAMING.value,
                suggestion=issue.suggestion,
            ))

        for violation in pattern_violations:
            review.comments.append(ReviewComment(
                reviewer_id=self.id,
                comment=violation.description,
                severity=violation.severity.value,
                category=ReviewCategory.PATTERN.value,
                suggestion=violation.suggested_fix,
            ))

        # Calculate quality scores
        review.quality_scores = self._calculate_quality_scores(
            code, naming_issues, complexity_report, pattern_violations
        )
        review.overall_score = review.quality_scores.overall

        # Count blocking issues
        review.blocking_issues = sum(
            1 for c in review.comments
            if c.severity in (ReviewSeverity.ERROR.value, ReviewSeverity.CRITICAL.value)
        )

        # Determine approval status
        if review.blocking_issues > 0:
            review.approval_status = "request_changes"
        elif review.overall_score >= 0.8:
            review.approval_status = "approved"
        else:
            review.approval_status = "request_changes"

        # Generate summary
        review.summary = self._generate_summary(review)

        return review

    async def check_naming(self, code: str) -> list[NamingIssue]:
        """Check naming conventions in code.

        Args:
            code: Source code to check

        Returns:
            List of naming issues found
        """
        issues: list[NamingIssue] = []

        try:
            tree = ast.parse(code)
        except SyntaxError:
            return issues

        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                if not self.NAMING_PATTERNS["class"].match(node.name):
                    issues.append(NamingIssue(
                        name=node.name,
                        issue_type="class_name",
                        line_number=node.lineno,
                        expected_pattern="PascalCase",
                        suggestion=self._to_pascal_case(node.name),
                        explanation=f"Class name '{node.name}' should use PascalCase",
                    ))

            elif isinstance(node, ast.FunctionDef):
                if not node.name.startswith("_") and not self.NAMING_PATTERNS["function"].match(node.name):
                    issues.append(NamingIssue(
                        name=node.name,
                        issue_type="function_name",
                        line_number=node.lineno,
                        expected_pattern="snake_case",
                        suggestion=self._to_snake_case(node.name),
                        explanation=f"Function name '{node.name}' should use snake_case",
                    ))

            elif isinstance(node, ast.Name):
                # Check for constants (all caps in module scope)
                if isinstance(node.ctx, ast.Store) and node.id.isupper():
                    if not self.NAMING_PATTERNS["constant"].match(node.id):
                        issues.append(NamingIssue(
                            name=node.id,
                            issue_type="constant",
                            line_number=getattr(node, "lineno", 0),
                            expected_pattern="SCREAMING_SNAKE_CASE",
                            suggestion=node.id.upper().replace(" ", "_"),
                            explanation=f"Constant '{node.id}' should use SCREAMING_SNAKE_CASE",
                        ))

        return issues

    async def analyze_complexity(self, code: str) -> ComplexityReport:
        """Analyze code complexity.

        Args:
            code: Source code to analyze

        Returns:
            Complexity analysis report
        """
        report = ComplexityReport()

        # Count lines
        lines = code.split("\n")
        report.loc = len(lines)
        report.sloc = sum(1 for line in lines if line.strip() and not line.strip().startswith("#"))

        try:
            tree = ast.parse(code)
        except SyntaxError:
            return report

        # Analyze functions
        max_nesting = 0
        total_complexity = 0

        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                complexity = self._calculate_cyclomatic_complexity(node)
                report.function_complexities[node.name] = complexity
                total_complexity += complexity

                nesting = self._calculate_nesting_depth(node)
                max_nesting = max(max_nesting, nesting)

                if complexity > 10:
                    report.hotspots.append({
                        "name": node.name,
                        "line": node.lineno,
                        "complexity": complexity,
                        "type": "function",
                    })

        report.max_nesting_depth = max_nesting
        report.cyclomatic_complexity = total_complexity

        # Calculate overall score (0-10, lower is better)
        if report.function_complexities:
            avg_complexity = total_complexity / len(report.function_complexities)
            report.overall_score = min(avg_complexity, 10)
        else:
            report.overall_score = 0

        # Generate recommendations
        if report.overall_score > 5:
            report.recommendations.append("Consider breaking down complex functions")
        if report.max_nesting_depth > 4:
            report.recommendations.append("Reduce nesting depth by extracting helper functions")
        if report.sloc > 500:
            report.recommendations.append("Consider splitting into multiple modules")

        return report

    async def suggest_refactoring(self, code: str) -> list[RefactoringSuggestion]:
        """Suggest code refactorings.

        Args:
            code: Source code to analyze

        Returns:
            List of refactoring suggestions
        """
        suggestions: list[RefactoringSuggestion] = []

        try:
            tree = ast.parse(code)
        except SyntaxError:
            return suggestions

        for node in ast.walk(tree):
            # Long functions
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                end_line = getattr(node, "end_lineno", node.lineno + 20)
                func_length = end_line - node.lineno

                if func_length > 50:
                    suggestions.append(RefactoringSuggestion(
                        title=f"Extract method from {node.name}",
                        description=f"Function '{node.name}' is {func_length} lines long. "
                                   "Consider extracting logical sections into helper methods.",
                        category="extract_method",
                        priority=2,
                        line_start=node.lineno,
                        line_end=end_line,
                        estimated_impact="significant",
                        effort="medium",
                    ))

            # Duplicate code detection (simplified)
            if isinstance(node, ast.If):
                # Check for long if-else chains
                elif_count = sum(1 for _ in ast.walk(node) if isinstance(_, ast.If))
                if elif_count > 3:
                    suggestions.append(RefactoringSuggestion(
                        title="Replace conditional with polymorphism",
                        description="Long if-else chain detected. Consider using "
                                   "strategy pattern or dictionary dispatch.",
                        category="simplify_conditional",
                        priority=3,
                        line_start=node.lineno,
                        line_end=getattr(node, "end_lineno", node.lineno + 10),
                        estimated_impact="moderate",
                        effort="medium",
                        pattern="Strategy",
                    ))

        return suggestions

    async def verify_patterns(self, code: str) -> list[PatternViolation]:
        """Verify design pattern compliance.

        Args:
            code: Source code to verify

        Returns:
            List of pattern violations found
        """
        violations: list[PatternViolation] = []

        try:
            tree = ast.parse(code)
        except SyntaxError:
            return violations

        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                # Check for God class (too many methods/attributes)
                methods = [n for n in node.body if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))]
                if len(methods) > 20:
                    violations.append(PatternViolation(
                        pattern_name="Single Responsibility Principle",
                        violation_type="anti_pattern",
                        location=f"line {node.lineno}",
                        description=f"Class '{node.name}' has {len(methods)} methods. "
                                   "This may indicate it's doing too much.",
                        severity=ReviewSeverity.WARNING,
                        suggested_fix="Split into smaller, focused classes",
                        references=["SOLID principles", "Clean Code"],
                    ))

                # Check for missing __init__ in non-dataclass
                has_init = any(
                    isinstance(n, ast.FunctionDef) and n.name == "__init__"
                    for n in node.body
                )
                is_dataclass = any(
                    isinstance(d, ast.Name) and d.id == "dataclass"
                    for d in node.decorator_list
                ) if node.decorator_list else False

                if not has_init and not is_dataclass and methods:
                    violations.append(PatternViolation(
                        pattern_name="Constructor Pattern",
                        violation_type="missing",
                        location=f"line {node.lineno}",
                        description=f"Class '{node.name}' has no __init__ method",
                        severity=ReviewSeverity.INFO,
                        suggested_fix="Add an __init__ method or use @dataclass",
                    ))

        return violations

    def _calculate_quality_scores(
        self,
        code: str,
        naming_issues: list[NamingIssue],
        complexity_report: ComplexityReport,
        pattern_violations: list[PatternViolation],
    ) -> QualityScores:
        """Calculate quality scores based on analysis results."""
        scores = QualityScores()

        # Readability score
        naming_penalty = min(len(naming_issues) * 0.05, 0.3)
        scores.readability = max(0, 1.0 - naming_penalty)

        # Maintainability score
        complexity_penalty = min(complexity_report.overall_score * 0.1, 0.5)
        pattern_penalty = min(len(pattern_violations) * 0.1, 0.3)
        scores.maintainability = max(0, 1.0 - complexity_penalty - pattern_penalty)

        # Performance score (basic heuristics)
        scores.performance = 0.8  # Default, would need runtime analysis

        # Security score (basic)
        scores.security = 0.9  # Default, would need security analysis

        # Testability
        testability_penalty = min(complexity_report.max_nesting_depth * 0.1, 0.4)
        scores.testability = max(0, 1.0 - testability_penalty)

        # Documentation
        lines = code.split("\n")
        doc_lines = sum(1 for line in lines if '"""' in line or "'''" in line or line.strip().startswith("#"))
        doc_ratio = doc_lines / max(len(lines), 1)
        scores.documentation = min(doc_ratio * 5, 1.0)  # 20% docs = 100%

        return scores

    def _generate_summary(self, review: CodeReview) -> str:
        """Generate a human-readable review summary."""
        parts = [
            f"Code Review completed with overall score: {review.overall_score:.1%}",
            f"Status: {review.approval_status}",
        ]

        if review.blocking_issues > 0:
            parts.append(f"Blocking issues: {review.blocking_issues}")

        if review.naming_issues:
            parts.append(f"Naming issues: {len(review.naming_issues)}")

        if review.refactoring_suggestions:
            parts.append(f"Refactoring suggestions: {len(review.refactoring_suggestions)}")

        if review.pattern_violations:
            parts.append(f"Pattern violations: {len(review.pattern_violations)}")

        return " | ".join(parts)

    def _calculate_cyclomatic_complexity(self, node: ast.AST) -> int:
        """Calculate cyclomatic complexity of a function."""
        complexity = 1  # Base complexity

        for child in ast.walk(node):
            if isinstance(child, (ast.If, ast.While, ast.For, ast.ExceptHandler)):
                complexity += 1
            elif isinstance(child, ast.BoolOp):
                complexity += len(child.values) - 1
            elif isinstance(child, (ast.And, ast.Or)):
                complexity += 1

        return complexity

    def _calculate_nesting_depth(self, node: ast.AST, depth: int = 0) -> int:
        """Calculate maximum nesting depth."""
        max_depth = depth

        for child in ast.iter_child_nodes(node):
            if isinstance(child, (ast.If, ast.While, ast.For, ast.With, ast.Try)):
                child_depth = self._calculate_nesting_depth(child, depth + 1)
                max_depth = max(max_depth, child_depth)
            else:
                child_depth = self._calculate_nesting_depth(child, depth)
                max_depth = max(max_depth, child_depth)

        return max_depth

    def _to_pascal_case(self, name: str) -> str:
        """Convert name to PascalCase."""
        parts = re.split(r"[_\s]+", name)
        return "".join(word.capitalize() for word in parts)

    def _to_snake_case(self, name: str) -> str:
        """Convert name to snake_case."""
        s1 = re.sub(r"(.)([A-Z][a-z]+)", r"\1_\2", name)
        return re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", s1).lower()


# =============================================================================
# Exports
# =============================================================================

__all__ = [
    # Enums
    "ReviewSeverity",
    "ReviewCategory",
    # Data Classes
    "ReviewContext",
    "NamingIssue",
    "ComplexityReport",
    "RefactoringSuggestion",
    "PatternViolation",
    "QualityScores",
    "CodeReview",
    # Agents
    "BaseExpertAgent",
    "CodeReviewerAgent",
]
