"""
Protection Module - 风控保护层.

V3PRO+ Platform Component - Phase 2
V2 SPEC: 5.9

Exports:
- LiquidityGate: 流动性门控
- FatFingerGate: 胖手指检查
- ThrottleGate: 节流控制
- ProtectionChain: 保护链
"""

from src.execution.protection.fat_finger import FatFingerConfig, FatFingerGate
from src.execution.protection.liquidity import LiquidityConfig, LiquidityGate
from src.execution.protection.throttle import ThrottleConfig, ThrottleGate


__all__ = [
    "FatFingerConfig",
    "FatFingerGate",
    "LiquidityConfig",
    "LiquidityGate",
    "ThrottleConfig",
    "ThrottleGate",
]
