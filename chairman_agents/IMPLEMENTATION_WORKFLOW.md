  P1 - 高优先级 (逻辑错误风险)

       | 文件                      | 行号 | 错误类型   | 问题描述                    |
       |---------------------------|------|------------|-----------------------------|
       | cognitive/memory.py       | 339  | arg-type   | `list[float]                |
       | workflow/stage_manager.py | 403  | assignment | float 赋值给 int 类型变量   |
       | workflow/stage_manager.py | 743  | union-attr | 未处理 None 情况访问 .value |
       | api/server.py             | 269  | arg-type   | 异常处理器签名不兼容        |

       P2 - 中优先级 (API 类型问题)

       | 文件          | 行号 | 错误类型      | 问题描述                            |
       |---------------|------|---------------|-------------------------------------|
       | api/routes.py | 140  | arg-type (x7) | TaskResponse 构造参数展开类型不匹配 |
       | api/routes.py | 308  | var-annotated | 缺少 stage_info 类型注解            |
       | api/routes.py | 337  | arg-type (x7) | WorkflowResponse 构造参数类型不匹配 |

       P3 - 测试代码 (非关键)

       | 文件                                               | 错误数 | 主要问题                                       |
       |----------------------------------------------------|--------|------------------------------------------------|
       | tests/workflow/test_pipeline.py                    | 4      | None 检查缺失                                  |
       | tests/orchestration/test_task_scheduler.py         | 3      | `Task                                          |
       | tests/integration/test_agent_team_integration.py   | 7      | 枚举成员不存在 (DEBUGGING, TESTING, LEAD, MID) |
       | tests/integration/test_llm_cache.py                | 2      | 缺少类型注解                                   |
       | tests/integration/test_llm_pipeline_integration.py | 1      | get_stats 方法不存在                           |

       ---
       修复优先级汇总

       | 优先级 | 文件数 | 错误数 | 建议                              |
       |--------|--------|--------|-----------------------------------|
       | P0     | 2      | 9      | 立即修复 - 回调签名和异步任务类型 |
       | P1     | 3      | 4      | 尽快修复 - None 检查和类型转换    |
       | P2     | 1      | 16     | 计划修复 - API 响应构造重构       |
       | P3     | 5      | 16     | 可延后 - 测试代码类型问题         |

       ---
       建议的修复方案

       P0 核心修复 (parallel_executor.py + task_scheduler.py):
       1. 统一回调函数签名: Callable[[Task, Optional[Exception]], None]
       2. 使用 TypeVar 或 Protocol 定义回调类型
       3. 为 create_task 添加正确的泛型类型注解

       P1 快速修复:
       1. memory.py:339 - 添加 None 检查或使用默认空列表
       2. stage_manager.py:403 - 使用 int() 显式转换
       3. stage_manager.py:743 - 添加 if status is not None: 守卫
