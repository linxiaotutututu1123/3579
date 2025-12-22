"""Chairman Agents - Core Type Definitions.

This module defines all core types, enums, and data classes used throughout
the Chairman Agents system.

Type Aliases:
    AgentId: Unique identifier for agents
    TaskId: Unique identifier for tasks
    ArtifactId: Unique identifier for artifacts

Enums:
    AgentRole: 18 specialized agent roles
    ExpertiseLevel: 6 expertise levels from Junior to Fellow
    AgentCapability: 35 fine-grained capabilities
    TaskStatus: Task lifecycle states
    TaskPriority: Task priority levels
    MessageType: Inter-agent message types
    ArtifactType: Output artifact types
    ToolType: Available tool types

Data Classes:
    AgentProfile: Agent configuration and capabilities
    Task: Task definition with requirements
    TaskContext: Execution context for tasks
    Artifact: Output artifacts with metadata
    QualityRequirements: Quality standards for tasks
    TaskResult: Task execution results
    ReasoningStep: Cognitive reasoning trace
    ReviewComment: Code review comments
    AgentMessage: Inter-agent communication
    AgentState: Agent runtime state
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, TypeAlias


# =============================================================================
# Type Aliases
# =============================================================================

AgentId: TypeAlias = str
"""Unique identifier for agents."""

TaskId: TypeAlias = str
"""Unique identifier for tasks."""

ArtifactId: TypeAlias = str
"""Unique identifier for artifacts."""


def generate_id(prefix: str = "") -> str:
    """Generate a unique ID with optional prefix.

    Args:
        prefix: Optional prefix for the ID (e.g., 'agent', 'task')

    Returns:
        A unique identifier string
    """
    uid = uuid.uuid4().hex[:12]
    return f"{prefix}_{uid}" if prefix else uid


# =============================================================================
# Agent Role Enumeration - 18 Specialized Roles
# =============================================================================


class AgentRole(Enum):
    """Agent role enumeration - 18 specialized expert roles.

    Organized by organizational layer:
    - Management: PROJECT_MANAGER
    - Decision: TECH_DIRECTOR
    - Architecture: SYSTEM_ARCHITECT, SOLUTION_ARCHITECT
    - Development: TECH_LEAD, BACKEND_ENGINEER, FRONTEND_ENGINEER, FULLSTACK_ENGINEER
    - Quality: QA_ENGINEER, QA_LEAD, CODE_REVIEWER, PERFORMANCE_ENGINEER
    - Security: SECURITY_ARCHITECT
    - Operations: DEVOPS_ENGINEER, SRE_ENGINEER
    - Documentation: TECH_WRITER
    """

    # -------------------------------------------------------------------------
    # Management Layer
    # -------------------------------------------------------------------------
    PROJECT_MANAGER = "project_manager"
    """Project Manager - Requirements analysis, task breakdown, progress tracking"""

    # -------------------------------------------------------------------------
    # Decision Layer
    # -------------------------------------------------------------------------
    TECH_DIRECTOR = "tech_director"
    """Technical Director - Technical decisions, architecture governance, standards"""

    # -------------------------------------------------------------------------
    # Architecture Layer
    # -------------------------------------------------------------------------
    SYSTEM_ARCHITECT = "system_architect"
    """System Architect - Overall architecture design, technology selection"""

    SOLUTION_ARCHITECT = "solution_architect"
    """Solution Architect - Specific solution design, integration planning"""

    # -------------------------------------------------------------------------
    # Development Layer
    # -------------------------------------------------------------------------
    TECH_LEAD = "tech_lead"
    """Technical Lead - Technical guidance, development mentoring, code quality"""

    BACKEND_ENGINEER = "backend_engineer"
    """Backend Engineer - Backend services, APIs, databases"""

    FRONTEND_ENGINEER = "frontend_engineer"
    """Frontend Engineer - Frontend UI, interactions, user experience"""

    FULLSTACK_ENGINEER = "fullstack_engineer"
    """Fullstack Engineer - End-to-end development, rapid prototyping"""

    # -------------------------------------------------------------------------
    # Quality Layer
    # -------------------------------------------------------------------------
    QA_ENGINEER = "qa_engineer"
    """QA Engineer - Test strategy, test case design, automated testing"""

    QA_LEAD = "qa_lead"
    """QA Lead - Test planning, quality standards, team coordination"""

    CODE_REVIEWER = "code_reviewer"
    """Code Reviewer - Code quality, best practices, standards enforcement"""

    PERFORMANCE_ENGINEER = "performance_engineer"
    """Performance Engineer - Performance optimization, bottleneck analysis"""

    # -------------------------------------------------------------------------
    # Security Layer
    # -------------------------------------------------------------------------
    SECURITY_ARCHITECT = "security_architect"
    """Security Architect - Security design, vulnerability analysis, auditing"""

    # -------------------------------------------------------------------------
    # Operations Layer
    # -------------------------------------------------------------------------
    DEVOPS_ENGINEER = "devops_engineer"
    """DevOps Engineer - CI/CD, deployment, infrastructure"""

    SRE_ENGINEER = "sre_engineer"
    """SRE Engineer - Reliability, monitoring, incident handling"""

    # -------------------------------------------------------------------------
    # Documentation Layer
    # -------------------------------------------------------------------------
    TECH_WRITER = "tech_writer"
    """Technical Writer - Documentation, API docs, user guides"""


# =============================================================================
# Expertise Level Enumeration
# =============================================================================


class ExpertiseLevel(Enum):
    """Professional expertise level enumeration.

    Levels represent increasing mastery and experience:
    - JUNIOR (1): Entry-level, learning fundamentals
    - INTERMEDIATE (2): Solid foundation, independent work
    - SENIOR (3): Deep expertise, mentoring ability
    - STAFF (4): Cross-team impact, technical leadership
    - PRINCIPAL (5): Organization-wide influence, strategic vision
    - FELLOW (6): Industry recognition, thought leadership
    """

    JUNIOR = 1
    """Junior - Entry-level, learning fundamentals"""

    INTERMEDIATE = 2
    """Intermediate - Solid foundation, independent work"""

    SENIOR = 3
    """Senior - Deep expertise, mentoring ability"""

    STAFF = 4
    """Staff - Cross-team impact, technical leadership"""

    PRINCIPAL = 5
    """Principal - Organization-wide influence, strategic vision"""

    FELLOW = 6
    """Fellow - Industry recognition, thought leadership (highest level)"""


# =============================================================================
# Agent Capability Enumeration - 35 Fine-grained Capabilities
# =============================================================================


class AgentCapability(Enum):
    """Agent capability enumeration - 35 fine-grained capabilities.

    Organized by domain:
    - Requirements & Planning: Analysis, decomposition, estimation, risk, roadmap
    - Architecture Design: System, API, database, microservices, event-driven, distributed
    - Coding: Generation, review, refactoring, optimization, debugging
    - Languages & Frameworks: Python, JavaScript, TypeScript, SQL expertise
    - Testing: Planning, case design, unit, integration, E2E, performance
    - Security: Analysis, vulnerability, audit, penetration
    - DevOps: CI/CD, containerization, orchestration, IaC, monitoring
    - Documentation: Technical docs, API docs
    """

    # -------------------------------------------------------------------------
    # Requirements & Planning Capabilities
    # -------------------------------------------------------------------------
    REQUIREMENT_ANALYSIS = "requirement_analysis"
    """Requirement Analysis - Understanding and documenting requirements"""

    TASK_DECOMPOSITION = "task_decomposition"
    """Task Decomposition - Breaking down complex tasks"""

    EFFORT_ESTIMATION = "effort_estimation"
    """Effort Estimation - Estimating work effort and timelines"""

    RISK_ASSESSMENT = "risk_assessment"
    """Risk Assessment - Identifying and evaluating risks"""

    ROADMAP_PLANNING = "roadmap_planning"
    """Roadmap Planning - Strategic planning and milestone definition"""

    # -------------------------------------------------------------------------
    # Architecture Design Capabilities
    # -------------------------------------------------------------------------
    SYSTEM_DESIGN = "system_design"
    """System Design - High-level system architecture"""

    API_DESIGN = "api_design"
    """API Design - RESTful/GraphQL API design"""

    DATABASE_DESIGN = "database_design"
    """Database Design - Schema design and optimization"""

    MICROSERVICES_DESIGN = "microservices_design"
    """Microservices Design - Service decomposition and communication"""

    EVENT_DRIVEN_DESIGN = "event_driven_design"
    """Event-Driven Design - Event sourcing and messaging patterns"""

    DISTRIBUTED_SYSTEMS = "distributed_systems"
    """Distributed Systems - Distributed architecture patterns"""

    # -------------------------------------------------------------------------
    # Coding Capabilities
    # -------------------------------------------------------------------------
    CODE_GENERATION = "code_generation"
    """Code Generation - Writing new code"""

    CODE_REVIEW = "code_review"
    """Code Review - Reviewing code for quality and standards"""

    CODE_REFACTORING = "code_refactoring"
    """Code Refactoring - Improving code structure"""

    CODE_OPTIMIZATION = "code_optimization"
    """Code Optimization - Performance tuning"""

    CODE_DEBUGGING = "code_debugging"
    """Code Debugging - Finding and fixing bugs"""

    # -------------------------------------------------------------------------
    # Language & Framework Expertise
    # -------------------------------------------------------------------------
    PYTHON_EXPERT = "python_expert"
    """Python Expert - Python language mastery"""

    JAVASCRIPT_EXPERT = "javascript_expert"
    """JavaScript Expert - JavaScript/ES6+ mastery"""

    TYPESCRIPT_EXPERT = "typescript_expert"
    """TypeScript Expert - TypeScript mastery"""

    SQL_EXPERT = "sql_expert"
    """SQL Expert - SQL and database query optimization"""

    # -------------------------------------------------------------------------
    # Testing Capabilities
    # -------------------------------------------------------------------------
    TEST_PLANNING = "test_planning"
    """Test Planning - Test strategy development"""

    TEST_CASE_DESIGN = "test_case_design"
    """Test Case Design - Designing effective test cases"""

    UNIT_TESTING = "unit_testing"
    """Unit Testing - Writing unit tests"""

    INTEGRATION_TESTING = "integration_testing"
    """Integration Testing - Writing integration tests"""

    E2E_TESTING = "e2e_testing"
    """E2E Testing - End-to-end testing"""

    PERFORMANCE_TESTING = "performance_testing"
    """Performance Testing - Load and stress testing"""

    # -------------------------------------------------------------------------
    # Security Capabilities
    # -------------------------------------------------------------------------
    SECURITY_ANALYSIS = "security_analysis"
    """Security Analysis - Security vulnerability analysis"""

    VULNERABILITY_ASSESSMENT = "vulnerability_assessment"
    """Vulnerability Assessment - Identifying security vulnerabilities"""

    SECURITY_AUDIT = "security_audit"
    """Security Audit - Comprehensive security review"""

    PENETRATION_TESTING = "penetration_testing"
    """Penetration Testing - Simulated attack testing"""

    # -------------------------------------------------------------------------
    # DevOps Capabilities
    # -------------------------------------------------------------------------
    CI_CD_PIPELINE = "ci_cd_pipeline"
    """CI/CD Pipeline - Continuous integration and deployment"""

    CONTAINERIZATION = "containerization"
    """Containerization - Docker and container technologies"""

    ORCHESTRATION = "orchestration"
    """Orchestration - Kubernetes and container orchestration"""

    INFRASTRUCTURE_AS_CODE = "iac"
    """Infrastructure as Code - Terraform, CloudFormation, etc."""

    MONITORING = "monitoring"
    """Monitoring - Observability and alerting"""

    # -------------------------------------------------------------------------
    # Documentation Capabilities
    # -------------------------------------------------------------------------
    DOCUMENTATION = "documentation"
    """Documentation - Technical documentation writing"""

    API_DOCUMENTATION = "api_documentation"
    """API Documentation - API reference documentation"""


# =============================================================================
# Task Status Enumeration
# =============================================================================


class TaskStatus(Enum):
    """Task lifecycle status enumeration.

    States organized by phase:
    - Initial: DRAFT, PENDING
    - Execution: QUEUED, ASSIGNED, IN_PROGRESS
    - Collaboration: IN_REVIEW, IN_DEBATE, AWAITING_CONSENSUS, REVISION_REQUIRED
    - Blocked: BLOCKED, WAITING_DEPENDENCY
    - Terminal: COMPLETED, FAILED, CANCELLED
    """

    # Initial States
    DRAFT = "draft"
    """Draft - Task is being defined"""

    PENDING = "pending"
    """Pending - Task is ready to be assigned"""

    # Execution States
    QUEUED = "queued"
    """Queued - Task is in the execution queue"""

    ASSIGNED = "assigned"
    """Assigned - Task is assigned to an agent"""

    IN_PROGRESS = "in_progress"
    """In Progress - Task is being executed"""

    # Collaboration States
    IN_REVIEW = "in_review"
    """In Review - Task output is being reviewed"""

    IN_DEBATE = "in_debate"
    """In Debate - Task approach is being debated"""

    AWAITING_CONSENSUS = "awaiting_consensus"
    """Awaiting Consensus - Waiting for team agreement"""

    REVISION_REQUIRED = "revision_required"
    """Revision Required - Task needs modifications"""

    # Blocked States
    BLOCKED = "blocked"
    """Blocked - Task cannot proceed"""

    WAITING_DEPENDENCY = "waiting_dependency"
    """Waiting Dependency - Task waiting for dependencies"""

    # Terminal States
    COMPLETED = "completed"
    """Completed - Task finished successfully"""

    FAILED = "failed"
    """Failed - Task could not be completed"""

    CANCELLED = "cancelled"
    """Cancelled - Task was cancelled"""


# =============================================================================
# Task Priority Enumeration
# =============================================================================


class TaskPriority(Enum):
    """Task priority level enumeration.

    Priority levels from highest to lowest:
    - CRITICAL (1): Blocking issues, immediate attention required
    - HIGH (2): Core functionality, important features
    - MEDIUM (3): Standard features, normal work
    - LOW (4): Optimizations, improvements
    - BACKLOG (5): Future consideration, nice-to-have
    """

    CRITICAL = 1
    """Critical - Blocking issues, immediate attention required"""

    HIGH = 2
    """High - Core functionality, important features"""

    MEDIUM = 3
    """Medium - Standard features, normal work"""

    LOW = 4
    """Low - Optimizations, improvements"""

    BACKLOG = 5
    """Backlog - Future consideration, nice-to-have"""


# =============================================================================
# Message Type Enumeration
# =============================================================================


class MessageType(Enum):
    """Inter-agent message type enumeration.

    Message categories:
    - Task-related: Assignment, update, completion, failure
    - Collaboration: Review requests, feedback, help
    - Debate: Start, argument, rebuttal, conclusion
    - Consensus: Proposal, vote, resolution
    - Pair Programming: Session management, suggestions
    - System: Status, errors, notifications
    """

    # Task-related Messages
    TASK_ASSIGNMENT = "task_assignment"
    """Task Assignment - Assigning a task to an agent"""

    TASK_UPDATE = "task_update"
    """Task Update - Progress update on a task"""

    TASK_COMPLETED = "task_completed"
    """Task Completed - Task finished successfully"""

    TASK_FAILED = "task_failed"
    """Task Failed - Task could not be completed"""

    # Collaboration Messages
    REQUEST_REVIEW = "request_review"
    """Request Review - Asking for code/work review"""

    REVIEW_FEEDBACK = "review_feedback"
    """Review Feedback - Providing review comments"""

    REQUEST_HELP = "request_help"
    """Request Help - Asking for assistance"""

    PROVIDE_HELP = "provide_help"
    """Provide Help - Offering assistance"""

    # Debate Messages
    DEBATE_START = "debate_start"
    """Debate Start - Initiating a technical debate"""

    DEBATE_ARGUMENT = "debate_argument"
    """Debate Argument - Presenting an argument"""

    DEBATE_REBUTTAL = "debate_rebuttal"
    """Debate Rebuttal - Responding to an argument"""

    DEBATE_CONCLUSION = "debate_conclusion"
    """Debate Conclusion - Concluding the debate"""

    # Consensus Messages
    CONSENSUS_PROPOSAL = "consensus_proposal"
    """Consensus Proposal - Proposing a decision"""

    CONSENSUS_VOTE = "consensus_vote"
    """Consensus Vote - Voting on a proposal"""

    CONSENSUS_REACHED = "consensus_reached"
    """Consensus Reached - Agreement achieved"""

    # Pair Programming Messages
    PAIR_SESSION_START = "pair_session_start"
    """Pair Session Start - Starting pair programming"""

    PAIR_SUGGESTION = "pair_suggestion"
    """Pair Suggestion - Suggesting code/approach"""

    PAIR_SESSION_END = "pair_session_end"
    """Pair Session End - Ending pair programming"""

    # System Messages
    STATUS_UPDATE = "status_update"
    """Status Update - Agent status change"""

    ERROR_REPORT = "error_report"
    """Error Report - Reporting an error"""

    NOTIFICATION = "notification"
    """Notification - General notification"""


# =============================================================================
# Artifact Type Enumeration
# =============================================================================


class ArtifactType(Enum):
    """Output artifact type enumeration.

    Artifact categories:
    - Documents: Requirements, design, architecture, API spec, test plan, runbook
    - Code: Source, test, config, script, migration
    - Configuration: Dockerfile, K8s manifest, CI config
    - Reports: Review, security, performance
    - Other: Diagrams
    """

    # Document Artifacts
    REQUIREMENT_DOC = "requirement_doc"
    """Requirement Document - Requirements specification"""

    DESIGN_DOC = "design_doc"
    """Design Document - Design specification"""

    ARCHITECTURE_DOC = "architecture_doc"
    """Architecture Document - Architecture documentation"""

    API_SPEC = "api_spec"
    """API Specification - API documentation"""

    TEST_PLAN = "test_plan"
    """Test Plan - Testing strategy document"""

    RUNBOOK = "runbook"
    """Runbook - Operations runbook"""

    # Code Artifacts
    SOURCE_CODE = "source_code"
    """Source Code - Application source code"""

    TEST_CODE = "test_code"
    """Test Code - Test source code"""

    CONFIG_FILE = "config_file"
    """Configuration File - Configuration files"""

    SCRIPT = "script"
    """Script - Utility scripts"""

    MIGRATION = "migration"
    """Migration - Database migration scripts"""

    # Configuration Artifacts
    DOCKERFILE = "dockerfile"
    """Dockerfile - Docker container definition"""

    K8S_MANIFEST = "k8s_manifest"
    """Kubernetes Manifest - K8s deployment files"""

    CI_CONFIG = "ci_config"
    """CI Configuration - CI/CD pipeline config"""

    # Report Artifacts
    REVIEW_REPORT = "review_report"
    """Review Report - Code review report"""

    SECURITY_REPORT = "security_report"
    """Security Report - Security analysis report"""

    PERFORMANCE_REPORT = "performance_report"
    """Performance Report - Performance analysis report"""

    # Other Artifacts
    DIAGRAM = "diagram"
    """Diagram - Architecture/flow diagrams"""


# =============================================================================
# Tool Type Enumeration
# =============================================================================


class ToolType(Enum):
    """Available tool type enumeration.

    Tools available to agents:
    - CODE_EXECUTOR: Execute code snippets
    - FILE_SYSTEM: File operations
    - GIT: Version control operations
    - TERMINAL: Shell command execution
    - BROWSER: Web browsing capabilities
    - SEARCH: Web search functionality
    - LINTER: Code quality checking
    - TEST_RUNNER: Test execution
    - DATABASE: Database operations
    """

    CODE_EXECUTOR = "code_executor"
    """Code Executor - Execute code snippets"""

    FILE_SYSTEM = "file_system"
    """File System - File read/write operations"""

    GIT = "git"
    """Git - Version control operations"""

    TERMINAL = "terminal"
    """Terminal - Shell command execution"""

    BROWSER = "browser"
    """Browser - Web browsing capabilities"""

    SEARCH = "search"
    """Search - Web search functionality"""

    LINTER = "linter"
    """Linter - Code quality checking"""

    TEST_RUNNER = "test_runner"
    """Test Runner - Test execution"""

    DATABASE = "database"
    """Database - Database operations"""


# =============================================================================
# Core Data Classes
# =============================================================================


@dataclass
class QualityRequirements:
    """Quality requirements for task execution.

    Defines quality standards that must be met:
    - Code quality: Coverage, complexity, type hints, docstrings
    - Security: Scan requirements, allowed vulnerabilities
    - Performance: Test requirements, response time limits
    - Review: Architecture and security review requirements
    """

    # Code Quality
    min_test_coverage: float = 0.8
    """Minimum required test coverage (0.0-1.0)"""

    max_complexity: int = 10
    """Maximum cyclomatic complexity allowed"""

    require_type_hints: bool = True
    """Whether type hints are required"""

    require_docstrings: bool = True
    """Whether docstrings are required"""

    # Security Requirements
    security_scan_required: bool = True
    """Whether security scanning is required"""

    allowed_vulnerabilities: int = 0
    """Number of allowed vulnerabilities (typically 0)"""

    # Performance Requirements
    performance_test_required: bool = False
    """Whether performance testing is required"""

    max_response_time_ms: int | None = None
    """Maximum allowed response time in milliseconds"""

    # Review Requirements
    require_architecture_review: bool = False
    """Whether architecture review is required"""

    require_security_review: bool = False
    """Whether security review is required"""


@dataclass
class ReasoningStep:
    """A single step in the cognitive reasoning trace.

    Captures the agent's thought process during task execution:
    - step_number: Order of this step
    - thought: The agent's current thinking
    - action: Action taken (if any)
    - observation: Result of the action
    - reflection: Meta-cognitive reflection
    - confidence: Confidence in the current step
    """

    step_number: int = 0
    """Order of this step in the reasoning trace"""

    thought: str = ""
    """The agent's current thinking"""

    action: str | None = None
    """Action taken (if any)"""

    observation: str | None = None
    """Result/observation from the action"""

    reflection: str | None = None
    """Meta-cognitive reflection on the step"""

    confidence: float = 0.0
    """Confidence level in this step (0.0-1.0)"""

    timestamp: datetime = field(default_factory=datetime.now)
    """When this step occurred"""


@dataclass
class ReviewComment:
    """Code review comment with location and suggestions.

    Represents a single review comment:
    - Location: file path, line numbers
    - Content: comment text, severity, category
    - Suggestions: recommended changes, auto-fix capability
    - Status: resolution tracking
    """

    id: str = field(default_factory=lambda: generate_id("comment"))
    """Unique identifier for this comment"""

    reviewer_id: AgentId = ""
    """ID of the reviewing agent"""

    # Location
    file_path: str | None = None
    """Path to the file being reviewed"""

    line_start: int | None = None
    """Starting line number"""

    line_end: int | None = None
    """Ending line number"""

    # Content
    comment: str = ""
    """The review comment text"""

    severity: str = "info"
    """Severity: info, suggestion, warning, error, critical"""

    category: str = ""
    """Category: style, logic, security, performance, etc."""

    # Suggestions
    suggestion: str | None = None
    """Suggested change description"""

    suggested_code: str | None = None
    """Suggested replacement code"""

    auto_fixable: bool = False
    """Whether this can be auto-fixed"""

    # Status
    resolved: bool = False
    """Whether this comment has been addressed"""

    resolution: str | None = None
    """How the comment was resolved"""


@dataclass
class Artifact:
    """Output artifact with metadata and quality information.

    Represents a produced artifact (code, document, etc.):
    - Identity: id, type, name
    - Content: content string or file path
    - Metadata: language, framework, version
    - Quality: scores, coverage, review status
    """

    id: ArtifactId = field(default_factory=lambda: generate_id("artifact"))
    """Unique identifier for this artifact"""

    type: ArtifactType = ArtifactType.SOURCE_CODE
    """Type of artifact"""

    name: str = ""
    """Human-readable name"""

    # Content
    content: str = ""
    """Artifact content (for small artifacts)"""

    file_path: Path | None = None
    """File path (for file-based artifacts)"""

    # Metadata
    language: str | None = None
    """Programming language (for code)"""

    framework: str | None = None
    """Framework used (if applicable)"""

    # Version Control
    version: str = "1.0.0"
    """Semantic version"""

    created_at: datetime = field(default_factory=datetime.now)
    """Creation timestamp"""

    created_by: AgentId | None = None
    """ID of the creating agent"""

    # Quality Information
    quality_score: float | None = None
    """Overall quality score (0.0-1.0)"""

    test_coverage: float | None = None
    """Test coverage percentage"""

    # Review Information
    reviewed: bool = False
    """Whether this has been reviewed"""

    approved: bool = False
    """Whether this has been approved"""

    review_comments: list[ReviewComment] = field(default_factory=list)
    """Review comments on this artifact"""


@dataclass
class TaskResult:
    """Result of task execution.

    Contains:
    - Outcome: success status, artifacts produced
    - Reasoning: thought trace, reflections
    - Quality: confidence and quality scores, metrics
    - Execution: time, tokens, tools used
    - Errors: error details if failed
    - Improvements: suggestions, warnings, lessons
    """

    task_id: TaskId = ""
    """ID of the executed task"""

    success: bool = False
    """Whether the task succeeded"""

    # Artifacts
    artifacts: list[Artifact] = field(default_factory=list)
    """Produced artifacts"""

    # Reasoning Trace
    reasoning_trace: list[ReasoningStep] = field(default_factory=list)
    """Step-by-step reasoning trace"""

    reflections: list[str] = field(default_factory=list)
    """High-level reflections"""

    # Quality Metrics
    confidence_score: float = 0.0
    """Confidence in the result (0.0-1.0)"""

    quality_score: float = 0.0
    """Overall quality score (0.0-1.0)"""

    metrics: dict[str, float] = field(default_factory=dict)
    """Detailed metrics (coverage, complexity, etc.)"""

    # Execution Information
    execution_time_seconds: float = 0.0
    """Time taken to execute"""

    token_usage: dict[str, int] = field(default_factory=dict)
    """Token usage breakdown"""

    tools_used: list[ToolType] = field(default_factory=list)
    """Tools used during execution"""

    # Error Information
    error_message: str | None = None
    """Error message if failed"""

    error_type: str | None = None
    """Error type/category"""

    # Improvement Suggestions
    suggestions: list[str] = field(default_factory=list)
    """Improvement suggestions"""

    warnings: list[str] = field(default_factory=list)
    """Warnings to note"""

    learned_lessons: list[str] = field(default_factory=list)
    """Lessons learned during execution"""


@dataclass
class Task:
    """Task definition with requirements and metadata.

    Complete task specification including:
    - Identity: id, title, description
    - Classification: type, priority, status
    - Requirements: capabilities, role, expertise level
    - Complexity: difficulty, time estimate, risk
    - Quality: quality requirements specification
    - Collaboration: review, debate, pair programming needs
    - Tools: required tool types
    - Dependencies: task relationships
    - Assignment: assigned agent, reviewers
    - Timing: timestamps and deadlines
    - Context: additional data
    - Result: execution result
    """

    id: TaskId = field(default_factory=lambda: generate_id("task"))
    """Unique identifier for this task"""

    title: str = ""
    """Task title"""

    description: str = ""
    """Detailed task description"""

    # Classification
    type: str = "development"
    """Task type (development, review, documentation, etc.)"""

    priority: TaskPriority = TaskPriority.MEDIUM
    """Task priority level"""

    status: TaskStatus = TaskStatus.PENDING
    """Current task status"""

    # Capability Requirements
    required_capabilities: list[AgentCapability] = field(default_factory=list)
    """Required agent capabilities"""

    required_role: AgentRole | None = None
    """Required agent role (if specific)"""

    min_expertise_level: ExpertiseLevel = ExpertiseLevel.INTERMEDIATE
    """Minimum expertise level required"""

    # Complexity Assessment
    complexity: int = 5
    """Complexity rating (1-10)"""

    estimated_hours: float = 4.0
    """Estimated hours to complete"""

    risk_level: str = "medium"
    """Risk level: low, medium, high, critical"""

    # Quality Requirements
    quality_requirements: QualityRequirements | None = None
    """Quality standards for this task"""

    # Collaboration Requirements
    requires_review: bool = True
    """Whether code review is required"""

    requires_debate: bool = False
    """Whether technical debate is needed"""

    requires_pair_programming: bool = False
    """Whether pair programming is needed"""

    min_reviewers: int = 1
    """Minimum number of reviewers required"""

    # Tool Requirements
    required_tools: list[ToolType] = field(default_factory=list)
    """Tools required for this task"""

    # Dependencies
    dependencies: list[TaskId] = field(default_factory=list)
    """Tasks that must complete before this one"""

    blocked_by: list[TaskId] = field(default_factory=list)
    """Tasks currently blocking this one"""

    subtasks: list[TaskId] = field(default_factory=list)
    """Child task IDs"""

    parent_task_id: TaskId | None = None
    """Parent task ID (if subtask)"""

    # Assignment
    assigned_to: AgentId | None = None
    """Assigned agent ID"""

    reviewers: list[AgentId] = field(default_factory=list)
    """Assigned reviewer agent IDs"""

    # Timing
    created_at: datetime = field(default_factory=datetime.now)
    """Task creation timestamp"""

    started_at: datetime | None = None
    """When execution started"""

    completed_at: datetime | None = None
    """When execution completed"""

    deadline: datetime | None = None
    """Task deadline"""

    # Context
    context: dict[str, Any] = field(default_factory=dict)
    """Additional context data"""

    # Result
    result: TaskResult | None = None
    """Execution result"""


@dataclass
class AgentProfile:
    """Agent configuration and capability profile.

    Complete agent specification including:
    - Identity: id, name, role
    - Capabilities: capabilities list, levels, expertise
    - Cognitive: thinking style, reflection, planning depth
    - Collaboration: style, debate skill, consensus flexibility
    - Tools: allowed tool types
    - LLM: system prompt, temperature, tokens, model
    - Execution: retries, timeout
    """

    id: AgentId = field(default_factory=lambda: generate_id("agent"))
    """Unique identifier for this agent"""

    name: str = ""
    """Human-readable agent name"""

    role: AgentRole = AgentRole.BACKEND_ENGINEER
    """Agent's primary role"""

    # Capability Configuration
    capabilities: list[AgentCapability] = field(default_factory=list)
    """List of agent capabilities"""

    capability_levels: dict[AgentCapability, int] = field(default_factory=dict)
    """Capability proficiency levels (1-10)"""

    expertise_level: ExpertiseLevel = ExpertiseLevel.SENIOR
    """Overall expertise level"""

    # Cognitive Configuration
    thinking_style: str = "analytical"
    """Thinking style: analytical, creative, balanced"""

    reflection_enabled: bool = True
    """Whether reflection/meta-cognition is enabled"""

    planning_depth: int = 3
    """Depth of planning lookahead"""

    # Collaboration Configuration
    collaboration_style: str = "cooperative"
    """Style: cooperative, assertive, balanced"""

    debate_skill: int = 7
    """Debate/argumentation skill (1-10)"""

    consensus_flexibility: float = 0.7
    """Willingness to compromise (0.0-1.0)"""

    # Tool Permissions
    allowed_tools: list[ToolType] = field(default_factory=list)
    """Tools this agent can use"""

    # LLM Configuration
    system_prompt: str = ""
    """System prompt for the agent"""

    temperature: float = 0.7
    """LLM temperature setting"""

    max_tokens: int = 4096
    """Maximum tokens per response"""

    model: str = "gpt-4"
    """LLM model identifier"""

    # Execution Configuration
    max_retries: int = 3
    """Maximum retry attempts"""

    timeout_seconds: int = 300
    """Execution timeout in seconds"""

    def has_capability(
        self,
        capability: AgentCapability,
        min_level: int = 1,
    ) -> bool:
        """Check if agent has a capability at minimum level.

        Args:
            capability: The capability to check
            min_level: Minimum proficiency level required (1-10)

        Returns:
            True if agent has the capability at required level
        """
        if capability not in self.capabilities:
            return False
        return self.capability_levels.get(capability, 0) >= min_level

    def can_use_tool(self, tool: ToolType) -> bool:
        """Check if agent has permission to use a tool.

        Args:
            tool: The tool to check

        Returns:
            True if agent can use the tool
        """
        return tool in self.allowed_tools


@dataclass
class TaskContext:
    """Execution context for tasks.

    Provides context needed for task execution:
    - Project: name, description, root path
    - Technology: stack, coding standards
    - Architecture: decisions, patterns
    - Resources: existing artifacts, completed tasks
    - Knowledge: domain knowledge, learned patterns
    - Constraints: limitations, non-functional requirements
    - Session: conversation history, variables
    """

    # Project Information
    project_name: str = ""
    """Name of the project"""

    project_description: str = ""
    """Project description"""

    project_root: Path | None = None
    """Root directory of the project"""

    # Technology Stack
    tech_stack: dict[str, list[str]] = field(default_factory=dict)
    """Technology stack (e.g., {'backend': ['python', 'fastapi']})"""

    # Coding Standards
    coding_standards: dict[str, Any] = field(default_factory=dict)
    """Coding standards and conventions"""

    # Architecture
    architecture_decisions: list[str] = field(default_factory=list)
    """Recorded architecture decisions (ADRs)"""

    design_patterns: list[str] = field(default_factory=list)
    """Design patterns in use"""

    # Existing Resources
    existing_artifacts: list[Artifact] = field(default_factory=list)
    """Previously created artifacts"""

    completed_tasks: list[TaskId] = field(default_factory=list)
    """IDs of completed tasks"""

    # Knowledge Base
    domain_knowledge: dict[str, Any] = field(default_factory=dict)
    """Domain-specific knowledge"""

    learned_patterns: list[str] = field(default_factory=list)
    """Patterns learned during execution"""

    # Constraints
    constraints: list[str] = field(default_factory=list)
    """Project constraints"""

    non_functional_requirements: dict[str, Any] = field(default_factory=dict)
    """Non-functional requirements (performance, security, etc.)"""

    # Session
    conversation_history: list[dict[str, str]] = field(default_factory=list)
    """Conversation history"""

    variables: dict[str, Any] = field(default_factory=dict)
    """Session variables"""


@dataclass
class AgentMessage:
    """Inter-agent communication message.

    Message structure for agent-to-agent communication:
    - Identity: id, type
    - Routing: sender, receiver (None for broadcast)
    - Content: subject, content, data payload
    - Association: task, artifact, reply chain
    - Priority: priority level, expiration
    - Status: timestamp, read/processed flags
    """

    id: str = field(default_factory=lambda: generate_id("msg"))
    """Unique message identifier"""

    type: MessageType = MessageType.NOTIFICATION
    """Type of message"""

    # Routing
    sender_id: AgentId = ""
    """Sender agent ID"""

    receiver_id: AgentId | None = None
    """Receiver agent ID (None for broadcast)"""

    # Content
    subject: str = ""
    """Message subject/title"""

    content: str = ""
    """Message content"""

    data: dict[str, Any] = field(default_factory=dict)
    """Structured data payload"""

    # Associations
    task_id: TaskId | None = None
    """Related task ID"""

    artifact_id: ArtifactId | None = None
    """Related artifact ID"""

    reply_to: str | None = None
    """ID of message being replied to"""

    thread_id: str | None = None
    """Thread ID for conversation grouping"""

    # Priority and Expiration
    priority: int = 3
    """Priority level (1-5, lower is higher priority)"""

    expires_at: datetime | None = None
    """When this message expires"""

    # Status
    timestamp: datetime = field(default_factory=datetime.now)
    """When the message was sent"""

    read: bool = False
    """Whether the message has been read"""

    processed: bool = False
    """Whether the message has been processed"""


@dataclass
class AgentState:
    """Runtime state of an agent.

    Tracks agent's current state:
    - Identity: agent_id, status
    - Work: current task, activity
    - Cognitive: thinking state
    - Queue: pending messages, reviews
    - Statistics: completed/failed counts
    - Performance: average times, scores, success rate
    - Timing: activity timestamps
    """

    agent_id: AgentId = ""
    """Agent identifier"""

    status: str = "idle"
    """Status: idle, working, reviewing, debating, blocked"""

    # Current Work
    current_task_id: TaskId | None = None
    """Currently assigned task"""

    current_activity: str | None = None
    """Current activity description"""

    # Cognitive State
    thinking: bool = False
    """Whether agent is in thinking mode"""

    current_thought: str | None = None
    """Current thought (for observability)"""

    # Queue Status
    pending_messages: int = 0
    """Number of unprocessed messages"""

    pending_reviews: int = 0
    """Number of pending reviews"""

    # Statistics
    tasks_completed: int = 0
    """Total tasks completed"""

    tasks_failed: int = 0
    """Total tasks failed"""

    reviews_completed: int = 0
    """Total reviews completed"""

    # Performance Metrics
    average_task_time: float = 0.0
    """Average task completion time (seconds)"""

    average_quality_score: float = 0.0
    """Average quality score (0.0-1.0)"""

    success_rate: float = 1.0
    """Task success rate (0.0-1.0)"""

    # Timing
    last_active: datetime = field(default_factory=datetime.now)
    """Last activity timestamp"""

    session_start: datetime = field(default_factory=datetime.now)
    """Session start timestamp"""


# =============================================================================
# Exports
# =============================================================================

__all__ = [
    # Type Aliases
    "AgentId",
    "TaskId",
    "ArtifactId",
    "generate_id",

    # Enums
    "AgentRole",
    "ExpertiseLevel",
    "AgentCapability",
    "TaskStatus",
    "TaskPriority",
    "MessageType",
    "ArtifactType",
    "ToolType",

    # Data Classes
    "QualityRequirements",
    "ReasoningStep",
    "ReviewComment",
    "Artifact",
    "TaskResult",
    "Task",
    "AgentProfile",
    "TaskContext",
    "AgentMessage",
    "AgentState",
]
