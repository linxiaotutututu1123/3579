"""训练监控系统 (军规级 v3.0).

提供实时训练进度监控，让操作人员随时了解训练状态。

功能特性:
    - 实时进度显示
    - 训练历史记录
    - 预估完成时间
    - 告警通知

示例:
    monitor = TrainingMonitor()
    session = monitor.start_session("ppo_strategy_v1")

    # 每日更新
    monitor.record_daily(session.session_id, daily_data)

    # 查看进度
    progress = monitor.get_progress(session.session_id)
    print(progress.display())
"""

from __future__ import annotations

import hashlib
import json
import math
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import ClassVar

from src.strategy.experimental.maturity_evaluator import (
    MaturityEvaluator,
    MaturityLevel,
    MaturityReport,
    TrainingHistory,
)


class TrainingStatus(Enum):
    """训练状态."""

    NOT_STARTED = "not_started"   # 未开始
    RUNNING = "running"           # 训练中
    PAUSED = "paused"             # 暂停
    COMPLETED = "completed"       # 完成
    FAILED = "failed"             # 失败
    CANCELLED = "cancelled"       # 取消


@dataclass
class TrainingSession:
    """训练会话.

    属性:
        session_id: 会话ID
        strategy_id: 策略ID
        strategy_name: 策略名称
        strategy_type: 策略类型
        start_time: 开始时间
        status: 状态
        history: 训练历史
        last_update: 最后更新时间
        notes: 备注
    """

    session_id: str
    strategy_id: str
    strategy_name: str
    strategy_type: str
    start_time: datetime
    status: TrainingStatus = TrainingStatus.NOT_STARTED
    history: TrainingHistory | None = None
    last_update: datetime | None = None
    notes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        """转换为字典."""
        return {
            "session_id": self.session_id,
            "strategy_id": self.strategy_id,
            "strategy_name": self.strategy_name,
            "strategy_type": self.strategy_type,
            "start_time": self.start_time.isoformat(),
            "status": self.status.value,
            "last_update": self.last_update.isoformat() if self.last_update else None,
            "training_days": self.history.training_days if self.history else 0,
            "notes": self.notes,
        }


@dataclass
class TrainingProgress:
    """训练进度.

    属性:
        session: 训练会话
        maturity_report: 成熟度报告
        progress_pct: 进度百分比（基于成熟度）
        days_elapsed: 已训练天数
        days_remaining: 预估剩余天数
        eta: 预估完成时间
        trend: 趋势（improving/stable/declining）
        alerts: 告警信息
    """

    session: TrainingSession
    maturity_report: MaturityReport | None
    progress_pct: float
    days_elapsed: int
    days_remaining: int
    eta: datetime | None
    trend: str
    alerts: list[str]

    def display(self) -> str:
        """生成显示文本.

        返回:
            人类可读的进度文本
        """
        lines = [
            "",
            "┌" + "─" * 58 + "┐",
            "│" + "        📊 策略训练进度监控面板".center(50) + "│",
            "├" + "─" * 58 + "┤",
            "",
        ]

        # 基本信息
        lines.append(f"  策略名称: {self.session.strategy_name}")
        lines.append(f"  策略类型: {self.session.strategy_type}")
        lines.append(f"  会话ID: {self.session.session_id[:8]}...")
        lines.append(f"  状态: {self._status_text()}")
        lines.append("")

        # 进度条
        lines.append("  训练进度:")
        lines.append(f"  {self._big_progress_bar(self.progress_pct)}")
        lines.append(f"  当前成熟度: {self.progress_pct:.1%} / 80% (启用门槛)")
        lines.append("")

        # 时间信息
        lines.append("  📅 时间统计:")
        lines.append(f"     已训练: {self.days_elapsed} 天")
        lines.append(f"     最低要求: 90 天")

        if self.days_remaining > 0:
            lines.append(f"     预估剩余: {self.days_remaining} 天")
            if self.eta:
                lines.append(f"     预估完成: {self.eta.strftime('%Y-%m-%d')}")
        else:
            lines.append("     ✓ 已达到最低训练时间要求")

        lines.append("")

        # 维度得分
        if self.maturity_report:
            lines.append("  📈 各维度得分:")
            for score in self.maturity_report.dimension_scores:
                emoji = "✅" if score.is_passing else "❌"
                bar = self._mini_progress_bar(score.score)
                lines.append(f"     {emoji} {score.dimension}: {bar} {score.score:.1%}")

        lines.append("")

        # 趋势
        trend_emoji = {"improving": "📈", "stable": "➡️", "declining": "📉"}.get(
            self.trend, "❓"
        )
        lines.append(f"  趋势: {trend_emoji} {self.trend}")
        lines.append("")

        # 告警
        if self.alerts:
            lines.append("  ⚠️ 告警:")
            for alert in self.alerts:
                lines.append(f"     • {alert}")
            lines.append("")

        # 启用状态
        if self.progress_pct >= 0.80 and self.days_elapsed >= 90:
            lines.append("  ✅ 策略已达到启用标准！可以申请人工审批。")
        else:
            if self.progress_pct < 0.80:
                diff = 0.80 - self.progress_pct
                lines.append(f"  ⏳ 距离启用门槛还差: {diff:.1%}")
            if self.days_elapsed < 90:
                diff_days = 90 - self.days_elapsed
                lines.append(f"  ⏳ 距离最低训练时间还差: {diff_days} 天")

        lines.append("")
        lines.append("└" + "─" * 58 + "┘")

        return "\n".join(lines)

    def _status_text(self) -> str:
        """状态文本."""
        status_map = {
            TrainingStatus.NOT_STARTED: "⚪ 未开始",
            TrainingStatus.RUNNING: "🟢 训练中",
            TrainingStatus.PAUSED: "🟡 暂停",
            TrainingStatus.COMPLETED: "🔵 完成",
            TrainingStatus.FAILED: "🔴 失败",
            TrainingStatus.CANCELLED: "⚫ 取消",
        }
        return status_map.get(self.session.status, "❓ 未知")

    def _big_progress_bar(self, pct: float, width: int = 40) -> str:
        """大进度条."""
        filled = int(pct * width)
        empty = width - filled

        # 80%位置的标记
        threshold_pos = int(0.80 * width)

        bar = ""
        for i in range(width):
            if i < filled:
                if pct >= 0.80:
                    bar += "█"
                else:
                    bar += "▓"
            elif i == threshold_pos:
                bar += "|"  # 80%标记
            else:
                bar += "░"

        return f"[{bar}] {pct:.1%}"

    def _mini_progress_bar(self, pct: float, width: int = 15) -> str:
        """小进度条."""
        filled = int(pct * width)
        empty = width - filled
        return "█" * filled + "░" * empty


class TrainingMonitor:
    """训练监控器.

    监控所有实验性策略的训练进度。
    """

    # 最低训练天数
    MIN_TRAINING_DAYS: ClassVar[int] = 90

    # 启用门槛
    ACTIVATION_THRESHOLD: ClassVar[float] = 0.80

    def __init__(self, evaluator: MaturityEvaluator | None = None) -> None:
        """初始化训练监控器.

        参数:
            evaluator: 成熟度评估器
        """
        self._evaluator = evaluator or MaturityEvaluator()
        self._sessions: dict[str, TrainingSession] = {}
        self._progress_history: dict[str, list[float]] = {}  # 成熟度历史

    def start_session(
        self,
        strategy_id: str,
        strategy_name: str,
        strategy_type: str,
    ) -> TrainingSession:
        """开始训练会话.

        参数:
            strategy_id: 策略ID
            strategy_name: 策略名称
            strategy_type: 策略类型

        返回:
            训练会话
        """
        session_id = str(uuid.uuid4())

        history = TrainingHistory(
            strategy_id=strategy_id,
            start_date=datetime.now(),
        )

        session = TrainingSession(
            session_id=session_id,
            strategy_id=strategy_id,
            strategy_name=strategy_name,
            strategy_type=strategy_type,
            start_time=datetime.now(),
            status=TrainingStatus.RUNNING,
            history=history,
            last_update=datetime.now(),
        )

        self._sessions[session_id] = session
        self._progress_history[session_id] = []

        return session

    def record_daily(
        self,
        session_id: str,
        daily_return: float,
        daily_position: float,
        daily_signal: float,
        market_regime: str,
        drawdown: float,
    ) -> None:
        """记录每日数据.

        参数:
            session_id: 会话ID
            daily_return: 日收益率
            daily_position: 日持仓
            daily_signal: 日信号
            market_regime: 市场状态
            drawdown: 回撤
        """
        session = self._sessions.get(session_id)
        if not session or not session.history:
            return

        session.history.daily_returns.append(daily_return)
        session.history.daily_positions.append(daily_position)
        session.history.daily_signals.append(daily_signal)
        session.history.market_regimes.append(market_regime)
        session.history.drawdowns.append(drawdown)

        session.last_update = datetime.now()

        # 更新统计指标
        self._update_statistics(session)

        # 记录成熟度进度
        report = self._evaluator.evaluate(session.history)
        self._progress_history[session_id].append(report.total_score)

    def _update_statistics(self, session: TrainingSession) -> None:
        """更新统计指标.

        参数:
            session: 训练会话
        """
        history = session.history
        if not history or not history.daily_returns:
            return

        returns = history.daily_returns

        # 计算夏普比率
        if len(returns) >= 20:
            mean_return = sum(returns) / len(returns)
            variance = sum((r - mean_return) ** 2 for r in returns) / len(returns)
            std_return = math.sqrt(variance) if variance > 0 else 1e-8
            history.sharpe_ratio = mean_return / std_return * math.sqrt(252)

        # 计算最大回撤
        if history.drawdowns:
            history.max_drawdown = min(history.drawdowns)

        # 计算卡玛比率
        if history.max_drawdown != 0 and len(returns) >= 20:
            annual_return = sum(returns) * 252 / len(returns)
            history.calmar_ratio = annual_return / abs(history.max_drawdown)

        # 模拟胜率和盈亏比（实际应基于交易记录）
        positive_returns = sum(1 for r in returns if r > 0)
        history.win_rate = positive_returns / len(returns) if returns else 0

        positive_sum = sum(r for r in returns if r > 0)
        negative_sum = abs(sum(r for r in returns if r < 0))
        history.profit_factor = positive_sum / negative_sum if negative_sum > 0 else 1.0

        history.trade_count = len(returns)  # 简化为日数

    def get_progress(self, session_id: str) -> TrainingProgress | None:
        """获取训练进度.

        参数:
            session_id: 会话ID

        返回:
            训练进度
        """
        session = self._sessions.get(session_id)
        if not session or not session.history:
            return None

        # 评估成熟度
        report = self._evaluator.evaluate(session.history)

        # 计算天数
        days_elapsed = session.history.training_days
        days_remaining = max(0, self.MIN_TRAINING_DAYS - days_elapsed)

        # 计算ETA
        if days_remaining > 0:
            eta = datetime.now() + timedelta(days=days_remaining)
        elif report.total_score < self.ACTIVATION_THRESHOLD:
            # 预估还需要多少天达到80%
            history_scores = self._progress_history.get(session_id, [])
            if len(history_scores) >= 7:
                # 计算最近7天的平均进步
                recent_progress = (history_scores[-1] - history_scores[-7]) / 7
                if recent_progress > 0:
                    remaining_pct = self.ACTIVATION_THRESHOLD - report.total_score
                    est_days = int(remaining_pct / recent_progress)
                    eta = datetime.now() + timedelta(days=est_days)
                else:
                    eta = None
            else:
                eta = None
        else:
            eta = None  # 已达标

        # 判断趋势
        trend = self._calculate_trend(session_id)

        # 生成告警
        alerts = self._generate_alerts(session, report)

        return TrainingProgress(
            session=session,
            maturity_report=report,
            progress_pct=report.total_score,
            days_elapsed=days_elapsed,
            days_remaining=days_remaining,
            eta=eta,
            trend=trend,
            alerts=alerts,
        )

    def _calculate_trend(self, session_id: str) -> str:
        """计算趋势.

        参数:
            session_id: 会话ID

        返回:
            趋势
        """
        history = self._progress_history.get(session_id, [])
        if len(history) < 7:
            return "stable"

        recent = history[-7:]
        avg_recent = sum(recent) / len(recent)
        previous = history[-14:-7] if len(history) >= 14 else history[:-7]
        avg_previous = sum(previous) / len(previous) if previous else avg_recent

        diff = avg_recent - avg_previous
        if diff > 0.01:  # 1%提升
            return "improving"
        if diff < -0.01:  # 1%下降
            return "declining"
        return "stable"

    def _generate_alerts(
        self,
        session: TrainingSession,
        report: MaturityReport,
    ) -> list[str]:
        """生成告警.

        参数:
            session: 训练会话
            report: 成熟度报告

        返回:
            告警列表
        """
        alerts: list[str] = []

        # 检查各维度是否有明显短板
        for score in report.dimension_scores:
            if score.score < 0.4:
                alerts.append(f"{score.dimension}得分过低 ({score.score:.1%})，需要重点关注")
            elif score.score < 0.6:
                alerts.append(f"{score.dimension}未达标 ({score.score:.1%})，需要改善")

        # 检查趋势
        trend = self._calculate_trend(session.session_id)
        if trend == "declining":
            alerts.append("成熟度呈下降趋势，请检查策略表现")

        # 检查训练时间
        if session.history:
            days = session.history.training_days
            if days < 30:
                alerts.append(f"训练天数较少 ({days}天)，建议至少训练30天后再评估")
            elif days >= 90 and report.total_score < 0.60:
                alerts.append("已训练90天但成熟度仍低于60%，建议审视策略逻辑")

        return alerts

    def get_all_sessions(self) -> list[TrainingSession]:
        """获取所有会话.

        返回:
            会话列表
        """
        return list(self._sessions.values())

    def get_session(self, session_id: str) -> TrainingSession | None:
        """获取会话.

        参数:
            session_id: 会话ID

        返回:
            训练会话
        """
        return self._sessions.get(session_id)

    def pause_session(self, session_id: str) -> bool:
        """暂停会话.

        参数:
            session_id: 会话ID

        返回:
            是否成功
        """
        session = self._sessions.get(session_id)
        if session and session.status == TrainingStatus.RUNNING:
            session.status = TrainingStatus.PAUSED
            return True
        return False

    def resume_session(self, session_id: str) -> bool:
        """恢复会话.

        参数:
            session_id: 会话ID

        返回:
            是否成功
        """
        session = self._sessions.get(session_id)
        if session and session.status == TrainingStatus.PAUSED:
            session.status = TrainingStatus.RUNNING
            return True
        return False

    def cancel_session(self, session_id: str, reason: str) -> bool:
        """取消会话.

        参数:
            session_id: 会话ID
            reason: 取消原因

        返回:
            是否成功
        """
        session = self._sessions.get(session_id)
        if session:
            session.status = TrainingStatus.CANCELLED
            session.notes.append(f"取消原因: {reason}")
            return True
        return False

    def add_note(self, session_id: str, note: str) -> bool:
        """添加备注.

        参数:
            session_id: 会话ID
            note: 备注

        返回:
            是否成功
        """
        session = self._sessions.get(session_id)
        if session:
            session.notes.append(f"[{datetime.now().strftime('%Y-%m-%d')}] {note}")
            return True
        return False

    def export_report(self, session_id: str) -> str | None:
        """导出报告.

        参数:
            session_id: 会话ID

        返回:
            JSON报告
        """
        progress = self.get_progress(session_id)
        if not progress:
            return None

        report = {
            "session": progress.session.to_dict(),
            "progress": {
                "maturity_pct": progress.progress_pct,
                "days_elapsed": progress.days_elapsed,
                "days_remaining": progress.days_remaining,
                "eta": progress.eta.isoformat() if progress.eta else None,
                "trend": progress.trend,
            },
            "maturity_report": progress.maturity_report.to_dict() if progress.maturity_report else None,
            "alerts": progress.alerts,
            "generated_at": datetime.now().isoformat(),
        }

        return json.dumps(report, ensure_ascii=False, indent=2)
