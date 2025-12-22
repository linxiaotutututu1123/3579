"""推理引擎模块 - 实现思维链和思维树推理.

本模块提供高级推理能力，支持:
- 思维链 (Chain of Thought, CoT): 线性逐步推理
- 思维树 (Tree of Thought, ToT): 探索多个推理路径并选择最优解

架构设计:
    ThoughtNode: 表示推理树中的单个节点
    ReasoningResult: 推理过程的最终结果
    ReasoningEngine: 核心推理引擎，协调 LLM 进行复杂推理

Example:
    >>> engine = ReasoningEngine(llm_client)
    >>> result = await engine.chain_of_thought(
    ...     problem="设计一个高可用的分布式缓存系统",
    ...     context={"constraints": ["低延迟", "高吞吐"]}
    ... )
    >>> print(result.conclusion)
"""

from __future__ import annotations

import asyncio
import json
import re
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING, Any, Protocol

from chairman_agents.core.types import generate_id

if TYPE_CHECKING:
    pass


# =============================================================================
# 类型定义
# =============================================================================


class LLMClientProtocol(Protocol):
    """LLM 客户端协议，定义推理引擎所需的接口."""

    async def generate(
        self,
        prompt: str,
        *,
        temperature: float = 0.7,
        max_tokens: int = 2048,
    ) -> str:
        """生成文本响应.

        Args:
            prompt: 输入提示
            temperature: 采样温度
            max_tokens: 最大生成 token 数

        Returns:
            生成的文本响应
        """
        ...


class ReasoningStrategy(Enum):
    """推理策略枚举."""

    CHAIN_OF_THOUGHT = "chain_of_thought"
    """思维链 - 线性逐步推理"""

    TREE_OF_THOUGHT = "tree_of_thought"
    """思维树 - 多路径探索"""

    SELF_CONSISTENCY = "self_consistency"
    """自一致性 - 多次采样取多数"""

    REFLECTION = "reflection"
    """反思推理 - 迭代优化"""


# =============================================================================
# 数据类
# =============================================================================


@dataclass
class ThoughtNode:
    """推理树中的思考节点.

    表示推理过程中的一个思考步骤，可以形成链式或树状结构。

    Attributes:
        id: 节点唯一标识符
        thought: 思考内容
        depth: 节点在树中的深度（根节点深度为 0）
        score: 思考质量评分 (0.0-1.0)
        parent_id: 父节点 ID（根节点为 None）
        children_ids: 子节点 ID 列表
        metadata: 附加元数据

    Example:
        >>> node = ThoughtNode(
        ...     id="thought_001",
        ...     thought="首先分析问题的核心约束...",
        ...     depth=1,
        ...     score=0.85,
        ...     parent_id="root_000"
        ... )
    """

    id: str = field(default_factory=lambda: generate_id("thought"))
    """节点唯一标识符"""

    thought: str = ""
    """思考内容"""

    depth: int = 0
    """节点在树中的深度"""

    score: float = 0.0
    """思考质量评分 (0.0-1.0)"""

    parent_id: str | None = None
    """父节点 ID"""

    children_ids: list[str] = field(default_factory=list)
    """子节点 ID 列表"""

    metadata: dict[str, Any] = field(default_factory=dict)
    """附加元数据"""

    created_at: datetime = field(default_factory=datetime.now)
    """创建时间戳"""

    def __repr__(self) -> str:
        """返回节点的简洁表示."""
        thought_preview = (
            self.thought[:50] + "..." if len(self.thought) > 50 else self.thought
        )
        return (
            f"ThoughtNode(id={self.id!r}, depth={self.depth}, "
            f"score={self.score:.2f}, thought={thought_preview!r})"
        )

    @property
    def is_root(self) -> bool:
        """判断是否为根节点."""
        return self.parent_id is None

    @property
    def is_leaf(self) -> bool:
        """判断是否为叶子节点."""
        return len(self.children_ids) == 0

    @property
    def has_children(self) -> bool:
        """判断是否有子节点."""
        return len(self.children_ids) > 0


@dataclass
class ReasoningResult:
    """推理结果数据类.

    包含推理过程的最终结论、置信度、推理路径和备选方案。

    Attributes:
        conclusion: 最终结论
        confidence: 置信度 (0.0-1.0)
        reasoning_path: 从根到结论的推理路径
        alternatives: 备选结论列表
        metadata: 附加元数据

    Example:
        >>> result = ReasoningResult(
        ...     conclusion="推荐使用 Redis Cluster 架构",
        ...     confidence=0.92,
        ...     reasoning_path=[root_node, step1, step2, conclusion_node],
        ...     alternatives=["使用 Memcached 集群", "自研分布式缓存"]
        ... )
    """

    conclusion: str = ""
    """最终结论"""

    confidence: float = 0.0
    """置信度 (0.0-1.0)"""

    reasoning_path: list[ThoughtNode] = field(default_factory=list)
    """推理路径（从根到结论的节点序列）"""

    alternatives: list[str] = field(default_factory=list)
    """备选结论列表"""

    metadata: dict[str, Any] = field(default_factory=dict)
    """附加元数据"""

    strategy_used: ReasoningStrategy = ReasoningStrategy.CHAIN_OF_THOUGHT
    """使用的推理策略"""

    total_nodes_explored: int = 0
    """探索的总节点数"""

    execution_time_seconds: float = 0.0
    """推理执行时间（秒）"""

    def __repr__(self) -> str:
        """返回结果的简洁表示."""
        conclusion_preview = (
            self.conclusion[:50] + "..."
            if len(self.conclusion) > 50
            else self.conclusion
        )
        return (
            f"ReasoningResult(conclusion={conclusion_preview!r}, "
            f"confidence={self.confidence:.2f}, "
            f"path_length={len(self.reasoning_path)})"
        )

    @property
    def path_length(self) -> int:
        """推理路径长度."""
        return len(self.reasoning_path)

    @property
    def average_path_score(self) -> float:
        """推理路径的平均分数."""
        if not self.reasoning_path:
            return 0.0
        return sum(node.score for node in self.reasoning_path) / len(
            self.reasoning_path
        )

    def format_reasoning_chain(self) -> str:
        """格式化输出推理链.

        Returns:
            格式化的推理链字符串
        """
        if not self.reasoning_path:
            return "无推理路径"

        lines = ["推理链:"]
        for i, node in enumerate(self.reasoning_path):
            prefix = "  " * node.depth
            score_str = f"[{node.score:.2f}]" if node.score > 0 else ""
            lines.append(f"{prefix}Step {i + 1} {score_str}: {node.thought}")

        lines.append(f"\n结论 (置信度: {self.confidence:.2f}): {self.conclusion}")
        return "\n".join(lines)


# =============================================================================
# 推理引擎
# =============================================================================


class ReasoningEngine:
    """推理引擎 - 实现思维链和思维树推理.

    提供多种推理策略，协调 LLM 进行复杂的多步骤推理。

    Attributes:
        llm_client: LLM 客户端实例
        max_depth: 推理树的最大深度
        branching_factor: 每个节点的默认分支数
        node_index: 节点索引，用于快速查找和路径追溯

    Example:
        >>> engine = ReasoningEngine(
        ...     llm_client=my_llm_client,
        ...     max_depth=5,
        ...     branching_factor=3
        ... )
        >>> result = await engine.tree_of_thought(
        ...     problem="如何优化数据库查询性能？",
        ...     num_branches=4
        ... )
    """

    def __init__(
        self,
        llm_client: Any,  # LLMClientProtocol
        max_depth: int = 5,
        branching_factor: int = 3,
        temperature: float = 0.7,
        evaluation_temperature: float = 0.3,
    ) -> None:
        """初始化推理引擎.

        Args:
            llm_client: LLM 客户端，需实现 generate 方法
            max_depth: 推理树的最大深度限制
            branching_factor: 默认分支因子（每步生成的思考数）
            temperature: 生成思考时的采样温度
            evaluation_temperature: 评估思考时的采样温度
        """
        self.llm_client = llm_client
        self.max_depth = max_depth
        self.branching_factor = branching_factor
        self.temperature = temperature
        self.evaluation_temperature = evaluation_temperature

        # 节点索引：id -> ThoughtNode
        # 用于路径追溯和快速查找
        self.node_index: dict[str, ThoughtNode] = {}

    def _register_node(self, node: ThoughtNode) -> None:
        """注册节点到索引.

        Args:
            node: 要注册的思考节点
        """
        self.node_index[node.id] = node

    def _clear_index(self) -> None:
        """清空节点索引（开始新的推理会话时调用）."""
        self.node_index.clear()

    # =========================================================================
    # 思维链推理 (Chain of Thought)
    # =========================================================================

    async def chain_of_thought(
        self,
        problem: str,
        context: dict[str, Any] | None = None,
    ) -> ReasoningResult:
        """思维链推理 - 线性逐步分析.

        通过一系列连贯的推理步骤，逐步分解和解决问题。
        每一步都基于前一步的结果，形成线性推理链。

        Args:
            problem: 需要解决的问题描述
            context: 可选的上下文信息（约束、背景等）

        Returns:
            包含结论和推理路径的 ReasoningResult

        Example:
            >>> result = await engine.chain_of_thought(
            ...     problem="设计一个用户认证系统",
            ...     context={
            ...         "requirements": ["支持 OAuth2", "支持 MFA"],
            ...         "constraints": ["延迟 < 100ms"]
            ...     }
            ... )
        """
        import time

        start_time = time.time()
        self._clear_index()
        context = context or {}

        # 创建根节点（问题陈述）
        root_node = ThoughtNode(
            id=generate_id("thought"),
            thought=f"问题: {problem}",
            depth=0,
            score=1.0,
            parent_id=None,
            metadata={"type": "root", "problem": problem, "context": context},
        )
        self._register_node(root_node)

        reasoning_path: list[ThoughtNode] = [root_node]
        current_thought = problem

        # 逐步推理
        for step in range(1, self.max_depth + 1):
            # 生成下一步思考
            next_thought = await self._generate_next_step(
                current_thought=current_thought,
                step_number=step,
                total_steps=self.max_depth,
                context=context,
                previous_thoughts=[n.thought for n in reasoning_path],
            )

            # 评估思考质量
            score = await self._evaluate_thought(
                thought=next_thought,
                problem=problem,
                context=context,
            )

            # 创建新节点
            new_node = ThoughtNode(
                id=generate_id("thought"),
                thought=next_thought,
                depth=step,
                score=score,
                parent_id=reasoning_path[-1].id,
                metadata={"step": step, "type": "reasoning_step"},
            )
            self._register_node(new_node)

            # 更新父节点的子节点列表
            reasoning_path[-1].children_ids.append(new_node.id)
            reasoning_path.append(new_node)

            current_thought = next_thought

            # 检查是否可以得出结论
            if await self._is_conclusion_ready(
                thoughts=[n.thought for n in reasoning_path],
                problem=problem,
                context=context,
            ):
                break

        # 生成最终结论
        conclusion = await self._synthesize_conclusion(
            reasoning_path=reasoning_path,
            problem=problem,
            context=context,
        )

        # 计算置信度
        confidence = self._calculate_confidence(reasoning_path)

        execution_time = time.time() - start_time

        return ReasoningResult(
            conclusion=conclusion,
            confidence=confidence,
            reasoning_path=reasoning_path,
            alternatives=[],
            metadata={
                "strategy": "chain_of_thought",
                "problem": problem,
                "context": context,
                "steps_taken": len(reasoning_path) - 1,
            },
            strategy_used=ReasoningStrategy.CHAIN_OF_THOUGHT,
            total_nodes_explored=len(reasoning_path),
            execution_time_seconds=execution_time,
        )

    async def _generate_next_step(
        self,
        current_thought: str,
        step_number: int,
        total_steps: int,
        context: dict[str, Any],
        previous_thoughts: list[str],
    ) -> str:
        """生成下一步推理思考.

        Args:
            current_thought: 当前思考内容
            step_number: 当前步骤编号
            total_steps: 总步骤数
            context: 上下文信息
            previous_thoughts: 之前的思考列表

        Returns:
            下一步思考内容
        """
        context_str = json.dumps(context, ensure_ascii=False) if context else "无"
        previous_str = "\n".join(
            f"  Step {i}: {t}" for i, t in enumerate(previous_thoughts, 1)
        )

        prompt = f"""你是一个严谨的推理专家。请基于当前的分析，进行下一步推理。

## 背景上下文
{context_str}

## 之前的推理步骤
{previous_str}

## 当前状态
步骤 {step_number}/{total_steps}

## 任务
请进行下一步推理分析。要求:
1. 基于之前的分析，深入探讨一个具体方面
2. 提供具体的分析、推导或解决方案
3. 保持逻辑连贯性
4. 如果这是最后几步，开始收敛到具体结论

请直接输出你的思考内容，不要有额外格式:"""

        response = await self.llm_client.generate(
            prompt,
            temperature=self.temperature,
            max_tokens=1024,
        )

        return response.strip()

    async def _is_conclusion_ready(
        self,
        thoughts: list[str],
        problem: str,
        context: dict[str, Any],
    ) -> bool:
        """判断是否可以得出结论.

        Args:
            thoughts: 所有思考内容列表
            problem: 原始问题
            context: 上下文信息

        Returns:
            是否可以得出结论
        """
        if len(thoughts) < 3:
            return False

        prompt = f"""分析以下推理过程，判断是否已经可以得出结论。

问题: {problem}

推理步骤:
{chr(10).join(f'{i}. {t}' for i, t in enumerate(thoughts, 1))}

请判断:
1. 是否已经充分分析了问题的各个方面？
2. 是否已经有足够的依据得出结论？
3. 继续推理是否会带来实质性新信息？

请只回答 YES 或 NO:"""

        response = await self.llm_client.generate(
            prompt,
            temperature=0.1,
            max_tokens=10,
        )

        return "YES" in response.upper()

    async def _synthesize_conclusion(
        self,
        reasoning_path: list[ThoughtNode],
        problem: str,
        context: dict[str, Any],
    ) -> str:
        """综合推理路径生成最终结论.

        Args:
            reasoning_path: 推理路径
            problem: 原始问题
            context: 上下文信息

        Returns:
            最终结论
        """
        thoughts_str = "\n".join(
            f"Step {i}: {node.thought}" for i, node in enumerate(reasoning_path, 1)
        )

        prompt = f"""基于以下推理过程，生成简洁明确的最终结论。

## 原始问题
{problem}

## 推理过程
{thoughts_str}

## 要求
请综合所有分析，给出:
1. 明确的结论或建议
2. 结论的核心依据（1-2 句话）

请直接输出结论:"""

        response = await self.llm_client.generate(
            prompt,
            temperature=0.3,
            max_tokens=512,
        )

        return response.strip()

    # =========================================================================
    # 思维树推理 (Tree of Thought)
    # =========================================================================

    async def tree_of_thought(
        self,
        problem: str,
        context: dict[str, Any] | None = None,
        num_branches: int = 3,
    ) -> ReasoningResult:
        """思维树推理 - 探索多个推理路径.

        构建推理树，在每个节点生成多个可能的思考分支，
        通过评估选择最优路径。支持回溯和剪枝。

        Args:
            problem: 需要解决的问题描述
            context: 可选的上下文信息
            num_branches: 每个节点的分支数（默认 3）

        Returns:
            包含最优推理路径的 ReasoningResult

        Example:
            >>> result = await engine.tree_of_thought(
            ...     problem="选择最适合的微服务架构模式",
            ...     context={"team_size": 10, "scale": "中型"},
            ...     num_branches=4
            ... )
        """
        import time

        start_time = time.time()
        self._clear_index()
        context = context or {}

        # 创建根节点
        root_node = ThoughtNode(
            id=generate_id("thought"),
            thought=f"问题分析: {problem}",
            depth=0,
            score=1.0,
            parent_id=None,
            metadata={"type": "root", "problem": problem},
        )
        self._register_node(root_node)

        # 使用 BFS 风格的探索，但使用优先级队列选择最优节点
        # 存储 (score, node) 的列表，按分数排序
        frontier: list[ThoughtNode] = [root_node]
        best_leaf: ThoughtNode | None = None
        best_score = -1.0
        total_explored = 1

        while frontier and total_explored < self.max_depth * num_branches * 2:
            # 选择当前最优节点进行扩展
            frontier.sort(key=lambda n: n.score, reverse=True)
            current_node = frontier.pop(0)

            # 检查深度限制
            if current_node.depth >= self.max_depth:
                if current_node.score > best_score:
                    best_score = current_node.score
                    best_leaf = current_node
                continue

            # 生成多个思考分支
            thoughts = await self._generate_thoughts(
                current_thought=current_node.thought,
                num_branches=num_branches,
                context={**context, "depth": current_node.depth},
            )

            for thought in thoughts:
                # 评估每个思考
                score = await self._evaluate_thought(
                    thought=thought,
                    problem=problem,
                    context=context,
                )

                # 创建子节点
                child_node = ThoughtNode(
                    id=generate_id("thought"),
                    thought=thought,
                    depth=current_node.depth + 1,
                    score=score,
                    parent_id=current_node.id,
                    metadata={"branch_index": len(current_node.children_ids)},
                )
                self._register_node(child_node)
                current_node.children_ids.append(child_node.id)
                total_explored += 1

                # 剪枝：只保留分数较高的节点
                if score > 0.3:  # 阈值
                    frontier.append(child_node)

                # 更新最优叶子节点
                if child_node.depth >= self.max_depth - 1 and score > best_score:
                    best_score = score
                    best_leaf = child_node

        # 如果没有找到最优叶子，使用根节点
        if best_leaf is None:
            best_leaf = root_node

        # 追溯最优路径
        reasoning_path = self._trace_path(best_leaf, root_node)

        # 生成结论
        conclusion = await self._synthesize_conclusion(
            reasoning_path=reasoning_path,
            problem=problem,
            context=context,
        )

        # 收集备选方案（其他高分路径的结论）
        alternatives = await self._collect_alternatives(
            root_node=root_node,
            best_path=reasoning_path,
            problem=problem,
            context=context,
        )

        confidence = self._calculate_confidence(reasoning_path)
        execution_time = time.time() - start_time

        return ReasoningResult(
            conclusion=conclusion,
            confidence=confidence,
            reasoning_path=reasoning_path,
            alternatives=alternatives,
            metadata={
                "strategy": "tree_of_thought",
                "problem": problem,
                "context": context,
                "branches_per_node": num_branches,
                "best_path_score": best_score,
            },
            strategy_used=ReasoningStrategy.TREE_OF_THOUGHT,
            total_nodes_explored=total_explored,
            execution_time_seconds=execution_time,
        )

    def _trace_path(
        self,
        node: ThoughtNode,
        root: ThoughtNode,
    ) -> list[ThoughtNode]:
        """追溯从根到节点的路径 - 修复版.

        使用 self.node_index 维护的节点索引进行路径追溯。
        从目标节点开始，通过 parent_id 向上遍历直到根节点，
        然后反转路径得到从根到目标的顺序。

        Args:
            node: 目标节点（通常是最优叶子节点）
            root: 根节点

        Returns:
            从根到目标节点的路径列表

        Note:
            此方法依赖 node_index 的正确维护。
            每个节点在创建后都应通过 _register_node 注册。
        """
        path: list[ThoughtNode] = []
        current: ThoughtNode | None = node

        # 从目标节点向上追溯到根节点
        while current is not None:
            path.append(current)

            # 如果已经到达根节点，停止追溯
            if current.id == root.id:
                break

            # 获取父节点
            parent_id = current.parent_id
            if parent_id is None:
                # 没有父节点但也不是目标根节点，说明可能有问题
                break

            # 从索引中查找父节点
            current = self.node_index.get(parent_id)

        # 反转路径：从根到目标
        return list(reversed(path))

    async def _generate_thoughts(
        self,
        current_thought: str,
        num_branches: int,
        context: dict[str, Any],
    ) -> list[str]:
        """生成下一步思考分支.

        为当前思考生成多个可能的后续思考方向。

        Args:
            current_thought: 当前思考内容
            num_branches: 要生成的分支数
            context: 上下文信息

        Returns:
            生成的思考列表
        """
        depth = context.get("depth", 0)
        context_str = json.dumps(
            {k: v for k, v in context.items() if k != "depth"},
            ensure_ascii=False,
        )

        prompt = f"""你是一个创造性的推理专家。请基于当前思考，生成 {num_branches} 个不同的后续思考方向。

## 当前思考
{current_thought}

## 上下文
{context_str if context_str != '{{}}' else '无额外上下文'}

## 当前深度
{depth}

## 要求
请生成 {num_branches} 个不同的后续思考方向:
1. 每个方向应该探索问题的不同方面
2. 方向之间应该有明显区别
3. 保持与当前思考的逻辑连贯性
4. 深度越大，思考应该越具体

请用以下格式输出（每个思考占一行，以数字开头）:
1. [第一个思考方向]
2. [第二个思考方向]
...
"""

        response = await self.llm_client.generate(
            prompt,
            temperature=self.temperature,
            max_tokens=1024,
        )

        # 解析响应
        thoughts = []
        lines = response.strip().split("\n")
        for line in lines:
            # 匹配 "1. xxx" 或 "1) xxx" 或 "- xxx" 格式
            match = re.match(r"^[\d]+[.)\s]+(.+)$", line.strip())
            if match:
                thought = match.group(1).strip()
                if thought:
                    thoughts.append(thought)

        # 如果解析失败，尝试按行分割
        if len(thoughts) < num_branches and lines:
            thoughts = [
                line.strip()
                for line in lines
                if line.strip() and not line.strip().startswith("#")
            ][:num_branches]

        # 确保至少有一个思考
        if not thoughts:
            thoughts = [f"继续深入分析: {current_thought}"]

        return thoughts[:num_branches]

    async def _evaluate_thought(
        self,
        thought: str,
        problem: str,
        context: dict[str, Any],
    ) -> float:
        """评估思考质量.

        使用 LLM 评估一个思考的质量分数。

        Args:
            thought: 要评估的思考内容
            problem: 原始问题
            context: 上下文信息

        Returns:
            质量分数 (0.0-1.0)
        """
        prompt = f"""请评估以下思考对于解决问题的质量。

## 原始问题
{problem}

## 思考内容
{thought}

## 评估标准
1. 相关性 (0-25分): 思考与问题的相关程度
2. 深度 (0-25分): 分析的深入程度
3. 可行性 (0-25分): 思考是否可执行/可验证
4. 创新性 (0-25分): 是否提供新的视角或见解

请给出总分 (0-100) 和简短理由。格式:
分数: [数字]
理由: [简短说明]"""

        response = await self.llm_client.generate(
            prompt,
            temperature=self.evaluation_temperature,
            max_tokens=200,
        )

        # 解析分数
        try:
            # 尝试从响应中提取分数
            match = re.search(r"分数[：:]\s*(\d+)", response)
            if match:
                score = int(match.group(1))
                return min(max(score / 100.0, 0.0), 1.0)

            # 备选：直接查找数字
            numbers = re.findall(r"\b(\d+)\b", response)
            if numbers:
                score = int(numbers[0])
                if 0 <= score <= 100:
                    return score / 100.0
        except (ValueError, IndexError):
            pass

        # 默认中等分数
        return 0.5

    async def _collect_alternatives(
        self,
        root_node: ThoughtNode,
        best_path: list[ThoughtNode],
        problem: str,
        context: dict[str, Any],
    ) -> list[str]:
        """收集备选方案.

        从其他高分路径中提取备选结论。

        Args:
            root_node: 根节点
            best_path: 最优路径
            problem: 原始问题
            context: 上下文信息

        Returns:
            备选方案列表
        """
        best_path_ids = {node.id for node in best_path}
        alternatives = []

        # 找到其他叶子节点
        other_leaves: list[ThoughtNode] = []
        for node in self.node_index.values():
            if node.is_leaf and node.id not in best_path_ids and node.score > 0.4:
                other_leaves.append(node)

        # 按分数排序
        other_leaves.sort(key=lambda n: n.score, reverse=True)

        # 取前 3 个备选
        for leaf in other_leaves[:3]:
            alt_path = self._trace_path(leaf, root_node)
            if len(alt_path) > 1:
                # 使用路径的最后一个思考作为备选
                alt_summary = alt_path[-1].thought
                if len(alt_summary) > 100:
                    alt_summary = alt_summary[:100] + "..."
                alternatives.append(f"[{leaf.score:.2f}] {alt_summary}")

        return alternatives

    def _calculate_confidence(
        self,
        reasoning_path: list[ThoughtNode],
    ) -> float:
        """计算推理结果的置信度.

        基于推理路径的分数计算总体置信度。

        Args:
            reasoning_path: 推理路径

        Returns:
            置信度 (0.0-1.0)
        """
        if not reasoning_path:
            return 0.0

        # 加权平均：后面的步骤权重更高
        total_weight = 0.0
        weighted_sum = 0.0

        for i, node in enumerate(reasoning_path):
            weight = i + 1  # 线性增长权重
            weighted_sum += node.score * weight
            total_weight += weight

        if total_weight == 0:
            return 0.0

        return weighted_sum / total_weight

    # =========================================================================
    # 反思与优化
    # =========================================================================

    async def reflect(
        self,
        result: ReasoningResult,
    ) -> ReasoningResult:
        """反思并优化推理结果.

        对已有的推理结果进行批判性反思，识别潜在问题并优化结论。

        Args:
            result: 原始推理结果

        Returns:
            优化后的推理结果

        Example:
            >>> initial_result = await engine.chain_of_thought(problem)
            >>> improved_result = await engine.reflect(initial_result)
        """
        import time

        start_time = time.time()

        # 构建反思提示
        reasoning_summary = "\n".join(
            f"Step {i + 1}: {node.thought}"
            for i, node in enumerate(result.reasoning_path)
        )

        prompt = f"""请对以下推理过程进行批判性反思和优化。

## 原始问题
{result.metadata.get('problem', '未知')}

## 推理过程
{reasoning_summary}

## 原始结论
{result.conclusion}

## 置信度
{result.confidence:.2f}

## 反思任务
请从以下角度进行反思:
1. 逻辑漏洞: 推理过程中是否有逻辑跳跃或不一致？
2. 遗漏因素: 是否忽略了重要的考虑因素？
3. 假设检验: 隐含的假设是否合理？
4. 结论优化: 如何让结论更准确或更完整？

请输出:
## 反思发现
[列出发现的问题]

## 优化后的结论
[给出改进后的结论]

## 新的置信度
[0-100 的数字]"""

        response = await self.llm_client.generate(
            prompt,
            temperature=0.4,
            max_tokens=1024,
        )

        # 解析响应
        improved_conclusion = result.conclusion
        new_confidence = result.confidence
        reflections: list[str] = []

        # 提取反思发现
        findings_match = re.search(
            r"##\s*反思发现\s*\n(.*?)(?=##|$)", response, re.DOTALL
        )
        if findings_match:
            reflections = [
                line.strip()
                for line in findings_match.group(1).strip().split("\n")
                if line.strip() and not line.strip().startswith("#")
            ]

        # 提取优化后的结论
        conclusion_match = re.search(
            r"##\s*优化后的结论\s*\n(.*?)(?=##|$)", response, re.DOTALL
        )
        if conclusion_match:
            improved_conclusion = conclusion_match.group(1).strip()

        # 提取新的置信度
        confidence_match = re.search(r"##\s*新的置信度\s*\n\s*(\d+)", response)
        if confidence_match:
            try:
                new_confidence = int(confidence_match.group(1)) / 100.0
                new_confidence = min(max(new_confidence, 0.0), 1.0)
            except ValueError:
                pass

        # 创建反思节点
        reflection_node = ThoughtNode(
            id=generate_id("thought"),
            thought=f"反思: {'; '.join(reflections[:3]) if reflections else '无重大问题'}",
            depth=len(result.reasoning_path),
            score=new_confidence,
            parent_id=(
                result.reasoning_path[-1].id if result.reasoning_path else None
            ),
            metadata={"type": "reflection", "findings": reflections},
        )
        self._register_node(reflection_node)

        # 更新路径
        new_path = result.reasoning_path.copy()
        if new_path:
            new_path[-1].children_ids.append(reflection_node.id)
        new_path.append(reflection_node)

        execution_time = time.time() - start_time

        return ReasoningResult(
            conclusion=improved_conclusion,
            confidence=new_confidence,
            reasoning_path=new_path,
            alternatives=result.alternatives,
            metadata={
                **result.metadata,
                "reflected": True,
                "reflections": reflections,
                "original_confidence": result.confidence,
                "original_conclusion": result.conclusion,
            },
            strategy_used=ReasoningStrategy.REFLECTION,
            total_nodes_explored=result.total_nodes_explored + 1,
            execution_time_seconds=result.execution_time_seconds + execution_time,
        )

    # =========================================================================
    # 辅助方法
    # =========================================================================

    async def self_consistency(
        self,
        problem: str,
        context: dict[str, Any] | None = None,
        num_samples: int = 5,
    ) -> ReasoningResult:
        """自一致性推理 - 多次采样取多数.

        通过多次独立推理，选择最一致的结论。

        Args:
            problem: 需要解决的问题
            context: 上下文信息
            num_samples: 采样次数

        Returns:
            基于多数投票的推理结果
        """
        import time

        start_time = time.time()
        context = context or {}

        # 并行执行多次推理
        tasks = [
            self.chain_of_thought(problem, context) for _ in range(num_samples)
        ]
        results = await asyncio.gather(*tasks)

        # 统计结论
        conclusion_counts: dict[str, list[ReasoningResult]] = {}
        for result in results:
            # 简化结论用于比较（取前 100 字符）
            key = result.conclusion[:100].lower().strip()
            if key not in conclusion_counts:
                conclusion_counts[key] = []
            conclusion_counts[key].append(result)

        # 找到最常见的结论
        best_group = max(conclusion_counts.values(), key=len)
        best_result = max(best_group, key=lambda r: r.confidence)

        # 计算一致性置信度
        consistency = len(best_group) / num_samples
        final_confidence = best_result.confidence * (0.5 + 0.5 * consistency)

        execution_time = time.time() - start_time

        return ReasoningResult(
            conclusion=best_result.conclusion,
            confidence=final_confidence,
            reasoning_path=best_result.reasoning_path,
            alternatives=[
                r.conclusion for r in results if r != best_result
            ][:3],
            metadata={
                "strategy": "self_consistency",
                "num_samples": num_samples,
                "consistency_ratio": consistency,
                "unique_conclusions": len(conclusion_counts),
            },
            strategy_used=ReasoningStrategy.SELF_CONSISTENCY,
            total_nodes_explored=sum(r.total_nodes_explored for r in results),
            execution_time_seconds=execution_time,
        )

    def get_node(self, node_id: str) -> ThoughtNode | None:
        """通过 ID 获取节点.

        Args:
            node_id: 节点 ID

        Returns:
            节点对象，如果不存在则返回 None
        """
        return self.node_index.get(node_id)

    def get_all_nodes(self) -> list[ThoughtNode]:
        """获取所有已注册的节点.

        Returns:
            所有节点的列表
        """
        return list(self.node_index.values())

    def visualize_tree(self, root_id: str | None = None) -> str:
        """可视化推理树结构.

        Args:
            root_id: 根节点 ID，如果为 None 则自动查找

        Returns:
            树的文本可视化表示
        """
        # 找到根节点
        if root_id:
            root = self.node_index.get(root_id)
        else:
            roots = [n for n in self.node_index.values() if n.is_root]
            root = roots[0] if roots else None

        if not root:
            return "无推理树"

        lines: list[str] = []

        def _visualize_node(node: ThoughtNode, prefix: str = "", is_last: bool = True):
            connector = "\\-- " if is_last else "|-- "
            thought_preview = (
                node.thought[:40] + "..." if len(node.thought) > 40 else node.thought
            )
            lines.append(
                f"{prefix}{connector}[{node.score:.2f}] {thought_preview}"
            )

            child_prefix = prefix + ("    " if is_last else "|   ")
            for i, child_id in enumerate(node.children_ids):
                child = self.node_index.get(child_id)
                if child:
                    _visualize_node(
                        child,
                        child_prefix,
                        i == len(node.children_ids) - 1,
                    )

        _visualize_node(root, "", True)
        return "\n".join(lines)


# =============================================================================
# 导出
# =============================================================================

__all__ = [
    "ThoughtNode",
    "ReasoningResult",
    "ReasoningEngine",
    "ReasoningStrategy",
    "LLMClientProtocol",
]
