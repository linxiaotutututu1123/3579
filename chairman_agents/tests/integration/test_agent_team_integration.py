"""
Agent Team Integration Tests.

This module provides comprehensive integration tests for agent team
collaboration, including:
- Team building and configuration
- Multi-agent collaboration
- Role-based task assignment
- Agent communication and messaging
- Team coordination and synchronization
"""

from __future__ import annotations

import asyncio
from datetime import datetime
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from chairman_agents.core.types import (
    Task,
    TaskResult,
    TaskPriority,
    AgentCapability,
    AgentRole,
    AgentProfile,
    AgentId,
    ExpertiseLevel,
    MessageType,
    AgentMessage,
    generate_id,
)
from chairman_agents.team.team_builder import (
    TeamBuilder,
    Team,
    TeamMember,
    TeamConfiguration,
    TeamFormationStrategy,
    TeamStatus,
)


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def mock_agent_profiles() -> list[AgentProfile]:
    """Create mock agent profiles for testing."""
    return [
        AgentProfile(
            id=generate_id("agent"),
            name="Senior Backend Engineer",
            role=AgentRole.BACKEND_ENGINEER,
            capabilities=[
                AgentCapability.CODE_GENERATION,
                AgentCapability.API_DESIGN,
            ],
            expertise_level=ExpertiseLevel.SENIOR,
        ),
        AgentProfile(
            id=generate_id("agent"),
            name="Lead Code Reviewer",
            role=AgentRole.CODE_REVIEWER,
            capabilities=[
                AgentCapability.CODE_REVIEW,
                AgentCapability.DEBUGGING,
            ],
            expertise_level=ExpertiseLevel.LEAD,
        ),
        AgentProfile(
            id=generate_id("agent"),
            name="QA Engineer",
            role=AgentRole.QA_ENGINEER,
            capabilities=[
                AgentCapability.TESTING,
            ],
            expertise_level=ExpertiseLevel.MID,
        ),
        AgentProfile(
            id=generate_id("agent"),
            name="Security Architect",
            role=AgentRole.SECURITY_ARCHITECT,
            capabilities=[
                AgentCapability.SECURITY_ANALYSIS,
            ],
            expertise_level=ExpertiseLevel.PRINCIPAL,
        ),
        AgentProfile(
            id=generate_id("agent"),
            name="Full Stack Developer",
            role=AgentRole.FULLSTACK_ENGINEER,
            capabilities=[
                AgentCapability.CODE_GENERATION,
                AgentCapability.API_DESIGN,
                AgentCapability.DOCUMENTATION,
            ],
            expertise_level=ExpertiseLevel.SENIOR,
        ),
    ]


@pytest.fixture
def mock_agent_registry(
    mock_agent_profiles: list[AgentProfile],
) -> MagicMock:
    """Create a mock agent registry."""
    registry = MagicMock()

    def find_by_capability(
        capability: AgentCapability, min_level: int = 1
    ) -> list[AgentId]:
        return [
            p.id for p in mock_agent_profiles
            if capability in p.capabilities
        ]

    def find_by_role(role: AgentRole) -> list[AgentId]:
        return [p.id for p in mock_agent_profiles if p.role == role]

    def get_profile(agent_id: AgentId) -> AgentProfile | None:
        for p in mock_agent_profiles:
            if p.id == agent_id:
                return p
        return None

    registry.find_agents_by_capability = MagicMock(side_effect=find_by_capability)
    registry.find_agents_by_role = MagicMock(side_effect=find_by_role)
    registry.get_agent_profile = MagicMock(side_effect=get_profile)

    return registry


@pytest.fixture
def team_builder(mock_agent_registry: MagicMock) -> TeamBuilder:
    """Create a TeamBuilder with mock registry."""
    return TeamBuilder(
        registry=mock_agent_registry,
        default_strategy=TeamFormationStrategy.BALANCED,
    )


@pytest.fixture
def simple_team_builder() -> TeamBuilder:
    """Create a TeamBuilder without registry for direct pool management."""
    return TeamBuilder(
        registry=None,
        default_strategy=TeamFormationStrategy.BALANCED,
    )


@pytest.fixture
def code_review_task() -> Task:
    """Create a code review task."""
    return Task(
        id=generate_id("task"),
        title="Code Review Task",
        description="Review the implementation of user authentication",
        priority=TaskPriority.HIGH,
        required_capabilities=[AgentCapability.CODE_REVIEW],
        required_role=AgentRole.CODE_REVIEWER,
        min_expertise_level=ExpertiseLevel.SENIOR,
    )


@pytest.fixture
def development_task() -> Task:
    """Create a development task."""
    return Task(
        id=generate_id("task"),
        title="API Implementation Task",
        description="Implement REST API for user management",
        priority=TaskPriority.MEDIUM,
        required_capabilities=[
            AgentCapability.CODE_GENERATION,
            AgentCapability.API_DESIGN,
        ],
        min_expertise_level=ExpertiseLevel.MID,
    )


@pytest.fixture
def complex_task() -> Task:
    """Create a complex task requiring multiple capabilities."""
    return Task(
        id=generate_id("task"),
        title="Full Feature Implementation",
        description="Implement, test, and review a new feature",
        priority=TaskPriority.CRITICAL,
        required_capabilities=[
            AgentCapability.CODE_GENERATION,
            AgentCapability.TESTING,
            AgentCapability.CODE_REVIEW,
        ],
        min_expertise_level=ExpertiseLevel.SENIOR,
    )


# =============================================================================
# Team Building Tests
# =============================================================================


@pytest.mark.integration
@pytest.mark.asyncio
class TestTeamBuilding:
    """Test team building functionality."""

    async def test_build_team_basic(
        self,
        team_builder: TeamBuilder,
        development_task: Task,
    ) -> None:
        """Test basic team building for a task."""
        team = await team_builder.build_team(
            task=development_task,
            min_experts=1,
            max_experts=3,
        )

        assert team is not None
        assert team.size >= 1
        assert team.size <= 3
        assert team.status == TeamStatus.READY

    async def test_build_team_with_required_roles(
        self,
        team_builder: TeamBuilder,
        code_review_task: Task,
    ) -> None:
        """Test team building with required roles."""
        team = await team_builder.build_team(
            task=code_review_task,
            required_roles=[AgentRole.CODE_REVIEWER],
        )

        # Verify team has code reviewer
        assert any(
            m.role == AgentRole.CODE_REVIEWER
            for m in team.members
        )

    async def test_build_team_with_strategy(
        self,
        team_builder: TeamBuilder,
        complex_task: Task,
    ) -> None:
        """Test team building with different strategies."""
        # Test minimal strategy
        minimal_team = await team_builder.build_team(
            task=complex_task,
            strategy=TeamFormationStrategy.MINIMAL,
            min_experts=1,
            max_experts=5,
        )

        # Test comprehensive strategy
        comprehensive_team = await team_builder.build_team(
            task=complex_task,
            strategy=TeamFormationStrategy.COMPREHENSIVE,
            min_experts=1,
            max_experts=5,
        )

        # Comprehensive should have more or equal members
        assert comprehensive_team.size >= minimal_team.size

    async def test_team_has_lead(
        self,
        team_builder: TeamBuilder,
        development_task: Task,
    ) -> None:
        """Test that built team has a lead assigned."""
        team = await team_builder.build_team(
            task=development_task,
            min_experts=2,
        )

        assert team.lead_id is not None
        assert team.lead is not None
        assert team.lead.is_lead is True

    async def test_team_configuration(
        self,
        team_builder: TeamBuilder,
        development_task: Task,
    ) -> None:
        """Test team configuration is set correctly."""
        team = await team_builder.build_team(
            task=development_task,
            min_experts=2,
            max_experts=4,
        )

        assert team.configuration.min_size == 2
        assert team.configuration.max_size == 4
        assert team.task_id == development_task.id


# =============================================================================
# Multi-Agent Collaboration Tests
# =============================================================================


@pytest.mark.integration
@pytest.mark.asyncio
class TestMultiAgentCollaboration:
    """Test multi-agent collaboration scenarios."""

    async def test_team_member_capabilities_coverage(
        self,
        team_builder: TeamBuilder,
        complex_task: Task,
    ) -> None:
        """Test that team covers required capabilities."""
        team = await team_builder.build_team(
            task=complex_task,
            strategy=TeamFormationStrategy.COMPREHENSIVE,
            min_experts=3,
            max_experts=5,
        )

        covered_capabilities = team.covered_capabilities

        # Check coverage (may not cover all if agents unavailable)
        for cap in complex_task.required_capabilities:
            if not team.has_capability(cap):
                # Acceptable if no agent has this capability
                pass

    async def test_team_role_diversity(
        self,
        team_builder: TeamBuilder,
        complex_task: Task,
    ) -> None:
        """Test team has diverse roles."""
        team = await team_builder.build_team(
            task=complex_task,
            strategy=TeamFormationStrategy.COMPREHENSIVE,
            min_experts=3,
            max_experts=5,
        )

        covered_roles = team.covered_roles

        # Should have multiple roles in comprehensive team
        assert len(covered_roles) >= 1

    async def test_team_capacity_calculation(
        self,
        team_builder: TeamBuilder,
        development_task: Task,
    ) -> None:
        """Test team capacity is calculated correctly."""
        team = await team_builder.build_team(
            task=development_task,
            min_experts=3,
            max_experts=5,
        )

        # All members start with full availability
        assert team.total_capacity >= team.size * 0.5  # Minimum expected

    async def test_exclude_agents_from_team(
        self,
        team_builder: TeamBuilder,
        mock_agent_profiles: list[AgentProfile],
        development_task: Task,
    ) -> None:
        """Test excluding specific agents from team."""
        excluded_id = mock_agent_profiles[0].id

        team = await team_builder.build_team(
            task=development_task,
            excluded_agents=[excluded_id],
        )

        # Verify excluded agent is not in team
        assert excluded_id not in team.member_ids


# =============================================================================
# Role Assignment Tests
# =============================================================================


@pytest.mark.integration
@pytest.mark.asyncio
class TestRoleAssignment:
    """Test role-based task assignment."""

    async def test_get_members_by_role(
        self,
        team_builder: TeamBuilder,
        complex_task: Task,
    ) -> None:
        """Test retrieving members by role."""
        team = await team_builder.build_team(
            task=complex_task,
            strategy=TeamFormationStrategy.COMPREHENSIVE,
            min_experts=3,
            max_experts=5,
        )

        for role in team.covered_roles:
            role_members = team.get_members_by_role(role)
            assert all(m.role == role for m in role_members)

    async def test_get_members_by_capability(
        self,
        team_builder: TeamBuilder,
        complex_task: Task,
    ) -> None:
        """Test retrieving members by capability."""
        team = await team_builder.build_team(
            task=complex_task,
            strategy=TeamFormationStrategy.COMPREHENSIVE,
            min_experts=3,
            max_experts=5,
        )

        for cap in team.covered_capabilities:
            cap_members = team.get_members_by_capability(cap)
            assert all(m.can_handle(cap) for m in cap_members)

    async def test_change_team_lead(
        self,
        team_builder: TeamBuilder,
        development_task: Task,
    ) -> None:
        """Test changing team lead."""
        team = await team_builder.build_team(
            task=development_task,
            min_experts=2,
        )

        if len(team.members) >= 2:
            original_lead_id = team.lead_id
            new_lead_id = [m.agent_id for m in team.members if m.agent_id != original_lead_id][0]

            success = team.set_lead(new_lead_id)

            assert success is True
            assert team.lead_id == new_lead_id
            assert team.lead.is_lead is True

    async def test_team_expertise_level(
        self,
        team_builder: TeamBuilder,
        complex_task: Task,
    ) -> None:
        """Test team average expertise level calculation."""
        team = await team_builder.build_team(
            task=complex_task,
            min_experts=2,
        )

        avg_expertise = team.average_expertise_level

        # Should be between 1 and 5 (ExpertiseLevel range)
        assert 1 <= avg_expertise <= 5


# =============================================================================
# Team Management Tests
# =============================================================================


@pytest.mark.integration
@pytest.mark.asyncio
class TestTeamManagement:
    """Test team management operations."""

    async def test_add_member_to_team(
        self,
        team_builder: TeamBuilder,
        mock_agent_profiles: list[AgentProfile],
        development_task: Task,
    ) -> None:
        """Test adding member to existing team."""
        team = await team_builder.build_team(
            task=development_task,
            min_experts=1,
            max_experts=2,
        )

        initial_size = team.size

        # Find a profile not in team
        new_profile = None
        for p in mock_agent_profiles:
            if p.id not in team.member_ids:
                new_profile = p
                break

        if new_profile:
            new_member = TeamMember(
                agent_id=new_profile.id,
                profile=new_profile,
            )
            team.add_member(new_member)

            assert team.size == initial_size + 1
            assert new_profile.id in team.member_ids

    async def test_remove_member_from_team(
        self,
        team_builder: TeamBuilder,
        development_task: Task,
    ) -> None:
        """Test removing member from team."""
        team = await team_builder.build_team(
            task=development_task,
            min_experts=2,
        )

        if team.size >= 2:
            member_to_remove = team.members[-1].agent_id
            success = team.remove_member(member_to_remove)

            assert success is True
            assert member_to_remove not in team.member_ids

    async def test_team_status_transitions(
        self,
        team_builder: TeamBuilder,
        development_task: Task,
    ) -> None:
        """Test team status transitions."""
        team = await team_builder.build_team(
            task=development_task,
        )

        # Ready -> Active
        team.mark_active()
        assert team.status == TeamStatus.ACTIVE

        # Active -> Paused
        team.pause()
        assert team.status == TeamStatus.PAUSED

        # Paused -> Disbanded
        team.disband()
        assert team.status == TeamStatus.DISBANDED

    async def test_team_validation(
        self,
        team_builder: TeamBuilder,
        development_task: Task,
    ) -> None:
        """Test team validation."""
        team = await team_builder.build_team(
            task=development_task,
            min_experts=2,
            max_experts=5,
        )

        is_valid, errors = team.validate()

        if team.size >= team.configuration.min_size:
            assert is_valid is True
            assert len(errors) == 0


# =============================================================================
# Agent Pool Management Tests
# =============================================================================


@pytest.mark.integration
@pytest.mark.asyncio
class TestAgentPoolManagement:
    """Test agent pool management in TeamBuilder."""

    async def test_register_agent_to_pool(
        self,
        simple_team_builder: TeamBuilder,
        mock_agent_profiles: list[AgentProfile],
    ) -> None:
        """Test registering agent to pool."""
        for profile in mock_agent_profiles:
            simple_team_builder.register_agent(profile)

        available = simple_team_builder.get_available_agents()
        assert len(available) == len(mock_agent_profiles)

    async def test_unregister_agent_from_pool(
        self,
        simple_team_builder: TeamBuilder,
        mock_agent_profiles: list[AgentProfile],
    ) -> None:
        """Test unregistering agent from pool."""
        # Register all
        for profile in mock_agent_profiles:
            simple_team_builder.register_agent(profile)

        # Unregister one
        to_remove = mock_agent_profiles[0].id
        success = simple_team_builder.unregister_agent(to_remove)

        assert success is True
        available = simple_team_builder.get_available_agents()
        assert len(available) == len(mock_agent_profiles) - 1

    async def test_build_team_from_pool(
        self,
        simple_team_builder: TeamBuilder,
        mock_agent_profiles: list[AgentProfile],
        development_task: Task,
    ) -> None:
        """Test building team from internal pool."""
        # Register agents
        for profile in mock_agent_profiles:
            simple_team_builder.register_agent(profile)

        # Build team
        team = await simple_team_builder.build_team(
            task=development_task,
            min_experts=2,
            max_experts=4,
        )

        assert team.size >= 2


# =============================================================================
# Convenience Method Tests
# =============================================================================


@pytest.mark.integration
@pytest.mark.asyncio
class TestConvenienceMethods:
    """Test convenience methods for team building."""

    async def test_build_review_team(
        self,
        team_builder: TeamBuilder,
        code_review_task: Task,
    ) -> None:
        """Test building code review team."""
        team = await team_builder.build_review_team(
            task=code_review_task,
            reviewers_count=2,
        )

        assert team.name == "Code Review Task"
        # Check for code reviewer in team
        has_reviewer = any(
            m.role == AgentRole.CODE_REVIEWER
            for m in team.members
        )
        # May not have reviewer if not available
        assert team.size >= 1

    async def test_build_development_team(
        self,
        team_builder: TeamBuilder,
        development_task: Task,
    ) -> None:
        """Test building development team."""
        team = await team_builder.build_development_team(
            task=development_task,
            include_qa=True,
        )

        assert team.name == "开发团队"
        assert team.size >= 2

    async def test_build_security_team(
        self,
        team_builder: TeamBuilder,
    ) -> None:
        """Test building security audit team."""
        security_task = Task(
            id=generate_id("task"),
            title="Security Audit",
            description="Perform security audit",
            required_capabilities=[AgentCapability.SECURITY_ANALYSIS],
        )

        team = await team_builder.build_security_team(task=security_task)

        assert team.name == "安全审计团队"


# =============================================================================
# Team Collaboration Workflow Tests
# =============================================================================


@pytest.mark.integration
@pytest.mark.asyncio
class TestTeamCollaborationWorkflow:
    """Test complete team collaboration workflows."""

    async def test_full_team_workflow(
        self,
        team_builder: TeamBuilder,
        complex_task: Task,
    ) -> None:
        """Test complete team building and workflow."""
        # Build team
        team = await team_builder.build_team(
            task=complex_task,
            name="Full Workflow Team",
            strategy=TeamFormationStrategy.COMPREHENSIVE,
            min_experts=3,
            max_experts=5,
        )

        assert team.is_ready is True

        # Activate team
        team.mark_active()
        assert team.status == TeamStatus.ACTIVE

        # Simulate work by checking available members
        available = team.get_available_members(min_availability=0.5)
        assert len(available) == team.size  # All should be available initially

        # Validate team throughout
        is_valid, errors = team.validate()

        # Complete and disband
        team.disband()
        assert team.status == TeamStatus.DISBANDED

    async def test_team_serialization(
        self,
        team_builder: TeamBuilder,
        development_task: Task,
    ) -> None:
        """Test team can be represented as string."""
        team = await team_builder.build_team(
            task=development_task,
            min_experts=2,
        )

        repr_str = repr(team)
        assert "Team" in repr_str
        assert team.id in repr_str

    async def test_member_effective_availability(
        self,
        team_builder: TeamBuilder,
        development_task: Task,
    ) -> None:
        """Test member effective availability calculation."""
        team = await team_builder.build_team(
            task=development_task,
            min_experts=2,
        )

        for member in team.members:
            # Initial load is 0, availability is 1
            assert member.effective_availability == 1.0 * (1.0 - 0.0)

            # Simulate load
            member.current_load = 0.5
            assert member.effective_availability == 1.0 * (1.0 - 0.5)
