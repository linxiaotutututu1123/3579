"""QA Engineer Agent Module for Chairman Agents.

This module implements the QA Engineer expert agent, which specializes in
test strategy design, test case generation, automated testing frameworks,
boundary condition analysis, and defect tracking.

The QA Engineer Agent applies systematic testing methodologies to ensure
software quality through comprehensive test coverage and rigorous validation.

Classes:
    TestSeverity: Severity levels for test cases and defects
    TestType: Types of tests (unit, integration, e2e, etc.)
    TestStatus: Execution status of tests
    CoverageType: Types of code coverage metrics
    EdgeCaseCategory: Categories of edge cases
    TestCase: Individual test case definition
    TestSuite: Collection of related test cases
    TestStrategy: Overall testing strategy specification
    EdgeCase: Identified edge case scenario
    TestDataSet: Test data collection with schema
    CoverageRequirement: Code coverage requirements
    DefectReport: Defect tracking information
    FeatureSpec: Feature specification for test generation
    FunctionSpec: Function specification for edge case analysis
    DataSchema: Schema definition for test data generation
    TestScope: Scope definition for test suite design
    QAEngineerAgent: Main QA Engineer agent implementation

Example:
    >>> agent = QAEngineerAgent()
    >>> strategy = await agent.analyze_requirements(requirements)
    >>> test_cases = await agent.generate_test_cases(feature_spec)
    >>> edge_cases = await agent.identify_edge_cases(function_spec)
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING, Any

from chairman_agents.core.types import (
    AgentCapability,
    AgentProfile,
    AgentRole,
    Artifact,
    ArtifactType,
    ReasoningStep,
    Task,
    TaskContext,
    TaskResult,
    TaskStatus,
    generate_id,
)
from chairman_agents.agents.experts.tech_writer import BaseExpertAgent

if TYPE_CHECKING:
    pass


# =============================================================================
# Logging Configuration
# =============================================================================

logger = logging.getLogger(__name__)


# =============================================================================
# Enumerations
# =============================================================================


class TestSeverity(Enum):
    """Severity levels for test cases and defects.

    Used to prioritize test execution and defect resolution.
    """

    CRITICAL = "critical"
    """Critical - System unusable, data loss, security breach"""

    HIGH = "high"
    """High - Major feature broken, significant impact"""

    MEDIUM = "medium"
    """Medium - Feature impaired but workaround exists"""

    LOW = "low"
    """Low - Minor issue, cosmetic problems"""

    TRIVIAL = "trivial"
    """Trivial - Negligible impact, enhancement suggestions"""


class TestType(Enum):
    """Types of tests in the testing pyramid.

    Organized from fastest/smallest to slowest/largest scope.
    """

    UNIT = "unit"
    """Unit Test - Tests individual functions/methods in isolation"""

    INTEGRATION = "integration"
    """Integration Test - Tests interaction between components"""

    CONTRACT = "contract"
    """Contract Test - Tests API contracts between services"""

    COMPONENT = "component"
    """Component Test - Tests complete component behavior"""

    E2E = "e2e"
    """End-to-End Test - Tests complete user workflows"""

    PERFORMANCE = "performance"
    """Performance Test - Tests response times and throughput"""

    SECURITY = "security"
    """Security Test - Tests for vulnerabilities and exploits"""

    ACCESSIBILITY = "accessibility"
    """Accessibility Test - Tests for a11y compliance"""

    SMOKE = "smoke"
    """Smoke Test - Quick sanity check for critical paths"""

    REGRESSION = "regression"
    """Regression Test - Ensures existing functionality works"""


class TestStatus(Enum):
    """Execution status of tests."""

    PENDING = "pending"
    """Pending - Not yet executed"""

    RUNNING = "running"
    """Running - Currently executing"""

    PASSED = "passed"
    """Passed - Test succeeded"""

    FAILED = "failed"
    """Failed - Test assertion failed"""

    ERROR = "error"
    """Error - Test threw unexpected exception"""

    SKIPPED = "skipped"
    """Skipped - Test was skipped"""

    FLAKY = "flaky"
    """Flaky - Test has intermittent failures"""


class CoverageType(Enum):
    """Types of code coverage metrics."""

    LINE = "line"
    """Line Coverage - Percentage of lines executed"""

    BRANCH = "branch"
    """Branch Coverage - Percentage of branches taken"""

    FUNCTION = "function"
    """Function Coverage - Percentage of functions called"""

    STATEMENT = "statement"
    """Statement Coverage - Percentage of statements executed"""

    CONDITION = "condition"
    """Condition Coverage - All boolean expressions evaluated"""

    PATH = "path"
    """Path Coverage - All execution paths taken"""

    MUTATION = "mutation"
    """Mutation Coverage - Percentage of mutants killed"""


class EdgeCaseCategory(Enum):
    """Categories of edge cases to consider."""

    BOUNDARY = "boundary"
    """Boundary - Min/max values, limits"""

    NULL_EMPTY = "null_empty"
    """Null/Empty - Null values, empty collections"""

    TYPE_MISMATCH = "type_mismatch"
    """Type Mismatch - Wrong types, type coercion"""

    OVERFLOW = "overflow"
    """Overflow - Integer overflow, buffer overflow"""

    CONCURRENCY = "concurrency"
    """Concurrency - Race conditions, deadlocks"""

    UNICODE = "unicode"
    """Unicode - Special characters, encoding issues"""

    INJECTION = "injection"
    """Injection - SQL, XSS, command injection"""

    TIMING = "timing"
    """Timing - Timeouts, delays, ordering"""

    RESOURCE = "resource"
    """Resource - Memory limits, file handles"""

    STATE = "state"
    """State - Invalid states, state transitions"""


# =============================================================================
# Data Classes - Input Specifications
# =============================================================================


@dataclass
class FeatureSpec:
    """Feature specification for test generation.

    Describes a feature to be tested, including its requirements,
    acceptance criteria, and constraints.

    Attributes:
        id: Unique identifier
        name: Feature name
        description: Detailed description
        requirements: List of requirements
        acceptance_criteria: Acceptance criteria
        constraints: Known constraints
        dependencies: Feature dependencies
        priority: Feature priority (1-5)
    """

    id: str = field(default_factory=lambda: generate_id("feature"))
    """Unique identifier"""

    name: str = ""
    """Feature name"""

    description: str = ""
    """Detailed feature description"""

    requirements: list[str] = field(default_factory=list)
    """List of functional requirements"""

    acceptance_criteria: list[str] = field(default_factory=list)
    """Acceptance criteria for the feature"""

    constraints: list[str] = field(default_factory=list)
    """Known constraints and limitations"""

    dependencies: list[str] = field(default_factory=list)
    """Dependencies on other features"""

    priority: int = 3
    """Priority level (1=highest, 5=lowest)"""


@dataclass
class FunctionSpec:
    """Function specification for edge case analysis.

    Describes a function's signature, behavior, and constraints
    for systematic edge case identification.

    Attributes:
        name: Function name
        description: What the function does
        parameters: Parameter definitions
        return_type: Return type description
        preconditions: Required preconditions
        postconditions: Guaranteed postconditions
        invariants: Invariants maintained
        exceptions: Possible exceptions
        side_effects: Side effects produced
    """

    name: str = ""
    """Function name"""

    description: str = ""
    """Function description"""

    parameters: list[dict[str, Any]] = field(default_factory=list)
    """Parameter definitions: [{'name': str, 'type': str, 'constraints': str}]"""

    return_type: str = ""
    """Return type description"""

    preconditions: list[str] = field(default_factory=list)
    """Required preconditions"""

    postconditions: list[str] = field(default_factory=list)
    """Guaranteed postconditions"""

    invariants: list[str] = field(default_factory=list)
    """Invariants that must be maintained"""

    exceptions: list[str] = field(default_factory=list)
    """Possible exceptions thrown"""

    side_effects: list[str] = field(default_factory=list)
    """Side effects produced"""


@dataclass
class DataSchema:
    """Schema definition for test data generation.

    Defines the structure and constraints of data to be generated
    for testing purposes.

    Attributes:
        name: Schema name
        fields: Field definitions
        constraints: Data constraints
        relationships: Relationships to other schemas
        cardinality: Expected data volume
    """

    name: str = ""
    """Schema name"""

    fields: list[dict[str, Any]] = field(default_factory=list)
    """Field definitions: [{'name': str, 'type': str, 'nullable': bool, ...}]"""

    constraints: list[str] = field(default_factory=list)
    """Data constraints (unique, foreign key, etc.)"""

    relationships: list[dict[str, str]] = field(default_factory=list)
    """Relationships: [{'target': str, 'type': 'one-to-many', ...}]"""

    cardinality: str = "small"
    """Expected data volume: small, medium, large"""


@dataclass
class TestScope:
    """Scope definition for test suite design.

    Defines the boundaries and focus areas for a test suite.

    Attributes:
        name: Scope name
        description: Scope description
        modules: Modules to include
        exclude_modules: Modules to exclude
        test_types: Types of tests to include
        coverage_targets: Coverage targets by type
        time_budget_seconds: Time budget for test execution
    """

    name: str = ""
    """Scope name"""

    description: str = ""
    """Scope description"""

    modules: list[str] = field(default_factory=list)
    """Modules to include in scope"""

    exclude_modules: list[str] = field(default_factory=list)
    """Modules to exclude from scope"""

    test_types: list[TestType] = field(default_factory=list)
    """Types of tests to include"""

    coverage_targets: dict[CoverageType, float] = field(default_factory=dict)
    """Coverage targets by type (0.0-1.0)"""

    time_budget_seconds: int = 300
    """Time budget for test execution"""


# =============================================================================
# Data Classes - Output Types
# =============================================================================


@dataclass
class TestCase:
    """Individual test case definition.

    Represents a single test case with its inputs, expected outputs,
    and execution metadata.

    Attributes:
        id: Unique test case identifier
        name: Test case name
        description: What this test verifies
        test_type: Type of test
        severity: Severity if this test fails
        preconditions: Setup requirements
        steps: Test steps to execute
        expected_result: Expected outcome
        actual_result: Actual outcome after execution
        status: Current execution status
        tags: Categorization tags
        data: Test data inputs
        assertions: Specific assertions to make
        cleanup: Cleanup steps after test
        timeout_seconds: Maximum execution time
        retry_count: Number of retries on failure
        flaky: Whether this test is known to be flaky
    """

    id: str = field(default_factory=lambda: generate_id("tc"))
    """Unique test case identifier"""

    name: str = ""
    """Test case name"""

    description: str = ""
    """What this test verifies"""

    test_type: TestType = TestType.UNIT
    """Type of test"""

    severity: TestSeverity = TestSeverity.MEDIUM
    """Severity if this test fails"""

    preconditions: list[str] = field(default_factory=list)
    """Setup requirements before test execution"""

    steps: list[str] = field(default_factory=list)
    """Test steps to execute"""

    expected_result: str = ""
    """Expected outcome"""

    actual_result: str | None = None
    """Actual outcome after execution"""

    status: TestStatus = TestStatus.PENDING
    """Current execution status"""

    tags: list[str] = field(default_factory=list)
    """Categorization tags"""

    data: dict[str, Any] = field(default_factory=dict)
    """Test data inputs"""

    assertions: list[str] = field(default_factory=list)
    """Specific assertions to make"""

    cleanup: list[str] = field(default_factory=list)
    """Cleanup steps after test"""

    timeout_seconds: int = 30
    """Maximum execution time"""

    retry_count: int = 0
    """Number of retries on failure"""

    flaky: bool = False
    """Whether this test is known to be flaky"""

    # Traceability
    requirement_id: str | None = None
    """Linked requirement ID"""

    feature_id: str | None = None
    """Linked feature ID"""

    created_at: datetime = field(default_factory=datetime.now)
    """When this test case was created"""

    executed_at: datetime | None = None
    """When this test was last executed"""

    execution_time_ms: int | None = None
    """Execution time in milliseconds"""


@dataclass
class TestSuite:
    """Collection of related test cases.

    Organizes test cases into logical groups with shared setup/teardown
    and execution configuration.

    Attributes:
        id: Unique suite identifier
        name: Suite name
        description: Suite description
        test_cases: Contained test cases
        setup: Suite-level setup steps
        teardown: Suite-level teardown steps
        tags: Categorization tags
        parallel: Whether tests can run in parallel
        timeout_seconds: Total suite timeout
        coverage_requirement: Required coverage
    """

    id: str = field(default_factory=lambda: generate_id("ts"))
    """Unique suite identifier"""

    name: str = ""
    """Suite name"""

    description: str = ""
    """Suite description"""

    test_cases: list[TestCase] = field(default_factory=list)
    """Contained test cases"""

    setup: list[str] = field(default_factory=list)
    """Suite-level setup steps"""

    teardown: list[str] = field(default_factory=list)
    """Suite-level teardown steps"""

    tags: list[str] = field(default_factory=list)
    """Categorization tags"""

    parallel: bool = False
    """Whether tests can run in parallel"""

    timeout_seconds: int = 600
    """Total suite timeout"""

    coverage_requirement: CoverageRequirement | None = None
    """Required coverage for this suite"""

    # Execution Statistics
    total_tests: int = 0
    """Total number of tests"""

    passed_tests: int = 0
    """Number of passed tests"""

    failed_tests: int = 0
    """Number of failed tests"""

    skipped_tests: int = 0
    """Number of skipped tests"""

    execution_time_seconds: float = 0.0
    """Total execution time"""

    def pass_rate(self) -> float:
        """Calculate the pass rate.

        Returns:
            Pass rate as a percentage (0.0-1.0)
        """
        if self.total_tests == 0:
            return 0.0
        return self.passed_tests / self.total_tests


@dataclass
class TestStrategy:
    """Overall testing strategy specification.

    Defines the comprehensive testing approach including test types,
    coverage requirements, and quality gates.

    Attributes:
        id: Unique strategy identifier
        name: Strategy name
        description: Strategy description
        test_types: Test types to include with priorities
        coverage_requirements: Coverage requirements by type
        quality_gates: Quality gate definitions
        risk_areas: Identified risk areas
        test_environments: Required test environments
        automation_scope: Scope of test automation
        manual_scope: Scope of manual testing
        estimated_effort_hours: Estimated testing effort
    """

    id: str = field(default_factory=lambda: generate_id("strategy"))
    """Unique strategy identifier"""

    name: str = ""
    """Strategy name"""

    description: str = ""
    """Strategy description"""

    test_types: dict[TestType, int] = field(default_factory=dict)
    """Test types with priority (1=highest)"""

    coverage_requirements: list[CoverageRequirement] = field(default_factory=list)
    """Coverage requirements"""

    quality_gates: list[dict[str, Any]] = field(default_factory=list)
    """Quality gate definitions"""

    risk_areas: list[str] = field(default_factory=list)
    """Identified high-risk areas requiring focused testing"""

    test_environments: list[str] = field(default_factory=list)
    """Required test environments"""

    automation_scope: list[str] = field(default_factory=list)
    """What should be automated"""

    manual_scope: list[str] = field(default_factory=list)
    """What requires manual testing"""

    estimated_effort_hours: float = 0.0
    """Estimated testing effort in hours"""

    recommendations: list[str] = field(default_factory=list)
    """Strategic recommendations"""


@dataclass
class EdgeCase:
    """Identified edge case scenario.

    Describes a specific edge case that should be tested,
    including its category, likelihood, and impact.

    Attributes:
        id: Unique identifier
        name: Edge case name
        description: Detailed description
        category: Category of edge case
        input_conditions: Conditions that trigger this edge case
        expected_behavior: Expected system behavior
        potential_issues: Potential issues if not handled
        likelihood: Likelihood of occurrence (1-5)
        impact: Impact severity if occurs (1-5)
        test_approach: How to test this edge case
        sample_inputs: Example inputs for testing
    """

    id: str = field(default_factory=lambda: generate_id("edge"))
    """Unique identifier"""

    name: str = ""
    """Edge case name"""

    description: str = ""
    """Detailed description"""

    category: EdgeCaseCategory = EdgeCaseCategory.BOUNDARY
    """Category of edge case"""

    input_conditions: list[str] = field(default_factory=list)
    """Conditions that trigger this edge case"""

    expected_behavior: str = ""
    """Expected system behavior"""

    potential_issues: list[str] = field(default_factory=list)
    """Potential issues if not handled"""

    likelihood: int = 3
    """Likelihood of occurrence (1=rare, 5=common)"""

    impact: int = 3
    """Impact severity if occurs (1=low, 5=critical)"""

    test_approach: str = ""
    """Recommended approach to test this edge case"""

    sample_inputs: list[dict[str, Any]] = field(default_factory=list)
    """Example inputs for testing"""

    def risk_score(self) -> int:
        """Calculate risk score.

        Returns:
            Risk score (likelihood * impact)
        """
        return self.likelihood * self.impact


@dataclass
class TestDataSet:
    """Test data collection with schema.

    Contains generated test data along with its schema definition
    and generation metadata.

    Attributes:
        id: Unique identifier
        name: Dataset name
        schema: Associated schema
        records: Generated data records
        positive_cases: Valid data cases
        negative_cases: Invalid data cases
        edge_cases: Edge case data
        generated_at: When data was generated
        generator_seed: Random seed for reproducibility
    """

    id: str = field(default_factory=lambda: generate_id("dataset"))
    """Unique identifier"""

    name: str = ""
    """Dataset name"""

    schema: DataSchema | None = None
    """Associated schema"""

    records: list[dict[str, Any]] = field(default_factory=list)
    """Generated data records"""

    positive_cases: list[dict[str, Any]] = field(default_factory=list)
    """Valid data cases"""

    negative_cases: list[dict[str, Any]] = field(default_factory=list)
    """Invalid data cases for negative testing"""

    edge_cases: list[dict[str, Any]] = field(default_factory=list)
    """Edge case data"""

    generated_at: datetime = field(default_factory=datetime.now)
    """When data was generated"""

    generator_seed: int | None = None
    """Random seed for reproducibility"""


@dataclass
class CoverageRequirement:
    """Code coverage requirements.

    Specifies the minimum coverage thresholds that must be met.

    Attributes:
        coverage_type: Type of coverage
        minimum_percentage: Minimum required percentage
        target_percentage: Target percentage (stretch goal)
        modules: Modules this applies to (empty = all)
        exclude_patterns: Patterns to exclude from coverage
        enforce: Whether to fail build on violation
    """

    coverage_type: CoverageType = CoverageType.LINE
    """Type of coverage"""

    minimum_percentage: float = 0.8
    """Minimum required percentage (0.0-1.0)"""

    target_percentage: float = 0.9
    """Target percentage (0.0-1.0)"""

    modules: list[str] = field(default_factory=list)
    """Modules this applies to (empty = all)"""

    exclude_patterns: list[str] = field(default_factory=list)
    """Patterns to exclude from coverage"""

    enforce: bool = True
    """Whether to fail build on violation"""


@dataclass
class DefectReport:
    """Defect tracking information.

    Records details about identified defects for tracking
    and resolution.

    Attributes:
        id: Unique defect identifier
        title: Defect title
        description: Detailed description
        severity: Defect severity
        status: Current status
        steps_to_reproduce: Reproduction steps
        expected_behavior: What should happen
        actual_behavior: What actually happens
        environment: Environment where found
        test_case_id: Related test case
        assigned_to: Assignee ID
        found_by: Reporter ID
        found_at: When defect was found
        resolved_at: When defect was resolved
    """

    id: str = field(default_factory=lambda: generate_id("defect"))
    """Unique defect identifier"""

    title: str = ""
    """Defect title"""

    description: str = ""
    """Detailed description"""

    severity: TestSeverity = TestSeverity.MEDIUM
    """Defect severity"""

    status: str = "open"
    """Current status: open, in_progress, resolved, closed, wont_fix"""

    steps_to_reproduce: list[str] = field(default_factory=list)
    """Steps to reproduce the defect"""

    expected_behavior: str = ""
    """What should happen"""

    actual_behavior: str = ""
    """What actually happens"""

    environment: str = ""
    """Environment where defect was found"""

    test_case_id: str | None = None
    """Related test case that found this defect"""

    assigned_to: str | None = None
    """Assignee ID"""

    found_by: str = ""
    """Reporter ID"""

    found_at: datetime = field(default_factory=datetime.now)
    """When defect was found"""

    resolved_at: datetime | None = None
    """When defect was resolved"""

    root_cause: str | None = None
    """Root cause analysis"""

    fix_description: str | None = None
    """Description of the fix"""


# =============================================================================
# QA Engineer Agent
# =============================================================================


class QAEngineerAgent(BaseExpertAgent):
    """QA Engineer expert agent.

    Specializes in test strategy design, test case generation, automated
    testing frameworks, boundary condition analysis, and defect tracking.

    The QA Engineer applies systematic testing methodologies to ensure
    comprehensive test coverage and high software quality.

    Capabilities:
        - Test strategy design
        - Test case generation
        - Edge case identification
        - Test data generation
        - Defect analysis and tracking

    Example:
        >>> profile = AgentProfile(
        ...     name="QA Engineer",
        ...     role=AgentRole.QA_ENGINEER,
        ...     capabilities=[AgentCapability.TEST_PLANNING]
        ... )
        >>> agent = QAEngineerAgent(profile, llm_client)
        >>> strategy = await agent.analyze_requirements(requirements)
        >>> test_cases = await agent.generate_test_cases(feature_spec)
    """

    role = AgentRole.QA_ENGINEER
    """The role of this agent"""

    def __init__(
        self,
        profile: AgentProfile,
        llm_client: Any,
    ) -> None:
        """Initialize the QA Engineer agent.

        Args:
            profile: Agent profile configuration
            llm_client: LLM client for text generation
        """
        super().__init__(profile, llm_client)
        self._reasoning_trace: list[ReasoningStep] = []

    # =========================================================================
    # Main Execution
    # =========================================================================

    async def execute(
        self,
        task: Task,
        context: TaskContext | None = None,
    ) -> TaskResult:
        """Execute a QA-related task.

        Handles various QA tasks including:
        - Test strategy creation
        - Test case generation
        - Test suite design
        - Edge case identification
        - Defect analysis

        Args:
            task: The task to execute
            context: Task context

        Returns:
            TaskResult with QA artifacts
        """
        import time

        start_time = time.time()
        self._reasoning_trace = []

        try:
            task.status = TaskStatus.IN_PROGRESS
            task.started_at = datetime.now()

            # Determine task type and route to appropriate handler
            task_type = task.context.get("qa_task_type", "general")
            artifacts: list[Artifact] = []

            if task_type == "strategy":
                requirements = task.context.get("requirements", [])
                strategy = await self.analyze_requirements(requirements)
                artifacts.append(self._strategy_to_artifact(strategy))

            elif task_type == "test_cases":
                feature_spec = self._extract_feature_spec(task)
                test_cases = await self.generate_test_cases(feature_spec)
                artifacts.append(self._test_cases_to_artifact(test_cases))

            elif task_type == "test_suite":
                scope = self._extract_test_scope(task)
                suite = await self.design_test_suite(scope)
                artifacts.append(self._test_suite_to_artifact(suite))

            elif task_type == "edge_cases":
                function_spec = self._extract_function_spec(task)
                edge_cases = await self.identify_edge_cases(function_spec)
                artifacts.append(self._edge_cases_to_artifact(edge_cases))

            elif task_type == "test_data":
                schema = self._extract_data_schema(task)
                dataset = await self.create_test_data(schema)
                artifacts.append(self._dataset_to_artifact(dataset))

            else:
                # General QA task - analyze and provide recommendations
                await self._execute_general_qa_task(task, artifacts)

            execution_time = time.time() - start_time
            task.status = TaskStatus.COMPLETED
            task.completed_at = datetime.now()

            result = TaskResult(
                task_id=task.id,
                success=True,
                artifacts=artifacts,
                reasoning_trace=self._reasoning_trace,
                confidence_score=0.85,
                quality_score=0.9,
                execution_time_seconds=execution_time,
                suggestions=[
                    "Review generated test cases for completeness",
                    "Consider adding more edge case tests",
                    "Ensure test data covers boundary conditions",
                ],
            )
            self._task_history.append(result)
            return result

        except Exception as e:
            logger.error("QA task execution failed: %s", e)
            task.status = TaskStatus.FAILED
            execution_time = time.time() - start_time
            return TaskResult(
                task_id=task.id,
                success=False,
                error_message=str(e),
                error_type=type(e).__name__,
                execution_time_seconds=execution_time,
            )

    # =========================================================================
    # Core QA Methods
    # =========================================================================

    async def analyze_requirements(
        self,
        requirements: list[str],
    ) -> TestStrategy:
        """Analyze requirements and create a comprehensive test strategy.

        Examines the provided requirements to determine:
        - Appropriate test types and their priorities
        - Coverage requirements
        - Risk areas requiring focused testing
        - Automation vs manual testing scope

        Args:
            requirements: List of requirement descriptions

        Returns:
            TestStrategy with comprehensive testing approach
        """
        logger.info("Analyzing %d requirements for test strategy", len(requirements))

        # Add reasoning step
        self._add_reasoning_step(
            "Analyzing requirements to identify testable scenarios, "
            "risk areas, and appropriate test types."
        )

        strategy = TestStrategy(
            name="Generated Test Strategy",
            description=f"Test strategy for {len(requirements)} requirements",
        )

        # Determine test types based on requirements
        strategy.test_types = {
            TestType.UNIT: 1,
            TestType.INTEGRATION: 2,
            TestType.E2E: 3,
        }

        # Add default coverage requirements
        strategy.coverage_requirements = [
            CoverageRequirement(
                coverage_type=CoverageType.LINE,
                minimum_percentage=0.8,
                target_percentage=0.9,
            ),
            CoverageRequirement(
                coverage_type=CoverageType.BRANCH,
                minimum_percentage=0.7,
                target_percentage=0.85,
            ),
        ]

        # Identify risk areas from requirements
        for req in requirements:
            req_lower = req.lower()
            if any(word in req_lower for word in ["security", "auth", "password"]):
                strategy.risk_areas.append(f"Security: {req[:50]}...")
                strategy.test_types[TestType.SECURITY] = 1
            if any(word in req_lower for word in ["performance", "fast", "latency"]):
                strategy.risk_areas.append(f"Performance: {req[:50]}...")
                strategy.test_types[TestType.PERFORMANCE] = 2

        # Define quality gates
        strategy.quality_gates = [
            {"name": "Unit Tests", "threshold": 0.8, "blocking": True},
            {"name": "Integration Tests", "threshold": 0.9, "blocking": True},
            {"name": "No Critical Defects", "threshold": 0, "blocking": True},
        ]

        # Set test environments
        strategy.test_environments = ["development", "staging", "pre-production"]

        # Define automation scope
        strategy.automation_scope = [
            "Unit tests",
            "API integration tests",
            "Regression test suite",
            "Performance benchmarks",
        ]

        strategy.manual_scope = [
            "Exploratory testing",
            "Usability testing",
            "Edge case validation",
        ]

        # Estimate effort
        strategy.estimated_effort_hours = len(requirements) * 2.5

        # Add recommendations
        strategy.recommendations = [
            "Prioritize unit tests for core business logic",
            "Implement contract tests for service boundaries",
            "Set up continuous integration with automated testing",
            "Create dedicated test data management strategy",
        ]

        logger.info("Generated test strategy with %d test types", len(strategy.test_types))
        return strategy

    async def generate_test_cases(
        self,
        feature: FeatureSpec,
    ) -> list[TestCase]:
        """Generate comprehensive test cases for a feature.

        Creates test cases covering:
        - Happy path scenarios
        - Error handling
        - Edge cases
        - Boundary conditions

        Args:
            feature: Feature specification

        Returns:
            List of generated test cases
        """
        logger.info("Generating test cases for feature: %s", feature.name)

        test_cases: list[TestCase] = []

        # Generate happy path test cases from acceptance criteria
        for i, criteria in enumerate(feature.acceptance_criteria):
            test_case = TestCase(
                name=f"test_{feature.name}_acceptance_{i + 1}",
                description=f"Verify: {criteria}",
                test_type=TestType.INTEGRATION,
                severity=TestSeverity.HIGH,
                steps=[
                    "Setup test environment",
                    f"Execute: {criteria}",
                    "Verify expected outcome",
                ],
                expected_result=criteria,
                tags=["acceptance", feature.name],
                feature_id=feature.id,
            )
            test_cases.append(test_case)

        # Generate requirement-based test cases
        for i, req in enumerate(feature.requirements):
            test_case = TestCase(
                name=f"test_{feature.name}_requirement_{i + 1}",
                description=f"Verify requirement: {req}",
                test_type=TestType.UNIT,
                severity=TestSeverity.MEDIUM,
                steps=[
                    "Prepare test data",
                    f"Test: {req}",
                    "Assert expected behavior",
                ],
                expected_result=f"Requirement satisfied: {req}",
                tags=["requirement", feature.name],
                requirement_id=f"REQ-{i + 1}",
                feature_id=feature.id,
            )
            test_cases.append(test_case)

        # Generate negative test cases
        negative_test = TestCase(
            name=f"test_{feature.name}_invalid_input",
            description="Verify proper handling of invalid inputs",
            test_type=TestType.UNIT,
            severity=TestSeverity.MEDIUM,
            steps=[
                "Prepare invalid test data",
                "Attempt operation with invalid data",
                "Verify appropriate error handling",
            ],
            expected_result="Appropriate error message returned",
            tags=["negative", "error-handling", feature.name],
            feature_id=feature.id,
        )
        test_cases.append(negative_test)

        # Generate boundary test case
        boundary_test = TestCase(
            name=f"test_{feature.name}_boundary_conditions",
            description="Verify boundary condition handling",
            test_type=TestType.UNIT,
            severity=TestSeverity.MEDIUM,
            steps=[
                "Prepare boundary value test data",
                "Test with minimum/maximum values",
                "Verify correct handling at boundaries",
            ],
            expected_result="Boundaries handled correctly",
            tags=["boundary", "edge-case", feature.name],
            feature_id=feature.id,
        )
        test_cases.append(boundary_test)

        logger.info("Generated %d test cases for feature %s", len(test_cases), feature.name)
        return test_cases

    async def design_test_suite(
        self,
        scope: TestScope,
    ) -> TestSuite:
        """Design a comprehensive test suite for the given scope.

        Creates a structured test suite with appropriate test cases,
        setup/teardown, and execution configuration.

        Args:
            scope: Test scope definition

        Returns:
            Designed TestSuite
        """
        logger.info("Designing test suite for scope: %s", scope.name)

        suite = TestSuite(
            name=scope.name,
            description=scope.description,
            tags=["automated", scope.name.lower().replace(" ", "-")],
            timeout_seconds=scope.time_budget_seconds,
        )

        # Set coverage requirement if specified
        if scope.coverage_targets:
            primary_coverage = list(scope.coverage_targets.items())[0]
            suite.coverage_requirement = CoverageRequirement(
                coverage_type=primary_coverage[0],
                minimum_percentage=primary_coverage[1],
            )

        # Add setup steps
        suite.setup = [
            "Initialize test environment",
            "Load test fixtures",
            "Configure mocks and stubs",
        ]

        # Add teardown steps
        suite.teardown = [
            "Cleanup test data",
            "Reset environment state",
            "Generate coverage report",
        ]

        # Determine if tests can run in parallel
        suite.parallel = TestType.UNIT in scope.test_types

        # Generate test cases for each module
        for module in scope.modules:
            for test_type in scope.test_types:
                test_case = TestCase(
                    name=f"test_{module}_{test_type.value}",
                    description=f"{test_type.value.title()} tests for {module}",
                    test_type=test_type,
                    severity=TestSeverity.MEDIUM,
                    tags=[module, test_type.value],
                )
                suite.test_cases.append(test_case)

        suite.total_tests = len(suite.test_cases)

        logger.info(
            "Designed test suite with %d test cases",
            len(suite.test_cases),
        )
        return suite

    async def identify_edge_cases(
        self,
        function_spec: FunctionSpec,
    ) -> list[EdgeCase]:
        """Identify edge cases for a function.

        Systematically analyzes the function specification to identify
        potential edge cases across multiple categories.

        Args:
            function_spec: Function specification

        Returns:
            List of identified edge cases
        """
        logger.info("Identifying edge cases for function: %s", function_spec.name)

        edge_cases: list[EdgeCase] = []

        # Analyze each parameter for edge cases
        for param in function_spec.parameters:
            param_name = param.get("name", "unknown")
            param_type = param.get("type", "any")

            # Boundary edge cases for numeric types
            if param_type in ["int", "float", "number"]:
                edge_cases.append(EdgeCase(
                    name=f"{param_name}_boundary_min",
                    description=f"Test minimum value for {param_name}",
                    category=EdgeCaseCategory.BOUNDARY,
                    input_conditions=[f"{param_name} = minimum allowed value"],
                    expected_behavior="Handle minimum value correctly",
                    likelihood=4,
                    impact=3,
                    test_approach="Use boundary value analysis",
                    sample_inputs=[{param_name: 0}, {param_name: -1}],
                ))

                edge_cases.append(EdgeCase(
                    name=f"{param_name}_overflow",
                    description=f"Test overflow for {param_name}",
                    category=EdgeCaseCategory.OVERFLOW,
                    input_conditions=[f"{param_name} exceeds maximum value"],
                    expected_behavior="Raise appropriate error or handle gracefully",
                    potential_issues=["Integer overflow", "Precision loss"],
                    likelihood=2,
                    impact=4,
                    test_approach="Use maximum values and beyond",
                ))

            # Null/empty edge cases for strings and collections
            if param_type in ["str", "string", "list", "array", "dict", "object"]:
                edge_cases.append(EdgeCase(
                    name=f"{param_name}_null_empty",
                    description=f"Test null/empty for {param_name}",
                    category=EdgeCaseCategory.NULL_EMPTY,
                    input_conditions=[
                        f"{param_name} is null",
                        f"{param_name} is empty",
                    ],
                    expected_behavior="Handle null/empty gracefully",
                    potential_issues=["NullPointerException", "Empty result"],
                    likelihood=5,
                    impact=3,
                    test_approach="Pass null and empty values",
                    sample_inputs=[{param_name: None}, {param_name: ""}],
                ))

            # Unicode edge cases for strings
            if param_type in ["str", "string"]:
                edge_cases.append(EdgeCase(
                    name=f"{param_name}_unicode",
                    description=f"Test unicode characters in {param_name}",
                    category=EdgeCaseCategory.UNICODE,
                    input_conditions=["Input contains unicode characters"],
                    expected_behavior="Handle unicode correctly",
                    potential_issues=["Encoding errors", "Display issues"],
                    likelihood=3,
                    impact=2,
                    test_approach="Use unicode test strings",
                    sample_inputs=[
                        {param_name: "Hello"},
                        {param_name: "emoji"},
                    ],
                ))

        # Check preconditions for state edge cases
        if function_spec.preconditions:
            edge_cases.append(EdgeCase(
                name=f"{function_spec.name}_precondition_violation",
                description="Test behavior when preconditions are violated",
                category=EdgeCaseCategory.STATE,
                input_conditions=["Preconditions not met"],
                expected_behavior="Raise appropriate exception",
                potential_issues=["Undefined behavior", "Data corruption"],
                likelihood=3,
                impact=4,
                test_approach="Violate each precondition systematically",
            ))

        logger.info(
            "Identified %d edge cases for function %s",
            len(edge_cases),
            function_spec.name,
        )
        return edge_cases

    async def create_test_data(
        self,
        schema: DataSchema,
    ) -> TestDataSet:
        """Create test data based on schema.

        Generates comprehensive test data including positive cases,
        negative cases, and edge cases.

        Args:
            schema: Data schema definition

        Returns:
            Generated TestDataSet
        """
        logger.info("Creating test data for schema: %s", schema.name)

        dataset = TestDataSet(
            name=f"TestData_{schema.name}",
            schema=schema,
        )

        # Generate positive test cases
        for i in range(3):
            record = {}
            for field_def in schema.fields:
                field_name = field_def.get("name", f"field_{i}")
                field_type = field_def.get("type", "string")
                record[field_name] = self._generate_sample_value(field_type, i)
            dataset.positive_cases.append(record)
            dataset.records.append(record)

        # Generate negative test cases
        for field_def in schema.fields:
            field_name = field_def.get("name", "unknown")
            nullable = field_def.get("nullable", True)

            if not nullable:
                # Create record with null value for non-nullable field
                negative_record = {f.get("name", ""): "valid" for f in schema.fields}
                negative_record[field_name] = None
                dataset.negative_cases.append(negative_record)

        # Generate edge case data
        edge_record = {}
        for field_def in schema.fields:
            field_name = field_def.get("name", "unknown")
            field_type = field_def.get("type", "string")
            edge_record[field_name] = self._generate_edge_value(field_type)
        dataset.edge_cases.append(edge_record)

        logger.info(
            "Created test dataset with %d positive, %d negative, %d edge cases",
            len(dataset.positive_cases),
            len(dataset.negative_cases),
            len(dataset.edge_cases),
        )
        return dataset

    # =========================================================================
    # Helper Methods
    # =========================================================================

    def _add_reasoning_step(self, thought: str) -> None:
        """Add a reasoning step to the current execution context."""
        step = ReasoningStep(
            step_number=len(self._reasoning_trace) + 1,
            thought=thought,
            confidence=0.8,
        )
        self._reasoning_trace.append(step)

    def _generate_sample_value(self, field_type: str, index: int) -> Any:
        """Generate a sample value for a field type."""
        if field_type in ["int", "integer"]:
            return index + 1
        elif field_type in ["float", "number"]:
            return float(index + 1) + 0.5
        elif field_type in ["bool", "boolean"]:
            return index % 2 == 0
        elif field_type in ["str", "string"]:
            return f"sample_value_{index}"
        elif field_type in ["list", "array"]:
            return [f"item_{i}" for i in range(3)]
        elif field_type in ["dict", "object"]:
            return {"key": f"value_{index}"}
        else:
            return f"value_{index}"

    def _generate_edge_value(self, field_type: str) -> Any:
        """Generate an edge case value for a field type."""
        if field_type in ["int", "integer"]:
            return 2147483647  # Max 32-bit int
        elif field_type in ["float", "number"]:
            return float("inf")
        elif field_type in ["str", "string"]:
            return ""  # Empty string
        elif field_type in ["list", "array"]:
            return []  # Empty list
        elif field_type in ["dict", "object"]:
            return {}  # Empty dict
        else:
            return None

    def _extract_feature_spec(self, task: Task) -> FeatureSpec:
        """Extract FeatureSpec from task context."""
        return FeatureSpec(
            name=task.context.get("feature_name", task.title),
            description=task.description,
            requirements=task.context.get("requirements", []),
            acceptance_criteria=task.context.get("acceptance_criteria", []),
        )

    def _extract_function_spec(self, task: Task) -> FunctionSpec:
        """Extract FunctionSpec from task context."""
        return FunctionSpec(
            name=task.context.get("function_name", "unknown"),
            description=task.description,
            parameters=task.context.get("parameters", []),
            return_type=task.context.get("return_type", "any"),
        )

    def _extract_data_schema(self, task: Task) -> DataSchema:
        """Extract DataSchema from task context."""
        return DataSchema(
            name=task.context.get("schema_name", "TestSchema"),
            fields=task.context.get("fields", []),
            constraints=task.context.get("constraints", []),
        )

    def _extract_test_scope(self, task: Task) -> TestScope:
        """Extract TestScope from task context."""
        return TestScope(
            name=task.context.get("scope_name", task.title),
            description=task.description,
            modules=task.context.get("modules", []),
            test_types=[TestType.UNIT, TestType.INTEGRATION],
        )

    async def _execute_general_qa_task(
        self,
        task: Task,
        artifacts: list[Artifact],
    ) -> None:
        """Execute a general QA task."""
        # Analyze requirements if provided
        requirements = task.context.get("requirements", [])
        if requirements:
            strategy = await self.analyze_requirements(requirements)
            artifacts.append(self._strategy_to_artifact(strategy))

        # Create general QA report
        report = Artifact(
            type=ArtifactType.TEST_PLAN,
            name="QA Analysis Report",
            content=f"QA analysis for task: {task.title}\n"
                   f"Description: {task.description}",
            created_by=self.agent_id,
        )
        artifacts.append(report)

    # =========================================================================
    # Artifact Conversion
    # =========================================================================

    def _strategy_to_artifact(self, strategy: TestStrategy) -> Artifact:
        """Convert TestStrategy to Artifact."""
        content = f"# Test Strategy: {strategy.name}\n\n"
        content += f"{strategy.description}\n\n"
        content += "## Test Types\n"
        for test_type, priority in strategy.test_types.items():
            content += f"- {test_type.value}: Priority {priority}\n"
        content += "\n## Risk Areas\n"
        for risk in strategy.risk_areas:
            content += f"- {risk}\n"

        return Artifact(
            type=ArtifactType.TEST_PLAN,
            name=strategy.name,
            content=content,
            created_by=self.id,
        )

    def _test_cases_to_artifact(self, test_cases: list[TestCase]) -> Artifact:
        """Convert test cases to Artifact."""
        content = "# Generated Test Cases\n\n"
        for tc in test_cases:
            content += f"## {tc.name}\n"
            content += f"- Type: {tc.test_type.value}\n"
            content += f"- Severity: {tc.severity.value}\n"
            content += f"- Description: {tc.description}\n\n"

        return Artifact(
            type=ArtifactType.TEST_CODE,
            name="Generated Test Cases",
            content=content,
            created_by=self.id,
        )

    def _test_suite_to_artifact(self, suite: TestSuite) -> Artifact:
        """Convert TestSuite to Artifact."""
        content = f"# Test Suite: {suite.name}\n\n"
        content += f"{suite.description}\n\n"
        content += f"Total Tests: {suite.total_tests}\n"
        content += f"Parallel Execution: {suite.parallel}\n\n"
        content += "## Test Cases\n"
        for tc in suite.test_cases:
            content += f"- {tc.name}\n"

        return Artifact(
            type=ArtifactType.TEST_PLAN,
            name=suite.name,
            content=content,
            created_by=self.id,
        )

    def _edge_cases_to_artifact(self, edge_cases: list[EdgeCase]) -> Artifact:
        """Convert edge cases to Artifact."""
        content = "# Identified Edge Cases\n\n"
        for ec in edge_cases:
            content += f"## {ec.name}\n"
            content += f"- Category: {ec.category.value}\n"
            content += f"- Risk Score: {ec.risk_score()}\n"
            content += f"- Description: {ec.description}\n\n"

        return Artifact(
            type=ArtifactType.TEST_PLAN,
            name="Edge Case Analysis",
            content=content,
            created_by=self.id,
        )

    def _dataset_to_artifact(self, dataset: TestDataSet) -> Artifact:
        """Convert TestDataSet to Artifact."""
        content = f"# Test Dataset: {dataset.name}\n\n"
        content += f"Positive Cases: {len(dataset.positive_cases)}\n"
        content += f"Negative Cases: {len(dataset.negative_cases)}\n"
        content += f"Edge Cases: {len(dataset.edge_cases)}\n"

        return Artifact(
            type=ArtifactType.TEST_CODE,
            name=dataset.name,
            content=content,
            created_by=self.id,
        )


# =============================================================================
# Exports
# =============================================================================

__all__ = [
    # Enums
    "TestSeverity",
    "TestType",
    "TestStatus",
    "CoverageType",
    "EdgeCaseCategory",
    # Input Specifications
    "FeatureSpec",
    "FunctionSpec",
    "DataSchema",
    "TestScope",
    # Output Types
    "TestCase",
    "TestSuite",
    "TestStrategy",
    "EdgeCase",
    "TestDataSet",
    "CoverageRequirement",
    "DefectReport",
    # Agent
    "QAEngineerAgent",
]
