#!/usr/bin/env python3
"""
综合功能测试脚本
展示所有模块化功能的集成使用
"""

import os
import sys
import asyncio
from pathlib import Path

# 添加项目根目录到Python路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.features.feature_manager import get_feature_manager
from app.features.async_validation import AsyncValidationFeature
from app.features.monitoring import MonitoringFeature
from app.features.structured_logging import StructuredLoggingFeature
from app.features.progress_display import ProgressDisplayFeature
from app.features.connection_pool import ConnectionPoolFeature
from app.features.database import DatabaseFeature
from app.features.plugin_system import PluginSystemFeature


def test_feature_manager_integration():
    """测试特性管理器集成"""
    print("🧪 测试特性管理器集成...")
    
    # 获取特性管理器实例
    feature_manager = get_feature_manager()
    
    # 显示所有功能状态
    print("📋 所有功能状态:")
    for feature_name, status in feature_manager.feature_status.items():
        enabled = "✅" if feature_manager.is_enabled(feature_name) else "❌"
        print(f"  {enabled} {feature_name}: {status}")
    
    print("\n✅ 特性管理器集成测试完成")


def test_logging_feature():
    """测试结构化日志功能"""
    print("\n🧪 测试结构化日志功能...")
    
    # 创建配置
    config = {
        'STRUCTURED_LOGGING_ENABLED': True,
        'DEFAULT_LOG_FORMAT': 'json',
        'LOG_LEVEL': 'INFO',
        'LOG_FILE': 'logs/test.log',
        'LOG_TO_FILE': True,
        'LOG_TO_CONSOLE': True
    }
    
    # 创建日志功能实例
    logging_feature = StructuredLoggingFeature(config)
    
    # 测试日志记录
    logging_feature.info("测试信息日志", {"test": "value"})
    logging_feature.warning("测试警告日志", {"warning": "test"})
    logging_feature.error("测试错误日志", {"error": "demo"})
    
    print("  ✅ 日志记录测试完成")
    
    # 获取最近日志
    recent_logs = logging_feature.get_recent_logs(5)
    print(f"  📋 最近日志数量: {len(recent_logs)}")
    
    print("\n✅ 结构化日志功能测试完成")


def test_progress_feature():
    """测试进度显示功能"""
    print("\n🧪 测试进度显示功能...")
    
    # 创建配置
    config = {
        'PROGRESS_DISPLAY_ENABLED': True,
        'PROGRESS_UPDATE_INTERVAL': 0.1,
        'DEFAULT_PROGRESS_STYLE': 'bar',
        'PROGRESS_BAR_WIDTH': 30
    }
    
    # 创建进度显示功能实例
    progress_feature = ProgressDisplayFeature(config)
    
    # 测试创建进度跟踪器
    tracker = progress_feature.create_progress(100, "测试进度")
    print(f"  🔄 进度跟踪器创建: {tracker is not None}")
    
    # 测试更新进度
    if tracker:
        tracker.update(10, "更新进度测试")
        print(f"  📊 当前进度: {tracker.get_percentage()*100:.1f}%")
    
    print("\n✅ 进度显示功能测试完成")


def test_database_feature():
    """测试数据库功能"""
    print("\n🧪 测试数据库功能...")
    
    # 创建配置
    config = {
        'DATABASE_ENABLED': True,
        'DATABASE_TYPE': 'sqlite',
        'DATABASE_NAME': 'data/test.db',
        'DATABASE_POOL_SIZE': 5
    }
    
    # 创建数据库功能实例
    try:
        database_feature = DatabaseFeature(config)
        
        # 测试健康检查
        is_healthy = database_feature.is_healthy()
        print(f"  ✅ 数据库健康检查: {'通过' if is_healthy else '失败'}")
        
        # 测试保存token
        token_id = database_feature.save_token(
            "test_token_1234567890", 
            "gemini", 
            True, 
            {"source": "test"}
        )
        print(f"  💾 Token保存ID: {token_id}")
        
        # 测试获取token
        token_info = database_feature.get_token("test_token_1234567890")
        print(f"  🔍 Token查询结果: {'找到' if token_info else '未找到'}")
        
        print("\n✅ 数据库功能测试完成")
        
    except Exception as e:
        print(f"  ❌ 数据库功能测试失败: {e}")


def test_connection_pool_feature():
    """测试连接池功能"""
    print("\n🧪 测试连接池功能...")
    
    # 创建配置
    config = {
        'MAX_CONNECTIONS': 10,
        'CONNECTION_TIMEOUT': 30,
        'CONNECTION_RETRIES': 3,
        'CONNECTION_RETRY_DELAY': 1.0
    }
    
    # 创建连接池功能实例
    connection_pool = ConnectionPoolFeature(config)
    
    # 测试健康检查
    is_healthy = connection_pool.is_healthy()
    print(f"  ✅ 连接池健康检查: {'通过' if is_healthy else '失败'}")
    
    # 测试降级实现
    fallback = connection_pool.get_fallback()
    print(f"  🔄 降级实现: {fallback}")
    
    print("\n✅ 连接池功能测试完成")


async def test_async_features():
    """测试异步功能"""
    print("\n🧪 测试异步功能...")
    
    # 创建配置
    config = {
        'MAX_CONCURRENT_VALIDATIONS': 10,
        'VALIDATION_BATCH_SIZE': 5,
        'VALIDATION_TIMEOUT': 30
    }
    
    # 创建异步验证功能实例
    async_validation = AsyncValidationFeature(config)
    
    # 测试健康检查
    is_healthy = async_validation.is_healthy()
    print(f"  ✅ 异步验证健康检查: {'通过' if is_healthy else '失败'}")
    
    # 测试批量验证（简化版）
    test_tokens = ['test_token_1', 'test_token_2']
    test_types = ['gemini', 'github']
    
    try:
        results = await async_validation.validate_tokens_batch(test_tokens, test_types)
        print(f"  📊 批量验证完成，结果数量: {len(results)}")
    except Exception as e:
        print(f"  ⚠️ 批量验证异常: {e}")
    
    print("\n✅ 异步功能测试完成")


async def main():
    """主测试函数"""
    print("🎪 Hajimi King 模块化功能综合测试")
    print("=" * 50)
    
    # 测试特性管理器集成
    test_feature_manager_integration()
    
    # 测试结构化日志功能
    test_logging_feature()
    
    # 测试进度显示功能
    test_progress_feature()
    
    # 测试数据库功能
    test_database_feature()
    
    # 测试连接池功能
    test_connection_pool_feature()
    
    # 测试异步功能
    await test_async_features()
    
    print("\n" + "=" * 50)
    print("🎉 所有测试完成!")


if __name__ == "__main__":
    asyncio.run(main())