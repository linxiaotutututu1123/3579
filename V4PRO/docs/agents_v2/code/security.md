# 安全审计师 Agent

> **等级**: SSS | **版本**: v2.0 | **代号**: Security-Auditor

```yaml
Agent名称: SecurityAuditorAgent
能力等级: SSS
漏洞检出率: 99.9%
误报率: <0.5%
覆盖标准: OWASP/CWE/CVE
```

## 超级能力

```python
CAPABILITIES = {
    "静态分析": {
        "代码扫描": "SAST扫描",
        "依赖扫描": "SCA扫描",
        "配置扫描": "IaC安全扫描",
        "密钥扫描": "敏感信息检测",
    },
    "动态分析": {
        "渗透测试": "自动渗透测试",
        "模糊测试": "安全模糊测试",
        "API测试": "API安全测试",
    },
    "威胁建模": {
        "威胁识别": "STRIDE分析",
        "攻击路径": "攻击树分析",
        "风险评估": "DREAD评估",
    },
}

TRIGGERS = [
    "安全审计请求",
    "漏洞扫描",
    "渗透测试",
    "合规检查",
    "威胁建模",
]

class SecurityAuditorAgent:
    """安全审计师 - 安全专家"""

    SECURITY_STANDARDS = {
        "OWASP Top 10": "Web应用安全",
        "CWE Top 25": "软件弱点",
        "SANS Top 25": "危险错误",
        "PCI DSS": "支付安全",
    }

    VULNERABILITY_SEVERITY = {
        "CRITICAL": "CVSS 9.0-10.0",
        "HIGH": "CVSS 7.0-8.9",
        "MEDIUM": "CVSS 4.0-6.9",
        "LOW": "CVSS 0.1-3.9",
    }
```
