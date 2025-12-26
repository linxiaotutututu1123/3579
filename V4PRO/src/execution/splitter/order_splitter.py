"""
智能拆单主逻辑模块.

V4PRO Platform Component - Intelligent Order Splitter
军规覆盖: M2(幂等执行), M3(完整审计), M5(成本先行), M7(回放一致), M12(双重确认)

V4PRO Scenarios:
- SPLITTER.SELECTOR: 智能算法选择
- SPLITTER.SPLIT: 大额订单拆分
- SPLITTER.CONFIRM: 与确认机制集成 (M12)

支持的拆单算法:
- TWAP: 时间加权平均价格
- VWAP: 成交量加权平均价格
- ICEBERG: 冰山订单
- BEHAVIORAL: 行为伪装

算法选择决策树:
1. 订单规模评估
2. 市场流动性评估
3. 交易时段评估
4. 策略类型评估
5. 综合选择最优算法
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Awaitable

from src.execution.mode2.executor_base import (
    ExecutorBase,
    ExecutorConfig,
    ExecutorStatus,
    ExecutionProgress,
)
from src.execution.mode2.executor_twap import TWAPConfig, TWAPExecutor
from src.execution.mode2.executor_vwap import VWAPConfig, VWAPExecutor
from src.execution.mode2.executor_iceberg import IcebergConfig, IcebergExecutor
from src.execution.mode2.intent import OrderIntent, AlgoType
from src.execution.splitter.behavioral_disguise import (
    BehavioralConfig,
    BehavioralDisguiseExecutor,
    DisguisePattern,
)
from src.execution.splitter.metrics import (
    ExecutionMetrics,
    ExecutionTargets,
    MetricsCollector,
    MetricStatus,
)


class SplitAlgorithm(str, Enum):
    """拆单算法枚举.

    D7-P1 定义的四种拆单算法。

    Attributes:
        TWAP: 时间加权平均价格
        VWAP: 成交量加权平均价格
        ICEBERG: 冰山订单
        BEHAVIORAL: 行为伪装
    """

    TWAP = "TWAP"
    VWAP = "VWAP"
    ICEBERG = "ICEBERG"
    BEHAVIORAL = "BEHAVIORAL"


class OrderSizeCategory(str, Enum):
    """订单规模分类.

    Attributes:
        SMALL: 小额订单 (<50万)
        MEDIUM: 中等订单 (50万-200万)
        LARGE: 大额订单 (200万-500万)
        HUGE: 超大订单 (>500万)
    """

    SMALL = "SMALL"
    MEDIUM = "MEDIUM"
    LARGE = "LARGE"
    HUGE = "HUGE"


class LiquidityLevel(str, Enum):
    """市场流动性水平.

    Attributes:
        HIGH: 高流动性 (主力合约活跃时段)
        NORMAL: 正常流动性
        LOW: 低流动性 (非主力/夜盘尾盘)
        CRITICAL: 极低流动性 (临近涨跌停)
    """

    HIGH = "HIGH"
    NORMAL = "NORMAL"
    LOW = "LOW"
    CRITICAL = "CRITICAL"


class SessionPhase(str, Enum):
    """交易时段阶段.

    Attributes:
        OPENING: 开盘阶段 (09:00-09:30)
        MORNING: 上午交易 (09:30-11:30)
        AFTERNOON: 下午交易 (13:00-14:30)
        CLOSING: 收盘阶段 (14:30-15:00)
        NIGHT_ACTIVE: 夜盘活跃期 (21:00-23:00)
        NIGHT_QUIET: 夜盘平静期 (23:00-02:30)
    """

    OPENING = "OPENING"
    MORNING = "MORNING"
    AFTERNOON = "AFTERNOON"
    CLOSING = "CLOSING"
    NIGHT_ACTIVE = "NIGHT_ACTIVE"
    NIGHT_QUIET = "NIGHT_QUIET"


@dataclass
class MarketContext:
    """市场上下文.

    用于算法选择的市场状态信息。

    Attributes:
        liquidity_level: 流动性水平
        session_phase: 交易时段
        volatility_pct: 波动率
        avg_volume: 平均成交量
        is_limit_up: 是否涨停
        is_limit_down: 是否跌停
    """

    liquidity_level: LiquidityLevel = LiquidityLevel.NORMAL
    session_phase: SessionPhase = SessionPhase.MORNING
    volatility_pct: float = 0.0
    avg_volume: int = 0
    is_limit_up: bool = False
    is_limit_down: bool = False


@dataclass
class SplitterConfig:
    """拆单器配置.

    Attributes:
        order_value_thresholds: 订单规模阈值
        default_algorithm: 默认算法
        twap_config: TWAP配置
        vwap_config: VWAP配置
        iceberg_config: 冰山单配置
        behavioral_config: 行为伪装配置
        enable_confirmation: 是否启用确认机制
        confirmation_threshold: 确认阈值(金额)
    """

    order_value_thresholds: dict[OrderSizeCategory, float] = field(
        default_factory=lambda: {
            OrderSizeCategory.SMALL: 500_000,
            OrderSizeCategory.MEDIUM: 2_000_000,
            OrderSizeCategory.LARGE: 5_000_000,
            OrderSizeCategory.HUGE: float("inf"),
        }
    )
    default_algorithm: SplitAlgorithm = SplitAlgorithm.TWAP
    twap_config: TWAPConfig = field(default_factory=TWAPConfig)
    vwap_config: VWAPConfig = field(default_factory=VWAPConfig)
    iceberg_config: IcebergConfig = field(default_factory=IcebergConfig)
    behavioral_config: BehavioralConfig = field(default_factory=BehavioralConfig)
    enable_confirmation: bool = True
    confirmation_threshold: float = 500_000  # M12: 50万以上需要确认


@dataclass
class AlgorithmScore:
    """算法评分.

    用于算法选择的评分结果。

    Attributes:
        algorithm: 算法类型
        score: 总分 (0-100)
        factors: 各因素评分
        reasons: 选择原因
    """

    algorithm: SplitAlgorithm
    score: float
    factors: dict[str, float] = field(default_factory=dict)
    reasons: list[str] = field(default_factory=list)


@dataclass
class SplitPlan:
    """拆单计划.

    Attributes:
        plan_id: 计划ID
        intent: 原始交易意图
        algorithm: 选择的算法
        executor: 执行器实例
        order_value: 订单估值
        size_category: 规模分类
        requires_confirmation: 是否需要确认
        confirmation_level: 确认级别
        metrics: 执行指标
        created_at: 创建时间
    """

    plan_id: str
    intent: OrderIntent
    algorithm: SplitAlgorithm
    executor: ExecutorBase
    order_value: float
    size_category: OrderSizeCategory
    requires_confirmation: bool = False
    confirmation_level: str = "AUTO"
    metrics: ExecutionMetrics | None = None
    created_at: float = field(default_factory=time.time)


# Type alias for confirmation callback
ConfirmationCallback = Callable[[OrderIntent, float], Awaitable[bool]]


class AlgorithmSelector:
    """算法选择器.

    V4PRO Scenario: SPLITTER.SELECTOR

    实现智能算法选择决策树。
    """

    # 算法权重配置
    ALGORITHM_WEIGHTS = {
        SplitAlgorithm.TWAP: {
            "time_sensitivity": 0.9,
            "impact_minimization": 0.7,
            "complexity": 0.3,
            "stealth": 0.4,
        },
        SplitAlgorithm.VWAP: {
            "time_sensitivity": 0.6,
            "impact_minimization": 0.9,
            "complexity": 0.5,
            "stealth": 0.5,
        },
        SplitAlgorithm.ICEBERG: {
            "time_sensitivity": 0.5,
            "impact_minimization": 0.8,
            "complexity": 0.4,
            "stealth": 0.9,
        },
        SplitAlgorithm.BEHAVIORAL: {
            "time_sensitivity": 0.4,
            "impact_minimization": 0.6,
            "complexity": 0.8,
            "stealth": 1.0,
        },
    }

    def __init__(self, config: SplitterConfig | None = None) -> None:
        """初始化算法选择器.

        Args:
            config: 拆单器配置
        """
        self.config = config or SplitterConfig()

    def classify_order_size(
        self, order_value: float
    ) -> OrderSizeCategory:
        """分类订单规模.

        Args:
            order_value: 订单估值

        Returns:
            订单规模分类
        """
        thresholds = self.config.order_value_thresholds
        if order_value < thresholds[OrderSizeCategory.SMALL]:
            return OrderSizeCategory.SMALL
        if order_value < thresholds[OrderSizeCategory.MEDIUM]:
            return OrderSizeCategory.MEDIUM
        if order_value < thresholds[OrderSizeCategory.LARGE]:
            return OrderSizeCategory.LARGE
        return OrderSizeCategory.HUGE

    def select_algorithm(
        self,
        intent: OrderIntent,
        order_value: float,
        market_context: MarketContext | None = None,
    ) -> tuple[SplitAlgorithm, list[str]]:
        """选择最优算法.

        V4PRO Scenario: SPLITTER.SELECTOR

        决策树:
        1. 小额订单 -> TWAP (简单高效)
        2. 高流动性 + 中等订单 -> VWAP (跟踪基准)
        3. 低流动性 + 大额订单 -> ICEBERG (隐藏规模)
        4. 超大订单 + 需隐蔽 -> BEHAVIORAL (行为伪装)
        5. 极端行情 -> 快速TWAP

        Args:
            intent: 交易意图
            order_value: 订单估值
            market_context: 市场上下文

        Returns:
            (选择的算法, 选择原因列表)
        """
        market = market_context or MarketContext()
        size_category = self.classify_order_size(order_value)
        reasons: list[str] = []

        # 1. 极端行情快速处理
        if market.is_limit_up or market.is_limit_down:
            reasons.append("极端行情(涨跌停): 选择快速TWAP")
            return SplitAlgorithm.TWAP, reasons

        # 2. 根据意图指定的算法
        if intent.algo != AlgoType.IMMEDIATE:
            algo_map = {
                AlgoType.TWAP: SplitAlgorithm.TWAP,
                AlgoType.VWAP: SplitAlgorithm.VWAP,
                AlgoType.ICEBERG: SplitAlgorithm.ICEBERG,
            }
            if intent.algo in algo_map:
                reasons.append(f"意图指定算法: {intent.algo.value}")
                return algo_map[intent.algo], reasons

        # 3. 评分选择
        scores = self._score_algorithms(
            size_category, market, intent
        )

        # 选择最高分算法
        best = max(scores, key=lambda s: s.score)
        reasons.extend(best.reasons)
        reasons.append(f"综合评分: {best.score:.2f}")

        return best.algorithm, reasons

    def _score_algorithms(
        self,
        size_category: OrderSizeCategory,
        market: MarketContext,
        intent: OrderIntent,
    ) -> list[AlgorithmScore]:
        """评估各算法得分.

        Args:
            size_category: 订单规模分类
            market: 市场上下文
            intent: 交易意图

        Returns:
            算法评分列表
        """
        scores: list[AlgorithmScore] = []

        for algo in SplitAlgorithm:
            score_obj = self._score_algorithm(
                algo, size_category, market, intent
            )
            scores.append(score_obj)

        return scores

    def _score_algorithm(
        self,
        algo: SplitAlgorithm,
        size_category: OrderSizeCategory,
        market: MarketContext,
        intent: OrderIntent,
    ) -> AlgorithmScore:
        """评估单个算法得分.

        Args:
            algo: 算法类型
            size_category: 订单规模分类
            market: 市场上下文
            intent: 交易意图

        Returns:
            算法评分
        """
        factors: dict[str, float] = {}
        reasons: list[str] = []
        weights = self.ALGORITHM_WEIGHTS[algo]

        # 1. 订单规模因素
        size_score = self._score_size_factor(algo, size_category)
        factors["size"] = size_score
        if size_score > 0.7:
            reasons.append(f"规模适配({size_category.value}): {size_score:.2f}")

        # 2. 流动性因素
        liquidity_score = self._score_liquidity_factor(algo, market.liquidity_level)
        factors["liquidity"] = liquidity_score
        if liquidity_score > 0.7:
            reasons.append(f"流动性适配: {liquidity_score:.2f}")

        # 3. 时段因素
        session_score = self._score_session_factor(algo, market.session_phase)
        factors["session"] = session_score
        if session_score > 0.7:
            reasons.append(f"时段适配: {session_score:.2f}")

        # 4. 隐蔽性因素
        stealth_score = weights["stealth"]
        factors["stealth"] = stealth_score

        # 5. 波动性因素
        volatility_score = self._score_volatility_factor(algo, market.volatility_pct)
        factors["volatility"] = volatility_score

        # 综合评分
        total_score = (
            size_score * 0.3
            + liquidity_score * 0.25
            + session_score * 0.15
            + stealth_score * 0.15
            + volatility_score * 0.15
        ) * 100

        return AlgorithmScore(
            algorithm=algo,
            score=total_score,
            factors=factors,
            reasons=reasons,
        )

    def _score_size_factor(
        self, algo: SplitAlgorithm, size: OrderSizeCategory
    ) -> float:
        """评估规模因素得分.

        Args:
            algo: 算法
            size: 订单规模

        Returns:
            得分 (0-1)
        """
        # 规模-算法适配矩阵
        matrix = {
            OrderSizeCategory.SMALL: {
                SplitAlgorithm.TWAP: 0.9,
                SplitAlgorithm.VWAP: 0.6,
                SplitAlgorithm.ICEBERG: 0.4,
                SplitAlgorithm.BEHAVIORAL: 0.3,
            },
            OrderSizeCategory.MEDIUM: {
                SplitAlgorithm.TWAP: 0.7,
                SplitAlgorithm.VWAP: 0.9,
                SplitAlgorithm.ICEBERG: 0.7,
                SplitAlgorithm.BEHAVIORAL: 0.5,
            },
            OrderSizeCategory.LARGE: {
                SplitAlgorithm.TWAP: 0.5,
                SplitAlgorithm.VWAP: 0.7,
                SplitAlgorithm.ICEBERG: 0.9,
                SplitAlgorithm.BEHAVIORAL: 0.8,
            },
            OrderSizeCategory.HUGE: {
                SplitAlgorithm.TWAP: 0.3,
                SplitAlgorithm.VWAP: 0.5,
                SplitAlgorithm.ICEBERG: 0.7,
                SplitAlgorithm.BEHAVIORAL: 1.0,
            },
        }
        return matrix[size][algo]

    def _score_liquidity_factor(
        self, algo: SplitAlgorithm, liquidity: LiquidityLevel
    ) -> float:
        """评估流动性因素得分.

        Args:
            algo: 算法
            liquidity: 流动性水平

        Returns:
            得分 (0-1)
        """
        matrix = {
            LiquidityLevel.HIGH: {
                SplitAlgorithm.TWAP: 0.9,
                SplitAlgorithm.VWAP: 1.0,
                SplitAlgorithm.ICEBERG: 0.7,
                SplitAlgorithm.BEHAVIORAL: 0.6,
            },
            LiquidityLevel.NORMAL: {
                SplitAlgorithm.TWAP: 0.8,
                SplitAlgorithm.VWAP: 0.8,
                SplitAlgorithm.ICEBERG: 0.8,
                SplitAlgorithm.BEHAVIORAL: 0.7,
            },
            LiquidityLevel.LOW: {
                SplitAlgorithm.TWAP: 0.6,
                SplitAlgorithm.VWAP: 0.5,
                SplitAlgorithm.ICEBERG: 0.9,
                SplitAlgorithm.BEHAVIORAL: 0.8,
            },
            LiquidityLevel.CRITICAL: {
                SplitAlgorithm.TWAP: 0.7,
                SplitAlgorithm.VWAP: 0.3,
                SplitAlgorithm.ICEBERG: 0.6,
                SplitAlgorithm.BEHAVIORAL: 0.9,
            },
        }
        return matrix[liquidity][algo]

    def _score_session_factor(
        self, algo: SplitAlgorithm, session: SessionPhase
    ) -> float:
        """评估时段因素得分.

        Args:
            algo: 算法
            session: 交易时段

        Returns:
            得分 (0-1)
        """
        matrix = {
            SessionPhase.OPENING: {
                SplitAlgorithm.TWAP: 0.6,
                SplitAlgorithm.VWAP: 0.9,
                SplitAlgorithm.ICEBERG: 0.5,
                SplitAlgorithm.BEHAVIORAL: 0.4,
            },
            SessionPhase.MORNING: {
                SplitAlgorithm.TWAP: 0.8,
                SplitAlgorithm.VWAP: 0.9,
                SplitAlgorithm.ICEBERG: 0.8,
                SplitAlgorithm.BEHAVIORAL: 0.7,
            },
            SessionPhase.AFTERNOON: {
                SplitAlgorithm.TWAP: 0.8,
                SplitAlgorithm.VWAP: 0.8,
                SplitAlgorithm.ICEBERG: 0.8,
                SplitAlgorithm.BEHAVIORAL: 0.7,
            },
            SessionPhase.CLOSING: {
                SplitAlgorithm.TWAP: 0.9,
                SplitAlgorithm.VWAP: 0.6,
                SplitAlgorithm.ICEBERG: 0.5,
                SplitAlgorithm.BEHAVIORAL: 0.4,
            },
            SessionPhase.NIGHT_ACTIVE: {
                SplitAlgorithm.TWAP: 0.7,
                SplitAlgorithm.VWAP: 0.7,
                SplitAlgorithm.ICEBERG: 0.8,
                SplitAlgorithm.BEHAVIORAL: 0.8,
            },
            SessionPhase.NIGHT_QUIET: {
                SplitAlgorithm.TWAP: 0.6,
                SplitAlgorithm.VWAP: 0.5,
                SplitAlgorithm.ICEBERG: 0.9,
                SplitAlgorithm.BEHAVIORAL: 0.9,
            },
        }
        return matrix[session][algo]

    def _score_volatility_factor(
        self, algo: SplitAlgorithm, volatility_pct: float
    ) -> float:
        """评估波动性因素得分.

        Args:
            algo: 算法
            volatility_pct: 波动率百分比

        Returns:
            得分 (0-1)
        """
        # 高波动时需要更快执行
        if volatility_pct > 0.05:  # >5%
            scores = {
                SplitAlgorithm.TWAP: 0.9,
                SplitAlgorithm.VWAP: 0.5,
                SplitAlgorithm.ICEBERG: 0.4,
                SplitAlgorithm.BEHAVIORAL: 0.3,
            }
        elif volatility_pct > 0.02:  # 2-5%
            scores = {
                SplitAlgorithm.TWAP: 0.7,
                SplitAlgorithm.VWAP: 0.7,
                SplitAlgorithm.ICEBERG: 0.6,
                SplitAlgorithm.BEHAVIORAL: 0.5,
            }
        else:  # <2%
            scores = {
                SplitAlgorithm.TWAP: 0.6,
                SplitAlgorithm.VWAP: 0.8,
                SplitAlgorithm.ICEBERG: 0.8,
                SplitAlgorithm.BEHAVIORAL: 0.8,
            }
        return scores[algo]


class OrderSplitter:
    """智能拆单器.

    V4PRO Scenarios:
    - SPLITTER.SPLIT: 大额订单拆分
    - SPLITTER.SELECTOR: 智能算法选择
    - SPLITTER.CONFIRM: 与确认机制集成 (M12)

    军规覆盖:
    - M2: 幂等执行
    - M3: 完整审计
    - M5: 成本先行
    - M12: 双重确认
    """

    def __init__(
        self,
        config: SplitterConfig | None = None,
        confirmation_callback: ConfirmationCallback | None = None,
    ) -> None:
        """初始化拆单器.

        Args:
            config: 拆单器配置
            confirmation_callback: 确认回调(M12集成)
        """
        self.config = config or SplitterConfig()
        self._selector = AlgorithmSelector(self.config)
        self._confirmation_callback = confirmation_callback
        self._plans: dict[str, SplitPlan] = {}
        self._metrics_collector = MetricsCollector()

    @property
    def metrics_collector(self) -> MetricsCollector:
        """获取指标收集器."""
        return self._metrics_collector

    def _create_executor(self, algorithm: SplitAlgorithm) -> ExecutorBase:
        """创建执行器实例.

        Args:
            algorithm: 算法类型

        Returns:
            执行器实例
        """
        if algorithm == SplitAlgorithm.TWAP:
            return TWAPExecutor(self.config.twap_config)
        if algorithm == SplitAlgorithm.VWAP:
            return VWAPExecutor(self.config.vwap_config)
        if algorithm == SplitAlgorithm.ICEBERG:
            return IcebergExecutor(self.config.iceberg_config)
        return BehavioralDisguiseExecutor(self.config.behavioral_config)

    def estimate_order_value(
        self,
        intent: OrderIntent,
        price: float | None = None,
    ) -> float:
        """估算订单金额.

        Args:
            intent: 交易意图
            price: 参考价格(None则使用限价)

        Returns:
            订单估值
        """
        ref_price = price or intent.limit_price or 0.0
        return ref_price * intent.target_qty

    async def create_split_plan(
        self,
        intent: OrderIntent,
        market_context: MarketContext | None = None,
        reference_price: float | None = None,
    ) -> SplitPlan:
        """创建拆单计划.

        V4PRO Scenarios:
        - SPLITTER.SPLIT: 订单拆分
        - SPLITTER.CONFIRM: M12确认集成

        Args:
            intent: 交易意图
            market_context: 市场上下文
            reference_price: 参考价格

        Returns:
            拆单计划

        Raises:
            ValueError: 确认被拒绝
        """
        plan_id = intent.intent_id

        # 幂等检查
        if plan_id in self._plans:
            return self._plans[plan_id]

        # 估算订单价值
        order_value = self.estimate_order_value(intent, reference_price)
        size_category = self._selector.classify_order_size(order_value)

        # M12: 确认机制
        requires_confirmation = (
            self.config.enable_confirmation
            and order_value >= self.config.confirmation_threshold
        )

        confirmation_level = "AUTO"
        if requires_confirmation and self._confirmation_callback:
            confirmed = await self._confirmation_callback(intent, order_value)
            if not confirmed:
                msg = f"订单确认被拒绝: {plan_id}, 金额: {order_value}"
                raise ValueError(msg)
            confirmation_level = "CONFIRMED"

        # 选择算法
        algorithm, reasons = self._selector.select_algorithm(
            intent, order_value, market_context
        )

        # 创建执行器
        executor = self._create_executor(algorithm)
        executor.make_plan(intent)

        # 创建指标
        metrics = self._metrics_collector.create_metrics(plan_id, algorithm.value)
        metrics.update_fill_rate(intent.target_qty, 0)

        # 创建计划
        plan = SplitPlan(
            plan_id=plan_id,
            intent=intent,
            algorithm=algorithm,
            executor=executor,
            order_value=order_value,
            size_category=size_category,
            requires_confirmation=requires_confirmation,
            confirmation_level=confirmation_level,
            metrics=metrics,
        )

        self._plans[plan_id] = plan

        return plan

    def get_plan(self, plan_id: str) -> SplitPlan | None:
        """获取拆单计划.

        Args:
            plan_id: 计划ID

        Returns:
            拆单计划或None
        """
        return self._plans.get(plan_id)

    def get_status(self, plan_id: str) -> ExecutorStatus | None:
        """获取计划状态.

        Args:
            plan_id: 计划ID

        Returns:
            状态
        """
        plan = self._plans.get(plan_id)
        if plan is None:
            return None
        return plan.executor.get_status(plan_id)

    def get_progress(self, plan_id: str) -> ExecutionProgress | None:
        """获取执行进度.

        Args:
            plan_id: 计划ID

        Returns:
            进度
        """
        plan = self._plans.get(plan_id)
        if plan is None:
            return None
        return plan.executor.get_progress(plan_id)

    def cancel_plan(self, plan_id: str, reason: str = "") -> bool:
        """取消计划.

        Args:
            plan_id: 计划ID
            reason: 取消原因

        Returns:
            是否成功取消
        """
        plan = self._plans.get(plan_id)
        if plan is None:
            return False
        return plan.executor.cancel_plan(plan_id, reason)

    def get_algorithm_selection_info(
        self,
        intent: OrderIntent,
        market_context: MarketContext | None = None,
        reference_price: float | None = None,
    ) -> dict[str, Any]:
        """获取算法选择信息(不执行).

        用于调试和审计。

        Args:
            intent: 交易意图
            market_context: 市场上下文
            reference_price: 参考价格

        Returns:
            选择信息字典
        """
        order_value = self.estimate_order_value(intent, reference_price)
        size_category = self._selector.classify_order_size(order_value)
        algorithm, reasons = self._selector.select_algorithm(
            intent, order_value, market_context
        )

        return {
            "intent_id": intent.intent_id,
            "order_value": order_value,
            "size_category": size_category.value,
            "selected_algorithm": algorithm.value,
            "selection_reasons": reasons,
            "requires_confirmation": order_value >= self.config.confirmation_threshold,
        }

    def get_all_plans(self) -> list[SplitPlan]:
        """获取所有计划.

        Returns:
            计划列表
        """
        return list(self._plans.values())

    def get_summary(self) -> dict[str, Any]:
        """获取汇总信息.

        Returns:
            汇总字典
        """
        total = len(self._plans)
        by_algorithm: dict[str, int] = {}
        by_status: dict[str, int] = {}

        for plan in self._plans.values():
            algo = plan.algorithm.value
            by_algorithm[algo] = by_algorithm.get(algo, 0) + 1

            status = plan.executor.get_status(plan.plan_id)
            if status:
                status_val = status.value
                by_status[status_val] = by_status.get(status_val, 0) + 1

        return {
            "total_plans": total,
            "by_algorithm": by_algorithm,
            "by_status": by_status,
            "metrics_summary": self._metrics_collector.get_summary(),
        }


# 决策树文档
ALGORITHM_DECISION_TREE = """
智能拆单算法选择决策树 (D7-P1)
==============================

┌──────────────────────────────────────────────────────────────┐
│                    开始: 接收交易意图                          │
└────────────────────────┬─────────────────────────────────────┘
                         │
                         ▼
┌──────────────────────────────────────────────────────────────┐
│ 1. 极端行情检查                                               │
│    涨停/跌停?                                                  │
│    ├── 是 → TWAP (快速执行)                                   │
│    └── 否 → 继续                                              │
└────────────────────────┬─────────────────────────────────────┘
                         │
                         ▼
┌──────────────────────────────────────────────────────────────┐
│ 2. 意图指定算法检查                                           │
│    intent.algo != IMMEDIATE?                                  │
│    ├── 是 → 使用指定算法                                      │
│    └── 否 → 继续评分选择                                      │
└────────────────────────┬─────────────────────────────────────┘
                         │
                         ▼
┌──────────────────────────────────────────────────────────────┐
│ 3. 订单规模评估                                               │
│    order_value < 50万?                                        │
│    ├── SMALL → 倾向 TWAP (简单高效)                          │
│    order_value < 200万?                                       │
│    ├── MEDIUM → 倾向 VWAP (跟踪基准)                         │
│    order_value < 500万?                                       │
│    ├── LARGE → 倾向 ICEBERG (隐藏规模)                       │
│    └── HUGE → 倾向 BEHAVIORAL (行为伪装)                     │
└────────────────────────┬─────────────────────────────────────┘
                         │
                         ▼
┌──────────────────────────────────────────────────────────────┐
│ 4. 流动性评估                                                 │
│    liquidity == HIGH?                                         │
│    ├── 是 → 提升 VWAP 评分                                   │
│    liquidity == LOW/CRITICAL?                                 │
│    └── 是 → 提升 ICEBERG/BEHAVIORAL 评分                     │
└────────────────────────┬─────────────────────────────────────┘
                         │
                         ▼
┌──────────────────────────────────────────────────────────────┐
│ 5. 时段评估                                                   │
│    session == OPENING/CLOSING?                                │
│    ├── 是 → 调整执行节奏                                      │
│    session == NIGHT_QUIET?                                    │
│    └── 是 → 提升 ICEBERG/BEHAVIORAL 评分                     │
└────────────────────────┬─────────────────────────────────────┘
                         │
                         ▼
┌──────────────────────────────────────────────────────────────┐
│ 6. 波动性评估                                                 │
│    volatility > 5%?                                           │
│    ├── 是 → 提升 TWAP 评分 (快速执行)                        │
│    volatility < 2%?                                           │
│    └── 是 → 提升 ICEBERG/BEHAVIORAL 评分                     │
└────────────────────────┬─────────────────────────────────────┘
                         │
                         ▼
┌──────────────────────────────────────────────────────────────┐
│ 7. 综合评分                                                   │
│    score = size*0.3 + liquidity*0.25 + session*0.15 +        │
│            stealth*0.15 + volatility*0.15                     │
│    → 选择最高分算法                                           │
└────────────────────────┬─────────────────────────────────────┘
                         │
                         ▼
┌──────────────────────────────────────────────────────────────┐
│ 8. M12确认检查                                                │
│    order_value >= 50万?                                       │
│    ├── 是 → 执行确认流程                                      │
│    │   ├── 确认通过 → 创建执行计划                           │
│    │   └── 确认拒绝 → 抛出异常                               │
│    └── 否 → 直接创建执行计划                                  │
└──────────────────────────────────────────────────────────────┘

算法适用场景总结:
┌────────────────┬────────────────────────────────────────────┐
│ TWAP           │ 小额订单、高波动时段、需要快速执行          │
├────────────────┼────────────────────────────────────────────┤
│ VWAP           │ 中等订单、高流动性、需要跟踪市场基准        │
├────────────────┼────────────────────────────────────────────┤
│ ICEBERG        │ 大额订单、低流动性、需要隐藏订单规模        │
├────────────────┼────────────────────────────────────────────┤
│ BEHAVIORAL     │ 超大订单、需要隐蔽交易意图、夜盘平静期      │
└────────────────┴────────────────────────────────────────────┘

执行质量目标 (D7-P1):
- 滑点: <=0.1%
- 成交率: >=95%
- 执行延迟: <=100ms
"""
