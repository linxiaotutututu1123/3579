"""增强型LSTM模型.

V4PRO Platform Component - Phase 6 B类模型层
军规覆盖: M7(回放一致), M3(完整审计)

V4PRO Scenarios:
- DL.MODEL.LSTM.FORWARD - LSTM前向传播
- DL.MODEL.LSTM.ATTENTION - 带注意力的LSTM
- DL.MODEL.LSTM.RESIDUAL - 残差LSTM
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from typing import Any

import torch
from torch import nn


@dataclass
class LSTMConfig:
    """LSTM模型配置.

    Attributes:
        input_dim: 输入特征维度
        hidden_dim: 隐藏层维度
        num_layers: LSTM层数
        output_dim: 输出维度
        dropout: Dropout比例
        bidirectional: 是否双向
        use_attention: 是否使用注意力
        use_residual: 是否使用残差连接
    """

    input_dim: int = 3  # 默认3个特征(returns, volume, range)
    hidden_dim: int = 64
    num_layers: int = 2
    output_dim: int = 1
    dropout: float = 0.1
    bidirectional: bool = False
    use_attention: bool = True
    use_residual: bool = True


class SelfAttention(nn.Module):
    """自注意力机制.

    用于捕获序列中的长期依赖关系。
    """

    def __init__(self, hidden_dim: int) -> None:
        """初始化自注意力层.

        Args:
            hidden_dim: 隐藏层维度
        """
        super().__init__()
        self.hidden_dim = hidden_dim

        # 注意力参数
        self.W_query = nn.Linear(hidden_dim, hidden_dim, bias=False)
        self.W_key = nn.Linear(hidden_dim, hidden_dim, bias=False)
        self.W_value = nn.Linear(hidden_dim, hidden_dim, bias=False)

        self.scale = hidden_dim**0.5

    def forward(
        self,
        hidden_states: torch.Tensor,
        mask: torch.Tensor | None = None,
    ) -> tuple[torch.Tensor, torch.Tensor]:
        """前向传播.

        Args:
            hidden_states: 隐藏状态 (batch, seq_len, hidden_dim)
            mask: 可选的注意力掩码

        Returns:
            (context, attention_weights)
        """
        # 计算Q, K, V
        query = self.W_query(hidden_states)
        key = self.W_key(hidden_states)
        value = self.W_value(hidden_states)

        # 计算注意力分数
        scores = torch.matmul(query, key.transpose(-2, -1)) / self.scale

        # 应用掩码
        if mask is not None:
            scores = scores.masked_fill(mask == 0, float("-inf"))

        # Softmax
        attention_weights = torch.softmax(scores, dim=-1)

        # 计算上下文向量
        context = torch.matmul(attention_weights, value)

        return context, attention_weights


class EnhancedLSTM(nn.Module):
    """增强型LSTM模型 (军规级).

    特性:
    - 多层LSTM
    - 可选的自注意力机制
    - 可选的残差连接
    - 确定性推理(M7)

    军规覆盖:
    - M7: 确定性推理
    - M3: 模型参数审计

    Example:
        >>> config = LSTMConfig(input_dim=3, hidden_dim=64)
        >>> model = EnhancedLSTM(config)
        >>> output, hidden = model(x)  # x: (batch, seq_len, input_dim)
    """

    def __init__(self, config: LSTMConfig | None = None) -> None:
        """初始化增强LSTM.

        Args:
            config: 模型配置
        """
        super().__init__()
        self.config = config or LSTMConfig()

        # 输入投影(用于残差连接)
        self.input_projection = None
        if self.config.use_residual:
            proj_in = self.config.input_dim
            proj_out = self.config.hidden_dim * (2 if self.config.bidirectional else 1)
            self.input_projection = nn.Linear(proj_in, proj_out)

        # 主LSTM层
        self.lstm = nn.LSTM(
            input_size=self.config.input_dim,
            hidden_size=self.config.hidden_dim,
            num_layers=self.config.num_layers,
            batch_first=True,
            dropout=self.config.dropout if self.config.num_layers > 1 else 0.0,
            bidirectional=self.config.bidirectional,
        )

        # 注意力层
        attention_dim = self.config.hidden_dim * (
            2 if self.config.bidirectional else 1
        )
        self.attention = None
        if self.config.use_attention:
            self.attention = SelfAttention(attention_dim)

        # Layer Normalization
        self.layer_norm = nn.LayerNorm(attention_dim)

        # 输出层
        self.output_layer = nn.Sequential(
            nn.Linear(attention_dim, self.config.hidden_dim),
            nn.ReLU(),
            nn.Dropout(self.config.dropout),
            nn.Linear(self.config.hidden_dim, self.config.output_dim),
            nn.Tanh(),  # 输出在[-1, 1]范围
        )

        # M3: 模型参数计数
        self._param_count = sum(p.numel() for p in self.parameters())

    def forward(
        self,
        x: torch.Tensor,
        hidden: tuple[torch.Tensor, torch.Tensor] | None = None,
    ) -> tuple[torch.Tensor, tuple[torch.Tensor, torch.Tensor]]:
        """前向传播 (DL.MODEL.LSTM.FORWARD).

        Args:
            x: 输入张量 (batch, seq_len, input_dim)
            hidden: 可选的初始隐藏状态

        Returns:
            (output, (h_n, c_n))
            - output: 输出分数 (batch, output_dim)
            - h_n: 最终隐藏状态
            - c_n: 最终单元状态
        """
        batch_size, seq_len, _ = x.shape

        # LSTM前向
        lstm_out, (h_n, c_n) = self.lstm(x, hidden)
        # lstm_out: (batch, seq_len, hidden_dim * num_directions)

        # 残差连接
        if self.config.use_residual and self.input_projection is not None:
            residual = self.input_projection(x)
            lstm_out = lstm_out + residual

        # 注意力机制
        if self.attention is not None:
            context, _ = self.attention(lstm_out)
            # 使用最后时刻的上下文向量
            pooled = context[:, -1, :]
        else:
            # 使用最后时刻的隐藏状态
            pooled = lstm_out[:, -1, :]

        # Layer Normalization
        normalized = self.layer_norm(pooled)

        # 输出层
        output = self.output_layer(normalized)

        return output, (h_n, c_n)

    def get_attention_weights(
        self,
        x: torch.Tensor,
    ) -> torch.Tensor | None:
        """获取注意力权重 (用于可解释性).

        Args:
            x: 输入张量

        Returns:
            注意力权重或None
        """
        if self.attention is None:
            return None

        with torch.no_grad():
            lstm_out, _ = self.lstm(x)

            if self.config.use_residual and self.input_projection is not None:
                residual = self.input_projection(x)
                lstm_out = lstm_out + residual

            _, attention_weights = self.attention(lstm_out)

        return attention_weights

    def compute_model_hash(self) -> str:
        """计算模型参数哈希 (M7).

        Returns:
            模型哈希值
        """
        hasher = hashlib.sha256()
        for param in self.parameters():
            hasher.update(param.data.cpu().numpy().tobytes())
        return hasher.hexdigest()[:32]

    def get_model_info(self) -> dict[str, Any]:
        """获取模型信息 (M3).

        Returns:
            模型信息字典
        """
        return {
            "input_dim": self.config.input_dim,
            "hidden_dim": self.config.hidden_dim,
            "num_layers": self.config.num_layers,
            "output_dim": self.config.output_dim,
            "bidirectional": self.config.bidirectional,
            "use_attention": self.config.use_attention,
            "use_residual": self.config.use_residual,
            "param_count": self._param_count,
            "model_hash": self.compute_model_hash(),
        }

    @classmethod
    def from_pretrained(
        cls,
        path: str,
        config: LSTMConfig | None = None,
    ) -> "EnhancedLSTM":
        """从预训练权重加载模型.

        Args:
            path: 模型权重路径
            config: 模型配置(可选)

        Returns:
            加载的模型
        """
        model = cls(config)
        state_dict = torch.load(path, map_location="cpu", weights_only=True)
        model.load_state_dict(state_dict)
        model.eval()
        return model


def create_lstm_model(
    input_dim: int,
    hidden_dim: int = 64,
    num_layers: int = 2,
    **kwargs: Any,
) -> EnhancedLSTM:
    """创建LSTM模型的便捷函数.

    Args:
        input_dim: 输入维度
        hidden_dim: 隐藏层维度
        num_layers: 层数
        **kwargs: 其他配置参数

    Returns:
        创建的模型
    """
    config = LSTMConfig(
        input_dim=input_dim,
        hidden_dim=hidden_dim,
        num_layers=num_layers,
        **kwargs,
    )
    return EnhancedLSTM(config)
