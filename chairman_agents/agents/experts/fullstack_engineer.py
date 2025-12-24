"""Fullstack Engineer Agent for Chairman Agents.

This module implements a fullstack engineer agent that excels at end-to-end
development, combining frontend, backend, and database expertise to deliver
complete features from conception to deployment.

Key Capabilities:
    - End-to-end feature development
    - RESTful/GraphQL API design and implementation
    - Database schema design and optimization
    - Rapid prototyping and MVP development
    - Service integration and orchestration

Classes:
    FeatureSpec: Specification for a feature to be developed
    EndpointSpec: API endpoint specification
    Entity: Database entity definition
    ServiceSpec: External service specification
    FeatureDesign: Complete feature design output
    APIImplementation: API implementation result
    DatabaseSchema: Database schema design output
    Prototype: Rapid prototype output
    IntegrationPlan: Service integration plan
    BaseExpertAgent: Base class for all expert agents
    FullstackEngineerAgent: Main fullstack engineer agent

Example:
    >>> agent = FullstackEngineerAgent(profile, llm_client, memory)
    >>> result = await agent.execute(task)
    >>> feature = await agent.design_feature(spec)
"""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING, Any, Protocol, runtime_checkable

from ...core.protocols import LLMClientProtocol
from ...core.types import (
    AgentCapability,
    AgentId,
    AgentProfile,
    AgentRole,
    Artifact,
    ArtifactType,
    ExpertiseLevel,
    ReasoningStep,
    Task,
    TaskResult,
    TaskStatus,
    ToolType,
    generate_id,
)

from ...cognitive.memory import MemoryQuery

if TYPE_CHECKING:
    from ...cognitive.memory import MemorySystem
    from ...cognitive.reasoning import ReasoningEngine


# =============================================================================
# Logging Configuration
# =============================================================================

logger = logging.getLogger(__name__)


# =============================================================================
# Technology Stack Enums
# =============================================================================


class FrontendFramework(Enum):
    """Supported frontend frameworks."""

    REACT = "react"
    """React with TypeScript"""

    VUE = "vue"
    """Vue.js 3 with Composition API"""

    ANGULAR = "angular"
    """Angular with TypeScript"""

    SVELTE = "svelte"
    """Svelte/SvelteKit"""

    NEXTJS = "nextjs"
    """Next.js (React SSR/SSG)"""

    NUXT = "nuxt"
    """Nuxt.js (Vue SSR/SSG)"""


class BackendFramework(Enum):
    """Supported backend frameworks."""

    FASTAPI = "fastapi"
    """FastAPI (Python async)"""

    DJANGO = "django"
    """Django with DRF"""

    EXPRESS = "express"
    """Express.js (Node.js)"""

    NESTJS = "nestjs"
    """NestJS (Node.js with TypeScript)"""

    SPRING = "spring"
    """Spring Boot (Java/Kotlin)"""

    GIN = "gin"
    """Gin (Go)"""


class DatabaseType(Enum):
    """Supported database types."""

    POSTGRESQL = "postgresql"
    """PostgreSQL relational database"""

    MYSQL = "mysql"
    """MySQL relational database"""

    MONGODB = "mongodb"
    """MongoDB document database"""

    REDIS = "redis"
    """Redis key-value store"""

    ELASTICSEARCH = "elasticsearch"
    """Elasticsearch search engine"""

    SQLITE = "sqlite"
    """SQLite embedded database"""


class APIStyle(Enum):
    """API design styles."""

    REST = "rest"
    """RESTful API"""

    GRAPHQL = "graphql"
    """GraphQL API"""

    GRPC = "grpc"
    """gRPC API"""

    WEBSOCKET = "websocket"
    """WebSocket real-time API"""


# =============================================================================
# Specification Data Classes
# =============================================================================


@dataclass
class FeatureSpec:
    """Specification for a feature to be developed.

    Contains all information needed to design and implement a complete
    feature spanning frontend, backend, and database layers.

    Attributes:
        id: Unique feature specification identifier
        name: Feature name
        description: Detailed feature description
        user_stories: List of user stories
        acceptance_criteria: Acceptance criteria for the feature
        frontend_requirements: Frontend-specific requirements
        backend_requirements: Backend-specific requirements
        data_requirements: Data and storage requirements
        integration_points: External integration requirements
        non_functional: Non-functional requirements (performance, security)
        priority: Feature priority level
        estimated_effort: Estimated development effort in hours
    """

    id: str = field(default_factory=lambda: generate_id("feature_spec"))
    """Unique feature specification identifier"""

    name: str = ""
    """Feature name"""

    description: str = ""
    """Detailed feature description"""

    user_stories: list[str] = field(default_factory=list)
    """List of user stories"""

    acceptance_criteria: list[str] = field(default_factory=list)
    """Acceptance criteria for the feature"""

    frontend_requirements: list[str] = field(default_factory=list)
    """Frontend-specific requirements"""

    backend_requirements: list[str] = field(default_factory=list)
    """Backend-specific requirements"""

    data_requirements: list[str] = field(default_factory=list)
    """Data and storage requirements"""

    integration_points: list[str] = field(default_factory=list)
    """External integration requirements"""

    non_functional: dict[str, Any] = field(default_factory=dict)
    """Non-functional requirements (performance, security)"""

    priority: str = "medium"
    """Feature priority level: low, medium, high, critical"""

    estimated_effort: float = 8.0
    """Estimated development effort in hours"""


@dataclass
class EndpointSpec:
    """API endpoint specification.

    Defines a single API endpoint with its method, path, request/response
    schemas, and behavior specifications.

    Attributes:
        id: Unique endpoint identifier
        method: HTTP method (GET, POST, PUT, DELETE, PATCH)
        path: URL path pattern (e.g., /api/users/{id})
        summary: Brief endpoint description
        description: Detailed endpoint description
        request_body: Request body schema definition
        response_schema: Response schema definition
        query_params: Query parameter definitions
        path_params: Path parameter definitions
        headers: Required header definitions
        auth_required: Whether authentication is required
        rate_limit: Rate limit configuration
        tags: API documentation tags
    """

    id: str = field(default_factory=lambda: generate_id("endpoint"))
    """Unique endpoint identifier"""

    method: str = "GET"
    """HTTP method: GET, POST, PUT, DELETE, PATCH"""

    path: str = ""
    """URL path pattern"""

    summary: str = ""
    """Brief endpoint description"""

    description: str = ""
    """Detailed endpoint description"""

    request_body: dict[str, Any] | None = None
    """Request body schema definition"""

    response_schema: dict[str, Any] = field(default_factory=dict)
    """Response schema definition"""

    query_params: list[dict[str, Any]] = field(default_factory=list)
    """Query parameter definitions"""

    path_params: list[dict[str, Any]] = field(default_factory=list)
    """Path parameter definitions"""

    headers: list[dict[str, Any]] = field(default_factory=list)
    """Required header definitions"""

    auth_required: bool = True
    """Whether authentication is required"""

    rate_limit: dict[str, int] | None = None
    """Rate limit configuration (requests_per_minute, burst)"""

    tags: list[str] = field(default_factory=list)
    """API documentation tags"""


@dataclass
class Entity:
    """Database entity definition.

    Represents a database table/collection with its fields, relationships,
    and constraints.

    Attributes:
        id: Unique entity identifier
        name: Entity name (table/collection name)
        description: Entity description
        fields: List of field definitions
        primary_key: Primary key field name(s)
        indexes: Index definitions
        constraints: Constraint definitions
        relationships: Relationship definitions
        soft_delete: Whether to use soft delete
        timestamps: Whether to include created_at/updated_at
    """

    id: str = field(default_factory=lambda: generate_id("entity"))
    """Unique entity identifier"""

    name: str = ""
    """Entity name (table/collection name)"""

    description: str = ""
    """Entity description"""

    fields: list[dict[str, Any]] = field(default_factory=list)
    """List of field definitions"""

    primary_key: str | list[str] = "id"
    """Primary key field name(s)"""

    indexes: list[dict[str, Any]] = field(default_factory=list)
    """Index definitions"""

    constraints: list[dict[str, Any]] = field(default_factory=list)
    """Constraint definitions (unique, check, foreign key)"""

    relationships: list[dict[str, Any]] = field(default_factory=list)
    """Relationship definitions (one-to-many, many-to-many)"""

    soft_delete: bool = True
    """Whether to use soft delete (deleted_at field)"""

    timestamps: bool = True
    """Whether to include created_at/updated_at fields"""


@dataclass
class ServiceSpec:
    """External service specification.

    Defines an external service to integrate with, including connection
    details, authentication, and API endpoints.

    Attributes:
        id: Unique service identifier
        name: Service name
        description: Service description
        service_type: Type of service (REST API, database, queue, etc.)
        base_url: Base URL for the service
        auth_type: Authentication type (api_key, oauth2, basic)
        auth_config: Authentication configuration
        endpoints: List of endpoints to integrate with
        retry_config: Retry configuration
        timeout_seconds: Request timeout in seconds
        rate_limit: Rate limit for this service
    """

    id: str = field(default_factory=lambda: generate_id("service"))
    """Unique service identifier"""

    name: str = ""
    """Service name"""

    description: str = ""
    """Service description"""

    service_type: str = "rest_api"
    """Type of service: rest_api, graphql, grpc, database, queue, cache"""

    base_url: str = ""
    """Base URL for the service"""

    auth_type: str = "api_key"
    """Authentication type: api_key, oauth2, basic, jwt, none"""

    auth_config: dict[str, Any] = field(default_factory=dict)
    """Authentication configuration"""

    endpoints: list[dict[str, Any]] = field(default_factory=list)
    """List of endpoints to integrate with"""

    retry_config: dict[str, int] = field(default_factory=lambda: {
        "max_retries": 3,
        "initial_delay_ms": 100,
        "max_delay_ms": 5000,
    })
    """Retry configuration"""

    timeout_seconds: int = 30
    """Request timeout in seconds"""

    rate_limit: dict[str, int] | None = None
    """Rate limit for this service"""


# =============================================================================
# Output Data Classes
# =============================================================================


@dataclass
class FeatureDesign:
    """Complete feature design output.

    Contains the full design for a feature including frontend, backend,
    and database components.

    Attributes:
        id: Unique design identifier
        feature_spec_id: Reference to the feature specification
        name: Feature name
        frontend: Frontend component design
        backend: Backend service design
        database: Database schema design
        api_endpoints: API endpoint designs
        architecture_notes: Architecture decisions and notes
        dependencies: Required dependencies
        estimated_effort: Updated effort estimate
        risks: Identified risks
        created_at: Design creation timestamp
    """

    id: str = field(default_factory=lambda: generate_id("feature_design"))
    """Unique design identifier"""

    feature_spec_id: str = ""
    """Reference to the feature specification"""

    name: str = ""
    """Feature name"""

    frontend: dict[str, Any] = field(default_factory=dict)
    """Frontend component design (components, state, routing)"""

    backend: dict[str, Any] = field(default_factory=dict)
    """Backend service design (services, handlers, middleware)"""

    database: dict[str, Any] = field(default_factory=dict)
    """Database schema design (tables, indexes, migrations)"""

    api_endpoints: list[dict[str, Any]] = field(default_factory=list)
    """API endpoint designs"""

    architecture_notes: list[str] = field(default_factory=list)
    """Architecture decisions and notes"""

    dependencies: dict[str, list[str]] = field(default_factory=dict)
    """Required dependencies by layer (frontend, backend, database)"""

    estimated_effort: float = 0.0
    """Updated effort estimate in hours"""

    risks: list[dict[str, Any]] = field(default_factory=list)
    """Identified risks with mitigation strategies"""

    created_at: datetime = field(default_factory=datetime.now)
    """Design creation timestamp"""


@dataclass
class APIImplementation:
    """API implementation result.

    Contains the generated API code, tests, and documentation.

    Attributes:
        id: Unique implementation identifier
        endpoint_spec_id: Reference to the endpoint specification
        framework: Backend framework used
        code: Generated source code by file
        tests: Generated test code by file
        documentation: API documentation (OpenAPI/Swagger)
        dependencies: Required packages
        configuration: Required configuration
        quality_score: Code quality score (0.0-1.0)
        created_at: Implementation creation timestamp
    """

    id: str = field(default_factory=lambda: generate_id("api_impl"))
    """Unique implementation identifier"""

    endpoint_spec_id: str = ""
    """Reference to the endpoint specification"""

    framework: BackendFramework = BackendFramework.FASTAPI
    """Backend framework used"""

    code: dict[str, str] = field(default_factory=dict)
    """Generated source code by file path"""

    tests: dict[str, str] = field(default_factory=dict)
    """Generated test code by file path"""

    documentation: dict[str, Any] = field(default_factory=dict)
    """API documentation (OpenAPI/Swagger schema)"""

    dependencies: list[str] = field(default_factory=list)
    """Required packages"""

    configuration: dict[str, Any] = field(default_factory=dict)
    """Required configuration (env vars, settings)"""

    quality_score: float = 0.0
    """Code quality score (0.0-1.0)"""

    created_at: datetime = field(default_factory=datetime.now)
    """Implementation creation timestamp"""


@dataclass
class DatabaseSchema:
    """Database schema design output.

    Contains the complete database schema design with migrations.

    Attributes:
        id: Unique schema identifier
        database_type: Database type used
        entities: List of entity definitions
        migrations: Migration scripts
        seed_data: Seed data scripts
        indexes: Index definitions
        views: View definitions
        stored_procedures: Stored procedure definitions
        diagram: Schema diagram (mermaid/PlantUML)
        performance_notes: Performance considerations
        created_at: Schema creation timestamp
    """

    id: str = field(default_factory=lambda: generate_id("db_schema"))
    """Unique schema identifier"""

    database_type: DatabaseType = DatabaseType.POSTGRESQL
    """Database type used"""

    entities: list[Entity] = field(default_factory=list)
    """List of entity definitions"""

    migrations: list[dict[str, str]] = field(default_factory=list)
    """Migration scripts (version, up_sql, down_sql)"""

    seed_data: dict[str, list[dict[str, Any]]] = field(default_factory=dict)
    """Seed data by entity name"""

    indexes: list[dict[str, Any]] = field(default_factory=list)
    """Additional index definitions"""

    views: list[dict[str, str]] = field(default_factory=list)
    """View definitions (name, sql)"""

    stored_procedures: list[dict[str, str]] = field(default_factory=list)
    """Stored procedure definitions"""

    diagram: str = ""
    """Schema diagram in mermaid or PlantUML format"""

    performance_notes: list[str] = field(default_factory=list)
    """Performance considerations and recommendations"""

    created_at: datetime = field(default_factory=datetime.now)
    """Schema creation timestamp"""


@dataclass
class Prototype:
    """Rapid prototype output.

    Contains a minimal viable implementation for quick validation.

    Attributes:
        id: Unique prototype identifier
        name: Prototype name
        description: Prototype description
        tech_stack: Technology stack used
        files: Generated files by path
        setup_instructions: Setup instructions
        demo_data: Demo data for testing
        limitations: Known limitations
        next_steps: Recommended next steps for production
        created_at: Prototype creation timestamp
    """

    id: str = field(default_factory=lambda: generate_id("prototype"))
    """Unique prototype identifier"""

    name: str = ""
    """Prototype name"""

    description: str = ""
    """Prototype description"""

    tech_stack: dict[str, str] = field(default_factory=dict)
    """Technology stack used (frontend, backend, database)"""

    files: dict[str, str] = field(default_factory=dict)
    """Generated files by path"""

    setup_instructions: list[str] = field(default_factory=list)
    """Setup instructions"""

    demo_data: dict[str, Any] = field(default_factory=dict)
    """Demo data for testing"""

    limitations: list[str] = field(default_factory=list)
    """Known limitations of the prototype"""

    next_steps: list[str] = field(default_factory=list)
    """Recommended next steps for production"""

    created_at: datetime = field(default_factory=datetime.now)
    """Prototype creation timestamp"""


@dataclass
class IntegrationPlan:
    """Service integration plan.

    Contains the plan for integrating multiple services.

    Attributes:
        id: Unique plan identifier
        services: List of services to integrate
        integration_patterns: Integration patterns to use
        data_flow: Data flow diagram/description
        error_handling: Error handling strategy
        retry_strategy: Retry strategy for failures
        circuit_breaker: Circuit breaker configuration
        monitoring: Monitoring and alerting plan
        security: Security considerations
        implementation_order: Recommended implementation order
        estimated_effort: Estimated integration effort
        created_at: Plan creation timestamp
    """

    id: str = field(default_factory=lambda: generate_id("integration_plan"))
    """Unique plan identifier"""

    services: list[ServiceSpec] = field(default_factory=list)
    """List of services to integrate"""

    integration_patterns: list[str] = field(default_factory=list)
    """Integration patterns (saga, choreography, orchestration)"""

    data_flow: str = ""
    """Data flow diagram/description"""

    error_handling: dict[str, Any] = field(default_factory=dict)
    """Error handling strategy by service"""

    retry_strategy: dict[str, Any] = field(default_factory=dict)
    """Retry strategy configuration"""

    circuit_breaker: dict[str, Any] = field(default_factory=dict)
    """Circuit breaker configuration"""

    monitoring: dict[str, Any] = field(default_factory=dict)
    """Monitoring and alerting plan"""

    security: list[str] = field(default_factory=list)
    """Security considerations"""

    implementation_order: list[str] = field(default_factory=list)
    """Recommended implementation order by service name"""

    estimated_effort: float = 0.0
    """Estimated integration effort in hours"""

    created_at: datetime = field(default_factory=datetime.now)
    """Plan creation timestamp"""


# =============================================================================
# Base Expert Agent
# =============================================================================


class BaseExpertAgent(ABC):
    """Base class for all expert agents.

    Provides common functionality for expert agents including reasoning,
    memory management, and task execution infrastructure.

    Attributes:
        profile: Agent configuration and capabilities
        reasoning: Reasoning engine for decision making
        memory: Memory system for context retention
        id: Unique agent identifier (from profile)
        name: Agent name (from profile)
        role: Agent role (from profile)

    Example:
        >>> class MyAgent(BaseExpertAgent):
        ...     role = AgentRole.BACKEND_ENGINEER
        ...
        ...     async def execute(self, task: Task) -> TaskResult:
        ...         # Implementation
        ...         pass
    """

    role: AgentRole = AgentRole.BACKEND_ENGINEER
    """Default role for the agent (override in subclass)"""

    def __init__(
        self,
        profile: AgentProfile,
        llm_client: LLMClientProtocol,
        memory: MemorySystem | None = None,
    ):
        """Initialize the expert agent.

        Args:
            profile: Agent configuration and capabilities
            llm_client: LLM client for text generation
            memory: Optional memory system for context retention
        """
        self.profile = profile
        self._llm_client = llm_client
        self._memory = memory
        self._reasoning: ReasoningEngine | None = None

        # Validate role matches profile
        if profile.role != self.role:
            logger.warning(
                "Profile role %s does not match agent role %s",
                profile.role,
                self.role,
            )

        logger.info(
            "Initialized %s agent: id=%s, name=%s",
            self.__class__.__name__,
            profile.id,
            profile.name,
        )

    @property
    def id(self) -> AgentId:
        """Get the agent's unique identifier."""
        return self.profile.id

    @property
    def name(self) -> str:
        """Get the agent's name."""
        return self.profile.name

    @property
    def reasoning(self) -> ReasoningEngine:
        """Get or create the reasoning engine."""
        if self._reasoning is None:
            from ...cognitive.reasoning import ReasoningEngine
            self._reasoning = ReasoningEngine(self._llm_client)
        return self._reasoning

    @property
    def memory(self) -> MemorySystem | None:
        """Get the memory system."""
        return self._memory

    @abstractmethod
    async def execute(self, task: Task) -> TaskResult:
        """Execute a task and return the result.

        This is the main entry point for task execution. Subclasses must
        implement this method to define their specific behavior.

        Args:
            task: The task to execute

        Returns:
            TaskResult containing the execution outcome

        Raises:
            NotImplementedError: If not implemented by subclass
        """
        raise NotImplementedError

    async def _think(self, problem: str, context: dict[str, Any] | None = None) -> str:
        """Use chain-of-thought reasoning to solve a problem.

        Args:
            problem: The problem to solve
            context: Optional context information

        Returns:
            The reasoning conclusion
        """
        result = await self.reasoning.chain_of_thought(problem, context)
        return result.conclusion

    async def _remember(self, content: str, memory_type: str = "episodic") -> None:
        """Store information in memory.

        Args:
            content: Content to remember
            memory_type: Type of memory (episodic, semantic, procedural)
        """
        if self._memory is not None:
            self._memory.store(content, memory_type=memory_type)

    async def _recall(
        self,
        query: str,
        limit: int = 5,
    ) -> list[str]:
        """Recall relevant information from memory.

        Args:
            query: Query to search for
            limit: Maximum number of results

        Returns:
            List of relevant memory contents
        """
        if self._memory is None:
            return []

        memory_query = MemoryQuery(query=query, limit=limit)
        results = self._memory.retrieve(memory_query)
        return [item.content for item, _score in results]

    def _create_artifact(
        self,
        name: str,
        content: str,
        artifact_type: ArtifactType,
        language: str | None = None,
    ) -> Artifact:
        """Create an artifact from the agent's work.

        Args:
            name: Artifact name
            content: Artifact content
            artifact_type: Type of artifact
            language: Optional programming language

        Returns:
            Created Artifact instance
        """
        return Artifact(
            name=name,
            content=content,
            type=artifact_type,
            language=language,
            created_by=self.id,
        )


# =============================================================================
# Fullstack Engineer Agent
# =============================================================================


class FullstackEngineerAgent(BaseExpertAgent):
    """Fullstack engineer agent for end-to-end development.

    Excels at designing and implementing complete features spanning
    frontend, backend, and database layers. Capable of rapid prototyping
    and service integration.

    Attributes:
        role: AgentRole.FULLSTACK_ENGINEER
        default_frontend: Default frontend framework
        default_backend: Default backend framework
        default_database: Default database type

    Capabilities:
        - End-to-end feature development
        - API design and implementation
        - Database schema design
        - Rapid prototyping
        - Service integration

    Example:
        >>> agent = FullstackEngineerAgent(profile, llm_client, memory)
        >>> design = await agent.design_feature(feature_spec)
        >>> api = await agent.implement_api(endpoint_spec)
    """

    role = AgentRole.FULLSTACK_ENGINEER

    def __init__(
        self,
        profile: AgentProfile,
        llm_client: LLMClientProtocol,
        memory: MemorySystem | None = None,
        *,
        default_frontend: FrontendFramework = FrontendFramework.REACT,
        default_backend: BackendFramework = BackendFramework.FASTAPI,
        default_database: DatabaseType = DatabaseType.POSTGRESQL,
    ):
        """Initialize the fullstack engineer agent.

        Args:
            profile: Agent configuration and capabilities
            llm_client: LLM client for text generation
            memory: Optional memory system for context retention
            default_frontend: Default frontend framework preference
            default_backend: Default backend framework preference
            default_database: Default database type preference
        """
        super().__init__(profile, llm_client, memory)

        self.default_frontend = default_frontend
        self.default_backend = default_backend
        self.default_database = default_database

        logger.info(
            "Fullstack engineer initialized with stack: %s/%s/%s",
            default_frontend.value,
            default_backend.value,
            default_database.value,
        )

    async def execute(self, task: Task) -> TaskResult:
        """Execute a fullstack development task.

        Analyzes the task requirements and delegates to appropriate
        specialized methods (design_feature, implement_api, etc.).

        Args:
            task: The task to execute

        Returns:
            TaskResult containing execution outcome and artifacts
        """
        start_time = datetime.now()
        task.status = TaskStatus.IN_PROGRESS
        task.started_at = start_time

        logger.info("Executing task: %s", task.title)

        try:
            # Analyze task type and requirements
            task_type = await self._analyze_task_type(task)

            artifacts: list[Artifact] = []
            reasoning_steps: list[ReasoningStep] = []

            # Execute based on task type
            if task_type == "feature":
                spec = self._extract_feature_spec(task)
                design = await self.design_feature(spec)
                artifacts.append(self._create_artifact(
                    name=f"feature_design_{design.name}",
                    content=self._serialize_design(design),
                    artifact_type=ArtifactType.DESIGN_DOC,
                ))

            elif task_type == "api":
                endpoint_spec = self._extract_endpoint_spec(task)
                impl = await self.implement_api(endpoint_spec)
                for file_path, code in impl.code.items():
                    artifacts.append(self._create_artifact(
                        name=file_path,
                        content=code,
                        artifact_type=ArtifactType.SOURCE_CODE,
                        language="python",
                    ))

            elif task_type == "database":
                entities = self._extract_entities(task)
                schema = await self.design_database(entities)
                artifacts.append(self._create_artifact(
                    name="database_schema",
                    content=self._serialize_schema(schema),
                    artifact_type=ArtifactType.DESIGN_DOC,
                ))

            elif task_type == "prototype":
                requirements = self._extract_requirements(task)
                prototype = await self.create_prototype(requirements)
                for file_path, content in prototype.files.items():
                    lang = self._detect_language(file_path)
                    artifacts.append(self._create_artifact(
                        name=file_path,
                        content=content,
                        artifact_type=ArtifactType.SOURCE_CODE,
                        language=lang,
                    ))

            elif task_type == "integration":
                services = self._extract_services(task)
                plan = await self.integrate_services(services)
                artifacts.append(self._create_artifact(
                    name="integration_plan",
                    content=self._serialize_plan(plan),
                    artifact_type=ArtifactType.DESIGN_DOC,
                ))

            else:
                # General fullstack task
                result_content = await self._think(
                    f"Execute fullstack task: {task.title}\n\n"
                    f"Description: {task.description}",
                    context=task.context,
                )
                artifacts.append(self._create_artifact(
                    name="task_result",
                    content=result_content,
                    artifact_type=ArtifactType.DESIGN_DOC,
                ))

            # Store in memory
            await self._remember(
                f"Completed task: {task.title} with {len(artifacts)} artifacts",
                memory_type="episodic",
            )

            # Calculate execution time
            execution_time = (datetime.now() - start_time).total_seconds()

            task.status = TaskStatus.COMPLETED
            task.completed_at = datetime.now()

            return TaskResult(
                task_id=task.id,
                success=True,
                artifacts=artifacts,
                confidence_score=0.85,
                quality_score=0.80,
                execution_time_seconds=execution_time,
                tools_used=[ToolType.CODE_EXECUTOR, ToolType.FILE_SYSTEM],
            )

        except Exception as e:
            logger.error("Task execution failed: %s", str(e))
            task.status = TaskStatus.FAILED

            return TaskResult(
                task_id=task.id,
                success=False,
                error_message=str(e),
                error_type=type(e).__name__,
                execution_time_seconds=(datetime.now() - start_time).total_seconds(),
            )

    async def design_feature(self, spec: FeatureSpec) -> FeatureDesign:
        """Design a complete feature from specification.

        Creates a comprehensive design covering frontend, backend, and
        database components.

        Args:
            spec: Feature specification

        Returns:
            Complete feature design
        """
        logger.info("Designing feature: %s", spec.name)

        # Use reasoning to create the design
        design_prompt = f"""
        Design a complete feature based on this specification:

        Name: {spec.name}
        Description: {spec.description}
        User Stories: {spec.user_stories}
        Acceptance Criteria: {spec.acceptance_criteria}

        Create a design covering:
        1. Frontend components and state management
        2. Backend services and API endpoints
        3. Database schema and relationships
        """

        design_result = await self._think(design_prompt)

        # Build the design structure
        design = FeatureDesign(
            feature_spec_id=spec.id,
            name=spec.name,
            frontend={
                "framework": self.default_frontend.value,
                "components": self._extract_frontend_components(design_result),
                "state_management": "zustand" if self.default_frontend == FrontendFramework.REACT else "pinia",
                "routing": self._extract_routes(design_result),
            },
            backend={
                "framework": self.default_backend.value,
                "services": self._extract_services_from_design(design_result),
                "middleware": ["authentication", "logging", "error_handling"],
            },
            database={
                "type": self.default_database.value,
                "tables": self._extract_tables(design_result),
                "indexes": self._extract_indexes(design_result),
            },
            api_endpoints=self._extract_api_endpoints(design_result),
            architecture_notes=[
                "Use repository pattern for data access",
                "Implement caching for frequently accessed data",
                "Use event-driven architecture for async operations",
            ],
            dependencies={
                "frontend": self._get_frontend_deps(),
                "backend": self._get_backend_deps(),
            },
            estimated_effort=spec.estimated_effort * 1.2,  # Add 20% buffer
        )

        logger.info("Feature design completed: %s", design.id)
        return design

    async def implement_api(self, endpoint: EndpointSpec) -> APIImplementation:
        """Implement an API endpoint from specification.

        Generates code, tests, and documentation for the endpoint.

        Args:
            endpoint: Endpoint specification

        Returns:
            API implementation with code and tests
        """
        logger.info("Implementing API endpoint: %s %s", endpoint.method, endpoint.path)

        # Generate implementation code
        impl_prompt = f"""
        Implement a {self.default_backend.value} API endpoint:

        Method: {endpoint.method}
        Path: {endpoint.path}
        Summary: {endpoint.summary}
        Request Body: {endpoint.request_body}
        Response Schema: {endpoint.response_schema}
        """

        impl_result = await self._think(impl_prompt)

        # Generate the implementation
        impl = APIImplementation(
            endpoint_spec_id=endpoint.id,
            framework=self.default_backend,
            code=self._generate_endpoint_code(endpoint),
            tests=self._generate_endpoint_tests(endpoint),
            documentation={
                "openapi": self._generate_openapi_spec(endpoint),
            },
            dependencies=self._get_backend_deps(),
            quality_score=0.85,
        )

        logger.info("API implementation completed: %s", impl.id)
        return impl

    async def design_database(self, entities: list[Entity]) -> DatabaseSchema:
        """Design database schema from entity definitions.

        Creates a complete schema with migrations and indexes.

        Args:
            entities: List of entity definitions

        Returns:
            Complete database schema
        """
        logger.info("Designing database schema for %d entities", len(entities))

        schema = DatabaseSchema(
            database_type=self.default_database,
            entities=entities,
            migrations=self._generate_migrations(entities),
            indexes=self._generate_indexes(entities),
            diagram=self._generate_schema_diagram(entities),
            performance_notes=[
                "Add composite indexes for common query patterns",
                "Consider partitioning for large tables",
                "Use connection pooling for production",
            ],
        )

        logger.info("Database schema completed: %s", schema.id)
        return schema

    async def create_prototype(self, requirements: list[str]) -> Prototype:
        """Create a rapid prototype from requirements.

        Generates a minimal viable implementation for quick validation.

        Args:
            requirements: List of requirements for the prototype

        Returns:
            Prototype with generated files
        """
        logger.info("Creating prototype for %d requirements", len(requirements))

        prototype = Prototype(
            name="rapid_prototype",
            description="Minimal viable implementation",
            tech_stack={
                "frontend": self.default_frontend.value,
                "backend": self.default_backend.value,
                "database": "sqlite",  # Use SQLite for prototypes
            },
            files=self._generate_prototype_files(requirements),
            setup_instructions=[
                "pip install -r requirements.txt",
                "npm install",
                "python manage.py migrate",
                "npm run dev",
            ],
            limitations=[
                "No authentication implemented",
                "In-memory database (data not persisted)",
                "Minimal error handling",
            ],
            next_steps=[
                "Add authentication and authorization",
                "Migrate to production database",
                "Implement comprehensive error handling",
                "Add unit and integration tests",
            ],
        )

        logger.info("Prototype created: %s", prototype.id)
        return prototype

    async def integrate_services(
        self,
        services: list[ServiceSpec],
    ) -> IntegrationPlan:
        """Create a plan for integrating multiple services.

        Designs the integration architecture with error handling and monitoring.

        Args:
            services: List of services to integrate

        Returns:
            Complete integration plan
        """
        logger.info("Creating integration plan for %d services", len(services))

        plan = IntegrationPlan(
            services=services,
            integration_patterns=["circuit_breaker", "retry", "fallback"],
            data_flow=self._generate_data_flow(services),
            error_handling={
                "strategy": "graceful_degradation",
                "fallback": "cached_response",
                "logging": "structured",
            },
            retry_strategy={
                "max_retries": 3,
                "backoff": "exponential",
                "initial_delay_ms": 100,
            },
            circuit_breaker={
                "failure_threshold": 5,
                "reset_timeout_ms": 30000,
            },
            monitoring={
                "metrics": ["latency", "error_rate", "throughput"],
                "alerts": ["high_error_rate", "high_latency"],
            },
            security=[
                "Use TLS for all communications",
                "Implement API key rotation",
                "Validate all inputs",
            ],
            implementation_order=[s.name for s in services],
            estimated_effort=len(services) * 4.0,  # 4 hours per service
        )

        logger.info("Integration plan created: %s", plan.id)
        return plan

    # =========================================================================
    # Private Helper Methods
    # =========================================================================

    async def _analyze_task_type(self, task: Task) -> str:
        """Analyze task to determine its type."""
        title_lower = task.title.lower()
        desc_lower = task.description.lower()

        if any(kw in title_lower for kw in ["feature", "implement"]):
            return "feature"
        elif any(kw in title_lower for kw in ["api", "endpoint"]):
            return "api"
        elif any(kw in title_lower for kw in ["database", "schema", "table"]):
            return "database"
        elif any(kw in title_lower for kw in ["prototype", "mvp", "poc"]):
            return "prototype"
        elif any(kw in title_lower for kw in ["integrate", "integration"]):
            return "integration"

        return "general"

    def _extract_feature_spec(self, task: Task) -> FeatureSpec:
        """Extract feature specification from task."""
        return FeatureSpec(
            name=task.title,
            description=task.description,
            user_stories=task.context.get("user_stories", []),
            acceptance_criteria=task.context.get("acceptance_criteria", []),
        )

    def _extract_endpoint_spec(self, task: Task) -> EndpointSpec:
        """Extract endpoint specification from task.

        Extracts a complete endpoint specification from the task context,
        including HTTP method, path, request/response schemas, parameters,
        authentication requirements, and API documentation metadata.

        Args:
            task: The task containing endpoint specification in its context.

        Returns:
            EndpointSpec: A fully populated endpoint specification.
        """
        context = task.context

        # Extract path parameters from the path pattern (e.g., /users/{id})
        path = context.get("path", "/api/resource")
        path_params = context.get("path_params", [])
        if not path_params:
            # Auto-extract path params from path pattern
            import re
            param_matches = re.findall(r"\{(\w+)\}", path)
            path_params = [
                {"name": param, "type": "str", "description": f"Path parameter: {param}"}
                for param in param_matches
            ]

        # Extract query parameters
        query_params = context.get("query_params", [])

        # Extract request body schema
        request_body = context.get("request_body")
        if request_body is None and context.get("method", "GET") in ("POST", "PUT", "PATCH"):
            # Generate default request body schema from entity if available
            entity = context.get("entity")
            if entity and isinstance(entity, dict):
                request_body = {
                    "properties": entity.get("fields", {}),
                    "required": entity.get("required_fields", []),
                }

        # Extract response schema
        response_schema = context.get("response_schema", {})
        if not response_schema:
            # Generate default response schema
            response_schema = {
                "properties": {
                    "success": {"type": "boolean", "description": "Operation success status"},
                    "data": {"type": "object", "description": "Response data"},
                    "message": {"type": "string", "description": "Response message"},
                },
                "required": ["success"],
            }

        # Extract headers
        headers = context.get("headers", [])

        # Extract authentication requirement
        auth_required = context.get("auth_required", True)

        # Extract rate limit configuration
        rate_limit = context.get("rate_limit")
        if rate_limit is None and context.get("is_public", False):
            # Apply default rate limit for public endpoints
            rate_limit = {"requests_per_minute": 60, "burst": 10}

        # Extract API documentation tags
        tags = context.get("tags", [])
        if not tags:
            # Auto-generate tags from path
            path_parts = [p for p in path.split("/") if p and not p.startswith("{")]
            if path_parts:
                tags = [path_parts[-1].replace("_", " ").title()]

        return EndpointSpec(
            method=context.get("method", "GET"),
            path=path,
            summary=task.title,
            description=task.description,
            request_body=request_body,
            response_schema=response_schema,
            query_params=query_params,
            path_params=path_params,
            headers=headers,
            auth_required=auth_required,
            rate_limit=rate_limit,
            tags=tags,
        )

    def _extract_entities(self, task: Task) -> list[Entity]:
        """Extract entity definitions from task."""
        entities_data = task.context.get("entities", [])
        return [Entity(**e) if isinstance(e, dict) else e for e in entities_data]

    def _extract_requirements(self, task: Task) -> list[str]:
        """Extract requirements from task."""
        return task.context.get("requirements", [task.description])

    def _extract_services(self, task: Task) -> list[ServiceSpec]:
        """Extract service specifications from task."""
        services_data = task.context.get("services", [])
        return [ServiceSpec(**s) if isinstance(s, dict) else s for s in services_data]

    def _serialize_design(self, design: FeatureDesign) -> str:
        """Serialize feature design to string."""
        import json
        return json.dumps({
            "id": design.id,
            "name": design.name,
            "frontend": design.frontend,
            "backend": design.backend,
            "database": design.database,
            "api_endpoints": design.api_endpoints,
        }, indent=2)

    def _serialize_schema(self, schema: DatabaseSchema) -> str:
        """Serialize database schema to string."""
        import json
        return json.dumps({
            "id": schema.id,
            "database_type": schema.database_type.value,
            "entities": [{"name": e.name, "fields": e.fields} for e in schema.entities],
            "diagram": schema.diagram,
        }, indent=2)

    def _serialize_plan(self, plan: IntegrationPlan) -> str:
        """Serialize integration plan to string."""
        import json
        return json.dumps({
            "id": plan.id,
            "services": [s.name for s in plan.services],
            "patterns": plan.integration_patterns,
            "estimated_effort": plan.estimated_effort,
        }, indent=2)

    def _detect_language(self, file_path: str) -> str | None:
        """Detect programming language from file path."""
        if file_path.endswith(".py"):
            return "python"
        elif file_path.endswith((".js", ".jsx")):
            return "javascript"
        elif file_path.endswith((".ts", ".tsx")):
            return "typescript"
        elif file_path.endswith(".sql"):
            return "sql"
        return None

    def _extract_frontend_components(self, design_result: str) -> list[str]:
        """Extract frontend component names from design."""
        return ["Header", "Footer", "MainContent", "Sidebar"]

    def _extract_routes(self, design_result: str) -> list[dict[str, str]]:
        """Extract routes from design."""
        return [
            {"path": "/", "component": "Home"},
            {"path": "/dashboard", "component": "Dashboard"},
        ]

    def _extract_services_from_design(self, design_result: str) -> list[str]:
        """Extract backend services from design."""
        return ["UserService", "AuthService", "DataService"]

    def _extract_tables(self, design_result: str) -> list[str]:
        """Extract table names from design."""
        return ["users", "sessions", "data"]

    def _extract_indexes(self, design_result: str) -> list[str]:
        """Extract index names from design."""
        return ["idx_users_email", "idx_sessions_user_id"]

    def _extract_api_endpoints(self, design_result: str) -> list[dict[str, Any]]:
        """Extract API endpoints from design."""
        return [
            {"method": "GET", "path": "/api/users"},
            {"method": "POST", "path": "/api/users"},
            {"method": "GET", "path": "/api/users/{id}"},
        ]

    def _get_frontend_deps(self) -> list[str]:
        """Get frontend dependencies based on framework."""
        deps = {
            FrontendFramework.REACT: ["react", "react-dom", "react-router-dom", "zustand"],
            FrontendFramework.VUE: ["vue", "vue-router", "pinia"],
            FrontendFramework.NEXTJS: ["next", "react", "react-dom"],
        }
        return deps.get(self.default_frontend, [])

    def _get_backend_deps(self) -> list[str]:
        """Get backend dependencies based on framework."""
        deps = {
            BackendFramework.FASTAPI: ["fastapi", "uvicorn", "pydantic", "sqlalchemy"],
            BackendFramework.DJANGO: ["django", "djangorestframework", "django-cors-headers"],
            BackendFramework.EXPRESS: ["express", "cors", "helmet"],
        }
        return deps.get(self.default_backend, [])

    def _generate_endpoint_code(self, endpoint: EndpointSpec) -> dict[str, str]:
        """Generate endpoint code."""
        if self.default_backend == BackendFramework.FASTAPI:
            return self._generate_fastapi_endpoint(endpoint)
        return {"endpoint.py": "# Generated endpoint code"}

    def _generate_fastapi_endpoint(self, endpoint: EndpointSpec) -> dict[str, str]:
        """Generate FastAPI endpoint code."""
        method_lower = endpoint.method.lower()
        path_name = endpoint.path.replace("/", "_").replace("{", "").replace("}", "").strip("_")
        func_name = f"{method_lower}_{path_name}".strip("_")

        # Build imports
        imports = [
            "from fastapi import APIRouter, HTTPException, Depends, Query, Path",
            "from pydantic import BaseModel, Field",
            "from typing import Any",
        ]

        # Build request/response models
        models = []
        if endpoint.request_body:
            models.append(self._generate_pydantic_model(
                f"{func_name.title().replace('_', '')}Request",
                endpoint.request_body
            ))
        if endpoint.response_schema:
            models.append(self._generate_pydantic_model(
                f"{func_name.title().replace('_', '')}Response",
                endpoint.response_schema
            ))

        # Build function signature parts
        params = []

        # Path parameters
        for param in endpoint.path_params:
            param_name = param.get("name", "id")
            param_type = param.get("type", "str")
            params.append(f'{param_name}: {param_type} = Path(..., description="{param.get("description", "")}")')

        # Query parameters
        for param in endpoint.query_params:
            param_name = param.get("name", "param")
            param_type = param.get("type", "str")
            required = param.get("required", False)
            default = "..." if required else "None"
            params.append(f'{param_name}: {param_type} | None = Query({default}, description="{param.get("description", "")}")')

        # Request body parameter
        request_body_param = ""
        if endpoint.request_body and method_lower in ("post", "put", "patch"):
            request_body_param = f"body: {func_name.title().replace('_', '')}Request"
            params.append(request_body_param)

        # Authentication dependency
        if endpoint.auth_required:
            imports.append("# from app.auth import get_current_user  # Uncomment when auth is configured")
            params.append("# current_user = Depends(get_current_user)")

        # Build function signature
        params_str = ", ".join(p for p in params if not p.startswith("#"))
        comments_in_params = [p for p in params if p.startswith("#")]

        # Build response annotation
        response_type = f"{func_name.title().replace('_', '')}Response" if endpoint.response_schema else "dict[str, Any]"

        # Generate code
        code_parts = [
            f'"""Auto-generated endpoint for {endpoint.path}."""',
            "",
            "\n".join(imports),
            "",
            "router = APIRouter()",
            "",
        ]

        # Add models
        if models:
            code_parts.extend(models)
            code_parts.append("")

        # Add endpoint function
        tags_str = f", tags={endpoint.tags}" if endpoint.tags else ""
        code_parts.append(f'@router.{method_lower}("{endpoint.path}"{tags_str})')
        code_parts.append(f"async def {func_name}({params_str}) -> {response_type}:")
        code_parts.append(f'    """{endpoint.summary or "Handle " + endpoint.method + " request."}')
        if endpoint.description:
            code_parts.append(f"")
            code_parts.append(f"    {endpoint.description}")
        code_parts.append(f'    """')

        # Add auth comment if needed
        for comment in comments_in_params:
            code_parts.append(f"    {comment}")

        # Add implementation stub based on method
        if method_lower == "get":
            code_parts.append("    # Retrieve and return resource(s)")
            code_parts.append('    return {"message": "Success", "data": None}')
        elif method_lower == "post":
            code_parts.append("    # Create new resource")
            code_parts.append('    return {"message": "Created", "data": body.model_dump() if body else None}')
        elif method_lower == "put" or method_lower == "patch":
            code_parts.append("    # Update existing resource")
            code_parts.append('    return {"message": "Updated", "data": body.model_dump() if body else None}')
        elif method_lower == "delete":
            code_parts.append("    # Delete resource")
            code_parts.append('    return {"message": "Deleted"}')
        else:
            code_parts.append('    return {"message": "Success"}')

        code_parts.append("")

        code = "\n".join(code_parts)
        return {f"routes/{path_name}.py": code}

    def _generate_pydantic_model(self, name: str, schema: dict[str, Any]) -> str:
        """Generate a Pydantic model from schema definition."""
        fields = []
        properties = schema.get("properties", schema)
        required_fields = schema.get("required", [])

        for field_name, field_def in properties.items():
            if isinstance(field_def, dict):
                field_type = self._map_schema_type(field_def.get("type", "str"))
                description = field_def.get("description", "")
                is_required = field_name in required_fields

                if is_required:
                    fields.append(f'    {field_name}: {field_type} = Field(..., description="{description}")')
                else:
                    fields.append(f'    {field_name}: {field_type} | None = Field(None, description="{description}")')
            else:
                fields.append(f"    {field_name}: Any = None")

        if not fields:
            fields.append("    pass")

        return f"class {name}(BaseModel):\n" + "\n".join(fields) + "\n"

    def _map_schema_type(self, schema_type: str) -> str:
        """Map JSON schema type to Python type."""
        type_map = {
            "string": "str",
            "integer": "int",
            "number": "float",
            "boolean": "bool",
            "array": "list",
            "object": "dict",
        }
        return type_map.get(schema_type, "Any")

    def _generate_endpoint_tests(self, endpoint: EndpointSpec) -> dict[str, str]:
        """Generate endpoint tests."""
        return {
            "test_endpoint.py": f'''"""Tests for {endpoint.path}."""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_{endpoint.method.lower()}_endpoint(client: AsyncClient):
    response = await client.{endpoint.method.lower()}("{endpoint.path}")
    assert response.status_code == 200
'''
        }

    def _generate_openapi_spec(self, endpoint: EndpointSpec) -> dict[str, Any]:
        """Generate OpenAPI specification for endpoint."""
        return {
            "paths": {
                endpoint.path: {
                    endpoint.method.lower(): {
                        "summary": endpoint.summary,
                        "description": endpoint.description,
                        "responses": {
                            "200": {"description": "Successful response"},
                        },
                    }
                }
            }
        }

    def _generate_migrations(self, entities: list[Entity]) -> list[dict[str, str]]:
        """Generate database migrations."""
        migrations = []
        for i, entity in enumerate(entities, 1):
            migrations.append({
                "version": f"00{i}",
                "name": f"create_{entity.name}",
                "up_sql": f"CREATE TABLE {entity.name} (...);",
                "down_sql": f"DROP TABLE {entity.name};",
            })
        return migrations

    def _generate_indexes(self, entities: list[Entity]) -> list[dict[str, Any]]:
        """Generate database indexes."""
        indexes = []
        for entity in entities:
            for idx in entity.indexes:
                indexes.append(idx)
        return indexes

    def _generate_schema_diagram(self, entities: list[Entity]) -> str:
        """Generate mermaid diagram for schema."""
        lines = ["erDiagram"]
        for entity in entities:
            lines.append(f"    {entity.name} {{")
            for field in entity.fields[:3]:  # Limit fields for brevity
                lines.append(f"        string {field.get('name', 'field')}")
            lines.append("    }")
        return "\n".join(lines)

    def _generate_prototype_files(self, requirements: list[str]) -> dict[str, str]:
        """Generate prototype files."""
        return {
            "main.py": "# Prototype main entry point\n",
            "requirements.txt": "fastapi\nuvicorn\n",
            "frontend/index.html": "<!DOCTYPE html><html>...</html>",
        }

    def _generate_data_flow(self, services: list[ServiceSpec]) -> str:
        """Generate data flow diagram."""
        lines = ["graph LR"]
        for i, service in enumerate(services):
            if i < len(services) - 1:
                lines.append(f"    {service.name} --> {services[i + 1].name}")
        return "\n".join(lines)


# =============================================================================
# Exports
# =============================================================================

__all__ = [
    # Enums
    "FrontendFramework",
    "BackendFramework",
    "DatabaseType",
    "APIStyle",
    # Specifications
    "FeatureSpec",
    "EndpointSpec",
    "Entity",
    "ServiceSpec",
    # Outputs
    "FeatureDesign",
    "APIImplementation",
    "DatabaseSchema",
    "Prototype",
    "IntegrationPlan",
    # Agents
    "BaseExpertAgent",
    "FullstackEngineerAgent",
]
