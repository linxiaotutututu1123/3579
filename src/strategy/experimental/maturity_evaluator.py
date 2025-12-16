"""训练成熟度评估算法 (军规级 v3.0).

CLAUDE上校的成熟度评估算法:
    综合评估实验性策略是否已经训练成熟，可以投入实盘使用。

评估维度（5大维度，20个子指标）:
    1. 收益稳定性 (25%权重)
    2. 风险控制能力 (25%权重)
    3. 市场适应性 (20%权重)
    4. 训练充分度 (20%权重)
    5. 一致性检验 (10%权重)

启用门槛:
    - 总成熟度 >= 80%
    - 任意维度 >= 60%
    - 训练时间 >= 90天

示例:
    evaluator = MaturityEvaluator()
    report = evaluator.evaluate(training_history)
    print(f"成熟度: {report.total_score:.1%}")
    print(f"可启用: {report.is_mature}")
"""

from __future__ import annotations

import json
import math
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import ClassVar


class MaturityLevel(Enum):
    """成熟度级别."""

    EMBRYONIC = "embryonic"       # 初生期 (0-20%)
    DEVELOPING = "developing"    # 发展期 (20-40%)
    GROWING = "growing"          # 成长期 (40-60%)
    MATURING = "maturing"        # 成熟期 (60-80%)
    MATURE = "mature"            # 成熟 (80-100%)


@dataclass(frozen=True)
class MaturityScore:
    """单维度成熟度分数.

    属性:
        dimension: 维度名称
        score: 得分 [0, 1]
        weight: 权重
        details: 详细子指标
        reason: 评分理由
    """

    dimension: str
    score: float
    weight: float
    details: dict[str, float]
    reason: str

    @property
    def weighted_score(self) -> float:
        """加权得分."""
        return self.score * self.weight

    @property
    def is_passing(self) -> bool:
        """是否通过（>=60%）."""
        return self.score >= 0.6


@dataclass
class MaturityReport:
    """成熟度评估报告.

    属性:
        strategy_id: 策略ID
        evaluated_at: 评估时间
        dimension_scores: 各维度得分
        total_score: 总得分
        level: 成熟度级别
        training_days: 训练天数
        min_training_days: 最低训练天数要求
        is_mature: 是否成熟
        can_activate: 是否可启用
        blocking_reasons: 阻止启用的原因
    """

    strategy_id: str
    evaluated_at: datetime
    dimension_scores: list[MaturityScore]
    total_score: float
    level: MaturityLevel
    training_days: int
    min_training_days: int
    is_mature: bool
    can_activate: bool
    blocking_reasons: list[str]

    def to_dict(self) -> dict:
        """转换为字典."""
        return {
            "strategy_id": self.strategy_id,
            "evaluated_at": self.evaluated_at.isoformat(),
            "total_score": self.total_score,
            "total_score_pct": f"{self.total_score:.1%}",
            "level": self.level.value,
            "training_days": self.training_days,
            "min_training_days": self.min_training_days,
            "is_mature": self.is_mature,
            "can_activate": self.can_activate,
            "blocking_reasons": self.blocking_reasons,
            "dimensions": [
                {
                    "name": s.dimension,
                    "score": s.score,
                    "score_pct": f"{s.score:.1%}",
                    "weight": s.weight,
                    "weighted": s.weighted_score,
                    "passing": s.is_passing,
                    "reason": s.reason,
                    "details": s.details,
                }
                for s in self.dimension_scores
            ],
        }

    def to_json(self) -> str:
        """转换为JSON."""
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=2)


@dataclass
class TrainingHistory:
    """训练历史数据.

    属性:
        strategy_id: 策略ID
        start_date: 开始训练日期
        daily_returns: 每日收益率序列
        daily_positions: 每日持仓序列
        daily_signals: 每日信号序列
        market_regimes: 市场状态序列
        drawdowns: 回撤序列
        trade_count: 交易次数
        win_rate: 胜率
        profit_factor: 盈亏比
        sharpe_ratio: 夏普比率
        max_drawdown: 最大回撤
        calmar_ratio: 卡玛比率
    """

    strategy_id: str
    start_date: datetime
    daily_returns: list[float] = field(default_factory=list)
    daily_positions: list[float] = field(default_factory=list)
    daily_signals: list[float] = field(default_factory=list)
    market_regimes: list[str] = field(default_factory=list)
    drawdowns: list[float] = field(default_factory=list)
    trade_count: int = 0
    win_rate: float = 0.0
    profit_factor: float = 0.0
    sharpe_ratio: float = 0.0
    max_drawdown: float = 0.0
    calmar_ratio: float = 0.0

    @property
    def training_days(self) -> int:
        """训练天数."""
        return len(self.daily_returns)


class MaturityEvaluator:
    """成熟度评估器.

    CLAUDE上校的成熟度评估算法，综合5个维度评估策略是否可以投入实盘。

    算法设计原则:
        1. 保守原则：宁可错过，不可错投
        2. 多维验证：任何短板都会阻止启用
        3. 时间沉淀：必须经历足够的市场周期
        4. 一致性要求：训练和验证结果必须一致
    """

    # ==================== 权重配置 ====================
    # 各维度权重，总和必须为1.0
    WEIGHT_RETURN_STABILITY: ClassVar[float] = 0.25      # 收益稳定性
    WEIGHT_RISK_CONTROL: ClassVar[float] = 0.25          # 风险控制
    WEIGHT_MARKET_ADAPTABILITY: ClassVar[float] = 0.20   # 市场适应性
    WEIGHT_TRAINING_SUFFICIENCY: ClassVar[float] = 0.20  # 训练充分度
    WEIGHT_CONSISTENCY: ClassVar[float] = 0.10           # 一致性

    # ==================== 门槛配置 ====================
    # 启用门槛
    ACTIVATION_THRESHOLD: ClassVar[float] = 0.80         # 总成熟度门槛80%
    DIMENSION_THRESHOLD: ClassVar[float] = 0.60          # 单维度门槛60%
    MIN_TRAINING_DAYS: ClassVar[int] = 90                # 最低训练90天

    # ==================== 评分标准 ====================
    # 收益稳定性评分标准
    SHARPE_EXCELLENT: ClassVar[float] = 2.0              # 优秀夏普
    SHARPE_GOOD: ClassVar[float] = 1.5                   # 良好夏普
    SHARPE_PASS: ClassVar[float] = 1.0                   # 及格夏普

    # 风险控制评分标准
    MAX_DD_EXCELLENT: ClassVar[float] = 0.10             # 优秀最大回撤10%
    MAX_DD_GOOD: ClassVar[float] = 0.15                  # 良好最大回撤15%
    MAX_DD_PASS: ClassVar[float] = 0.20                  # 及格最大回撤20%

    # 胜率评分标准
    WIN_RATE_EXCELLENT: ClassVar[float] = 0.55           # 优秀胜率55%
    WIN_RATE_GOOD: ClassVar[float] = 0.50                # 良好胜率50%
    WIN_RATE_PASS: ClassVar[float] = 0.45                # 及格胜率45%

    # 盈亏比评分标准
    PF_EXCELLENT: ClassVar[float] = 2.0                  # 优秀盈亏比
    PF_GOOD: ClassVar[float] = 1.5                       # 良好盈亏比
    PF_PASS: ClassVar[float] = 1.2                       # 及格盈亏比

    def __init__(self) -> None:
        """初始化成熟度评估器."""
        self._evaluation_count: int = 0

    def evaluate(self, history: TrainingHistory) -> MaturityReport:
        """评估策略成熟度.

        参数:
            history: 训练历史数据

        返回:
            成熟度评估报告
        """
        self._evaluation_count += 1

        # 计算各维度得分
        scores = [
            self._evaluate_return_stability(history),
            self._evaluate_risk_control(history),
            self._evaluate_market_adaptability(history),
            self._evaluate_training_sufficiency(history),
            self._evaluate_consistency(history),
        ]

        # 计算总分
        total_score = sum(s.weighted_score for s in scores)

        # 判断成熟度级别
        level = self._get_maturity_level(total_score)

        # 检查是否可启用
        blocking_reasons: list[str] = []

        # 检查总分
        if total_score < self.ACTIVATION_THRESHOLD:
            blocking_reasons.append(
                f"总成熟度 {total_score:.1%} < 80% 门槛"
            )

        # 检查各维度
        for score in scores:
            if not score.is_passing:
                blocking_reasons.append(
                    f"{score.dimension} 得分 {score.score:.1%} < 60% 门槛"
                )

        # 检查训练时间
        if history.training_days < self.MIN_TRAINING_DAYS:
            blocking_reasons.append(
                f"训练天数 {history.training_days} < {self.MIN_TRAINING_DAYS} 天要求"
            )

        is_mature = total_score >= self.ACTIVATION_THRESHOLD
        can_activate = len(blocking_reasons) == 0

        return MaturityReport(
            strategy_id=history.strategy_id,
            evaluated_at=datetime.now(),
            dimension_scores=scores,
            total_score=total_score,
            level=level,
            training_days=history.training_days,
            min_training_days=self.MIN_TRAINING_DAYS,
            is_mature=is_mature,
            can_activate=can_activate,
            blocking_reasons=blocking_reasons,
        )

    def _evaluate_return_stability(self, history: TrainingHistory) -> MaturityScore:
        """评估收益稳定性.

        子指标:
            1. 夏普比率 (40%)
            2. 收益率均值/标准差 (30%)
            3. 月度收益一致性 (30%)

        参数:
            history: 训练历史

        返回:
            收益稳定性得分
        """
        details: dict[str, float] = {}

        # 1. 夏普比率评分 (40%)
        sharpe = history.sharpe_ratio
        if sharpe >= self.SHARPE_EXCELLENT:
            sharpe_score = 1.0
        elif sharpe >= self.SHARPE_GOOD:
            sharpe_score = 0.8 + (sharpe - self.SHARPE_GOOD) / (self.SHARPE_EXCELLENT - self.SHARPE_GOOD) * 0.2
        elif sharpe >= self.SHARPE_PASS:
            sharpe_score = 0.6 + (sharpe - self.SHARPE_PASS) / (self.SHARPE_GOOD - self.SHARPE_PASS) * 0.2
        else:
            sharpe_score = max(0, sharpe / self.SHARPE_PASS * 0.6)
        details["sharpe_score"] = sharpe_score

        # 2. 收益率稳定性 (30%)
        if history.daily_returns:
            mean_return = sum(history.daily_returns) / len(history.daily_returns)
            variance = sum((r - mean_return) ** 2 for r in history.daily_returns) / len(history.daily_returns)
            std_return = math.sqrt(variance) if variance > 0 else 0

            # 变异系数（越小越好）
            if abs(mean_return) > 1e-8:
                cv = std_return / abs(mean_return)
                cv_score = max(0, 1 - cv / 5)  # CV < 5 时有分
            else:
                cv_score = 0.5
        else:
            cv_score = 0.0
        details["cv_score"] = cv_score

        # 3. 月度收益一致性 (30%)
        monthly_consistency = self._calculate_monthly_consistency(history.daily_returns)
        details["monthly_consistency"] = monthly_consistency

        # 综合得分
        total_score = (
            sharpe_score * 0.4 +
            cv_score * 0.3 +
            monthly_consistency * 0.3
        )

        reason = f"夏普{sharpe:.2f}, 稳定性{cv_score:.1%}, 月度一致{monthly_consistency:.1%}"

        return MaturityScore(
            dimension="收益稳定性",
            score=total_score,
            weight=self.WEIGHT_RETURN_STABILITY,
            details=details,
            reason=reason,
        )

    def _evaluate_risk_control(self, history: TrainingHistory) -> MaturityScore:
        """评估风险控制能力.

        子指标:
            1. 最大回撤 (35%)
            2. 卡玛比率 (25%)
            3. 胜率 (20%)
            4. 盈亏比 (20%)

        参数:
            history: 训练历史

        返回:
            风险控制得分
        """
        details: dict[str, float] = {}

        # 1. 最大回撤评分 (35%)
        max_dd = abs(history.max_drawdown)
        if max_dd <= self.MAX_DD_EXCELLENT:
            dd_score = 1.0
        elif max_dd <= self.MAX_DD_GOOD:
            dd_score = 0.8 + (self.MAX_DD_GOOD - max_dd) / (self.MAX_DD_GOOD - self.MAX_DD_EXCELLENT) * 0.2
        elif max_dd <= self.MAX_DD_PASS:
            dd_score = 0.6 + (self.MAX_DD_PASS - max_dd) / (self.MAX_DD_PASS - self.MAX_DD_GOOD) * 0.2
        else:
            dd_score = max(0, (0.30 - max_dd) / 0.10 * 0.6)  # 30%以上为0
        details["dd_score"] = dd_score

        # 2. 卡玛比率评分 (25%)
        calmar = history.calmar_ratio
        if calmar >= 3.0:
            calmar_score = 1.0
        elif calmar >= 2.0:
            calmar_score = 0.8 + (calmar - 2.0) * 0.2
        elif calmar >= 1.0:
            calmar_score = 0.6 + (calmar - 1.0) * 0.2
        else:
            calmar_score = max(0, calmar * 0.6)
        details["calmar_score"] = calmar_score

        # 3. 胜率评分 (20%)
        win_rate = history.win_rate
        if win_rate >= self.WIN_RATE_EXCELLENT:
            wr_score = 1.0
        elif win_rate >= self.WIN_RATE_GOOD:
            wr_score = 0.8 + (win_rate - self.WIN_RATE_GOOD) / (self.WIN_RATE_EXCELLENT - self.WIN_RATE_GOOD) * 0.2
        elif win_rate >= self.WIN_RATE_PASS:
            wr_score = 0.6 + (win_rate - self.WIN_RATE_PASS) / (self.WIN_RATE_GOOD - self.WIN_RATE_PASS) * 0.2
        else:
            wr_score = max(0, win_rate / self.WIN_RATE_PASS * 0.6)
        details["win_rate_score"] = wr_score

        # 4. 盈亏比评分 (20%)
        pf = history.profit_factor
        if pf >= self.PF_EXCELLENT:
            pf_score = 1.0
        elif pf >= self.PF_GOOD:
            pf_score = 0.8 + (pf - self.PF_GOOD) / (self.PF_EXCELLENT - self.PF_GOOD) * 0.2
        elif pf >= self.PF_PASS:
            pf_score = 0.6 + (pf - self.PF_PASS) / (self.PF_GOOD - self.PF_PASS) * 0.2
        else:
            pf_score = max(0, pf / self.PF_PASS * 0.6)
        details["profit_factor_score"] = pf_score

        # 综合得分
        total_score = (
            dd_score * 0.35 +
            calmar_score * 0.25 +
            wr_score * 0.20 +
            pf_score * 0.20
        )

        reason = f"最大回撤{max_dd:.1%}, 卡玛{calmar:.2f}, 胜率{win_rate:.1%}, 盈亏比{pf:.2f}"

        return MaturityScore(
            dimension="风险控制",
            score=total_score,
            weight=self.WEIGHT_RISK_CONTROL,
            details=details,
            reason=reason,
        )

    def _evaluate_market_adaptability(self, history: TrainingHistory) -> MaturityScore:
        """评估市场适应性.

        子指标:
            1. 经历的市场状态数量 (40%)
            2. 各状态下的表现一致性 (30%)
            3. 极端行情存活能力 (30%)

        参数:
            history: 训练历史

        返回:
            市场适应性得分
        """
        details: dict[str, float] = {}

        # 1. 经历的市场状态 (40%)
        # 理想情况应经历: 牛市、熊市、震荡、高波动、低波动
        unique_regimes = set(history.market_regimes)
        expected_regimes = {"bull", "bear", "sideways", "high_vol", "low_vol"}
        regime_coverage = len(unique_regimes & expected_regimes) / len(expected_regimes)
        details["regime_coverage"] = regime_coverage

        # 2. 各状态表现一致性 (30%)
        # 计算各状态下的收益率标准差
        regime_consistency = self._calculate_regime_consistency(
            history.daily_returns, history.market_regimes
        )
        details["regime_consistency"] = regime_consistency

        # 3. 极端行情存活能力 (30%)
        # 检查最大回撤发生后的恢复能力
        survival_score = self._calculate_survival_score(history.drawdowns)
        details["survival_score"] = survival_score

        # 综合得分
        total_score = (
            regime_coverage * 0.4 +
            regime_consistency * 0.3 +
            survival_score * 0.3
        )

        covered = len(unique_regimes & expected_regimes)
        reason = f"覆盖{covered}/5种市场状态, 一致性{regime_consistency:.1%}, 存活{survival_score:.1%}"

        return MaturityScore(
            dimension="市场适应性",
            score=total_score,
            weight=self.WEIGHT_MARKET_ADAPTABILITY,
            details=details,
            reason=reason,
        )

    def _evaluate_training_sufficiency(self, history: TrainingHistory) -> MaturityScore:
        """评估训练充分度.

        子指标:
            1. 训练天数 (50%)
            2. 交易次数 (30%)
            3. 数据多样性 (20%)

        参数:
            history: 训练历史

        返回:
            训练充分度得分
        """
        details: dict[str, float] = {}

        # 1. 训练天数评分 (50%)
        days = history.training_days
        if days >= 180:  # 6个月
            days_score = 1.0
        elif days >= 120:  # 4个月
            days_score = 0.8 + (days - 120) / 60 * 0.2
        elif days >= 90:  # 3个月（最低要求）
            days_score = 0.6 + (days - 90) / 30 * 0.2
        else:
            days_score = days / 90 * 0.6
        details["days_score"] = days_score

        # 2. 交易次数评分 (30%)
        trades = history.trade_count
        if trades >= 500:
            trades_score = 1.0
        elif trades >= 300:
            trades_score = 0.8 + (trades - 300) / 200 * 0.2
        elif trades >= 100:
            trades_score = 0.6 + (trades - 100) / 200 * 0.2
        else:
            trades_score = trades / 100 * 0.6
        details["trades_score"] = trades_score

        # 3. 数据多样性评分 (20%)
        # 检查是否覆盖了不同的市场周期
        diversity_score = len(set(history.market_regimes)) / 5 if history.market_regimes else 0
        details["diversity_score"] = min(1.0, diversity_score)

        # 综合得分
        total_score = (
            days_score * 0.5 +
            trades_score * 0.3 +
            details["diversity_score"] * 0.2
        )

        reason = f"训练{days}天, {trades}笔交易, 多样性{details['diversity_score']:.1%}"

        return MaturityScore(
            dimension="训练充分度",
            score=total_score,
            weight=self.WEIGHT_TRAINING_SUFFICIENCY,
            details=details,
            reason=reason,
        )

    def _evaluate_consistency(self, history: TrainingHistory) -> MaturityScore:
        """评估一致性.

        子指标:
            1. 信号与收益的相关性 (50%)
            2. 滚动窗口表现一致性 (50%)

        参数:
            history: 训练历史

        返回:
            一致性得分
        """
        details: dict[str, float] = {}

        # 1. 信号与收益相关性 (50%)
        signal_correlation = self._calculate_signal_return_correlation(
            history.daily_signals, history.daily_returns
        )
        # 相关性应该为正
        corr_score = max(0, signal_correlation)
        details["signal_correlation"] = corr_score

        # 2. 滚动窗口一致性 (50%)
        rolling_consistency = self._calculate_rolling_consistency(history.daily_returns)
        details["rolling_consistency"] = rolling_consistency

        # 综合得分
        total_score = (
            corr_score * 0.5 +
            rolling_consistency * 0.5
        )

        reason = f"信号相关{corr_score:.2f}, 滚动一致{rolling_consistency:.1%}"

        return MaturityScore(
            dimension="一致性检验",
            score=total_score,
            weight=self.WEIGHT_CONSISTENCY,
            details=details,
            reason=reason,
        )

    def _get_maturity_level(self, score: float) -> MaturityLevel:
        """获取成熟度级别.

        参数:
            score: 总分

        返回:
            成熟度级别
        """
        if score >= 0.8:
            return MaturityLevel.MATURE
        if score >= 0.6:
            return MaturityLevel.MATURING
        if score >= 0.4:
            return MaturityLevel.GROWING
        if score >= 0.2:
            return MaturityLevel.DEVELOPING
        return MaturityLevel.EMBRYONIC

    def _calculate_monthly_consistency(self, daily_returns: list[float]) -> float:
        """计算月度收益一致性.

        参数:
            daily_returns: 每日收益率

        返回:
            一致性得分 [0, 1]
        """
        if len(daily_returns) < 60:  # 至少2个月数据
            return 0.0

        # 按月分组（假设每月20个交易日）
        monthly_returns = []
        for i in range(0, len(daily_returns), 20):
            month_data = daily_returns[i:i + 20]
            if len(month_data) >= 15:  # 至少15天
                monthly_return = sum(month_data)
                monthly_returns.append(monthly_return)

        if len(monthly_returns) < 2:
            return 0.0

        # 计算正收益月份比例
        positive_months = sum(1 for r in monthly_returns if r > 0)
        consistency = positive_months / len(monthly_returns)

        return consistency

    def _calculate_regime_consistency(
        self,
        daily_returns: list[float],
        market_regimes: list[str],
    ) -> float:
        """计算不同市场状态下的表现一致性.

        参数:
            daily_returns: 每日收益率
            market_regimes: 市场状态序列

        返回:
            一致性得分 [0, 1]
        """
        if not daily_returns or not market_regimes:
            return 0.0

        if len(daily_returns) != len(market_regimes):
            return 0.0

        # 按状态分组计算平均收益
        regime_returns: dict[str, list[float]] = {}
        for ret, regime in zip(daily_returns, market_regimes):
            if regime not in regime_returns:
                regime_returns[regime] = []
            regime_returns[regime].append(ret)

        if len(regime_returns) < 2:
            return 0.5  # 只有一种状态，给中等分

        # 计算各状态的平均收益
        regime_means = []
        for returns in regime_returns.values():
            if returns:
                regime_means.append(sum(returns) / len(returns))

        # 计算状态间收益的一致性（正收益状态比例）
        positive_regimes = sum(1 for m in regime_means if m > 0)
        consistency = positive_regimes / len(regime_means)

        return consistency

    def _calculate_survival_score(self, drawdowns: list[float]) -> float:
        """计算极端行情存活能力.

        参数:
            drawdowns: 回撤序列

        返回:
            存活得分 [0, 1]
        """
        if not drawdowns:
            return 0.5

        # 找到最大回撤
        max_dd = min(drawdowns)  # 回撤是负数

        # 检查从最大回撤恢复的速度
        # 如果能恢复到最大回撤的50%以内，给高分
        if max_dd >= -0.05:  # 回撤小于5%
            return 1.0

        # 找到最大回撤后的恢复情况
        max_dd_idx = drawdowns.index(max_dd)
        recovery_dd = drawdowns[max_dd_idx:] if max_dd_idx < len(drawdowns) else []

        if not recovery_dd:
            return 0.5

        # 计算恢复程度
        final_dd = recovery_dd[-1] if recovery_dd else max_dd
        recovery_ratio = 1 - (final_dd / max_dd) if max_dd != 0 else 1

        return max(0, min(1, recovery_ratio))

    def _calculate_signal_return_correlation(
        self,
        signals: list[float],
        returns: list[float],
    ) -> float:
        """计算信号与收益的相关性.

        参数:
            signals: 信号序列
            returns: 收益序列

        返回:
            相关系数 [-1, 1]
        """
        if not signals or not returns:
            return 0.0

        n = min(len(signals), len(returns))
        if n < 10:
            return 0.0

        signals = signals[:n]
        returns = returns[:n]

        # 计算相关系数
        mean_s = sum(signals) / n
        mean_r = sum(returns) / n

        cov = sum((s - mean_s) * (r - mean_r) for s, r in zip(signals, returns)) / n
        std_s = math.sqrt(sum((s - mean_s) ** 2 for s in signals) / n)
        std_r = math.sqrt(sum((r - mean_r) ** 2 for r in returns) / n)

        if std_s < 1e-8 or std_r < 1e-8:
            return 0.0

        correlation = cov / (std_s * std_r)
        return max(-1, min(1, correlation))

    def _calculate_rolling_consistency(
        self,
        daily_returns: list[float],
        window: int = 20,
    ) -> float:
        """计算滚动窗口一致性.

        参数:
            daily_returns: 每日收益率
            window: 窗口大小

        返回:
            一致性得分 [0, 1]
        """
        if len(daily_returns) < window * 3:
            return 0.0

        # 计算滚动窗口的夏普比率
        rolling_sharpes = []
        for i in range(len(daily_returns) - window + 1):
            window_returns = daily_returns[i:i + window]
            mean = sum(window_returns) / window
            variance = sum((r - mean) ** 2 for r in window_returns) / window
            std = math.sqrt(variance) if variance > 0 else 1e-8
            sharpe = mean / std * math.sqrt(252)
            rolling_sharpes.append(sharpe)

        if not rolling_sharpes:
            return 0.0

        # 计算正夏普的比例
        positive_sharpes = sum(1 for s in rolling_sharpes if s > 0)
        consistency = positive_sharpes / len(rolling_sharpes)

        return consistency

    @property
    def evaluation_count(self) -> int:
        """评估次数."""
        return self._evaluation_count
