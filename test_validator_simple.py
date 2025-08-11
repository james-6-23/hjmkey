"""
简化的验证器测试
"""

import asyncio
import logging
from utils.gemini_key_validator_v2 import (
    GeminiKeyValidatorV2, 
    ValidatorConfig,
    setup_logging
)


async def test_simple():
    """简单测试"""
    # 设置日志
    setup_logging("INFO")
    
    # 测试密钥格式验证
    print("\n=== 测试密钥格式验证 ===")
    validator = GeminiKeyValidatorV2()
    
    test_keys = [
        "AIzaSyABCDEFGHIJKLMNOPQRSTUVWXYZ1234567",  # 正确格式
        "invalid_key",  # 错误格式
        "AIzaSy123",  # 太短
    ]
    
    for key in test_keys:
        is_valid = validator.validate_key_format(key)
        print(f"{key[:20]}... : {'✅ 格式正确' if is_valid else '❌ 格式错误'}")
    
    # 测试单个密钥验证（使用假密钥）
    print("\n=== 测试单个密钥验证 ===")
    valid_format_key = "AIzaSyABCDEFGHIJKLMNOPQRSTUVWXYZ1234567"
    
    async with validator.create_session() as session:
        result = await validator.validate_key(session, valid_format_key)
        print(f"密钥: {result.key[:10]}...")
        print(f"状态: {result.tier.value}")
        print(f"错误: {result.error_message}")
    
    # 清理
    await validator.connector.close()
    
    print("\n✅ 测试完成!")


if __name__ == "__main__":
    asyncio.run(test_simple())