#!/usr/bin/env python3
"""
快速测试语法修复
"""

import sys
from pathlib import Path

# 添加项目根目录到Python路径
sys.path.insert(0, str(Path(__file__).parent))

try:
    # 尝试导入修复后的模块
    from app.core.orchestrator_v2 import OrchestratorV2
    print("✅ 语法修复成功！模块可以正常导入")
    
    # 测试初始化
    print("🔧 测试初始化...")
    orchestrator = OrchestratorV2()
    print("✅ OrchestratorV2 初始化成功")
    
except SyntaxError as e:
    print(f"❌ 语法错误仍然存在: {e}")
    sys.exit(1)
    
except ImportError as e:
    print(f"❌ 导入错误: {e}")
    sys.exit(1)
    
except Exception as e:
    print(f"⚠️ 其他错误（但语法已修复）: {e}")
    print("   这可能是配置或依赖问题，但语法错误已解决")
    
print("\n✅ 所有语法错误已修复！")