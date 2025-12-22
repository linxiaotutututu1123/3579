"""Security Architect Agent - Application Security Expert.

This module implements a specialized security architect agent that provides
comprehensive security analysis, vulnerability detection, and security
architecture design capabilities.

Core Capabilities:
    - Security architecture design
    - OWASP Top 10 vulnerability detection
    - Code security auditing
    - Authentication/Authorization system design
    - Encryption scheme evaluation
    - Dependency security review

Classes:
    VulnerabilitySeverity: Severity levels for security vulnerabilities
    VulnerabilityType: Types of security vulnerabilities (OWASP Top 10 based)
    DataType: Classification of data requiring encryption
    Vulnerability: Security vulnerability with remediation guidance
    SecurityAuditReport: Comprehensive security audit results
    AuthRequirements: Authentication system requirements
    AuthDesign: Authentication system design specification
    EncryptionPlan: Data encryption strategy
    Dependency: External dependency information
    DependencyAudit: Dependency security audit results
    BaseExpertAgent: Abstract base class for expert agents
    SecurityArchitectAgent: Main security architect implementation

Example:
    >>> from chairman_agents.agents.experts import SecurityArchitectAgent
    >>> agent = SecurityArchitectAgent(profile, llm_client, memory)
    >>> report = await agent.audit_code(source_code, "python")
    >>> vulnerabilities = await agent.analyze_vulnerabilities(Path("./src"))
"""

from __future__ import annotations

import asyncio
import logging
import re
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import TYPE_CHECKING, Any, Protocol

from chairman_agents.core.types import (
    AgentCapability,
    AgentProfile,
    AgentRole,
    Artifact,
    ArtifactType,
    ReasoningStep,
    Task,
    TaskResult,
    TaskStatus,
    ToolType,
    generate_id,
)

if TYPE_CHECKING:
    from chairman_agents.cognitive.memory import MemorySystem
    from chairman_agents.cognitive.reasoning import ReasoningEngine


# =============================================================================
# Logging Configuration
# =============================================================================

logger = logging.getLogger(__name__)


# =============================================================================
# Protocol Definitions
# =============================================================================


class LLMClientProtocol(Protocol):
    """Protocol for LLM client interface."""

    async def generate(
        self,
        prompt: str,
        *,
        temperature: float = 0.7,
        max_tokens: int = 2048,
    ) -> str:
        """Generate text response from prompt."""
        ...


# =============================================================================
# Enums
# =============================================================================


class VulnerabilitySeverity(Enum):
    """Security vulnerability severity levels.

    Based on CVSS (Common Vulnerability Scoring System) severity ratings.
    """

    CRITICAL = "critical"
    """Critical - Immediate exploitation risk, system compromise possible"""

    HIGH = "high"
    """High - Serious security impact, exploitation likely"""

    MEDIUM = "medium"
    """Medium - Moderate security impact, exploitation requires conditions"""

    LOW = "low"
    """Low - Minor security impact, limited exploitation potential"""

    INFO = "info"
    """Informational - Security best practice recommendation"""


class VulnerabilityType(Enum):
    """Security vulnerability types based on OWASP Top 10 (2021).

    Categories aligned with industry-standard vulnerability classification.
    """

    # OWASP Top 10 2021
    A01_BROKEN_ACCESS_CONTROL = "A01:2021-Broken Access Control"
    """Broken Access Control - Unauthorized access to resources"""

    A02_CRYPTOGRAPHIC_FAILURES = "A02:2021-Cryptographic Failures"
    """Cryptographic Failures - Weak or missing encryption"""

    A03_INJECTION = "A03:2021-Injection"
    """Injection - SQL, NoSQL, OS, LDAP injection attacks"""

    A04_INSECURE_DESIGN = "A04:2021-Insecure Design"
    """Insecure Design - Missing or ineffective security controls"""

    A05_SECURITY_MISCONFIGURATION = "A05:2021-Security Misconfiguration"
    """Security Misconfiguration - Improper security settings"""

    A06_VULNERABLE_COMPONENTS = "A06:2021-Vulnerable and Outdated Components"
    """Vulnerable Components - Using components with known vulnerabilities"""

    A07_AUTH_FAILURES = "A07:2021-Identification and Authentication Failures"
    """Authentication Failures - Weak authentication mechanisms"""

    A08_INTEGRITY_FAILURES = "A08:2021-Software and Data Integrity Failures"
    """Integrity Failures - Code and data integrity verification issues"""

    A09_LOGGING_FAILURES = "A09:2021-Security Logging and Monitoring Failures"
    """Logging Failures - Insufficient logging and monitoring"""

    A10_SSRF = "A10:2021-Server-Side Request Forgery"
    """SSRF - Server-side request forgery vulnerabilities"""

    # Additional Common Vulnerabilities
    XSS = "Cross-Site Scripting (XSS)"
    """Cross-Site Scripting - Script injection in web pages"""

    CSRF = "Cross-Site Request Forgery (CSRF)"
    """CSRF - Unauthorized actions on behalf of authenticated users"""

    PATH_TRAVERSAL = "Path Traversal"
    """Path Traversal - Unauthorized file system access"""

    HARDCODED_SECRETS = "Hardcoded Secrets"
    """Hardcoded Secrets - Credentials or keys in source code"""

    INSECURE_DESERIALIZATION = "Insecure Deserialization"
    """Insecure Deserialization - Untrusted data deserialization"""


class DataType(Enum):
    """Data classification types for encryption planning."""

    PII = "pii"
    """Personally Identifiable Information"""

    PHI = "phi"
    """Protected Health Information (HIPAA)"""

    PCI = "pci"
    """Payment Card Information (PCI-DSS)"""

    CREDENTIALS = "credentials"
    """User credentials and secrets"""

    SESSION = "session"
    """Session tokens and authentication data"""

    BUSINESS_CRITICAL = "business_critical"
    """Business-critical proprietary data"""

    INTERNAL = "internal"
    """Internal use data"""

    PUBLIC = "public"
    """Public data requiring integrity protection"""


# =============================================================================
# Data Classes
# =============================================================================


@dataclass
class Vulnerability:
    """Security vulnerability with full context and remediation.

    Represents a discovered security vulnerability with severity,
    location, impact assessment, and remediation guidance.

    Attributes:
        id: Unique vulnerability identifier
        severity: Vulnerability severity level
        type: Vulnerability classification type
        title: Brief vulnerability title
        description: Detailed vulnerability description
        location: File path and line number
        code_snippet: Affected code snippet
        impact: Potential security impact
        remediation: Recommended fix
        references: External reference links
        cwe_id: CWE identifier if applicable
        cvss_score: CVSS score if applicable
        detected_at: Detection timestamp
        false_positive: Whether marked as false positive
        metadata: Additional context
    """

    id: str = field(default_factory=lambda: generate_id("vuln"))
    """Unique vulnerability identifier"""

    severity: VulnerabilitySeverity = VulnerabilitySeverity.MEDIUM
    """Vulnerability severity level"""

    type: VulnerabilityType = VulnerabilityType.A05_SECURITY_MISCONFIGURATION
    """Vulnerability classification type"""

    title: str = ""
    """Brief vulnerability title"""

    description: str = ""
    """Detailed vulnerability description"""

    location: str = ""
    """File path and line number (e.g., 'src/auth.py:42')"""

    code_snippet: str | None = None
    """Affected code snippet"""

    impact: str = ""
    """Potential security impact description"""

    remediation: str = ""
    """Recommended remediation steps"""

    references: list[str] = field(default_factory=list)
    """External reference links (OWASP, CWE, etc.)"""

    cwe_id: str | None = None
    """CWE (Common Weakness Enumeration) identifier"""

    cvss_score: float | None = None
    """CVSS score (0.0-10.0)"""

    detected_at: datetime = field(default_factory=datetime.now)
    """Detection timestamp"""

    false_positive: bool = False
    """Whether marked as false positive"""

    metadata: dict[str, Any] = field(default_factory=dict)
    """Additional vulnerability context"""


@dataclass
class SecurityAuditReport:
    """Comprehensive security audit report.

    Contains aggregated results from a security audit including
    all discovered vulnerabilities, statistics, and recommendations.

    Attributes:
        id: Unique report identifier
        target: Audit target description
        scan_type: Type of security scan performed
        started_at: Audit start timestamp
        completed_at: Audit completion timestamp
        vulnerabilities: List of discovered vulnerabilities
        summary: Executive summary
        recommendations: Prioritized recommendations
        compliance_status: Compliance check results
        risk_score: Overall risk score (0-100)
        passed_checks: Number of passed security checks
        failed_checks: Number of failed security checks
        metadata: Additional report context
    """

    id: str = field(default_factory=lambda: generate_id("audit"))
    """Unique report identifier"""

    target: str = ""
    """Audit target (file, module, or codebase)"""

    scan_type: str = "comprehensive"
    """Type of scan: quick, standard, comprehensive"""

    started_at: datetime = field(default_factory=datetime.now)
    """Audit start timestamp"""

    completed_at: datetime | None = None
    """Audit completion timestamp"""

    vulnerabilities: list[Vulnerability] = field(default_factory=list)
    """Discovered vulnerabilities"""

    summary: str = ""
    """Executive summary of findings"""

    recommendations: list[str] = field(default_factory=list)
    """Prioritized security recommendations"""

    compliance_status: dict[str, bool] = field(default_factory=dict)
    """Compliance framework check results"""

    risk_score: float = 0.0
    """Overall risk score (0-100, higher is riskier)"""

    passed_checks: int = 0
    """Number of passed security checks"""

    failed_checks: int = 0
    """Number of failed security checks"""

    metadata: dict[str, Any] = field(default_factory=dict)
    """Additional report metadata"""

    @property
    def critical_count(self) -> int:
        """Count of critical vulnerabilities."""
        return sum(
            1 for v in self.vulnerabilities
            if v.severity == VulnerabilitySeverity.CRITICAL
        )

    @property
    def high_count(self) -> int:
        """Count of high severity vulnerabilities."""
        return sum(
            1 for v in self.vulnerabilities
            if v.severity == VulnerabilitySeverity.HIGH
        )

    @property
    def medium_count(self) -> int:
        """Count of medium severity vulnerabilities."""
        return sum(
            1 for v in self.vulnerabilities
            if v.severity == VulnerabilitySeverity.MEDIUM
        )

    @property
    def is_secure(self) -> bool:
        """Check if audit passed (no critical/high vulnerabilities)."""
        return self.critical_count == 0 and self.high_count == 0


@dataclass
class AuthRequirements:
    """Authentication system requirements specification.

    Defines the requirements for designing an authentication system.

    Attributes:
        auth_methods: Required authentication methods
        mfa_required: Whether MFA is required
        session_duration_hours: Maximum session duration
        password_policy: Password policy requirements
        oauth_providers: OAuth provider requirements
        api_auth: API authentication requirements
        compliance_frameworks: Required compliance frameworks
        user_types: Types of users to support
        metadata: Additional requirements
    """

    auth_methods: list[str] = field(default_factory=lambda: ["password"])
    """Required authentication methods"""

    mfa_required: bool = False
    """Whether multi-factor authentication is required"""

    session_duration_hours: int = 24
    """Maximum session duration in hours"""

    password_policy: dict[str, Any] = field(default_factory=dict)
    """Password policy (min_length, complexity, etc.)"""

    oauth_providers: list[str] = field(default_factory=list)
    """Required OAuth providers (google, github, etc.)"""

    api_auth: list[str] = field(default_factory=lambda: ["jwt"])
    """API authentication methods (jwt, api_key, oauth2)"""

    compliance_frameworks: list[str] = field(default_factory=list)
    """Required compliance (GDPR, HIPAA, SOC2, etc.)"""

    user_types: list[str] = field(default_factory=lambda: ["standard"])
    """User types (standard, admin, service_account)"""

    metadata: dict[str, Any] = field(default_factory=dict)
    """Additional requirements"""


@dataclass
class AuthDesign:
    """Authentication system design specification.

    Complete design for an authentication and authorization system.

    Attributes:
        id: Unique design identifier
        architecture: High-level architecture description
        auth_flow: Authentication flow description
        token_strategy: Token management strategy
        session_management: Session handling approach
        password_handling: Password storage and validation
        mfa_implementation: MFA implementation details
        oauth_integration: OAuth integration design
        api_security: API security measures
        security_controls: Security control recommendations
        implementation_notes: Implementation guidance
        diagrams: Architecture diagram descriptions
        metadata: Additional design context
    """

    id: str = field(default_factory=lambda: generate_id("auth_design"))
    """Unique design identifier"""

    architecture: str = ""
    """High-level architecture description"""

    auth_flow: str = ""
    """Authentication flow description"""

    token_strategy: dict[str, Any] = field(default_factory=dict)
    """Token management (type, expiry, refresh, storage)"""

    session_management: dict[str, Any] = field(default_factory=dict)
    """Session handling (storage, timeout, invalidation)"""

    password_handling: dict[str, Any] = field(default_factory=dict)
    """Password storage (algorithm, salt, iterations)"""

    mfa_implementation: dict[str, Any] = field(default_factory=dict)
    """MFA details (methods, backup codes, recovery)"""

    oauth_integration: dict[str, Any] = field(default_factory=dict)
    """OAuth provider integration details"""

    api_security: dict[str, Any] = field(default_factory=dict)
    """API security (rate limiting, CORS, headers)"""

    security_controls: list[str] = field(default_factory=list)
    """Recommended security controls"""

    implementation_notes: list[str] = field(default_factory=list)
    """Implementation guidance notes"""

    diagrams: list[str] = field(default_factory=list)
    """Architecture diagram descriptions (Mermaid/PlantUML)"""

    metadata: dict[str, Any] = field(default_factory=dict)
    """Additional design metadata"""


@dataclass
class EncryptionPlan:
    """Data encryption strategy and implementation plan.

    Comprehensive encryption plan for different data types.

    Attributes:
        id: Unique plan identifier
        data_classification: Data type to encryption mapping
        algorithms: Recommended encryption algorithms
        key_management: Key management strategy
        at_rest: Encryption at rest approach
        in_transit: Encryption in transit approach
        recommendations: Implementation recommendations
        compliance_notes: Compliance-related notes
        metadata: Additional plan context
    """

    id: str = field(default_factory=lambda: generate_id("enc_plan"))
    """Unique plan identifier"""

    data_classification: dict[str, str] = field(default_factory=dict)
    """Data type to encryption level mapping"""

    algorithms: dict[str, str] = field(default_factory=dict)
    """Recommended algorithms per use case"""

    key_management: dict[str, Any] = field(default_factory=dict)
    """Key management (rotation, storage, access)"""

    at_rest: dict[str, Any] = field(default_factory=dict)
    """Encryption at rest (database, files, backups)"""

    in_transit: dict[str, Any] = field(default_factory=dict)
    """Encryption in transit (TLS config, certificates)"""

    recommendations: list[str] = field(default_factory=list)
    """Implementation recommendations"""

    compliance_notes: list[str] = field(default_factory=list)
    """Compliance-related notes"""

    metadata: dict[str, Any] = field(default_factory=dict)
    """Additional plan metadata"""


@dataclass
class Dependency:
    """External dependency information.

    Represents a software dependency for security review.

    Attributes:
        name: Package/library name
        version: Current version
        latest_version: Latest available version
        ecosystem: Package ecosystem (pypi, npm, etc.)
        license: License type
        direct: Whether direct or transitive dependency
        metadata: Additional dependency info
    """

    name: str = ""
    """Package/library name"""

    version: str = ""
    """Current version"""

    latest_version: str | None = None
    """Latest available version"""

    ecosystem: str = "pypi"
    """Package ecosystem (pypi, npm, maven, etc.)"""

    license: str | None = None
    """License type (MIT, Apache-2.0, etc.)"""

    direct: bool = True
    """Whether direct or transitive dependency"""

    metadata: dict[str, Any] = field(default_factory=dict)
    """Additional dependency information"""


@dataclass
class DependencyAudit:
    """Dependency security audit results.

    Results from auditing project dependencies for security issues.

    Attributes:
        id: Unique audit identifier
        total_dependencies: Total dependencies analyzed
        vulnerable_count: Number with known vulnerabilities
        outdated_count: Number of outdated dependencies
        vulnerabilities: Dependency vulnerabilities found
        recommendations: Update recommendations
        risk_summary: Overall risk assessment
        metadata: Additional audit context
    """

    id: str = field(default_factory=lambda: generate_id("dep_audit"))
    """Unique audit identifier"""

    total_dependencies: int = 0
    """Total dependencies analyzed"""

    vulnerable_count: int = 0
    """Number with known vulnerabilities"""

    outdated_count: int = 0
    """Number of outdated dependencies"""

    vulnerabilities: list[Vulnerability] = field(default_factory=list)
    """Dependency vulnerabilities found"""

    recommendations: list[str] = field(default_factory=list)
    """Prioritized update recommendations"""

    risk_summary: str = ""
    """Overall risk assessment summary"""

    metadata: dict[str, Any] = field(default_factory=dict)
    """Additional audit metadata"""


# =============================================================================
# OWASP Detection Rules
# =============================================================================


OWASP_DETECTION_RULES: dict[VulnerabilityType, list[dict[str, Any]]] = {
    VulnerabilityType.A03_INJECTION: [
        {
            "pattern": r"execute\s*\(\s*[\"'].*?\%s.*?[\"']",
            "title": "SQL Injection via String Formatting",
            "cwe": "CWE-89",
            "remediation": "Use parameterized queries instead of string formatting",
        },
        {
            "pattern": r"os\.system\s*\(",
            "title": "OS Command Injection Risk",
            "cwe": "CWE-78",
            "remediation": "Use subprocess with shell=False and proper input validation",
        },
        {
            "pattern": r"eval\s*\(|exec\s*\(",
            "title": "Code Injection via eval/exec",
            "cwe": "CWE-94",
            "remediation": "Avoid eval/exec; use safe alternatives like ast.literal_eval",
        },
    ],
    VulnerabilityType.A02_CRYPTOGRAPHIC_FAILURES: [
        {
            "pattern": r"md5\s*\(|sha1\s*\(",
            "title": "Weak Cryptographic Hash",
            "cwe": "CWE-328",
            "remediation": "Use SHA-256 or stronger for security-sensitive hashing",
        },
        {
            "pattern": r"DES|3DES|RC4|Blowfish",
            "title": "Weak Encryption Algorithm",
            "cwe": "CWE-327",
            "remediation": "Use AES-256-GCM or ChaCha20-Poly1305",
        },
    ],
    VulnerabilityType.HARDCODED_SECRETS: [
        {
            "pattern": r"(password|secret|api_key|token)\s*=\s*['\"][^'\"]{8,}['\"]",
            "title": "Hardcoded Secret",
            "cwe": "CWE-798",
            "remediation": "Use environment variables or secret management systems",
        },
        {
            "pattern": r"-----BEGIN (RSA |EC |)PRIVATE KEY-----",
            "title": "Hardcoded Private Key",
            "cwe": "CWE-798",
            "remediation": "Store private keys in secure vaults, not in code",
        },
    ],
    VulnerabilityType.XSS: [
        {
            "pattern": r"innerHTML\s*=|document\.write\s*\(",
            "title": "DOM-based XSS Risk",
            "cwe": "CWE-79",
            "remediation": "Use textContent or proper DOM APIs with sanitization",
        },
    ],
    VulnerabilityType.PATH_TRAVERSAL: [
        {
            "pattern": r"open\s*\([^)]*\+[^)]*\)|Path\s*\([^)]*\+",
            "title": "Path Traversal Risk",
            "cwe": "CWE-22",
            "remediation": "Validate and sanitize file paths; use Path.resolve()",
        },
    ],
    VulnerabilityType.A09_LOGGING_FAILURES: [
        {
            "pattern": r"except\s*:\s*pass|except\s+Exception\s*:\s*pass",
            "title": "Silent Exception Handling",
            "cwe": "CWE-390",
            "remediation": "Log exceptions properly for security monitoring",
        },
    ],
}


# =============================================================================
# Base Expert Agent
# =============================================================================


class BaseExpertAgent(ABC):
    """Abstract base class for expert agents.

    Provides common infrastructure for all expert agents including
    reasoning capabilities, memory integration, and task execution.

    Attributes:
        profile: Agent profile with capabilities and configuration
        llm_client: LLM client for generating responses
        memory: Memory system for context retention
        reasoning: Reasoning engine for decision making

    Subclasses must implement:
        - role: Class attribute defining the agent role
        - execute: Method to execute assigned tasks
    """

    role: AgentRole = AgentRole.BACKEND_ENGINEER
    """Agent role (must be overridden by subclasses)"""

    def __init__(
        self,
        profile: AgentProfile,
        llm_client: Any,
        memory: MemorySystem | None = None,
    ) -> None:
        """Initialize the expert agent.

        Args:
            profile: Agent profile with capabilities
            llm_client: LLM client for generation
            memory: Optional memory system for context
        """
        self.profile = profile
        self.llm_client = llm_client
        self.memory = memory
        self._reasoning_engine: ReasoningEngine | None = None

        logger.info(
            "Initialized %s agent: %s",
            self.__class__.__name__,
            profile.name,
        )

    @property
    def reasoning(self) -> ReasoningEngine:
        """Get or create reasoning engine (lazy initialization)."""
        if self._reasoning_engine is None:
            from chairman_agents.cognitive.reasoning import ReasoningEngine
            self._reasoning_engine = ReasoningEngine(self.llm_client)
        return self._reasoning_engine

    @property
    def id(self) -> str:
        """Agent unique identifier."""
        return self.profile.id

    @property
    def name(self) -> str:
        """Agent name."""
        return self.profile.name

    @abstractmethod
    async def execute(self, task: Task) -> TaskResult:
        """Execute an assigned task.

        Args:
            task: Task to execute

        Returns:
            TaskResult with execution results

        Raises:
            NotImplementedError: Must be implemented by subclasses
        """
        raise NotImplementedError

    async def _generate(
        self,
        prompt: str,
        temperature: float = 0.7,
        max_tokens: int = 2048,
    ) -> str:
        """Generate response using LLM client.

        Args:
            prompt: Input prompt
            temperature: Sampling temperature
            max_tokens: Maximum tokens to generate

        Returns:
            Generated text response
        """
        return await self.llm_client.generate(
            prompt,
            temperature=temperature,
            max_tokens=max_tokens,
        )


# =============================================================================
# Security Architect Agent
# =============================================================================


class SecurityArchitectAgent(BaseExpertAgent):
    """Security Architect Agent - Application Security Expert.

    Specialized agent for comprehensive security analysis, vulnerability
    detection, and security architecture design. Implements OWASP Top 10
    detection rules and provides security guidance.

    Capabilities:
        - SECURITY_ANALYSIS: Security vulnerability analysis
        - VULNERABILITY_ASSESSMENT: Identifying security vulnerabilities
        - SECURITY_AUDIT: Comprehensive security review
        - SYSTEM_DESIGN: Security architecture design

    Example:
        >>> profile = AgentProfile(
        ...     name="Security Architect",
        ...     role=AgentRole.SECURITY_ARCHITECT,
        ...     capabilities=[
        ...         AgentCapability.SECURITY_ANALYSIS,
        ...         AgentCapability.VULNERABILITY_ASSESSMENT,
        ...     ],
        ... )
        >>> agent = SecurityArchitectAgent(profile, llm_client, memory)
        >>> report = await agent.audit_code(code, "python")
    """

    role = AgentRole.SECURITY_ARCHITECT

    def __init__(
        self,
        profile: AgentProfile,
        llm_client: Any,
        memory: MemorySystem | None = None,
    ) -> None:
        """Initialize the Security Architect Agent.

        Args:
            profile: Agent profile (should have SECURITY_ARCHITECT role)
            llm_client: LLM client for analysis
            memory: Optional memory system
        """
        super().__init__(profile, llm_client, memory)
        self.detection_rules = OWASP_DETECTION_RULES

    async def execute(self, task: Task) -> TaskResult:
        """Execute a security-related task.

        Routes to appropriate method based on task type and description.

        Args:
            task: Task to execute

        Returns:
            TaskResult with security analysis results
        """
        import time

        start_time = time.time()
        task.status = TaskStatus.IN_PROGRESS
        reasoning_trace: list[ReasoningStep] = []
        artifacts: list[Artifact] = []

        try:
            # Determine task type from description
            description_lower = task.description.lower()

            if "audit" in description_lower or "review" in description_lower:
                # Extract code from task context if available
                code = task.context.get("code", "")
                language = task.context.get("language", "python")

                step = ReasoningStep(
                    step_number=1,
                    thought="Performing security audit on provided code",
                    action="audit_code",
                    confidence=0.9,
                )
                reasoning_trace.append(step)

                report = await self.audit_code(code, language)

                artifacts.append(Artifact(
                    type=ArtifactType.SECURITY_REPORT,
                    name="Security Audit Report",
                    content=report.summary,
                    quality_score=1.0 if report.is_secure else 0.5,
                ))

            elif "auth" in description_lower:
                requirements = AuthRequirements(**task.context.get("auth_requirements", {}))

                step = ReasoningStep(
                    step_number=1,
                    thought="Designing authentication system",
                    action="design_auth_system",
                    confidence=0.85,
                )
                reasoning_trace.append(step)

                design = await self.design_auth_system(requirements)

                artifacts.append(Artifact(
                    type=ArtifactType.DESIGN_DOC,
                    name="Authentication Design",
                    content=design.architecture,
                ))

            elif "vulnerabilit" in description_lower:
                codebase = Path(task.context.get("codebase_path", "."))

                step = ReasoningStep(
                    step_number=1,
                    thought="Analyzing codebase for vulnerabilities",
                    action="analyze_vulnerabilities",
                    confidence=0.9,
                )
                reasoning_trace.append(step)

                vulnerabilities = await self.analyze_vulnerabilities(codebase)

                artifacts.append(Artifact(
                    type=ArtifactType.SECURITY_REPORT,
                    name="Vulnerability Analysis",
                    content=f"Found {len(vulnerabilities)} vulnerabilities",
                ))

            else:
                # Default: comprehensive security analysis
                step = ReasoningStep(
                    step_number=1,
                    thought="Performing comprehensive security analysis",
                    action="comprehensive_analysis",
                    confidence=0.8,
                )
                reasoning_trace.append(step)

            task.status = TaskStatus.COMPLETED
            execution_time = time.time() - start_time

            return TaskResult(
                task_id=task.id,
                success=True,
                artifacts=artifacts,
                reasoning_trace=reasoning_trace,
                confidence_score=0.85,
                quality_score=0.9,
                execution_time_seconds=execution_time,
                tools_used=[ToolType.LINTER],
            )

        except Exception as e:
            logger.error("Security task execution failed: %s", str(e))
            task.status = TaskStatus.FAILED

            return TaskResult(
                task_id=task.id,
                success=False,
                error_message=str(e),
                error_type=type(e).__name__,
                reasoning_trace=reasoning_trace,
                execution_time_seconds=time.time() - start_time,
            )

    async def audit_code(
        self,
        code: str,
        language: str,
    ) -> SecurityAuditReport:
        """Perform security audit on source code.

        Analyzes code for security vulnerabilities using pattern matching
        and LLM-based analysis.

        Args:
            code: Source code to audit
            language: Programming language

        Returns:
            SecurityAuditReport with findings

        Example:
            >>> report = await agent.audit_code(source_code, "python")
            >>> print(f"Found {len(report.vulnerabilities)} issues")
        """
        report = SecurityAuditReport(
            target=f"Code snippet ({language})",
            scan_type="comprehensive",
        )

        vulnerabilities: list[Vulnerability] = []

        # Pattern-based detection
        for vuln_type, rules in self.detection_rules.items():
            for rule in rules:
                pattern = rule["pattern"]
                matches = list(re.finditer(pattern, code, re.IGNORECASE))

                for match in matches:
                    # Calculate line number
                    line_num = code[:match.start()].count("\n") + 1
                    snippet_start = max(0, match.start() - 50)
                    snippet_end = min(len(code), match.end() + 50)

                    vuln = Vulnerability(
                        severity=VulnerabilitySeverity.MEDIUM,
                        type=vuln_type,
                        title=rule["title"],
                        description=f"Detected pattern: {pattern}",
                        location=f"line {line_num}",
                        code_snippet=code[snippet_start:snippet_end],
                        remediation=rule["remediation"],
                        cwe_id=rule.get("cwe"),
                    )
                    vulnerabilities.append(vuln)

        # LLM-based analysis for deeper inspection
        if len(code) > 100:
            llm_findings = await self._llm_security_analysis(code, language)
            vulnerabilities.extend(llm_findings)

        report.vulnerabilities = vulnerabilities
        report.completed_at = datetime.now()
        report.failed_checks = len(vulnerabilities)
        report.passed_checks = 10 - min(len(vulnerabilities), 10)
        report.risk_score = min(100, len(vulnerabilities) * 15)
        report.summary = self._generate_audit_summary(vulnerabilities)

        return report

    async def _llm_security_analysis(
        self,
        code: str,
        language: str,
    ) -> list[Vulnerability]:
        """Use LLM for deep security analysis.

        Args:
            code: Source code to analyze
            language: Programming language

        Returns:
            List of discovered vulnerabilities
        """
        prompt = f"""Analyze the following {language} code for security vulnerabilities.
Focus on OWASP Top 10 issues, injection flaws, authentication weaknesses, and data exposure.

Code:
```{language}
{code[:3000]}
```

For each vulnerability found, provide:
1. Severity (critical/high/medium/low)
2. Type (e.g., SQL Injection, XSS, etc.)
3. Location (line number if possible)
4. Description
5. Remediation

Format: One vulnerability per paragraph, starting with "VULN:"
If no vulnerabilities found, respond with "NO_VULNERABILITIES_FOUND"
"""

        response = await self._generate(prompt, temperature=0.3)

        vulnerabilities: list[Vulnerability] = []

        if "NO_VULNERABILITIES_FOUND" in response:
            return vulnerabilities

        # Parse LLM response
        vuln_sections = response.split("VULN:")
        for section in vuln_sections[1:]:
            lines = section.strip().split("\n")
            if lines:
                vuln = Vulnerability(
                    title=lines[0].strip()[:100],
                    description=section.strip()[:500],
                    severity=self._parse_severity(section),
                    remediation="Review and address the identified issue",
                )
                vulnerabilities.append(vuln)

        return vulnerabilities

    def _parse_severity(self, text: str) -> VulnerabilitySeverity:
        """Parse severity level from text."""
        text_lower = text.lower()
        if "critical" in text_lower:
            return VulnerabilitySeverity.CRITICAL
        if "high" in text_lower:
            return VulnerabilitySeverity.HIGH
        if "low" in text_lower:
            return VulnerabilitySeverity.LOW
        return VulnerabilitySeverity.MEDIUM

    def _generate_audit_summary(
        self,
        vulnerabilities: list[Vulnerability],
    ) -> str:
        """Generate audit summary from vulnerabilities."""
        if not vulnerabilities:
            return "No security vulnerabilities detected. Code passed all security checks."

        critical = sum(1 for v in vulnerabilities if v.severity == VulnerabilitySeverity.CRITICAL)
        high = sum(1 for v in vulnerabilities if v.severity == VulnerabilitySeverity.HIGH)
        medium = sum(1 for v in vulnerabilities if v.severity == VulnerabilitySeverity.MEDIUM)
        low = sum(1 for v in vulnerabilities if v.severity == VulnerabilitySeverity.LOW)

        return (
            f"Security Audit Complete: Found {len(vulnerabilities)} vulnerabilities. "
            f"Critical: {critical}, High: {high}, Medium: {medium}, Low: {low}. "
            f"Immediate attention required for critical and high severity issues."
        )

    async def design_auth_system(
        self,
        requirements: AuthRequirements,
    ) -> AuthDesign:
        """Design authentication and authorization system.

        Creates a comprehensive authentication system design based on
        provided requirements.

        Args:
            requirements: Authentication requirements specification

        Returns:
            AuthDesign with complete system design

        Example:
            >>> reqs = AuthRequirements(mfa_required=True, oauth_providers=["google"])
            >>> design = await agent.design_auth_system(reqs)
        """
        prompt = f"""Design a secure authentication system with these requirements:

Authentication Methods: {requirements.auth_methods}
MFA Required: {requirements.mfa_required}
Session Duration: {requirements.session_duration_hours} hours
OAuth Providers: {requirements.oauth_providers}
API Auth Methods: {requirements.api_auth}
Compliance: {requirements.compliance_frameworks}
User Types: {requirements.user_types}

Provide:
1. High-level architecture description
2. Authentication flow
3. Token strategy (type, expiry, refresh)
4. Password handling (algorithm, salt rounds)
5. Security controls and best practices
"""

        response = await self._generate(prompt, temperature=0.5)

        design = AuthDesign(
            architecture=response,
            auth_flow="User -> Login -> Validate -> Token -> Access",
            token_strategy={
                "type": "JWT",
                "access_expiry_minutes": 15,
                "refresh_expiry_days": 7,
                "storage": "httpOnly cookie",
            },
            password_handling={
                "algorithm": "argon2id",
                "memory_cost": 65536,
                "time_cost": 3,
                "parallelism": 4,
            },
            security_controls=[
                "Rate limiting on auth endpoints",
                "Account lockout after failed attempts",
                "Secure session management",
                "CSRF protection",
                "Audit logging for auth events",
            ],
        )

        if requirements.mfa_required:
            design.mfa_implementation = {
                "methods": ["totp", "sms", "email"],
                "backup_codes": 10,
                "recovery_flow": "email verification + security questions",
            }

        return design

    async def analyze_vulnerabilities(
        self,
        codebase: Path,
    ) -> list[Vulnerability]:
        """Analyze codebase for security vulnerabilities.

        Scans all source files in the codebase for security issues.

        Args:
            codebase: Path to codebase directory

        Returns:
            List of discovered vulnerabilities

        Example:
            >>> vulns = await agent.analyze_vulnerabilities(Path("./src"))
            >>> for v in vulns:
            ...     print(f"{v.severity.value}: {v.title}")
        """
        vulnerabilities: list[Vulnerability] = []

        if not codebase.exists():
            logger.warning("Codebase path does not exist: %s", codebase)
            return vulnerabilities

        # Scan Python files
        python_files = list(codebase.rglob("*.py"))

        for file_path in python_files[:50]:  # Limit to 50 files
            try:
                content = file_path.read_text(encoding="utf-8", errors="ignore")
                report = await self.audit_code(content, "python")

                for vuln in report.vulnerabilities:
                    vuln.location = f"{file_path}:{vuln.location}"
                    vulnerabilities.append(vuln)

            except Exception as e:
                logger.warning("Failed to analyze %s: %s", file_path, str(e))

        return vulnerabilities

    async def recommend_encryption(
        self,
        data_types: list[DataType],
    ) -> EncryptionPlan:
        """Recommend encryption strategy for data types.

        Provides encryption recommendations based on data classification.

        Args:
            data_types: List of data types requiring encryption

        Returns:
            EncryptionPlan with recommendations

        Example:
            >>> plan = await agent.recommend_encryption([DataType.PII, DataType.CREDENTIALS])
            >>> print(plan.algorithms)
        """
        plan = EncryptionPlan()

        # Default algorithms
        plan.algorithms = {
            "symmetric": "AES-256-GCM",
            "asymmetric": "RSA-4096 or Ed25519",
            "hashing": "SHA-256 or SHA-3",
            "password": "Argon2id",
        }

        # Data classification mapping
        for data_type in data_types:
            if data_type in [DataType.PCI, DataType.CREDENTIALS]:
                plan.data_classification[data_type.value] = "AES-256-GCM + HSM"
            elif data_type in [DataType.PII, DataType.PHI]:
                plan.data_classification[data_type.value] = "AES-256-GCM"
            else:
                plan.data_classification[data_type.value] = "AES-256"

        plan.key_management = {
            "rotation_days": 90,
            "storage": "Hardware Security Module (HSM) or KMS",
            "access": "Role-based with audit logging",
        }

        plan.at_rest = {
            "database": "Transparent Data Encryption (TDE)",
            "files": "AES-256-GCM with unique keys per file",
            "backups": "Encrypted with separate key hierarchy",
        }

        plan.in_transit = {
            "protocol": "TLS 1.3",
            "cipher_suites": ["TLS_AES_256_GCM_SHA384", "TLS_CHACHA20_POLY1305_SHA256"],
            "certificate": "RSA-4096 or ECDSA P-384",
        }

        plan.recommendations = [
            "Use envelope encryption for large data",
            "Implement key rotation automation",
            "Enable encryption audit logging",
            "Use authenticated encryption (AEAD) modes",
        ]

        return plan

    async def review_dependencies(
        self,
        dependencies: list[Dependency],
    ) -> DependencyAudit:
        """Review dependencies for security vulnerabilities.

        Analyzes project dependencies for known vulnerabilities
        and outdated versions.

        Args:
            dependencies: List of dependencies to review

        Returns:
            DependencyAudit with security findings

        Example:
            >>> deps = [Dependency(name="requests", version="2.25.0")]
            >>> audit = await agent.review_dependencies(deps)
        """
        audit = DependencyAudit(
            total_dependencies=len(dependencies),
        )

        vulnerabilities: list[Vulnerability] = []
        outdated: list[str] = []

        for dep in dependencies:
            # Check for known vulnerable patterns
            if dep.version and self._is_vulnerable_version(dep.name, dep.version):
                vuln = Vulnerability(
                    severity=VulnerabilitySeverity.HIGH,
                    type=VulnerabilityType.A06_VULNERABLE_COMPONENTS,
                    title=f"Vulnerable dependency: {dep.name}",
                    description=f"{dep.name} version {dep.version} has known vulnerabilities",
                    remediation=f"Update {dep.name} to latest stable version",
                )
                vulnerabilities.append(vuln)

            # Check if outdated
            if dep.latest_version and dep.version != dep.latest_version:
                outdated.append(f"{dep.name}: {dep.version} -> {dep.latest_version}")

        audit.vulnerabilities = vulnerabilities
        audit.vulnerable_count = len(vulnerabilities)
        audit.outdated_count = len(outdated)
        audit.recommendations = outdated[:10]  # Top 10 updates
        audit.risk_summary = self._generate_dep_risk_summary(vulnerabilities, len(dependencies))

        return audit

    def _is_vulnerable_version(self, name: str, version: str) -> bool:
        """Check if dependency version is known to be vulnerable."""
        # Simplified check - in production, use vulnerability database
        known_vulnerable = {
            "requests": ["2.0.0", "2.1.0"],
            "django": ["1.0", "1.1", "2.0"],
            "flask": ["0.1", "0.2"],
        }
        return version in known_vulnerable.get(name, [])

    def _generate_dep_risk_summary(
        self,
        vulnerabilities: list[Vulnerability],
        total: int,
    ) -> str:
        """Generate dependency risk summary."""
        if not vulnerabilities:
            return f"All {total} dependencies passed security review."

        return (
            f"Found {len(vulnerabilities)} vulnerable dependencies out of {total}. "
            f"Update affected packages immediately to mitigate security risks."
        )


# =============================================================================
# Exports
# =============================================================================

__all__ = [
    # Enums
    "VulnerabilitySeverity",
    "VulnerabilityType",
    "DataType",
    # Data Classes
    "Vulnerability",
    "SecurityAuditReport",
    "AuthRequirements",
    "AuthDesign",
    "EncryptionPlan",
    "Dependency",
    "DependencyAudit",
    # Agents
    "BaseExpertAgent",
    "SecurityArchitectAgent",
    # Detection Rules
    "OWASP_DETECTION_RULES",
]
