#!/usr/bin/env python3
"""
监控告警模块测试脚本
测试系统健康和性能洞察功能
"""

import os
import sys
import asyncio
from pathlib import Path
from datetime import datetime

# 添加项目根目录到Python路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.features.monitoring import MonitoringFeature


def test_monitoring():
    """测试监控功能"""
    print("🧪 测试监控功能...")
    
    # 创建配置
    config = {
        'MONITORING_ENABLED': True,
        'METRICS_EXPORT_INTERVAL': 60,
        'ALERT_CHECK_INTERVAL': 30,
        'ERROR_RATE_THRESHOLD': 0.1,
        'LATENCY_THRESHOLD': 5.0
    }
    
    # 创建监控功能实例
    monitoring = MonitoringFeature(config)
    
    # 测试健康检查
    print(f"✅ 健康检查: {monitoring.is_healthy()}")
    
    # 测试降级实现
    fallback = monitoring.get_fallback()
    print(f"🔄 降级实现: {fallback}")
    
    # 记录一些指标
    print("\n📊 记录测试指标...")
    monitoring.increment_requests_total('GET', '/api/test', '200')
    monitoring.increment_requests_total('POST', '/api/test', '400')
    monitoring.observe_request_duration(0.5, 'GET', '/api/test')
    monitoring.set_active_connections(10)
    monitoring.increment_validation_attempts('gemini', 'success')
    monitoring.set_token_pool_size(100, 'gemini')
    
    # 获取指标文本
    metrics_text = monitoring.get_metrics_text()
    print(f"\n📈 指标文本预览 (前200字符):\n{metrics_text[:200]}...")
    
    # 获取系统统计
    stats = monitoring.get_system_stats()
    print(f"\n📊 系统统计: {stats}")
    
    # 获取最近告警
    alerts = monitoring.get_recent_alerts()
    print(f"🔔 最近告警数量: {len(alerts)}")
    
    print("\n✅ 监控功能测试完成")


def test_alerts():
    """测试告警功能"""
    print("\n🧪 测试告警功能...")
    
    # 创建配置
    config = {
        'MONITORING_ENABLED': True,
        'METRICS_EXPORT_INTERVAL': 60,
        'ALERT_CHECK_INTERVAL': 30,
        'ERROR_RATE_THRESHOLD': 0.1,
        'LATENCY_THRESHOLD': 5.0
    }
    
    # 创建监控功能实例
    monitoring = MonitoringFeature(config)
    
    # 模拟高错误率情况
    print("📊 模拟高错误率...")
    for i in range(20):
        if i < 18:
            monitoring.increment_requests_total('GET', '/api/test', '200')
        else:
            monitoring.increment_requests_total('GET', '/api/test', '500')
    
    # 获取系统统计（应该触发告警）
    stats = monitoring.get_system_stats()
    print(f"📊 系统统计: {stats}")
    
    # 获取最近告警
    alerts = monitoring.get_recent_alerts()
    print(f"🔔 最近告警数量: {len(alerts)}")
    
    print("\n✅ 告警功能测试完成")


if __name__ == "__main__":
    # 测试基本监控功能
    test_monitoring()
    
    # 测试告警功能
    test_alerts()