"""置信度API接口模块测试.

V4PRO Platform - 置信度评估API测试
军规覆盖: M3(完整审计), M19(风险归因)

测试场景:
- K56: CONFIDENCE.API.ASSESS - API评估接口
- K57: CONFIDENCE.API.STATS - 统计查询接口
- K58: CONFIDENCE.API.TREND - 趋势查询接口
"""

from __future__ import annotations

import json

import pytest

from src.risk.confidence import ConfidenceAssessor
from src.risk.confidence_api import (
    ConfidenceAPI,
    ConfidenceAPIRequest,
    ConfidenceAPIResponse,
    StatisticsResponse,
    TrendResponse,
    assess_from_json,
    create_api,
    quick_assess,
)


class TestConfidenceAPIRequest:
    """ConfidenceAPIRequest 测试类."""

    def test_create_request(self) -> None:
        """测试创建请求."""
        request = ConfidenceAPIRequest(
            task_type="STRATEGY_EXECUTION",
            task_name="test_task",
            context_data={"duplicate_check_complete": True},
        )

        assert request.task_type == "STRATEGY_EXECUTION"
        assert request.task_name == "test_task"
        assert request.request_id.startswith("req_")

    def test_to_context(self) -> None:
        """测试转换为上下文."""
        request = ConfidenceAPIRequest(
            task_type="STRATEGY_EXECUTION",
            task_name="test_task",
            context_data={
                "duplicate_check_complete": True,
                "architecture_verified": True,
            },
        )

        context = request.to_context()

        assert context.task_name == "test_task"
        assert context.duplicate_check_complete is True
        assert context.architecture_verified is True

    def test_to_context_invalid_task_type(self) -> None:
        """测试无效任务类型."""
        request = ConfidenceAPIRequest(
            task_type="INVALID_TYPE",
        )

        with pytest.raises(ValueError, match="无效的任务类型"):
            request.to_context()

    def test_to_json_and_from_json(self) -> None:
        """测试JSON序列化和反序列化."""
        request = ConfidenceAPIRequest(
            task_type="SIGNAL_GENERATION",
            task_name="test",
            context_data={"signal_strength": 0.8},
        )

        json_str = request.to_json()
        restored = ConfidenceAPIRequest.from_json(json_str)

        assert restored.task_type == request.task_type
        assert restored.task_name == request.task_name
        assert restored.context_data["signal_strength"] == 0.8


class TestConfidenceAPIResponse:
    """ConfidenceAPIResponse 测试类."""

    def test_from_result(self) -> None:
        """测试从结果创建响应."""
        assessor = ConfidenceAssessor()
        from src.risk.confidence import ConfidenceContext, TaskType

        context = ConfidenceContext(
            task_type=TaskType.STRATEGY_EXECUTION,
            duplicate_check_complete=True,
            architecture_verified=True,
            has_official_docs=True,
            has_oss_reference=True,
            root_cause_identified=True,
        )
        result = assessor.assess(context)

        response = ConfidenceAPIResponse.from_result(result, "test_req_id")

        assert response.success is True
        assert response.score >= 0.9
        assert response.level == "HIGH"
        assert response.request_id == "test_req_id"

    def test_error_response(self) -> None:
        """测试错误响应."""
        response = ConfidenceAPIResponse.error_response(
            "测试错误",
            "err_req_id",
        )

        assert response.success is False
        assert response.error == "测试错误"
        assert response.level == "ERROR"
        assert response.can_proceed is False

    def test_to_dict_and_json(self) -> None:
        """测试转换为字典和JSON."""
        response = ConfidenceAPIResponse(
            score=0.85,
            level="MEDIUM",
            can_proceed=False,
            checks=(),
            recommendation="测试建议",
            timestamp="2025-01-01T00:00:00",
        )

        d = response.to_dict()
        assert d["score"] == 0.85
        assert d["level"] == "MEDIUM"

        json_str = response.to_json()
        assert "MEDIUM" in json_str


class TestStatisticsResponse:
    """StatisticsResponse 测试类."""

    def test_create_response(self) -> None:
        """测试创建统计响应."""
        response = StatisticsResponse(
            total_assessments=100,
            high_count=60,
            medium_count=30,
            low_count=10,
            high_rate=0.6,
            medium_rate=0.3,
            low_rate=0.1,
        )

        assert response.total_assessments == 100
        assert response.high_rate == 0.6
        assert response.timestamp != ""

    def test_to_dict(self) -> None:
        """测试转换为字典."""
        response = StatisticsResponse(
            total_assessments=50,
            high_count=25,
            medium_count=15,
            low_count=10,
            high_rate=0.5,
            medium_rate=0.3,
            low_rate=0.2,
        )

        d = response.to_dict()
        assert d["total_assessments"] == 50
        assert d["high_rate"] == 0.5


class TestTrendResponse:
    """TrendResponse 测试类."""

    def test_create_response(self) -> None:
        """测试创建趋势响应."""
        response = TrendResponse(
            trend="STABLE",
            direction="NEUTRAL",
            recent_avg=0.85,
            overall_avg=0.82,
            alert=False,
            alert_message="",
            history_count=50,
        )

        assert response.trend == "STABLE"
        assert response.recent_avg == 0.85
        assert response.alert is False


class TestConfidenceAPI:
    """ConfidenceAPI 测试类."""

    def test_assess_high_confidence(self) -> None:
        """测试高置信度评估 (K56)."""
        api = ConfidenceAPI()
        request = ConfidenceAPIRequest(
            task_type="STRATEGY_EXECUTION",
            task_name="test",
            context_data={
                "duplicate_check_complete": True,
                "architecture_verified": True,
                "has_official_docs": True,
                "has_oss_reference": True,
                "root_cause_identified": True,
            },
        )

        response = api.assess(request)

        assert response.success is True
        assert response.score >= 0.9
        assert response.level == "HIGH"
        assert response.can_proceed is True

    def test_assess_low_confidence(self) -> None:
        """测试低置信度评估."""
        api = ConfidenceAPI()
        request = ConfidenceAPIRequest(
            task_type="STRATEGY_EXECUTION",
            task_name="test",
            context_data={},
        )

        response = api.assess(request)

        assert response.success is True
        assert response.score < 0.7
        assert response.level == "LOW"
        assert response.can_proceed is False

    def test_assess_invalid_task_type(self) -> None:
        """测试无效任务类型."""
        api = ConfidenceAPI()
        request = ConfidenceAPIRequest(
            task_type="INVALID",
            context_data={},
        )

        response = api.assess(request)

        assert response.success is False
        assert "无效" in response.error

    def test_assess_batch(self) -> None:
        """测试批量评估."""
        api = ConfidenceAPI()
        requests = [
            ConfidenceAPIRequest(
                task_type="STRATEGY_EXECUTION",
                context_data={"duplicate_check_complete": True},
            ),
            ConfidenceAPIRequest(
                task_type="SIGNAL_GENERATION",
                context_data={"signal_strength": 0.8, "signal_consistency": 0.85},
            ),
        ]

        responses = api.assess_batch(requests)

        assert len(responses) == 2
        assert all(r.success for r in responses)

    def test_get_statistics(self) -> None:
        """测试获取统计 (K57)."""
        api = ConfidenceAPI()

        # 先进行一些评估
        request = ConfidenceAPIRequest(
            task_type="STRATEGY_EXECUTION",
            context_data={"duplicate_check_complete": True},
        )
        api.assess(request)
        api.assess(request)

        stats = api.get_statistics()

        assert stats.total_assessments == 2

    def test_get_trend(self) -> None:
        """测试获取趋势 (K58)."""
        api = ConfidenceAPI()

        # 进行多次评估
        request = ConfidenceAPIRequest(
            task_type="STRATEGY_EXECUTION",
            context_data={
                "duplicate_check_complete": True,
                "architecture_verified": True,
                "has_official_docs": True,
            },
        )
        for _ in range(5):
            api.assess(request)

        trend = api.get_trend()

        assert trend.trend in ("STABLE", "IMPROVING", "DECLINING", "INSUFFICIENT_DATA")
        assert trend.history_count >= 5

    def test_reset(self) -> None:
        """测试重置."""
        api = ConfidenceAPI()

        # 进行一些评估
        request = ConfidenceAPIRequest(
            task_type="STRATEGY_EXECUTION",
            context_data={},
        )
        api.assess(request)

        # 重置
        api.reset()

        stats = api.get_statistics()
        assert stats.total_assessments == 0

    def test_health_check(self) -> None:
        """测试健康检查."""
        api = ConfidenceAPI()

        health = api.health_check()

        assert "healthy" in health
        assert "total_assessments" in health
        assert "timestamp" in health


class TestConvenienceFunctions:
    """便捷函数测试类."""

    def test_create_api(self) -> None:
        """测试创建API."""
        api = create_api(
            high_threshold=0.95,
            medium_threshold=0.75,
        )

        assert api.assessor._high_threshold == 0.95
        assert api.assessor._medium_threshold == 0.75

    def test_quick_assess(self) -> None:
        """测试快速评估."""
        response = quick_assess(
            "STRATEGY_EXECUTION",
            duplicate_check_complete=True,
            architecture_verified=True,
        )

        assert response.success is True
        assert response.score > 0

    def test_assess_from_json(self) -> None:
        """测试从JSON评估."""
        request_json = json.dumps({
            "task_type": "STRATEGY_EXECUTION",
            "task_name": "test",
            "context_data": {
                "duplicate_check_complete": True,
                "architecture_verified": True,
            },
        })

        response_json = assess_from_json(request_json)
        response_data = json.loads(response_json)

        assert response_data["success"] is True
        assert response_data["score"] > 0


class TestEdgeCases:
    """边界情况测试类."""

    def test_empty_context_data(self) -> None:
        """测试空上下文数据."""
        api = ConfidenceAPI()
        request = ConfidenceAPIRequest(
            task_type="STRATEGY_EXECUTION",
        )

        response = api.assess(request)
        assert response.success is True

    def test_all_task_types(self) -> None:
        """测试所有任务类型."""
        api = ConfidenceAPI()
        task_types = [
            "STRATEGY_EXECUTION",
            "SIGNAL_GENERATION",
            "RISK_ASSESSMENT",
            "ORDER_PLACEMENT",
            "POSITION_ADJUSTMENT",
        ]

        for task_type in task_types:
            request = ConfidenceAPIRequest(task_type=task_type)
            response = api.assess(request)
            assert response.success is True

    def test_custom_thresholds(self) -> None:
        """测试自定义阈值."""
        api = ConfidenceAPI(high_threshold=0.99, medium_threshold=0.90)
        request = ConfidenceAPIRequest(
            task_type="STRATEGY_EXECUTION",
            context_data={
                "duplicate_check_complete": True,
                "architecture_verified": True,
                "has_official_docs": True,
                "has_oss_reference": True,
                "root_cause_identified": True,
            },
        )

        response = api.assess(request)

        # 即使全部通过，由于阈值提高，可能不是HIGH
        assert response.success is True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
