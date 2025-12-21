"""
InstrumentCache - 合约元数据缓存

V3PRO+ Platform Component - Phase 0
V2 SPEC: 4.1
V2 Scenarios: INST.CACHE.LOAD, INST.CACHE.PERSIST

军规级要求:
- 从 JSON 加载 InstrumentInfo，包含必填字段
- 原子化落盘（先写 tmp，再 rename）
- 路径: artifacts/instruments/{exchange}_{trading_day}.json
"""

from __future__ import annotations

import json
import os
import tempfile
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import TYPE_CHECKING


if TYPE_CHECKING:
    pass


@dataclass(frozen=True)
class InstrumentInfo:
    """合约元数据.

    Attributes:
        symbol: 合约代码（如 AO2501）
        product: 品种代码（如 AO）
        exchange: 交易所（SHFE/CZCE/DCE/GFEX）
        expire_date: 到期日（YYYYMMDD）
        tick_size: 最小变动价位
        multiplier: 合约乘数
        max_order_volume: 单笔最大手数
        position_limit: 持仓限额
    """

    symbol: str
    product: str
    exchange: str
    expire_date: str
    tick_size: float
    multiplier: int
    max_order_volume: int = 500
    position_limit: int = 10000


class InstrumentCache:
    """合约元数据缓存.

    V2 Scenarios:
    - INST.CACHE.LOAD: 能正确加载合约信息
    - INST.CACHE.PERSIST: 能原子化落盘

    军规级要求:
    - 从 JSON 文件加载 InstrumentInfo
    - 先写 tmp，再 rename（原子化落盘）
    """

    def __init__(self) -> None:
        """初始化缓存."""
        self._cache: dict[str, InstrumentInfo] = {}
        self._by_product: dict[str, list[InstrumentInfo]] = {}

    def load_from_file(self, path: Path) -> None:
        """从 JSON 文件加载合约信息.

        V2 Scenario: INST.CACHE.LOAD

        Args:
            path: JSON 文件路径

        Raises:
            FileNotFoundError: 文件不存在
            json.JSONDecodeError: JSON 格式错误
            KeyError: 缺少必填字段
        """
        with open(path, encoding="utf-8") as f:
            data = json.load(f)

        self._cache.clear()
        self._by_product.clear()

        instruments = data if isinstance(data, list) else data.get("instruments", [])
        for item in instruments:
            info = InstrumentInfo(
                symbol=item["symbol"],
                product=item["product"],
                exchange=item["exchange"],
                expire_date=item["expire_date"],
                tick_size=float(item["tick_size"]),
                multiplier=int(item["multiplier"]),
                max_order_volume=int(item.get("max_order_volume", 500)),
                position_limit=int(item.get("position_limit", 10000)),
            )
            self._cache[info.symbol] = info
            if info.product not in self._by_product:
                self._by_product[info.product] = []
            self._by_product[info.product].append(info)

    def persist(self, path: Path, trading_day: str) -> None:
        """原子化落盘.

        V2 Scenario: INST.CACHE.PERSIST

        Args:
            path: 目标路径
            trading_day: 交易日（YYYYMMDD）

        军规级要求:
        - 先写 tmp 文件
        - 成功后 rename 到目标路径
        - 路径格式: artifacts/instruments/{exchange}_{trading_day}.json
        """
        path.parent.mkdir(parents=True, exist_ok=True)

        data = {
            "trading_day": trading_day,
            "instruments": [asdict(info) for info in self._cache.values()],
        }

        # 原子化写入：先写 tmp，再 rename
        fd, tmp_path = tempfile.mkstemp(suffix=".json", prefix="inst_", dir=path.parent)
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            os.replace(tmp_path, path)
        except Exception:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)
            raise

    def add(self, info: InstrumentInfo) -> None:
        """添加合约信息.

        Args:
            info: 合约元数据
        """
        self._cache[info.symbol] = info
        if info.product not in self._by_product:
            self._by_product[info.product] = []
        # Avoid duplicates
        if info not in self._by_product[info.product]:
            self._by_product[info.product].append(info)

    def get(self, symbol: str) -> InstrumentInfo | None:
        """获取合约信息.

        Args:
            symbol: 合约代码

        Returns:
            合约信息，不存在返回 None
        """
        return self._cache.get(symbol)

    def get_by_product(self, product: str) -> list[InstrumentInfo]:
        """获取品种下所有合约.

        Args:
            product: 品种代码

        Returns:
            合约列表
        """
        return self._by_product.get(product, [])

    def all_symbols(self) -> list[str]:
        """获取所有合约代码."""
        return list(self._cache.keys())

    def all_products(self) -> list[str]:
        """获取所有品种代码."""
        return list(self._by_product.keys())

    def __len__(self) -> int:
        """返回缓存的合约数量."""
        return len(self._cache)
