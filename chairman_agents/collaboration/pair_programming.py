"""Pair Programming Module for Chairman Agents.

This module implements a pair programming system that enables two agents
to collaborate on tasks using the driver/navigator pattern. The driver
writes code while the navigator reviews and provides suggestions in real-time.

Key Features:
    - Role-based collaboration (driver/navigator)
    - Automatic role switching based on time intervals
    - Message-based communication between paired agents
    - Session management and artifact tracking
    - Comprehensive result reporting

Classes:
    PairMessage: Message exchanged during pair programming session
    PairSession: Active pair programming session state
    PairResult: Result of a completed pair programming session
    PairProgrammingSystem: Main system for managing pair programming sessions

Example:
    >>> system = PairProgrammingSystem(switch_interval=300)
    >>> session = await system.start_session(driver, navigator, task)
    >>> await system.suggest(session, navigator.id, "Consider using a factory pattern")
    >>> await system.respond(session, driver.id, "Good idea, implementing now")
    >>> result = await system.end_session(session)
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING, Protocol, runtime_checkable

from ..core.types import (
    AgentId,
    Artifact,
    Task,
    TaskStatus,
    generate_id,
)

if TYPE_CHECKING:
    from typing import Any

# =============================================================================
# Logging Configuration
# =============================================================================

logger = logging.getLogger(__name__)


# =============================================================================
# Enums
# =============================================================================


class PairMessageType(Enum):
    """Types of messages exchanged during pair programming.

    Categories:
        - Communication: suggestion, question, response
        - Decisions: approval, concern, rejection
        - Session: role_switch, session_start, session_end
    """

    # Communication
    SUGGESTION = "suggestion"
    """Suggestion for code improvement or approach"""

    QUESTION = "question"
    """Question about implementation or design"""

    RESPONSE = "response"
    """Response to a question or suggestion"""

    # Decisions
    APPROVAL = "approval"
    """Approval of code or approach"""

    CONCERN = "concern"
    """Concern about implementation"""

    REJECTION = "rejection"
    """Rejection of a suggestion"""

    # Session Management
    ROLE_SWITCH = "role_switch"
    """Notification of role switch"""

    SESSION_START = "session_start"
    """Session start notification"""

    SESSION_END = "session_end"
    """Session end notification"""


class PairRole(Enum):
    """Roles in pair programming."""

    DRIVER = "driver"
    """Driver - actively writes code"""

    NAVIGATOR = "navigator"
    """Navigator - reviews and guides"""


# =============================================================================
# Protocol for Agent Interface
# =============================================================================


@runtime_checkable
class BaseAgent(Protocol):
    """Protocol defining the minimal interface required for pair programming.

    Agents participating in pair programming must implement this interface.
    """

    @property
    def id(self) -> AgentId:
        """Unique identifier for the agent."""
        ...

    @property
    def name(self) -> str:
        """Human-readable name of the agent."""
        ...

    async def receive_message(self, message: PairMessage) -> None:
        """Receive and process a pair programming message.

        Args:
            message: The message to process
        """
        ...


# =============================================================================
# Data Classes
# =============================================================================


@dataclass
class PairMessage:
    """Message exchanged during a pair programming session.

    Represents communication between driver and navigator during
    collaborative coding. Messages can be suggestions, questions,
    approvals, or concerns.

    Attributes:
        id: Unique message identifier
        sender: ID of the sending agent
        content: Message content/text
        message_type: Type of message (suggestion, question, etc.)
        timestamp: When the message was sent
        in_reply_to: ID of message this replies to (if any)
        code_reference: Optional code snippet being discussed
        line_numbers: Optional line number range reference
        metadata: Additional message metadata

    Example:
        >>> msg = PairMessage(
        ...     sender="agent_001",
        ...     content="Consider extracting this logic into a helper function",
        ...     message_type="suggestion"
        ... )
    """

    id: str = field(default_factory=lambda: generate_id("pair_msg"))
    """Unique message identifier"""

    sender: AgentId = ""
    """ID of the sending agent"""

    content: str = ""
    """Message content/text"""

    message_type: str = "suggestion"
    """Type of message: suggestion, question, approval, concern"""

    timestamp: datetime = field(default_factory=datetime.now)
    """When the message was sent"""

    in_reply_to: str | None = None
    """ID of message this is replying to"""

    code_reference: str | None = None
    """Optional code snippet being discussed"""

    line_numbers: tuple[int, int] | None = None
    """Optional (start_line, end_line) reference"""

    metadata: dict[str, Any] = field(default_factory=dict)
    """Additional message metadata"""


@dataclass
class PairSession:
    """Active pair programming session state.

    Tracks the state of an ongoing pair programming session including
    role assignments, messages exchanged, and artifacts produced.

    Attributes:
        id: Unique session identifier
        driver: ID of current driver (coding agent)
        navigator: ID of current navigator (reviewing agent)
        task: The task being worked on
        started_at: Session start timestamp
        artifacts: Artifacts produced during session
        messages: Messages exchanged during session
        role_switches: Number of role switches performed
        last_switch_at: Timestamp of last role switch
        is_active: Whether session is currently active
        current_file: Currently active file being edited
        paused_at: Timestamp if session is paused

    Example:
        >>> session = PairSession(
        ...     driver="agent_001",
        ...     navigator="agent_002",
        ...     task=my_task
        ... )
    """

    id: str = field(default_factory=lambda: generate_id("pair_session"))
    """Unique session identifier"""

    driver: AgentId = ""
    """ID of current driver (actively coding)"""

    navigator: AgentId = ""
    """ID of current navigator (reviewing/guiding)"""

    task: Task = field(default_factory=Task)
    """The task being worked on"""

    started_at: datetime = field(default_factory=datetime.now)
    """Session start timestamp"""

    artifacts: list[Artifact] = field(default_factory=list)
    """Artifacts produced during the session"""

    messages: list[PairMessage] = field(default_factory=list)
    """Messages exchanged during the session"""

    role_switches: int = 0
    """Number of times roles have been switched"""

    last_switch_at: datetime | None = None
    """Timestamp of last role switch"""

    is_active: bool = True
    """Whether the session is currently active"""

    current_file: str | None = None
    """Currently active file being edited"""

    paused_at: datetime | None = None
    """Timestamp if session is paused (None if not paused)"""

    def get_driver_messages(self) -> list[PairMessage]:
        """Get all messages sent by the current driver.

        Returns:
            List of messages from the driver
        """
        return [m for m in self.messages if m.sender == self.driver]

    def get_navigator_messages(self) -> list[PairMessage]:
        """Get all messages sent by the current navigator.

        Returns:
            List of messages from the navigator
        """
        return [m for m in self.messages if m.sender == self.navigator]

    def get_suggestions(self) -> list[PairMessage]:
        """Get all suggestion messages.

        Returns:
            List of suggestion messages
        """
        return [m for m in self.messages if m.message_type == "suggestion"]

    def get_concerns(self) -> list[PairMessage]:
        """Get all concern messages.

        Returns:
            List of concern messages
        """
        return [m for m in self.messages if m.message_type == "concern"]


@dataclass
class PairResult:
    """Result of a completed pair programming session.

    Contains summary information about the pair programming session
    including artifacts produced, statistics, and quality metrics.

    Attributes:
        session_id: ID of the completed session
        success: Whether the session achieved its goals
        artifacts: Artifacts produced during the session
        total_switches: Total number of role switches
        duration_seconds: Total session duration in seconds
        summary: Human-readable summary of the session
        driver_contributions: Number of contributions by final driver
        navigator_contributions: Number of contributions by final navigator
        suggestions_accepted: Number of suggestions that were accepted
        concerns_raised: Number of concerns raised
        concerns_resolved: Number of concerns that were resolved
        quality_score: Overall quality score (0.0-1.0)
        collaboration_score: Collaboration effectiveness score (0.0-1.0)

    Example:
        >>> result = PairResult(
        ...     session_id="pair_session_abc123",
        ...     success=True,
        ...     total_switches=3,
        ...     duration_seconds=1800.0,
        ...     summary="Successfully implemented feature X"
        ... )
    """

    session_id: str = ""
    """ID of the completed session"""

    success: bool = False
    """Whether the session achieved its goals"""

    artifacts: list[Artifact] = field(default_factory=list)
    """Artifacts produced during the session"""

    total_switches: int = 0
    """Total number of role switches"""

    duration_seconds: float = 0.0
    """Total session duration in seconds"""

    summary: str = ""
    """Human-readable summary of the session"""

    # Contribution Metrics
    driver_contributions: int = 0
    """Number of contributions by final driver role"""

    navigator_contributions: int = 0
    """Number of contributions by final navigator role"""

    # Collaboration Metrics
    suggestions_accepted: int = 0
    """Number of suggestions that were accepted"""

    concerns_raised: int = 0
    """Number of concerns raised during session"""

    concerns_resolved: int = 0
    """Number of concerns that were resolved"""

    # Quality Metrics
    quality_score: float = 0.0
    """Overall quality score (0.0-1.0)"""

    collaboration_score: float = 0.0
    """Collaboration effectiveness score (0.0-1.0)"""

    # Participants
    final_driver: AgentId = ""
    """ID of the driver at session end"""

    final_navigator: AgentId = ""
    """ID of the navigator at session end"""

    # Timing
    started_at: datetime | None = None
    """When the session started"""

    ended_at: datetime | None = None
    """When the session ended"""


# =============================================================================
# Main System Class
# =============================================================================


class PairProgrammingSystem:
    """System for managing pair programming sessions between agents.

    Implements the driver/navigator pair programming pattern where one
    agent writes code (driver) while another reviews and provides
    guidance (navigator). Supports automatic role switching.

    Attributes:
        active_sessions: Dictionary of currently active sessions
        switch_interval: Seconds between automatic role switches
        completed_sessions: List of completed session results

    Example:
        >>> system = PairProgrammingSystem(switch_interval=300)
        >>> session = await system.start_session(driver, navigator, task)
        >>> await system.suggest(session, navigator.id, "Use dependency injection")
        >>> result = await system.end_session(session)
    """

    def __init__(self, switch_interval: int = 300):
        """Initialize the pair programming system.

        Args:
            switch_interval: Seconds between automatic role switches.
                            Default is 300 seconds (5 minutes).
        """
        self.active_sessions: dict[str, PairSession] = {}
        self.switch_interval = switch_interval
        self.completed_sessions: list[PairResult] = []
        self._switch_tasks: dict[str, asyncio.Task[None]] = {}
        self._agents: dict[AgentId, BaseAgent] = {}

        logger.info(
            "PairProgrammingSystem initialized with switch_interval=%d seconds",
            switch_interval
        )

    async def start_session(
        self,
        driver: BaseAgent,
        navigator: BaseAgent,
        task: Task,
    ) -> PairSession:
        """Start a new pair programming session.

        Creates a new session with the specified driver and navigator
        agents working on the given task. Sets up automatic role
        switching if configured.

        Args:
            driver: Agent who will initially write code
            navigator: Agent who will initially review and guide
            task: The task to work on collaboratively

        Returns:
            The newly created PairSession

        Raises:
            ValueError: If driver and navigator are the same agent
            ValueError: If either agent is already in an active session

        Example:
            >>> session = await system.start_session(
            ...     driver=code_agent,
            ...     navigator=review_agent,
            ...     task=implementation_task
            ... )
        """
        # Validate agents are different
        if driver.id == navigator.id:
            raise ValueError("Driver and navigator must be different agents")

        # Check if agents are already in active sessions
        for session in self.active_sessions.values():
            if session.is_active:
                if driver.id in (session.driver, session.navigator):
                    raise ValueError(
                        f"Agent {driver.id} is already in an active session"
                    )
                if navigator.id in (session.driver, session.navigator):
                    raise ValueError(
                        f"Agent {navigator.id} is already in an active session"
                    )

        # Create the session
        session = PairSession(
            driver=driver.id,
            navigator=navigator.id,
            task=task,
            started_at=datetime.now(),
            last_switch_at=datetime.now(),
        )

        # Store agent references
        self._agents[driver.id] = driver
        self._agents[navigator.id] = navigator

        # Update task status
        task.status = TaskStatus.IN_PROGRESS

        # Store the session
        self.active_sessions[session.id] = session

        # Create start message
        start_message = PairMessage(
            sender=driver.id,
            content=f"Pair programming session started for task: {task.title}",
            message_type=PairMessageType.SESSION_START.value,
            metadata={
                "driver": driver.id,
                "navigator": navigator.id,
                "task_id": task.id,
            }
        )
        session.messages.append(start_message)

        # Start automatic role switch timer
        self._start_auto_switch_timer(session)

        logger.info(
            "Started pair programming session %s: driver=%s, navigator=%s, task=%s",
            session.id, driver.id, navigator.id, task.id
        )

        # Notify both agents
        await self._notify_agents(session, start_message)

        return session

    async def switch_roles(self, session: PairSession) -> None:
        """Switch driver and navigator roles.

        Exchanges the roles of the two participating agents. The
        current driver becomes the navigator and vice versa.

        Args:
            session: The session to switch roles in

        Raises:
            ValueError: If the session is not active

        Example:
            >>> await system.switch_roles(session)
            >>> print(f"New driver: {session.driver}")
        """
        if not session.is_active:
            raise ValueError("Cannot switch roles in an inactive session")

        # Swap roles
        old_driver = session.driver
        old_navigator = session.navigator
        session.driver = old_navigator
        session.navigator = old_driver

        # Update tracking
        session.role_switches += 1
        session.last_switch_at = datetime.now()

        # Create switch message
        switch_message = PairMessage(
            sender=session.driver,
            content=f"Roles switched: {session.driver} is now driving, "
                   f"{session.navigator} is now navigating",
            message_type=PairMessageType.ROLE_SWITCH.value,
            metadata={
                "previous_driver": old_driver,
                "previous_navigator": old_navigator,
                "new_driver": session.driver,
                "new_navigator": session.navigator,
                "switch_count": session.role_switches,
            }
        )
        session.messages.append(switch_message)

        logger.info(
            "Switched roles in session %s: new_driver=%s, new_navigator=%s "
            "(switch #%d)",
            session.id, session.driver, session.navigator, session.role_switches
        )

        # Notify both agents
        await self._notify_agents(session, switch_message)

        # Restart auto-switch timer
        self._start_auto_switch_timer(session)

    async def suggest(
        self,
        session: PairSession,
        agent_id: AgentId,
        suggestion: str,
        code_reference: str | None = None,
        line_numbers: tuple[int, int] | None = None,
    ) -> PairMessage:
        """Navigator provides a suggestion to the driver.

        Typically called by the navigator to suggest code changes,
        improvements, or alternative approaches to the driver.

        Args:
            session: The active pair programming session
            agent_id: ID of the agent making the suggestion
            suggestion: The suggestion content
            code_reference: Optional code snippet being discussed
            line_numbers: Optional line number range reference

        Returns:
            The created suggestion message

        Raises:
            ValueError: If the session is not active
            ValueError: If the agent is not in this session

        Example:
            >>> msg = await system.suggest(
            ...     session,
            ...     navigator.id,
            ...     "Consider using a context manager for resource cleanup"
            ... )
        """
        self._validate_session_and_agent(session, agent_id)

        message = PairMessage(
            sender=agent_id,
            content=suggestion,
            message_type=PairMessageType.SUGGESTION.value,
            code_reference=code_reference,
            line_numbers=line_numbers,
            metadata={
                "role": self._get_agent_role(session, agent_id).value,
            }
        )
        session.messages.append(message)

        logger.debug(
            "Suggestion in session %s from %s: %s",
            session.id, agent_id, suggestion[:50] + "..." if len(suggestion) > 50 else suggestion
        )

        # Notify the other agent
        await self._notify_other_agent(session, agent_id, message)

        return message

    async def respond(
        self,
        session: PairSession,
        agent_id: AgentId,
        response: str,
        in_reply_to: str | None = None,
    ) -> PairMessage:
        """Driver responds to a suggestion or question.

        Allows either agent to respond to messages from their partner.
        Can acknowledge suggestions, answer questions, or provide
        explanations.

        Args:
            session: The active pair programming session
            agent_id: ID of the responding agent
            response: The response content
            in_reply_to: Optional ID of message being replied to

        Returns:
            The created response message

        Raises:
            ValueError: If the session is not active
            ValueError: If the agent is not in this session

        Example:
            >>> msg = await system.respond(
            ...     session,
            ...     driver.id,
            ...     "Good point, I'll implement that pattern"
            ... )
        """
        self._validate_session_and_agent(session, agent_id)

        message = PairMessage(
            sender=agent_id,
            content=response,
            message_type=PairMessageType.RESPONSE.value,
            in_reply_to=in_reply_to,
            metadata={
                "role": self._get_agent_role(session, agent_id).value,
            }
        )
        session.messages.append(message)

        logger.debug(
            "Response in session %s from %s: %s",
            session.id, agent_id, response[:50] + "..." if len(response) > 50 else response
        )

        # Notify the other agent
        await self._notify_other_agent(session, agent_id, message)

        return message

    async def raise_concern(
        self,
        session: PairSession,
        agent_id: AgentId,
        concern: str,
        severity: str = "medium",
        code_reference: str | None = None,
    ) -> PairMessage:
        """Raise a concern about the current implementation.

        Allows either agent to raise concerns about code quality,
        potential bugs, security issues, or design problems.

        Args:
            session: The active pair programming session
            agent_id: ID of the agent raising the concern
            concern: Description of the concern
            severity: Severity level (low, medium, high, critical)
            code_reference: Optional code snippet causing concern

        Returns:
            The created concern message

        Raises:
            ValueError: If the session is not active
            ValueError: If the agent is not in this session
        """
        self._validate_session_and_agent(session, agent_id)

        message = PairMessage(
            sender=agent_id,
            content=concern,
            message_type=PairMessageType.CONCERN.value,
            code_reference=code_reference,
            metadata={
                "role": self._get_agent_role(session, agent_id).value,
                "severity": severity,
            }
        )
        session.messages.append(message)

        logger.info(
            "Concern raised in session %s by %s (severity=%s): %s",
            session.id, agent_id, severity, concern[:50] + "..." if len(concern) > 50 else concern
        )

        # Notify the other agent
        await self._notify_other_agent(session, agent_id, message)

        return message

    async def approve(
        self,
        session: PairSession,
        agent_id: AgentId,
        comment: str = "Approved",
    ) -> PairMessage:
        """Approve current code or approach.

        Typically called by the navigator to indicate approval of
        the driver's implementation.

        Args:
            session: The active pair programming session
            agent_id: ID of the approving agent
            comment: Optional approval comment

        Returns:
            The created approval message
        """
        self._validate_session_and_agent(session, agent_id)

        message = PairMessage(
            sender=agent_id,
            content=comment,
            message_type=PairMessageType.APPROVAL.value,
            metadata={
                "role": self._get_agent_role(session, agent_id).value,
            }
        )
        session.messages.append(message)

        logger.debug(
            "Approval in session %s from %s",
            session.id, agent_id
        )

        # Notify the other agent
        await self._notify_other_agent(session, agent_id, message)

        return message

    async def ask_question(
        self,
        session: PairSession,
        agent_id: AgentId,
        question: str,
        code_reference: str | None = None,
    ) -> PairMessage:
        """Ask a question about the implementation.

        Allows either agent to ask clarifying questions about
        code, design decisions, or requirements.

        Args:
            session: The active pair programming session
            agent_id: ID of the agent asking
            question: The question content
            code_reference: Optional code snippet being questioned

        Returns:
            The created question message
        """
        self._validate_session_and_agent(session, agent_id)

        message = PairMessage(
            sender=agent_id,
            content=question,
            message_type=PairMessageType.QUESTION.value,
            code_reference=code_reference,
            metadata={
                "role": self._get_agent_role(session, agent_id).value,
            }
        )
        session.messages.append(message)

        logger.debug(
            "Question in session %s from %s: %s",
            session.id, agent_id, question[:50] + "..." if len(question) > 50 else question
        )

        # Notify the other agent
        await self._notify_other_agent(session, agent_id, message)

        return message

    async def add_artifact(
        self,
        session: PairSession,
        artifact: Artifact,
    ) -> None:
        """Add an artifact produced during the session.

        Records artifacts (code files, documents, etc.) created
        during the pair programming session.

        Args:
            session: The active pair programming session
            artifact: The artifact to add
        """
        if not session.is_active:
            raise ValueError("Cannot add artifacts to an inactive session")

        session.artifacts.append(artifact)

        logger.info(
            "Artifact added to session %s: %s (%s)",
            session.id, artifact.name, artifact.type.value
        )

    async def end_session(self, session: PairSession) -> PairResult:
        """End the pair programming session and generate results.

        Terminates the session, calculates metrics, and returns
        a comprehensive result summary.

        Args:
            session: The session to end

        Returns:
            PairResult containing session summary and metrics

        Raises:
            ValueError: If the session is not active

        Example:
            >>> result = await system.end_session(session)
            >>> print(f"Duration: {result.duration_seconds}s")
            >>> print(f"Role switches: {result.total_switches}")
        """
        if not session.is_active:
            raise ValueError("Session is already ended")

        # Mark session as inactive
        session.is_active = False

        # Cancel auto-switch timer
        self._cancel_auto_switch_timer(session.id)

        # Calculate duration
        ended_at = datetime.now()
        duration = (ended_at - session.started_at).total_seconds()

        # Calculate metrics
        suggestions = [m for m in session.messages
                      if m.message_type == PairMessageType.SUGGESTION.value]
        concerns = [m for m in session.messages
                   if m.message_type == PairMessageType.CONCERN.value]
        approvals = [m for m in session.messages
                    if m.message_type == PairMessageType.APPROVAL.value]

        # Count contributions by final roles
        driver_msgs = [m for m in session.messages if m.sender == session.driver]
        navigator_msgs = [m for m in session.messages if m.sender == session.navigator]

        # Calculate collaboration score
        total_messages = len(session.messages)
        collaboration_score = 0.0
        if total_messages > 0:
            # Score based on balanced communication and constructive feedback
            balance_score = 1.0 - abs(
                len(driver_msgs) - len(navigator_msgs)
            ) / max(total_messages, 1)
            feedback_score = min(
                (len(suggestions) + len(approvals)) / max(total_messages, 1), 1.0
            )
            collaboration_score = (balance_score + feedback_score) / 2

        # Calculate quality score based on artifacts
        quality_score = 0.0
        if session.artifacts:
            artifact_scores = [
                a.quality_score for a in session.artifacts
                if a.quality_score is not None
            ]
            if artifact_scores:
                quality_score = sum(artifact_scores) / len(artifact_scores)

        # Create end message
        end_message = PairMessage(
            sender=session.driver,
            content=f"Pair programming session ended. Duration: {duration:.0f}s, "
                   f"Role switches: {session.role_switches}",
            message_type=PairMessageType.SESSION_END.value,
            metadata={
                "duration_seconds": duration,
                "role_switches": session.role_switches,
                "artifacts_count": len(session.artifacts),
            }
        )
        session.messages.append(end_message)

        # Generate summary
        summary = self._generate_session_summary(session, duration)

        # Create result
        result = PairResult(
            session_id=session.id,
            success=len(session.artifacts) > 0 or len(suggestions) > 0,
            artifacts=session.artifacts.copy(),
            total_switches=session.role_switches,
            duration_seconds=duration,
            summary=summary,
            driver_contributions=len(driver_msgs),
            navigator_contributions=len(navigator_msgs),
            suggestions_accepted=len(approvals),
            concerns_raised=len(concerns),
            concerns_resolved=sum(
                1 for c in concerns
                if any(r.in_reply_to == c.id for r in session.messages)
            ),
            quality_score=quality_score,
            collaboration_score=collaboration_score,
            final_driver=session.driver,
            final_navigator=session.navigator,
            started_at=session.started_at,
            ended_at=ended_at,
        )

        # Store completed session
        self.completed_sessions.append(result)

        # Remove from active sessions
        if session.id in self.active_sessions:
            del self.active_sessions[session.id]

        # Update task status
        session.task.status = TaskStatus.IN_REVIEW

        logger.info(
            "Ended pair programming session %s: duration=%.0fs, switches=%d, "
            "artifacts=%d, collaboration_score=%.2f",
            session.id, duration, session.role_switches,
            len(session.artifacts), collaboration_score
        )

        # Notify both agents
        await self._notify_agents(session, end_message)

        return result

    async def pause_session(self, session: PairSession) -> None:
        """Pause an active session.

        Temporarily pauses the session, stopping the auto-switch timer.

        Args:
            session: The session to pause
        """
        if not session.is_active:
            raise ValueError("Cannot pause an inactive session")

        session.paused_at = datetime.now()
        self._cancel_auto_switch_timer(session.id)

        logger.info("Paused pair programming session %s", session.id)

    async def resume_session(self, session: PairSession) -> None:
        """Resume a paused session.

        Resumes a previously paused session and restarts the
        auto-switch timer.

        Args:
            session: The session to resume
        """
        if not session.is_active:
            raise ValueError("Cannot resume an inactive session")
        if session.paused_at is None:
            raise ValueError("Session is not paused")

        session.paused_at = None
        self._start_auto_switch_timer(session)

        logger.info("Resumed pair programming session %s", session.id)

    async def _auto_switch_check(self, session: PairSession) -> bool:
        """Check if automatic role switch is needed.

        Evaluates whether enough time has passed since the last
        role switch to trigger an automatic switch.

        Args:
            session: The session to check

        Returns:
            True if a switch was performed, False otherwise
        """
        if not session.is_active or session.paused_at is not None:
            return False

        last_switch = session.last_switch_at or session.started_at
        elapsed = (datetime.now() - last_switch).total_seconds()

        if elapsed >= self.switch_interval:
            logger.info(
                "Auto-switching roles in session %s (elapsed: %.0fs)",
                session.id, elapsed
            )
            await self.switch_roles(session)
            return True

        return False

    def get_session(self, session_id: str) -> PairSession | None:
        """Get a session by ID.

        Args:
            session_id: The session ID to look up

        Returns:
            The session if found, None otherwise
        """
        return self.active_sessions.get(session_id)

    def get_active_sessions(self) -> list[PairSession]:
        """Get all active sessions.

        Returns:
            List of currently active sessions
        """
        return [s for s in self.active_sessions.values() if s.is_active]

    def get_agent_sessions(self, agent_id: AgentId) -> list[PairSession]:
        """Get all sessions involving a specific agent.

        Args:
            agent_id: The agent ID to filter by

        Returns:
            List of sessions involving the agent
        """
        return [
            s for s in self.active_sessions.values()
            if agent_id in (s.driver, s.navigator)
        ]

    # =========================================================================
    # Private Helper Methods
    # =========================================================================

    def _validate_session_and_agent(
        self,
        session: PairSession,
        agent_id: AgentId,
    ) -> None:
        """Validate session is active and agent is a participant.

        Args:
            session: The session to validate
            agent_id: The agent ID to validate

        Raises:
            ValueError: If validation fails
        """
        if not session.is_active:
            raise ValueError("Session is not active")

        if agent_id not in (session.driver, session.navigator):
            raise ValueError(
                f"Agent {agent_id} is not a participant in this session"
            )

    def _get_agent_role(
        self,
        session: PairSession,
        agent_id: AgentId,
    ) -> PairRole:
        """Get the current role of an agent in a session.

        Args:
            session: The session to check
            agent_id: The agent ID to look up

        Returns:
            The agent's current role
        """
        if agent_id == session.driver:
            return PairRole.DRIVER
        return PairRole.NAVIGATOR

    def _start_auto_switch_timer(self, session: PairSession) -> None:
        """Start the automatic role switch timer.

        Args:
            session: The session to start timer for
        """
        # Cancel existing timer if any
        self._cancel_auto_switch_timer(session.id)

        async def auto_switch_loop() -> None:
            while session.is_active and session.id in self.active_sessions:
                await asyncio.sleep(self.switch_interval)
                if session.is_active and session.paused_at is None:
                    await self._auto_switch_check(session)

        self._switch_tasks[session.id] = asyncio.create_task(auto_switch_loop())

    def _cancel_auto_switch_timer(self, session_id: str) -> None:
        """Cancel the automatic role switch timer.

        Args:
            session_id: The session ID to cancel timer for
        """
        if session_id in self._switch_tasks:
            self._switch_tasks[session_id].cancel()
            del self._switch_tasks[session_id]

    async def _notify_agents(
        self,
        session: PairSession,
        message: PairMessage,
    ) -> None:
        """Notify both agents in a session of a message.

        Args:
            session: The session containing the agents
            message: The message to send
        """
        for agent_id in (session.driver, session.navigator):
            if agent_id in self._agents:
                try:
                    await self._agents[agent_id].receive_message(message)
                except Exception as e:
                    logger.warning(
                        "Failed to notify agent %s: %s",
                        agent_id, str(e)
                    )

    async def _notify_other_agent(
        self,
        session: PairSession,
        sender_id: AgentId,
        message: PairMessage,
    ) -> None:
        """Notify the other agent (not the sender) of a message.

        Args:
            session: The session containing the agents
            sender_id: ID of the sending agent
            message: The message to send
        """
        other_id = session.navigator if sender_id == session.driver else session.driver
        if other_id in self._agents:
            try:
                await self._agents[other_id].receive_message(message)
            except Exception as e:
                logger.warning(
                    "Failed to notify agent %s: %s",
                    other_id, str(e)
                )

    def _generate_session_summary(
        self,
        session: PairSession,
        duration: float,
    ) -> str:
        """Generate a human-readable session summary.

        Args:
            session: The session to summarize
            duration: Session duration in seconds

        Returns:
            Summary string
        """
        minutes = int(duration // 60)
        suggestions = len(session.get_suggestions())
        concerns = len(session.get_concerns())

        summary_parts = [
            f"Pair programming session completed in {minutes} minutes.",
            f"Task: {session.task.title}",
            f"Role switches: {session.role_switches}",
            f"Artifacts produced: {len(session.artifacts)}",
            f"Suggestions made: {suggestions}",
            f"Concerns raised: {concerns}",
            f"Total messages: {len(session.messages)}",
        ]

        return " ".join(summary_parts)


# =============================================================================
# Exports
# =============================================================================

__all__ = [
    # Enums
    "PairMessageType",
    "PairRole",
    # Protocol
    "BaseAgent",
    # Data Classes
    "PairMessage",
    "PairSession",
    "PairResult",
    # Main System
    "PairProgrammingSystem",
]
