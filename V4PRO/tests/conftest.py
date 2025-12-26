"""
V4PRO Platform 测试根配置.

设置Python路径以支持src模块导入。
"""

from __future__ import annotations

import sys
from pathlib import Path

# 将项目根目录添加到Python路径
project_root = Path(__file__).parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))
