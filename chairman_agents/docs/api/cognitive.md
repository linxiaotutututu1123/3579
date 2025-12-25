# Cognitive 模块 API

认知系统，包括记忆管理和推理引擎。

## memory 模块

### MemoryItem

记忆条目。

```python
@dataclass
class MemoryItem:
    id: str
    content: str
    memory_type: str  # episodic, semantic, procedural
    importance: float
    created_at: datetime
    last_accessed: datetime
    access_count: int = 0
    embedding: list[float] | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
```

**方法：**

#### to_dict

```python
def to_dict(self) -> dict[str, Any]
```

转换为字典格式，用于序列化。

#### from_dict

```python
@classmethod
def from_dict(cls, data: dict[str, Any]) -> MemoryItem
```

从字典创建MemoryItem实例。

---

### MemoryQuery

记忆检索查询参数。

```python
@dataclass
class MemoryQuery:
    query: str
    memory_types: list[str] | None = None
    limit: int = 10
    min_relevance: float = 0.3
    time_decay: bool = True
    time_decay_factor: float = 0.1
```

**属性：**
- `query` - 查询文本
- `memory_types` - 限定记忆类型列表
- `limit` - 返回结果数量上限
- `min_relevance` - 最小相关度阈值
- `time_decay` - 是否启用时间衰减
- `time_decay_factor` - 衰减因子（越大衰减越快）

---

### MemorySystem

记忆系统主类。

```python
class MemorySystem:
    MEMORY_TYPES = {"episodic", "semantic", "procedural"}
```

#### 初始化

```python
def __init__(
    self,
    storage_path: Path | None = None,
    use_embeddings: bool = False,
    embedding_model: str = "paraphrase-multilingual-MiniLM-L12-v2",
)
```

**参数：**
- `storage_path` - 持久化存储路径
- `use_embeddings` - 是否使用向量嵌入
- `embedding_model` - sentence-transformers模型名称

#### store

存储新记忆。

```python
def store(
    self,
    content: str,
    memory_type: str,
    importance: float = 0.5,
    metadata: dict[str, Any] | None = None,
) -> MemoryItem
```

**参数：**
- `content` - 记忆内容
- `memory_type` - 类型：episodic/semantic/procedural
- `importance` - 重要性(0-1)
- `metadata` - 额外元数据

**返回：** 创建的MemoryItem

**示例：**
```python
memory = MemorySystem(use_embeddings=True)
item = memory.store(
    content="用户偏好使用Python进行开发",
    memory_type="semantic",
    importance=0.8,
    metadata={"source": "conversation"}
)
```

#### retrieve

检索相关记忆。

```python
def retrieve(
    self,
    query: MemoryQuery,
) -> list[tuple[MemoryItem, float]]
```

**参数：**
- `query` - 查询参数

**返回：** (MemoryItem, 相关度)元组列表，按相关度降序排列

**示例：**
```python
query = MemoryQuery(
    query="Python开发偏好",
    memory_types=["semantic"],
    limit=5,
    min_relevance=0.5
)
results = memory.retrieve(query)
for item, score in results:
    print(f"{item.content}: {score:.2f}")
```

#### retrieve_by_type

按类型检索记忆。

```python
def retrieve_by_type(
    self,
    memory_type: str,
    limit: int = 10,
) -> list[MemoryItem]
```

#### forget

删除记忆。

```python
def forget(self, memory_id: str) -> bool
```

**返回：** 是否删除成功

#### consolidate

整合记忆：合并相似项、清理过期项。

```python
def consolidate(
    self,
    similarity_threshold: float = 0.8,
    min_importance: float = 0.2,
    max_age_days: int = 90,
) -> int
```

**参数：**
- `similarity_threshold` - 合并相似度阈值
- `min_importance` - 保留的最小重要性
- `max_age_days` - 最大保留天数

**返回：** 移除/合并的记忆数量

#### save_to_disk

持久化到磁盘。

```python
def save_to_disk(self) -> None
```

#### load_from_disk

从磁盘加载。

```python
def load_from_disk(self) -> None
```

#### get_statistics

获取统计信息。

```python
def get_statistics(self) -> dict[str, Any]
```

**返回：**
```python
{
    "total_memories": 100,
    "by_type": {"episodic": 40, "semantic": 50, "procedural": 10},
    "average_importance": 0.65,
    "total_access_count": 500,
    "jieba_available": True,
    "embeddings_available": True,
    "embedding_model": "paraphrase-multilingual-MiniLM-L12-v2",
    "memories_with_embeddings": 95,
}
```

#### update_importance

更新记忆重要性。

```python
def update_importance(self, memory_id: str, importance: float) -> bool
```

#### search_by_metadata

按元数据搜索。

```python
def search_by_metadata(
    self,
    key: str,
    value: Any,
    limit: int = 10,
) -> list[MemoryItem]
```

#### clear

清空所有记忆。

```python
def clear(self) -> int
```

**返回：** 清除的记忆数量

---

## 特性说明

### 中文支持

系统自动检测中文内容，优先使用jieba分词：

```python
# 安装jieba获得更好的中文支持
pip install jieba
```

若未安装jieba，系统降级为字符级分词。

### 向量嵌入

启用向量嵌入可提高检索精度：

```python
# 安装sentence-transformers
pip install sentence-transformers

memory = MemorySystem(use_embeddings=True)
```

支持的模型：
- `paraphrase-multilingual-MiniLM-L12-v2` (默认，多语言)
- 其他sentence-transformers兼容模型

### 相关度计算

相关度综合考虑：
1. 向量余弦相似度（若启用嵌入）或Jaccard相似度
2. 词频加权
3. 重要性权重
4. 时间衰减
5. 访问频率加成
