"""
V4PRO 顶级AI AGENT 简易 Demo Runner
运行方法：
  python -m V4PRO.agents.run_demo
或
  python V4PRO/agents/run_demo.py
"""
from .fin_multi_strategy_agent import FinMultiStrategyAgent
from .data_fusion import DataFusion
from .risk_control import RiskControl
from .asset_allocation import AssetAllocator
from .explainable import ExplainableAI
from .code_multilang_agent import CodeMultiLangAgent
from .auto_workflow import AutoWorkflowAgent
from .debug_optimize import DebugOptimizeAgent
from .security import SecurityAgent
from .knowledge import KnowledgeIntegrator
from .collab import CollabAgent


def mock_data():
    market_data = {"prices": {"AAPL": 180.0, "MSFT": 330.0}}
    news_data = [{"title": "Earnings beat", "ticker": "AAPL"}]
    social_data = [{"ticker": "AAPL", "sentiment": 0.7}]
    macro_data = {"rates": 0.035}
    return market_data, news_data, social_data, macro_data


def main():
    print("启动 V4PRO AGENT demo...")
    market_data, news_data, social_data, macro_data = mock_data()

    fusion = DataFusion()
    features = fusion.fuse(market_data, news_data, social_data, macro_data)
    print("融合特征：", features)

    fin_agent = FinMultiStrategyAgent()
    signal = fin_agent.run(market_data, news_data, social_data, macro_data)
    print("投研信号：", signal)

    allocator = AssetAllocator()
    allocation = allocator.allocate(features)
    print("资产配置：", allocation)

    rc = RiskControl()
    risk = rc.assess(allocation.get('portfolio', {}), market_data)
    print("风险评估：", risk)

    explain = ExplainableAI()
    print("决策解释：", explain.explain(signal))

    code_agent = CodeMultiLangAgent()
    sample_code = code_agent.run('示例：打印Hello', language='python')
    print("编码AGENT生成代码：\n", sample_code)

    workflow = AutoWorkflowAgent()
    wres = workflow.run(sample_code)
    print("自动化工作流执行：", wres)

    dbg = DebugOptimizeAgent()
    print("调试结果：", dbg.debug(sample_code))
    print("优化建议：", dbg.optimize(sample_code))

    sec = SecurityAgent()
    print("安全扫描：", sec.scan(sample_code))

    ki = KnowledgeIntegrator()
    print("知识查询：", ki.query('量化策略最佳实践'))

    collab = CollabAgent()
    print("代码审查：", collab.review(sample_code))
    print("知识共享：", collab.share('量化策略文档'))

    print("Demo 完成。")


if __name__ == '__main__':
    main()
