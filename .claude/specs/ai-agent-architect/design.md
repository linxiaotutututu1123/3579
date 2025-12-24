# 设计文档：AI Agent — Architect（ai-agent-architect）

> **版本**: v0.1
> **状态**: 草稿
> **作者**: 自动生成（可修改）
> **语言**: 中文（支持中/英双语输出）
> **最后更新**: 2025-12-24

---

## 📋 执行摘要

**目标**: 创建一款面向架构师与开发团队的 AI Agent，主要能力包括：
- 自动生成架构设计文档（基于 `spec-design` 模板）✅
- 审查并给出现有设计改进建议（包含 ADR 建议）✅
- 参与代码审查并给出架构/安全/可观测性相关建议✅
- 提供交互式聊天（基于 Claude Code）以完成设计对话与澄清需求✅

**用户群**: 内部开发者、系统架构师、产品经理（也可用于外部客户演示）

**主要质量关注点**: 性能 / 可用性 / 安全 / 可观测性 / 可解释性

**关键决策（初稿）**:
1. LLM 后端：优先集成 **Claude Code**（如需可扩展到其它模型） — ADR-001
2. 运行时与语言：**Python**（便于现有 repo 集成与扩展） — ADR-002
3. 部署形式：**CLI + HTTP 服务 + VS Code Chat（可选扩展）** — ADR-003
4. 文档格式：**Markdown + Mermaid**（存放位置：`.claude/specs/{feature}/design.md`） — ADR-004
5. CI/CD：**GitHub Actions** + Docker 镜像构建 + 单元测试与静态分析 — ADR-005

---

## 🎯 功能与用例

### 核心用例
- U1: 用户在聊天中描述需求，Agent 生成完整的架构设计草案（含 C4、时序图、ADR 建议）
- U2: 用户提交现有设计文件，Agent 进行审查并返回逐条改进建议与参考代码片段
- U3: Agent 在 Pull Request 上发表评论（通过 CI hook）并提出安全/性能/可观测性建议
- U4: 用户请求生成 ADR 模板，Agent 草拟 ADR 并提供比较选项与风险评估

### 交互方式
- 聊天交互（主要）: Claude Code 驱动，支持中/英双语
- CLI: 生成文档命令（例如 `aagent gen --feature orders --lang zh`）
- HTTP API: 支持 programmatic 调用（POST /generate、/review、/suggest-adr）

---

## 🏗️ 高层架构（C4 上下文）

```mermaid
C4Context
    title AI Agent - Architect
    Person(user, "开发者 / 架构师 / PM", "使用聊天或 CLI 与 Agent 交互")
    System(agent, "AI Agent", "生成文档 / 审查 / ADR 建议")
    System_Ext(claude, "Claude Code", "LLM 提供者")

    user -> agent : 发起对话 / 提交设计 / 请求 ADR
    agent -> claude : 请求生成文本、图表、建议
    agent -> user : 返回文档、建议、PR 评论
```

---

## 🔧 组件设计

- Chat Adapter（Claude Code 集成）
  - 负责管理对话上下文、系统提示与多轮状态
  - 支持调用 Claude Code 的 streaming/同步 API

- Spec Engine（模板驱动文档生成）
  - 基于 `spec-design` 模板填充（Mermaid + Markdown）
  - 支持模式：新建/更新/审查

- Review Engine（静态审查 + 规则引擎）
  - 风险检测、性能建议、安全检测脚本（基于规则+模型）

- ADR Recommender
  - 基于设计变更与比较矩阵生成 ADR 草案

- Integrations
  - GitHub Actions（CI hooks、PR 注释）
  - VS Code Chat（可选扩展或现成 chat client 集成）

- Infra
  - HTTP API（FastAPI）
  - CLI（Click/Typer）
  - Docker 镜像

---

## 🔐 安全与隐私

- LLM Key 管理：使用環境變量 + secrets 管理（GitHub Secrets / Vault）
- 请求与响应日志：敏感字段脱敏（`token`, `authorization`, `password`）
- 数据保留策略：默认不存储用户私有文档，若需存储必须显式授权并加密
- 访问控制：API token + 基本 RBAC（初期）

---

## 📈 性能 / 可用性 / 可观测性

- 性能目标（示例）：
  - 生成小型设计（< 1 页）：P95 < 3s
  - 生成复杂设计（含多图）：P95 < 15s
- 可用性：支持自动重试、Claude Code 限流降级策略（fallback 模式）
- 可观测性：Prometheus + OpenTelemetry tracing + 结构化日志
- 指标示例：requests_total、generation_time_seconds、review_issues_found

---

## ✅ 验收标准（MVP）

- 能通过 CLI/HTTP 接口生成包含：执行摘要、架构图（Mermaid）、组件清单、关键决策与 ADR 建议的 Markdown 文档
- 能对提交的 `design.md` 给出逐条审查建议并输出可复制的补丁或改进点
- 在 GH Actions 中能对 PR 触发静态审查并发表评论
- 包含单元测试覆盖关键函数、CI 流程（lint、tests、build）、Dockerfile

---

## 🧪 测试与 CI

- 单元测试：pytest
- 集成测试：在 Docker 容器中运行 FastAPI + 模拟 Claude Code（可切换为 mock）
- CI（GitHub Actions）：lint (ruff/flake8), pytest, build docker image, security scan

---

## 📦 交付物与目录结构（建议）

- `aagent/`
  - `cli.py` (Typer)
  - `server/` (FastAPI)
  - `integrations/claude.py`
  - `spec_engine/` (模板填充)
  - `review/` (审查规则)
  - `adr/` (ADR 生成器)
  - `tests/`
- `Dockerfile`, `docker-compose.yml`, `.github/workflows/ci.yml`

---

## 🛣️ 里程碑与任务（短期）

1. 设计规范 & 用例确认（本文件） ✅
2. 搭建代码骨架（包、CLI、简单 HTTP） — 目标：可通过 `aagent gen` 生成最小设计 ✅（下一步）
3. 集成 Claude Code（stub -> 实际 API）
4. 实现 Spec Engine 模板填充
5. 实现审查规则并在 PR 上发表评论
6. 编写测试 & CI

---

## ADR 建议（草案）
- ADR-001: 采用 Claude Code 作为首选 LLM 后端（理由：符合需求中的 "CLAUDE CODE" 优先集成）
- ADR-002: 代码语言选型为 Python（理由：团队熟悉、生态丰富）
- ADR-003: 部署形式为 CLI + HTTP + VS Code 集成（逐步实现）

---

## 未来扩展
- 支持多模型（OpenAI/Anthropic 等）与本地模型的插件式后端
- 增强 PR 审查能力：自动生成测试用例、代码片段 & 可执行补丁
- 可视化 UI（Web dashboard）展示生成的图表和 ADR 历史

---

## 附：示例 CLI 使用

```bash
# 生成新特性设计（中文）
aagent gen --feature orders --lang zh --output .claude/specs/orders/design.md

# 审查现有设计
aagent review --file .claude/specs/orders/design.md
```

---

> **待确认**:
> - 是否需要在 MVP 中提供 VS Code 扩展（若需要，开发工作量会增加）
> - 是否允许 Agent 将审查结果自动推 PR 注释（安全与权限问题需评估）


---

**接下步**: 如果你确认此规范，我会把当前 todo 标记为完成并开始搭建代码骨架（`编写 Agent 设计规范` → 完成，`搭建代码骨架` → 进行中）。


*文档生成自 `spec-design` 模板并根据你的偏好定制。*