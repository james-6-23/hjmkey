#!/usr/bin/env python3
"""
特性管理器测试脚本
测试模块化架构的核心组件
"""

import os
import sys
from pathlib import Path

# 添加项目根目录到Python路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.features.feature_manager import get_feature_manager


def test_feature_manager():
    """测试特性管理器"""
    print("🧪 测试特性管理器...")
    
    # 创建特性管理器实例
    feature_manager = get_feature_manager()
    
    # 显示所有功能状态
    print("📋 功能状态:")
    for feature_name, status in feature_manager.feature_status.items():
        print(f"  {feature_name}: {status}")
    
    # 测试特定功能
    print("\n🔍 测试异步验证功能:")
    if feature_manager.is_enabled('async_validation'):
        async_validation = feature_manager.get_feature('async_validation')
        print(f"  异步验证功能已启用: {async_validation}")
    else:
        print("  异步验证功能未启用")
    
    print("\n🔍 测试监控功能:")
    if feature_manager.is_enabled('monitoring'):
        monitoring = feature_manager.get_feature('monitoring')
        print(f"  监控功能已启用: {monitoring}")
    else:
        print("  监控功能未启用")
    
    print("\n✅ 特性管理器测试完成")


if __name__ == "__main__":
    test_feature_manager()