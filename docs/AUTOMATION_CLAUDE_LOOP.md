# Claude 自动闭环契约 (AUTOMATION_CLAUDE_LOOP)

> **本文档是 Claude Agent 的操作协议，Claude 必须严格按照此文档执行**

## 核心原则

```text
+------------------------------------------------------------------+
|  自动闭环 = 生成 context → 修改代码 → 运行检查 → 解析 JSON → 循环  |
+------------------------------------------------------------------+
```

**绝对禁止**：
- ❌ 手动运行 `ruff`、`mypy`、`pytest` 等底层工具
- ❌ 跳过 JSON 解析直接看日志输出
- ❌ 在未阅读 context.md 的情况下开始修改代码

**必须遵守**：
- ✅ 使用 `make.ps1 ci-json` 获取机器可读结果
- ✅ 使用 `make.ps1 replay-json` 或 `sim-json` 运行回放/仿真
- ✅ 每轮循环前刷新 context（`make.ps1 context-dev`）

---

## A. 自动编码闭环（Code Fix Loop）

### 流程图

```
┌─────────────────────────────────────────────────────────────────┐
│                    Claude 自动编码闭环                          │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│   ┌──────────────┐    ┌──────────────┐    ┌──────────────┐     │
│   │ 1. 生成上下文 │───▶│ 2. 分析问题  │───▶│ 3. 修改代码  │     │
│   │ context-dev  │    │ 读 context.md│    │ 精确编辑     │     │
│   └──────────────┘    └──────────────┘    └──────────────┘     │
│          ▲                                       │              │
│          │                                       ▼              │
│   ┌──────┴──────┐                        ┌──────────────┐      │
│   │ 5. 有失败?   │◀───────────────────────│ 4. 运行 CI   │      │
│   │ 解析 JSON   │                        │ ci-json      │      │
│   └─────────────┘                        └──────────────┘      │
│          │                                                      │
│          ▼ 全部通过                                             │
│   ┌──────────────┐                                             │
│   │ 6. 完成!     │                                             │
│   └──────────────┘                                             │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### 执行命令

```powershell
# Step 1: 生成开发上下文
.\scripts\make.ps1 context-dev

# Step 2: 阅读上下文
cat artifacts\context\context.md

# Step 3: 修改代码（使用编辑器工具）

# Step 4: 运行 CI 并获取 JSON 结果
.\scripts\make.ps1 ci-json

# Step 5: 解析结果
cat artifacts\check\report.json
```

### JSON 报告格式 (artifacts/check/report.json)

```json
{
  "version": "1.0",
  "timestamp": "2025-01-15T10:30:00Z",
  "overall": "FAIL",
  "exit_code": 2,
  "steps": [
    {
      "name": "format-check",
      "status": "PASS",
      "exit_code": 0,
      "duration_ms": 1234,
      "output_summary": ""
    },
    {
      "name": "lint",
      "status": "FAIL",
      "exit_code": 2,
      "duration_ms": 2345,
      "output_summary": "src/foo.py:42:1: E501 line too long",
      "failures": [
        {
          "file": "src/foo.py",
          "line": 42,
          "rule": "E501",
          "message": "line too long (120 > 88)"
        }
      ]
    },
    {
      "name": "type",
      "status": "SKIP",
      "exit_code": null,
      "reason": "previous step failed"
    },
    {
      "name": "test",
      "status": "SKIP",
      "exit_code": null,
      "reason": "previous step failed"
    }
  ]
}
```

### 失败处理策略

| 失败类型 | exit_code | Claude 应采取的动作 |
|---------|-----------|---------------------|
| format  | 2         | 运行 `make.ps1 format` 自动修复 |
| lint    | 2         | 根据 failures 数组修改代码 |
| type    | 3         | 根据 mypy 错误修改类型标注 |
| test    | 4         | 根据测试失败修改逻辑或测试 |
| coverage| 5         | 添加测试覆盖未测代码 |

---

## B. 自动回放/仿真闭环（Replay/Sim Loop）

### 流程图

```
┌─────────────────────────────────────────────────────────────────┐
│                Claude 回放/仿真闭环                              │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│   ┌──────────────┐    ┌──────────────┐    ┌──────────────┐     │
│   │ 1. CI 先绿   │───▶│ 2. 运行回放  │───▶│ 3. 解析报告  │     │
│   │ ci-json 通过 │    │ replay-json  │    │ sim report   │     │
│   └──────────────┘    └──────────────┘    └──────────────┘     │
│                              ▲                   │              │
│                              │                   ▼              │
│                       ┌──────┴──────┐    ┌──────────────┐      │
│                       │ 5. 有错误?   │◀───│ 4. 检查结果  │      │
│                       │ 修改代码    │    │ assertions   │      │
│                       └─────────────┘    └──────────────┘      │
│                              │                                  │
│                              ▼ 全部通过                         │
│                       ┌──────────────┐                         │
│                       │ 6. 完成!     │                         │
│                       └──────────────┘                         │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### 执行命令

```powershell
# Step 1: 确保 CI 绿
.\scripts\make.ps1 ci-json
# 确认 overall == "PASS"

# Step 2: 运行回放
.\scripts\make.ps1 replay-json
# 或仿真
.\scripts\make.ps1 sim-json

# Step 3: 解析结果
cat artifacts\sim\report.json
```

### JSON 报告格式 (artifacts/sim/report.json)

```json
{
  "version": "1.0",
  "timestamp": "2025-01-15T10:35:00Z",
  "type": "replay",
  "overall": "FAIL",
  "scenarios_total": 10,
  "scenarios_passed": 8,
  "scenarios_failed": 2,
  "failures": [
    {
      "scenario": "test_flatten_on_margin_call",
      "tick": 42,
      "expected": {"position": 0},
      "actual": {"position": 5},
      "error": "Position not fully flattened after margin call"
    },
    {
      "scenario": "test_order_rejection_recovery",
      "tick": 15,
      "expected": {"state": "RETRY"},
      "actual": {"state": "ABORT"},
      "error": "FSM did not transition to RETRY on rejection"
    }
  ],
  "metrics": {
    "total_ticks": 1000,
    "avg_tick_duration_ms": 1.5,
    "max_drawdown_pct": 2.3,
    "orders_placed": 45,
    "orders_rejected": 3
  }
}
```

---

## C. 完整闭环（Full Loop = CI + Replay）

Claude 应该在完成 CI 闭环后，自动进入 Replay/Sim 闭环：

```powershell
# 完整自动循环脚本
.\scripts\claude_loop.ps1 -MaxRounds 5
```

### claude_loop.ps1 行为

1. 运行 `context-dev` 生成上下文
2. 运行 `ci-json` 检查代码质量
3. 如果失败，解析 `artifacts/check/report.json`，通知 Claude 修复
4. 如果 CI 通过，运行 `replay-json` 检查回放
5. 如果失败，解析 `artifacts/sim/report.json`，通知 Claude 修复
6. 重复直到全部通过或达到 MaxRounds

---

## D. 关键约定

### 1. 文件路径（绝对不变）

| 用途 | 路径 |
|------|------|
| 开发上下文 | `artifacts/context/context.md` |
| CI 报告 | `artifacts/check/report.json` |
| 回放/仿真报告 | `artifacts/sim/report.json` |

### 2. 退出码映射

| 阶段 | 通过 | 失败 |
|------|------|------|
| CI | 0 | 2/3/4/5 (见 EXIT_CODES.md) |
| Replay | 0 | 10 |
| Sim | 0 | 11 |

### 3. Claude 读取 JSON 的方式

```python
# Claude 应该使用这种结构化方式处理结果
import json

with open("artifacts/check/report.json") as f:
    report = json.load(f)

if report["overall"] == "PASS":
    print("CI 通过，进入下一阶段")
else:
    for step in report["steps"]:
        if step["status"] == "FAIL":
            print(f"失败步骤: {step['name']}")
            for failure in step.get("failures", []):
                print(f"  - {failure['file']}:{failure['line']}: {failure['message']}")
```

---

## E. 禁止事项清单（Claude 必读）

| ❌ 禁止 | ✅ 应该 |
|--------|--------|
| 直接运行 `pytest` | 使用 `make.ps1 test` 或 `ci-json` |
| 猜测错误位置 | 解析 JSON 中的 `failures` 数组 |
| 一次修改太多文件 | 每轮只修复一个失败类型 |
| 跳过 context 刷新 | 每轮开始前运行 `context-dev` |
| 在 CHECK_MODE 下调用 broker | 检查是否有 `assert_not_check_mode` |

---

## F. 示例：Claude 完整执行流程

```
[Round 1]
> .\scripts\make.ps1 context-dev
> 阅读 artifacts\context\context.md
> 分析代码结构

> .\scripts\make.ps1 ci-json
> 读取 artifacts\check\report.json
> 发现: lint 失败 (src/foo.py:42 E501)
> 修改 src/foo.py 第42行

[Round 2]
> .\scripts\make.ps1 ci-json
> 读取 artifacts\check\report.json
> 发现: type 失败 (src/bar.py:10 incompatible types)
> 修改 src/bar.py 类型标注

[Round 3]
> .\scripts\make.ps1 ci-json
> overall: PASS
> 进入 replay 阶段

> .\scripts\make.ps1 replay-json
> 读取 artifacts\sim\report.json
> overall: PASS

[完成] CI + Replay 全部通过
```

---

## G. 与其他文档的关系

| 文档 | 内容 | 本文档引用 |
|------|------|-----------|
| [DEVELOPMENT.md](DEVELOPMENT.md) | 开发流程和工具使用 | 入口命令规范 |
| [EXIT_CODES.md](EXIT_CODES.md) | 退出码定义 | 失败类型映射 |
| [SPEC_CONTRACT_AUTOORDER.md](SPEC_CONTRACT_AUTOORDER.md) | 接口规范 | 代码修改参考 |
