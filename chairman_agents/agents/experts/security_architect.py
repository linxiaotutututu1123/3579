"""Security Architect Agent - Application Security Expert.

This module implements a security architect agent for comprehensive security
analysis, vulnerability detection, and security architecture design.

Core Capabilities:
    - Security architecture design
    - OWASP Top 10 vulnerability detection
    - Code security auditing
    - Authentication/Authorization system design
    - Encryption scheme evaluation
    - Dependency security review
"""

from __future__ import annotations

import logging
import re
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import TYPE_CHECKING, Any, Protocol

from chairman_agents.core.protocols import LLMClientProtocol
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

logger = logging.getLogger(__name__)


class VulnerabilitySeverity(Enum):
    """Security vulnerability severity levels (CVSS-based)."""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


class VulnerabilityType(Enum):
    """Security vulnerability types (OWASP Top 10 2021)."""
    A01_BROKEN_ACCESS_CONTROL = "A01:2021-Broken Access Control"
    A02_CRYPTOGRAPHIC_FAILURES = "A02:2021-Cryptographic Failures"
    A03_INJECTION = "A03:2021-Injection"
    A04_INSECURE_DESIGN = "A04:2021-Insecure Design"
    A05_SECURITY_MISCONFIGURATION = "A05:2021-Security Misconfiguration"
    A06_VULNERABLE_COMPONENTS = "A06:2021-Vulnerable and Outdated Components"
    A07_AUTH_FAILURES = "A07:2021-Identification and Authentication Failures"
    A08_INTEGRITY_FAILURES = "A08:2021-Software and Data Integrity Failures"
    A09_LOGGING_FAILURES = "A09:2021-Security Logging and Monitoring Failures"
    A10_SSRF = "A10:2021-Server-Side Request Forgery"
    XSS = "Cross-Site Scripting (XSS)"
    CSRF = "Cross-Site Request Forgery (CSRF)"
    PATH_TRAVERSAL = "Path Traversal"
    HARDCODED_SECRETS = "Hardcoded Secrets"
    INSECURE_DESERIALIZATION = "Insecure Deserialization"


class DataType(Enum):
    """Data classification types for encryption planning."""
    PII = "pii"
    PHI = "phi"
    PCI = "pci"
    CREDENTIALS = "credentials"
    SESSION = "session"
    BUSINESS_CRITICAL = "business_critical"
    INTERNAL = "internal"
    PUBLIC = "public"


@dataclass
class Vulnerability:
    """Security vulnerability with remediation guidance."""
    id: str = field(default_factory=lambda: generate_id("vuln"))
    severity: VulnerabilitySeverity = VulnerabilitySeverity.MEDIUM
    type: VulnerabilityType = VulnerabilityType.A05_SECURITY_MISCONFIGURATION
    title: str = ""
    description: str = ""
    location: str = ""
    code_snippet: str | None = None
    impact: str = ""
    remediation: str = ""
    references: list[str] = field(default_factory=list)
    cwe_id: str | None = None
    cvss_score: float | None = None
    detected_at: datetime = field(default_factory=datetime.now)
    false_positive: bool = False
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class SecurityAuditReport:
    """Comprehensive security audit report."""
    id: str = field(default_factory=lambda: generate_id("audit"))
    target: str = ""
    scan_type: str = "comprehensive"
    started_at: datetime = field(default_factory=datetime.now)
    completed_at: datetime | None = None
    vulnerabilities: list[Vulnerability] = field(default_factory=list)
    summary: str = ""
    recommendations: list[str] = field(default_factory=list)
    compliance_status: dict[str, bool] = field(default_factory=dict)
    risk_score: float = 0.0
    passed_checks: int = 0
    failed_checks: int = 0
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def critical_count(self) -> int:
        return sum(1 for v in self.vulnerabilities if v.severity == VulnerabilitySeverity.CRITICAL)

    @property
    def high_count(self) -> int:
        return sum(1 for v in self.vulnerabilities if v.severity == VulnerabilitySeverity.HIGH)

    @property
    def is_secure(self) -> bool:
        return self.critical_count == 0 and self.high_count == 0


@dataclass
class AuthRequirements:
    """Authentication system requirements specification."""
    auth_methods: list[str] = field(default_factory=lambda: ["password"])
    mfa_required: bool = False
    session_duration_hours: int = 24
    password_policy: dict[str, Any] = field(default_factory=dict)
    oauth_providers: list[str] = field(default_factory=list)
    api_auth: list[str] = field(default_factory=lambda: ["jwt"])
    compliance_frameworks: list[str] = field(default_factory=list)
    user_types: list[str] = field(default_factory=lambda: ["standard"])
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class AuthDesign:
    """Authentication system design specification."""
    id: str = field(default_factory=lambda: generate_id("auth_design"))
    architecture: str = ""
    auth_flow: str = ""
    token_strategy: dict[str, Any] = field(default_factory=dict)
    session_management: dict[str, Any] = field(default_factory=dict)
    password_handling: dict[str, Any] = field(default_factory=dict)
    mfa_implementation: dict[str, Any] = field(default_factory=dict)
    oauth_integration: dict[str, Any] = field(default_factory=dict)
    api_security: dict[str, Any] = field(default_factory=dict)
    security_controls: list[str] = field(default_factory=list)
    implementation_notes: list[str] = field(default_factory=list)
    diagrams: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class EncryptionPlan:
    """Data encryption strategy and implementation plan."""
    id: str = field(default_factory=lambda: generate_id("enc_plan"))
    data_classification: dict[str, str] = field(default_factory=dict)
    algorithms: dict[str, str] = field(default_factory=dict)
    key_management: dict[str, Any] = field(default_factory=dict)
    at_rest: dict[str, Any] = field(default_factory=dict)
    in_transit: dict[str, Any] = field(default_factory=dict)
    recommendations: list[str] = field(default_factory=list)
    compliance_notes: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class Dependency:
    """External dependency information for security review."""
    name: str = ""
    version: str = ""
    latest_version: str | None = None
    ecosystem: str = "pypi"
    license: str | None = None
    direct: bool = True
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class DependencyAudit:
    """Dependency security audit results."""
    id: str = field(default_factory=lambda: generate_id("dep_audit"))
    total_dependencies: int = 0
    vulnerable_count: int = 0
    outdated_count: int = 0
    vulnerabilities: list[Vulnerability] = field(default_factory=list)
    recommendations: list[str] = field(default_factory=list)
    risk_summary: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)


# OWASP Detection Rules
OWASP_DETECTION_RULES: dict[VulnerabilityType, list[dict[str, Any]]] = {
    VulnerabilityType.A03_INJECTION: [
        {"pattern": r"execute\s*\(\s*[\"'].*?\%s.*?[\"']", "title": "SQL Injection via String Formatting",
         "cwe": "CWE-89", "remediation": "Use parameterized queries"},
        {"pattern": r"os\.system\s*\(", "title": "OS Command Injection Risk",
         "cwe": "CWE-78", "remediation": "Use subprocess with shell=False"},
        {"pattern": r"eval\s*\(|exec\s*\(", "title": "Code Injection via eval/exec",
         "cwe": "CWE-94", "remediation": "Avoid eval/exec; use ast.literal_eval"},
    ],
    VulnerabilityType.A02_CRYPTOGRAPHIC_FAILURES: [
        {"pattern": r"md5\s*\(|sha1\s*\(", "title": "Weak Cryptographic Hash",
         "cwe": "CWE-328", "remediation": "Use SHA-256 or stronger"},
        {"pattern": r"DES|3DES|RC4|Blowfish", "title": "Weak Encryption Algorithm",
         "cwe": "CWE-327", "remediation": "Use AES-256-GCM"},
    ],
    VulnerabilityType.HARDCODED_SECRETS: [
        {"pattern": r"(password|secret|api_key|token)\s*=\s*['\"][^'\"]{8,}['\"]",
         "title": "Hardcoded Secret", "cwe": "CWE-798",
         "remediation": "Use environment variables or secret management"},
        {"pattern": r"-----BEGIN (RSA |EC |)PRIVATE KEY-----", "title": "Hardcoded Private Key",
         "cwe": "CWE-798", "remediation": "Store keys in secure vaults"},
    ],
    VulnerabilityType.XSS: [
        {"pattern": r"innerHTML\s*=|document\.write\s*\(", "title": "DOM-based XSS Risk",
         "cwe": "CWE-79", "remediation": "Use textContent with sanitization"},
    ],
    VulnerabilityType.PATH_TRAVERSAL: [
        {"pattern": r"open\s*\([^)]*\+[^)]*\)|Path\s*\([^)]*\+", "title": "Path Traversal Risk",
         "cwe": "CWE-22", "remediation": "Validate paths; use Path.resolve()"},
    ],
    VulnerabilityType.A09_LOGGING_FAILURES: [
        {"pattern": r"except\s*:\s*pass|except\s+Exception\s*:\s*pass",
         "title": "Silent Exception Handling", "cwe": "CWE-390",
         "remediation": "Log exceptions for security monitoring"},
    ],
}


class BaseExpertAgent(ABC):
    """Abstract base class for expert agents."""
    role: AgentRole = AgentRole.BACKEND_ENGINEER

    def __init__(
        self, profile: AgentProfile, llm_client: Any, memory: MemorySystem | None = None
    ) -> None:
        self.profile = profile
        self.llm_client = llm_client
        self.memory = memory
        self._reasoning_engine: ReasoningEngine | None = None
        logger.info("Initialized %s: %s", self.__class__.__name__, profile.name)

    @property
    def reasoning(self) -> ReasoningEngine:
        if self._reasoning_engine is None:
            from chairman_agents.cognitive.reasoning import ReasoningEngine
            self._reasoning_engine = ReasoningEngine(self.llm_client)
        return self._reasoning_engine

    @property
    def id(self) -> str:
        return self.profile.id

    @property
    def name(self) -> str:
        return self.profile.name

    @abstractmethod
    async def execute(self, task: Task) -> TaskResult:
        raise NotImplementedError

    async def _generate(self, prompt: str, temperature: float = 0.7, max_tokens: int = 2048) -> str:
        return await self.llm_client.generate(prompt, temperature=temperature, max_tokens=max_tokens)


class SecurityArchitectAgent(BaseExpertAgent):
    """Security Architect Agent - Application Security Expert.

    Specialized agent for security analysis, vulnerability detection,
    and security architecture design with OWASP Top 10 detection rules.
    """
    role = AgentRole.SECURITY_ARCHITECT

    def __init__(
        self, profile: AgentProfile, llm_client: Any, memory: MemorySystem | None = None
    ) -> None:
        super().__init__(profile, llm_client, memory)
        self.detection_rules = OWASP_DETECTION_RULES

    async def execute(self, task: Task) -> TaskResult:
        """Execute a security-related task."""
        import time
        start_time = time.time()
        task.status = TaskStatus.IN_PROGRESS
        reasoning_trace: list[ReasoningStep] = []
        artifacts: list[Artifact] = []

        try:
            desc = task.description.lower()
            if "audit" in desc or "review" in desc:
                code = task.context.get("code", "")
                language = task.context.get("language", "python")
                reasoning_trace.append(ReasoningStep(
                    step_number=1, thought="Performing security audit", action="audit_code", confidence=0.9
                ))
                report = await self.audit_code(code, language)
                artifacts.append(Artifact(
                    type=ArtifactType.SECURITY_REPORT, name="Security Audit Report",
                    content=report.summary, quality_score=1.0 if report.is_secure else 0.5
                ))
            elif "auth" in desc:
                reqs = AuthRequirements(**task.context.get("auth_requirements", {}))
                reasoning_trace.append(ReasoningStep(
                    step_number=1, thought="Designing auth system", action="design_auth_system", confidence=0.85
                ))
                design = await self.design_auth_system(reqs)
                artifacts.append(Artifact(
                    type=ArtifactType.DESIGN_DOC, name="Auth Design", content=design.architecture
                ))
            elif "vulnerabilit" in desc:
                codebase = Path(task.context.get("codebase_path", "."))
                reasoning_trace.append(ReasoningStep(
                    step_number=1, thought="Analyzing vulnerabilities", action="analyze_vulnerabilities", confidence=0.9
                ))
                vulns = await self.analyze_vulnerabilities(codebase)
                artifacts.append(Artifact(
                    type=ArtifactType.SECURITY_REPORT, name="Vulnerability Analysis",
                    content=f"Found {len(vulns)} vulnerabilities"
                ))

            task.status = TaskStatus.COMPLETED
            return TaskResult(
                task_id=task.id, success=True, artifacts=artifacts,
                reasoning_trace=reasoning_trace, confidence_score=0.85, quality_score=0.9,
                execution_time_seconds=time.time() - start_time, tools_used=[ToolType.LINTER]
            )
        except Exception as e:
            logger.error("Security task failed: %s", str(e))
            task.status = TaskStatus.FAILED
            return TaskResult(
                task_id=task.id, success=False, error_message=str(e),
                error_type=type(e).__name__, reasoning_trace=reasoning_trace,
                execution_time_seconds=time.time() - start_time
            )

    async def audit_code(self, code: str, language: str) -> SecurityAuditReport:
        """Perform security audit on source code using pattern matching and LLM analysis."""
        report = SecurityAuditReport(target=f"Code ({language})", scan_type="comprehensive")
        vulnerabilities: list[Vulnerability] = []

        for vuln_type, rules in self.detection_rules.items():
            for rule in rules:
                for match in re.finditer(rule["pattern"], code, re.IGNORECASE):
                    line_num = code[:match.start()].count("\n") + 1
                    snippet_start, snippet_end = max(0, match.start() - 50), min(len(code), match.end() + 50)
                    vulnerabilities.append(Vulnerability(
                        severity=VulnerabilitySeverity.MEDIUM, type=vuln_type, title=rule["title"],
                        description=f"Pattern: {rule['pattern']}", location=f"line {line_num}",
                        code_snippet=code[snippet_start:snippet_end], remediation=rule["remediation"],
                        cwe_id=rule.get("cwe")
                    ))

        if len(code) > 100:
            vulnerabilities.extend(await self._llm_security_analysis(code, language))

        report.vulnerabilities = vulnerabilities
        report.completed_at = datetime.now()
        report.failed_checks = len(vulnerabilities)
        report.passed_checks = max(0, 10 - len(vulnerabilities))
        report.risk_score = min(100, len(vulnerabilities) * 15)
        report.summary = self._generate_audit_summary(vulnerabilities)
        return report

    async def _llm_security_analysis(self, code: str, language: str) -> list[Vulnerability]:
        """Use LLM for deep security analysis."""
        prompt = f"""Analyze {language} code for security vulnerabilities (OWASP Top 10).
```{language}
{code[:3000]}
```
Format each finding as: VULN: [severity] [type] [description] [remediation]
If none found, respond: NO_VULNERABILITIES_FOUND"""

        response = await self._generate(prompt, temperature=0.3)
        if "NO_VULNERABILITIES_FOUND" in response:
            return []

        vulnerabilities = []
        for section in response.split("VULN:")[1:]:
            lines = section.strip().split("\n")
            if lines:
                vulnerabilities.append(Vulnerability(
                    title=lines[0].strip()[:100], description=section.strip()[:500],
                    severity=self._parse_severity(section), remediation="Review the identified issue"
                ))
        return vulnerabilities

    def _parse_severity(self, text: str) -> VulnerabilitySeverity:
        text_lower = text.lower()
        if "critical" in text_lower: return VulnerabilitySeverity.CRITICAL
        if "high" in text_lower: return VulnerabilitySeverity.HIGH
        if "low" in text_lower: return VulnerabilitySeverity.LOW
        return VulnerabilitySeverity.MEDIUM

    def _generate_audit_summary(self, vulnerabilities: list[Vulnerability]) -> str:
        if not vulnerabilities:
            return "No security vulnerabilities detected."
        counts = {s: sum(1 for v in vulnerabilities if v.severity == s) for s in VulnerabilitySeverity}
        return (f"Found {len(vulnerabilities)} vulnerabilities. Critical: {counts[VulnerabilitySeverity.CRITICAL]}, "
                f"High: {counts[VulnerabilitySeverity.HIGH]}, Medium: {counts[VulnerabilitySeverity.MEDIUM]}")

    async def design_auth_system(self, requirements: AuthRequirements) -> AuthDesign:
        """Design authentication and authorization system."""
        prompt = f"""Design secure auth system:
Methods: {requirements.auth_methods}, MFA: {requirements.mfa_required}
Session: {requirements.session_duration_hours}h, OAuth: {requirements.oauth_providers}
Provide: architecture, auth flow, token strategy, security controls."""

        response = await self._generate(prompt, temperature=0.5)
        design = AuthDesign(
            architecture=response, auth_flow="User -> Login -> Validate -> Token -> Access",
            token_strategy={"type": "JWT", "access_expiry_minutes": 15, "refresh_expiry_days": 7},
            password_handling={"algorithm": "argon2id", "memory_cost": 65536, "time_cost": 3},
            security_controls=["Rate limiting", "Account lockout", "CSRF protection", "Audit logging"]
        )
        if requirements.mfa_required:
            design.mfa_implementation = {"methods": ["totp", "sms"], "backup_codes": 10}
        return design

    async def analyze_vulnerabilities(self, codebase: Path) -> list[Vulnerability]:
        """Analyze codebase for security vulnerabilities."""
        vulnerabilities: list[Vulnerability] = []
        if not codebase.exists():
            logger.warning("Codebase not found: %s", codebase)
            return vulnerabilities

        for file_path in list(codebase.rglob("*.py"))[:50]:
            try:
                content = file_path.read_text(encoding="utf-8", errors="ignore")
                report = await self.audit_code(content, "python")
                for vuln in report.vulnerabilities:
                    vuln.location = f"{file_path}:{vuln.location}"
                    vulnerabilities.append(vuln)
            except Exception as e:
                logger.warning("Failed to analyze %s: %s", file_path, e)
        return vulnerabilities

    async def recommend_encryption(self, data_types: list[DataType]) -> EncryptionPlan:
        """Recommend encryption strategy for data types."""
        plan = EncryptionPlan(
            algorithms={"symmetric": "AES-256-GCM", "asymmetric": "RSA-4096", "hashing": "SHA-256", "password": "Argon2id"},
            key_management={"rotation_days": 90, "storage": "HSM or KMS", "access": "RBAC with audit"},
            at_rest={"database": "TDE", "files": "AES-256-GCM", "backups": "Separate key hierarchy"},
            in_transit={"protocol": "TLS 1.3", "cipher_suites": ["TLS_AES_256_GCM_SHA384"]},
            recommendations=["Use envelope encryption", "Automate key rotation", "Enable audit logging"]
        )
        for dt in data_types:
            enc = "AES-256-GCM + HSM" if dt in [DataType.PCI, DataType.CREDENTIALS] else "AES-256-GCM" if dt in [DataType.PII, DataType.PHI] else "AES-256"
            plan.data_classification[dt.value] = enc
        return plan

    async def review_dependencies(self, dependencies: list[Dependency]) -> DependencyAudit:
        """Review dependencies for security vulnerabilities."""
        audit = DependencyAudit(total_dependencies=len(dependencies))
        known_vulnerable = {"requests": ["2.0.0"], "django": ["1.0", "2.0"], "flask": ["0.1"]}

        for dep in dependencies:
            if dep.version in known_vulnerable.get(dep.name, []):
                audit.vulnerabilities.append(Vulnerability(
                    severity=VulnerabilitySeverity.HIGH, type=VulnerabilityType.A06_VULNERABLE_COMPONENTS,
                    title=f"Vulnerable: {dep.name}", description=f"{dep.name} {dep.version} has known vulnerabilities",
                    remediation=f"Update {dep.name} to latest version"
                ))
            if dep.latest_version and dep.version != dep.latest_version:
                audit.recommendations.append(f"{dep.name}: {dep.version} -> {dep.latest_version}")

        audit.vulnerable_count = len(audit.vulnerabilities)
        audit.outdated_count = len(audit.recommendations)
        audit.risk_summary = f"Found {audit.vulnerable_count} vulnerable of {len(dependencies)} dependencies"
        return audit


__all__ = [
    "VulnerabilitySeverity", "VulnerabilityType", "DataType",
    "Vulnerability", "SecurityAuditReport", "AuthRequirements", "AuthDesign",
    "EncryptionPlan", "Dependency", "DependencyAudit",
    "BaseExpertAgent", "SecurityArchitectAgent", "OWASP_DETECTION_RULES",
]
