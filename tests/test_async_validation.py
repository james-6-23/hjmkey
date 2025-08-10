#!/usr/bin/env python3
"""
异步批量验证模块测试脚本
测试10倍性能提升的验证功能
"""

import os
import sys
import asyncio
from pathlib import Path

# 添加项目根目录到Python路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.features.async_validation import AsyncValidationFeature


def test_async_validation():
    """测试异步验证功能"""
    print("🧪 测试异步验证功能...")
    
    # 创建配置
    config = {
        'MAX_CONCURRENT_VALIDATIONS': 10,
        'VALIDATION_BATCH_SIZE': 5,
        'VALIDATION_TIMEOUT': 30,
        'VALIDATION_RETRIES': 3
    }
    
    # 创建异步验证功能实例
    async_validation = AsyncValidationFeature(config)
    
    # 测试健康检查
    print(f"✅ 健康检查: {async_validation.is_healthy()}")
    
    # 测试降级实现
    fallback = async_validation.get_fallback()
    print(f"🔄 降级实现: {fallback}")
    
    print("\n✅ 异步验证功能测试完成")


async def test_batch_validation():
    """测试批量验证"""
    print("🧪 测试批量验证...")
    
    # 创建配置
    config = {
        'MAX_CONCURRENT_VALIDATIONS': 10,
        'VALIDATION_BATCH_SIZE': 5,
        'VALIDATION_TIMEOUT': 30,
        'VALIDATION_RETRIES': 3
    }
    
    # 创建异步验证功能实例
    async_validation = AsyncValidationFeature(config)
    
    # 测试数据
    test_tokens = [
        'AIzaSyA1234567890abcdef1234567890abcd1234567890',
        'AIzaSyB1234567890abcdef1234567890abcd1234567890',
        'AIzaSyC1234567890abcdef1234567890abcd1234567890',
        'invalid_token_example',
        'AIzaSyD1234567890abcdef1234567890abcd1234567890'
    ]
    
    test_types = ['gemini', 'gemini', 'gemini', 'github', 'gemini']
    
    # 执行批量验证
    results = await async_validation.validate_tokens_batch(test_tokens, test_types)
    
    print(f"📊 验证结果 ({len(results)} 个token):")
    for i, result in enumerate(results):
        token_display = test_tokens[i][:20] + "..." if len(test_tokens[i]) > 20 else test_tokens[i]
        print(f"  {i+1}. {token_display} -> {'有效' if result.get('is_valid', False) else '无效'}")
    
    print("\n✅ 批量验证测试完成")


if __name__ == "__main__":
    # 测试基本功能
    test_async_validation()
    
    print("\n" + "="*50 + "\n")
    
    # 测试批量验证（异步）
    asyncio.run(test_batch_validation())