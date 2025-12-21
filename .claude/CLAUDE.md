# V4PRO 框架的架构、设计原则与绝对规则

本文件会在会话启动时由 Claude Code 读取，以确保开发工作始终符合项目标准，产出一致且高质量的成果。

🎯 项目目标

看 行为准则.md 文件。
详细看 V4PRO_UPGRADE_PLAN_SUPREME_DIRECTIVE.md 文件。

💡 核心使命 (详细看 V4PRO_UPGRADE_PLAN_SUPREME_DIRECTIVE.md 文件)
通过以下能力提升人工智能辅助开发的效率与可靠性：
执行前置信度校验（避免开发方向偏差）
智能拆解任务（自动识别子任务）
自动生成代码（提高开发速度）
智能提示与补全（减少手动输入）
实施后效果验证（杜绝生成内容失真）
跨会话学习（基于反思模式）
高令牌效率的并行执行（提速 3.5 倍）
持续迭代更新（支持增量式升级））

💡 架构图
![V4PRO 框架架构图]（V4PRO_UPGRADE_PLAN_SUPREME_DIRECTIVE.md）

💡 绝对规则 (详细看 V4PRO_UPGRADE_PLAN_SUPREME_DIRECTIVE.md 文件)
1. 不允许修改框架的源码，只能通过配置文件来调整框架的行为。
2. 不允许添加新的依赖库，除非经过审核批准。
3. 不允许删除已有的功能或模块，除非有明确的理由和替代方案。
4. 不允许更改框架的核心算法和逻辑，除非有充分的理由和证明。
5. 不允许在框架中引入不安全的代码或操作，如访问敏感数据等。
6. 遵守 行为准则.md 文件。

📐 设计原则 (详细看 V4PRO_UPGRADE_PLAN_SUPREME_DIRECTIVE.md 文件)
1. 遵循 V4PRO_UPGRADE_PLAN_SUPREME_DIRECTIVE.md 中定义的行为规范和指令集。任何违反这些规定的代码或行为都将被拒绝。
2. 确保代码质量，遵循最佳实践编写代码。
3. 使用模块化设计，确保代码易于维护和扩展。
4. 优先考虑能力优化，确保框架在各种环境下都能高效计算准确率。
5. 保持良好的文档记录，确保代码易于理解和使用。
6. 确保安全性，防止潜在的安全漏洞。
7. 在编写代码之前，请先进行需求分析和设计文档撰写，以确保代码质量和可维护性。
8. 对于框架中的任何问题或建议，请及时反馈给开发团队，以便改进和完善框架。
9. 定期进行代码审查和测试，确保代码质量和稳定性。


  必须遵守的五大核心规范

1. 基于证据的开发
杜绝主观臆断—— 所有开发工作必须基于官方来源验证：
调用 Context7 MCP 获取官方文档
通过 WebFetch/WebSearch 开展调研
实施前先通过 Glob/Grep 检索现有代码
基于测试结果验证假设合理性
反模式警示：严禁基于主观假设或过时知识开展开发。
2. 置信度优先的实施流程
启动开发工作前必须完成置信度检查：
≥90%：直接推进功能实施
70%-89%：提供备选方案，继续深化调研
<70%：立即停止 —— 补充问题调研，完善前期准备
投入产出比（ROI）：投入 100-200 令牌进行置信度检查，可避免因方向错误浪费 5,000-50,000 令牌。
3. 并行优先的执行模式
采用 波浪式→检查点→波浪式 执行模式：
plaintext
第一波：[读取文件1、读取文件2、读取文件3]（并行执行）
   ↓
检查点：汇总分析所有文件内容
   ↓
第二波：[编辑文件1、编辑文件2、编辑文件3]（并行执行）
核心优势：相比串行执行提速 3.5 倍
适用场景：
独立操作（如多文件读取）
批量转换（如多文件编辑）
并行搜索（如多目录全局检索）
禁用场景：
存在依赖关系的操作（必须等待前置结果）
串行分析任务（需逐步构建上下文）
4. 令牌效率优化
根据任务复杂度分配令牌配额：
简单任务（如拼写错误修复）：200 令牌
中等任务（如 Bug 修复）：1,000 令牌
复杂任务（如功能开发）：2,500 令牌
置信度检查投入产出比：可实现 25-250 倍的令牌节约。
5. 零内容失真保障
采用自检协议（SelfCheckProtocol）杜绝生成内容失真：
四项核心校验问题：
所有测试是否全部通过？（需附输出结果）
所有需求是否全部满足？（需列核对清单）
是否存在未经验证的假设？（需附文档依据）
是否具备充分验证证据？（需附测试结果、代码变更记录、验证报告）
七大风险警示信号：
声称 “测试通过” 却不提供输出结果
声称 “功能正常” 却无任何验证证据
声称 “实施完成” 但测试用例失败
刻意忽略错误提示信息
无视代码编译警告
隐瞒功能故障问题
使用 “可能可用” 等模糊表述
🚫 绝对规则
Python 环境规范
Python 操作必须使用 UV 工具
bash
运行
uv run pytest              # 禁用：python -m pytest
uv pip install package     # 禁用：pip install package
uv run python script.py    # 禁用：python script.py
软件包结构：采用 src 目录布局
源码存放路径：src/superclaude/
测试代码路径：tests/
严禁将源码与测试代码混放同一目录
入口点配置：通过 pyproject.toml 声明
命令行工具：配置 [project.scripts] 节点
pytest 插件：配置 [project.entry-points.pytest11] 节点
测试规范
所有新功能必须配套测试用例
为独立组件编写单元测试
为组件交互逻辑编写集成测试
使用 pytest 标记区分测试类型：@pytest.mark.unit（单元测试）、@pytest.mark.integration（集成测试）
测试中必须集成项目管理智能体模式
python
运行
@pytest.mark.confidence_check
def test_feature(confidence_checker):
    context = {...}
    assert confidence_checker.assess(context) >= 0.7

@pytest.mark.self_check
def test_implementation(self_check_protocol):
    passed, issues = self_check_protocol.validate(impl)
    assert passed
测试夹具管理：通过 conftest.py 定义共享测试夹具
Git 工作流规范
分支结构
master：生产环境就绪代码
integration：集成测试分支（暂未创建）
feature/*、fix/*、docs/*：功能开发 / 问题修复 / 文档更新分支
提交信息：遵循约定式提交规范
feat: - 新增功能
fix: - 问题修复
docs: - 文档更新
refactor: - 代码重构
test: - 添加测试用例
chore: - 日常维护工作
禁止提交内容
__pycache__/、*.pyc 编译文件
.venv/、venv/ 虚拟环境目录
个人文件（如 TODO.txt、CRUSH.md）
API 密钥、敏感配置信息
文档规范
代码文档
所有公共函数必须编写文档字符串（Docstring）
强制使用类型注解
文档字符串中需包含使用示例
项目文档
更新 CLAUDE.md 完善 Claude Code 开发指引
更新 README.md 补充用户操作说明
更新本文件 PLANNING.md 记录架构决策
更新 TASK.md 维护当前工作任务
文档同步机制
代码变更时同步更新相关文档
新增功能时更新 CHANGELOG.md 变更日志
架构调整时更新本文件 PLANNING.md
版本管理规范
版本号权威来源
框架版本：存储在 VERSION 文件（例如 V4.0.0）
Python 包版本：配置在 pyproject.toml（例如 0.4.0）
NPM 包版本：配置在 package.json（需与 VERSION 文件版本一致）
版本升级规则
主版本：包含不兼容的 API 变更
次版本：新增功能且保持向后兼容
补丁版本：仅包含问题修复
🔄 开发工作流
新功能开发流程
调研阶段
阅读 PLANNING.md、TASK.md、KNOWLEDGE.md,V4PRO_UPGRADE_PLAN_SUPREME_DIRECTIVE.md 文档
通过 Glob/Grep 检索现有代码，检查功能重复
查阅官方文档（Context7 MCP）和开源实现方案（WebSearch）
执行置信度检查（目标置信度 ≥90%）
实施阶段
创建功能分支：git checkout -b feature/功能名称
遵循测试驱动开发（TDD）原则，先编写测试用例
功能代码开发实现
运行测试：uv run pytest
代码规范检查：make lint
代码格式化：make format
验证阶段
执行自检协议（SelfCheckProtocol）
验证所有测试用例通过
确认所有需求点满足
验证所有假设均有依据
整理并提供完整验证证据
文档阶段
更新相关技术文档
为新增代码编写文档字符串
更新 CHANGELOG.md 变更日志
更新 TASK.md（标记任务完成状态）
更新 CLAUDE.md（必要）
更新 README.md（必要）
更新 PLANNING.md（必要）
更新 V4PRO_UPGRADE_PLAN_SUPREME_DIRECTIVE.md（必须）
评审阶段
创建合并请求（Pull Request）
发起代码评审
处理评审反馈意见
合并到集成分支（若无集成分支则合并到主分支）
Bug 修复流程
根因分析阶段
复现 Bug 问题
定位根本原因（而非仅解决表面症状）
查阅反思记忆库，检索相似问题模式
执行置信度检查
修复实施阶段
编写可复现问题的失败测试用例
开发 Bug 修复代码
验证测试用例通过
运行完整测试套件
将修复方案记录到反思记忆库
预防机制
添加回归测试用例
必要时更新相关文档
在 KNOWLEDGE.md 中分享经验总结
📊 质量指标
代码质量
测试覆盖率：目标值 >95%
代码规范：零 ruff 检查错误
类型检查：强制使用类型注解，mypy 检查错误数最小化
文档覆盖率：所有公共 API 100% 文档化
项目管理智能体指标
置信度检查投入产出比：25-250 倍令牌节约
自检失真检测率：94%
并行执行效率：相比串行执行提速 3.5 倍
令牌效率：合理预算分配可减少 30-50% 令牌消耗
发布验收标准
新版本发布前必须满足以下条件：
✅ 所有测试用例通过
✅ 相关文档已同步更新
✅ CHANGELOG.md 已更新
✅ 所有版本号保持一致
✅ 无Bug
✅ 已通过安全审计
✅ 完成 V4PRO_UPGRADE_PLAN_SUPREME_DIRECTIVE.md 全部的内容和记录
✅ 完成本文件 CLAUDE.md 全部的内容
✅ 完成 TASK.md 全部的内容和记录
✅ 完成 KNOWNLEGE.md 全部的内容和记录
✅ 完成 CLAUDE.md 全部的内容和记录
✅ 完成 PLANNING.md 全变的内容和记录
✅ 完成 README.md 全部的内容和记录
详细看 V4PRO_UPGRADE_PLAN_SUPREME_DIRECTIVE.md 文件。



核心要点：
严格遵守本文件和 V4PRO_UPGRADE_PLAN_SUPREME_DIRECTIVE.md 文件和 行为准则.md 文件中的绝对规则
所有新增代码必须配套测试用例
集成项目管理智能体模式
同步更新相关文档
提交合并请求前必须发起代码评审

⚠ 最终一切以 V4PRO_UPGRADE_PLAN_SUPREME_DIRECTIVE.md 文件和 行为准则.md 文件为准。

📚 参考资源
TASK.md：当前任务与优先级列表
KNOWLEDGE.md：经验总结与最佳实践
CONTRIBUTING.md：贡献指南
docs/：完整项目文档库

本文件由 山东齐沥开发团队维护，任何架构决策变更均需同步更新。
最后更新时间：2025-11-12（修复议题 #466 时自动生成）