"""中国六大期货交易所配置模块 (军规级 v4.0).

本模块提供中国六大期货交易所的完整配置信息，包括：
- 交易所基本信息
- 交易时段配置（含夜盘）
- 品种分类与映射
- 交易所特定规则

军规覆盖:
- M15: 夜盘跨日处理 - 提供夜盘时段配置
- M20: 跨所一致 - 统一的交易所配置接口

场景覆盖:
- CHINA.EXCHANGE.CONFIG_LOAD: 配置加载正确
- CHINA.EXCHANGE.PRODUCT_MAP: 品种映射正确

示例:
    >>> from src.market.exchange_config import Exchange, get_exchange_for_product
    >>> exchange = get_exchange_for_product("rb")
    >>> print(exchange)
    Exchange.SHFE
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import ClassVar


class Exchange(Enum):
    """中国六大期货交易所枚举.

    属性:
        SHFE: 上海期货交易所
        DCE: 大连商品交易所
        CZCE: 郑州商品交易所
        CFFEX: 中国金融期货交易所
        GFEX: 广州期货交易所
        INE: 上海国际能源交易中心
    """

    SHFE = "上海期货交易所"
    DCE = "大连商品交易所"
    CZCE = "郑州商品交易所"
    CFFEX = "中国金融期货交易所"
    GFEX = "广州期货交易所"
    INE = "上海国际能源交易中心"


class NightSessionEnd(Enum):
    """夜盘结束时间分类.

    属性:
        T_23_00: 23:00结束（农产品、软商品）
        T_01_00: 01:00结束（黑色系、能化）
        T_02_30: 02:30结束（贵金属、有色金属）
        NONE: 无夜盘（股指期货、国债期货）
    """

    T_23_00 = "23:00"
    T_01_00 = "01:00"
    T_02_30 = "02:30"
    NONE = "无夜盘"


@dataclass(frozen=True)
class TradingSession:
    """交易时段配置.

    属性:
        start: 开始时间 (HH:MM格式)
        end: 结束时间 (HH:MM格式)
        name: 时段名称
    """

    start: str
    end: str
    name: str = ""


@dataclass
class ExchangeConfig:
    """交易所配置信息.

    属性:
        exchange: 交易所枚举
        name: 交易所全称
        code: 交易所代码
        trading_sessions: 日盘交易时段列表
        night_session_start: 夜盘开始时间
        night_session_end: 夜盘结束分类
        settlement_time: 结算时间
        products: 该交易所的品种列表
    """

    exchange: Exchange
    name: str
    code: str
    trading_sessions: list[TradingSession] = field(default_factory=list)
    night_session_start: str = "21:00"
    night_session_end: NightSessionEnd = NightSessionEnd.NONE
    settlement_time: str = "15:15"
    products: list[str] = field(default_factory=list)


# ============================================================================
# 日盘标准交易时段（所有交易所通用）
# ============================================================================
DAY_SESSIONS: list[TradingSession] = [
    TradingSession("09:00", "10:15", "早盘第一节"),
    TradingSession("10:30", "11:30", "早盘第二节"),
    TradingSession("13:30", "15:00", "午盘"),
]

# CFFEX特殊时段（股指期货）
CFFEX_INDEX_SESSIONS: list[TradingSession] = [
    TradingSession("09:30", "11:30", "早盘"),
    TradingSession("13:00", "15:00", "午盘"),
]

# CFFEX国债期货时段
CFFEX_BOND_SESSIONS: list[TradingSession] = [
    TradingSession("09:15", "11:30", "早盘"),
    TradingSession("13:00", "15:15", "午盘"),
]


# ============================================================================
# 六大交易所配置
# ============================================================================
EXCHANGE_CONFIGS: dict[Exchange, ExchangeConfig] = {
    Exchange.SHFE: ExchangeConfig(
        exchange=Exchange.SHFE,
        name="上海期货交易所",
        code="SHFE",
        trading_sessions=DAY_SESSIONS,
        night_session_start="21:00",
        night_session_end=NightSessionEnd.T_02_30,
        settlement_time="15:15",
        products=[
            # 有色金属
            "cu",  # 铜
            "al",  # 铝
            "zn",  # 锌
            "pb",  # 铅
            "ni",  # 镍
            "sn",  # 锡
            "ao",  # 氧化铝
            # 贵金属
            "au",  # 黄金
            "ag",  # 白银
            # 黑色系
            "rb",  # 螺纹钢
            "hc",  # 热轧卷板
            "ss",  # 不锈钢
            "wr",  # 线材
            # 能源化工
            "bu",  # 沥青
            "ru",  # 天然橡胶
            "sp",  # 纸浆
            "nr",  # 20号胶
            "fu",  # 燃料油
        ],
    ),
    Exchange.DCE: ExchangeConfig(
        exchange=Exchange.DCE,
        name="大连商品交易所",
        code="DCE",
        trading_sessions=DAY_SESSIONS,
        night_session_start="21:00",
        night_session_end=NightSessionEnd.T_23_00,
        settlement_time="15:15",
        products=[
            # 农产品
            "c",  # 玉米
            "cs",  # 玉米淀粉
            "a",  # 豆一
            "b",  # 豆二
            "m",  # 豆粕
            "y",  # 豆油
            "p",  # 棕榈油
            "jd",  # 鸡蛋
            "lh",  # 生猪
            "rr",  # 粳米
            # 化工
            "l",  # 塑料
            "v",  # PVC
            "pp",  # 聚丙烯
            "eg",  # 乙二醇
            "eb",  # 苯乙烯
            "pg",  # LPG
            # 黑色系
            "i",  # 铁矿石
            "j",  # 焦炭
            "jm",  # 焦煤
            # 其他
            "fb",  # 纤维板
            "bb",  # 胶合板
        ],
    ),
    Exchange.CZCE: ExchangeConfig(
        exchange=Exchange.CZCE,
        name="郑州商品交易所",
        code="CZCE",
        trading_sessions=DAY_SESSIONS,
        night_session_start="21:00",
        night_session_end=NightSessionEnd.T_23_00,
        settlement_time="15:15",
        products=[
            # 农产品
            "WH",  # 强麦
            "PM",  # 普麦
            "RI",  # 早籼稻
            "LR",  # 晚籼稻
            "JR",  # 粳稻
            "CF",  # 棉花
            "CY",  # 棉纱
            "SR",  # 白糖
            "OI",  # 菜籽油
            "RM",  # 菜籽粕
            "RS",  # 油菜籽
            "AP",  # 苹果
            "CJ",  # 红枣
            "PK",  # 花生
            # 化工
            "MA",  # 甲醇
            "TA",  # PTA
            "SA",  # 纯碱
            "UR",  # 尿素
            "PF",  # 短纤
            "FG",  # 玻璃
            "ZC",  # 动力煤（已停止交易）
            # 其他
            "SM",  # 锰硅
            "SF",  # 硅铁
        ],
    ),
    Exchange.CFFEX: ExchangeConfig(
        exchange=Exchange.CFFEX,
        name="中国金融期货交易所",
        code="CFFEX",
        trading_sessions=CFFEX_INDEX_SESSIONS,
        night_session_start="",
        night_session_end=NightSessionEnd.NONE,
        settlement_time="15:15",
        products=[
            # 股指期货
            "IF",  # 沪深300股指期货
            "IH",  # 上证50股指期货
            "IC",  # 中证500股指期货
            "IM",  # 中证1000股指期货
            # 国债期货
            "T",  # 10年期国债期货
            "TF",  # 5年期国债期货
            "TS",  # 2年期国债期货
            "TL",  # 30年期国债期货
        ],
    ),
    Exchange.GFEX: ExchangeConfig(
        exchange=Exchange.GFEX,
        name="广州期货交易所",
        code="GFEX",
        trading_sessions=DAY_SESSIONS,
        night_session_start="21:00",
        night_session_end=NightSessionEnd.T_23_00,
        settlement_time="15:15",
        products=[
            "lc",  # 碳酸锂
            "si",  # 工业硅
        ],
    ),
    Exchange.INE: ExchangeConfig(
        exchange=Exchange.INE,
        name="上海国际能源交易中心",
        code="INE",
        trading_sessions=DAY_SESSIONS,
        night_session_start="21:00",
        night_session_end=NightSessionEnd.T_02_30,
        settlement_time="15:15",
        products=[
            "sc",  # 原油
            "lu",  # 低硫燃料油
            "bc",  # 国际铜
            "nr",  # 20号胶（与SHFE共享）
            "ec",  # 集运指数（欧线）
        ],
    ),
}


# ============================================================================
# 品种分类
# ============================================================================
PRODUCT_CATEGORIES: dict[str, dict[str, list[str]]] = {
    "金属": {
        "SHFE": ["cu", "al", "zn", "pb", "ni", "sn", "ao"],
        "GFEX": ["si"],
        "INE": ["bc"],
    },
    "贵金属": {
        "SHFE": ["au", "ag"],
    },
    "黑色系": {
        "SHFE": ["rb", "hc", "ss", "wr"],
        "DCE": ["i", "j", "jm"],
        "CZCE": ["SM", "SF"],
    },
    "能源化工": {
        "SHFE": ["bu", "ru", "sp", "nr", "fu"],
        "DCE": ["l", "v", "pp", "eg", "eb", "pg"],
        "CZCE": ["MA", "TA", "SA", "UR", "PF", "FG"],
        "INE": ["sc", "lu"],
        "GFEX": ["lc"],
    },
    "农产品": {
        "DCE": ["c", "cs", "a", "b", "m", "y", "p", "jd", "lh", "rr", "fb", "bb"],
        "CZCE": [
            "WH",
            "PM",
            "RI",
            "LR",
            "JR",
            "CF",
            "CY",
            "SR",
            "OI",
            "RM",
            "RS",
            "AP",
            "CJ",
            "PK",
        ],
    },
    "金融": {
        "CFFEX": ["IF", "IH", "IC", "IM", "T", "TF", "TS", "TL"],
    },
}


# ============================================================================
# 品种到交易所的映射缓存
# ============================================================================
class ProductExchangeMapper:
    """品种到交易所映射器.

    提供品种代码到交易所的快速查找功能。

    类变量:
        _cache: 品种到交易所的映射缓存
        _initialized: 缓存是否已初始化
    """

    _cache: ClassVar[dict[str, Exchange]] = {}
    _initialized: ClassVar[bool] = False

    @classmethod
    def _init_cache(cls) -> None:
        """初始化品种到交易所的映射缓存."""
        if cls._initialized:
            return

        for exchange, config in EXCHANGE_CONFIGS.items():
            for product in config.products:
                # 统一转换为小写进行存储
                cls._cache[product.lower()] = exchange

        cls._initialized = True

    @classmethod
    def get_exchange(cls, product: str) -> Exchange | None:
        """根据品种代码获取交易所.

        参数:
            product: 品种代码（如 "rb", "IF", "sc"）

        返回:
            对应的交易所枚举，未找到返回None
        """
        cls._init_cache()
        return cls._cache.get(product.lower())

    @classmethod
    def get_all_products(cls) -> list[str]:
        """获取所有已配置的品种代码.

        返回:
            所有品种代码列表
        """
        cls._init_cache()
        return list(cls._cache.keys())


# ============================================================================
# 便捷函数
# ============================================================================
def get_exchange_for_product(product: str) -> Exchange | None:
    """根据品种代码获取交易所.

    参数:
        product: 品种代码（如 "rb", "IF", "sc"）

    返回:
        对应的交易所枚举，未找到返回None

    示例:
        >>> get_exchange_for_product("rb")
        Exchange.SHFE
        >>> get_exchange_for_product("IF")
        Exchange.CFFEX
    """
    return ProductExchangeMapper.get_exchange(product)


def get_exchange_config(exchange: Exchange) -> ExchangeConfig:
    """获取交易所配置.

    参数:
        exchange: 交易所枚举

    返回:
        交易所配置对象

    异常:
        KeyError: 交易所未配置
    """
    return EXCHANGE_CONFIGS[exchange]


def get_trading_sessions(exchange: Exchange) -> list[TradingSession]:
    """获取交易所的日盘交易时段.

    参数:
        exchange: 交易所枚举

    返回:
        交易时段列表
    """
    return EXCHANGE_CONFIGS[exchange].trading_sessions


def has_night_session(exchange: Exchange) -> bool:
    """判断交易所是否有夜盘.

    参数:
        exchange: 交易所枚举

    返回:
        是否有夜盘
    """
    return EXCHANGE_CONFIGS[exchange].night_session_end != NightSessionEnd.NONE


def get_night_session_end(exchange: Exchange) -> NightSessionEnd:
    """获取交易所夜盘结束时间分类.

    参数:
        exchange: 交易所枚举

    返回:
        夜盘结束时间分类
    """
    return EXCHANGE_CONFIGS[exchange].night_session_end


def get_products_by_exchange(exchange: Exchange) -> list[str]:
    """获取交易所的所有品种.

    参数:
        exchange: 交易所枚举

    返回:
        品种代码列表
    """
    return EXCHANGE_CONFIGS[exchange].products


def get_products_by_category(category: str) -> dict[str, list[str]]:
    """根据品种分类获取品种列表.

    参数:
        category: 品种分类（如 "金属", "农产品"）

    返回:
        交易所到品种列表的映射

    异常:
        KeyError: 分类不存在
    """
    return PRODUCT_CATEGORIES[category]


def get_all_exchanges() -> list[Exchange]:
    """获取所有交易所列表.

    返回:
        交易所枚举列表
    """
    return list(Exchange)


def get_exchange_by_code(code: str) -> Exchange | None:
    """根据交易所代码获取交易所枚举.

    参数:
        code: 交易所代码（如 "SHFE", "DCE"）

    返回:
        交易所枚举，未找到返回None
    """
    code_upper = code.upper()
    for exchange, config in EXCHANGE_CONFIGS.items():
        if config.code == code_upper:
            return exchange
    return None


# ============================================================================
# 夜盘品种配置（不同夜盘结束时间）
# ============================================================================
NIGHT_SESSION_PRODUCTS: dict[NightSessionEnd, list[str]] = {
    NightSessionEnd.T_23_00: [
        # DCE农产品
        "c",
        "cs",
        "a",
        "b",
        "m",
        "y",
        "p",
        "jd",
        "lh",
        "rr",
        # DCE化工
        "l",
        "v",
        "pp",
        "eg",
        "eb",
        "pg",
        # DCE黑色
        "i",
        "j",
        "jm",
        # CZCE农产品
        "CF",
        "CY",
        "SR",
        "OI",
        "RM",
        "AP",
        "CJ",
        "PK",
        # CZCE化工
        "MA",
        "TA",
        "SA",
        "UR",
        "PF",
        "FG",
        # GFEX
        "lc",
        "si",
    ],
    NightSessionEnd.T_01_00: [
        # SHFE黑色
        "rb",
        "hc",
        "ss",
        # SHFE能化
        "bu",
        "ru",
        "sp",
        "fu",
    ],
    NightSessionEnd.T_02_30: [
        # SHFE有色金属
        "cu",
        "al",
        "zn",
        "pb",
        "ni",
        "sn",
        "ao",
        # SHFE贵金属
        "au",
        "ag",
        # INE
        "sc",
        "lu",
        "bc",
        "nr",
    ],
    NightSessionEnd.NONE: [
        # CFFEX（无夜盘）
        "IF",
        "IH",
        "IC",
        "IM",
        "T",
        "TF",
        "TS",
        "TL",
    ],
}


def get_night_session_end_for_product(product: str) -> NightSessionEnd:
    """根据品种获取夜盘结束时间分类.

    参数:
        product: 品种代码

    返回:
        夜盘结束时间分类
    """
    product_lower = product.lower()
    product_upper = product.upper()

    for end_time, products in NIGHT_SESSION_PRODUCTS.items():
        if product_lower in [p.lower() for p in products]:
            return end_time
        if product_upper in products:
            return end_time

    # 默认返回无夜盘
    return NightSessionEnd.NONE
