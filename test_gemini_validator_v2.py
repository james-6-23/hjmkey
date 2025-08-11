"""
测试改进后的 Gemini 密钥验证器
"""

import asyncio
import logging
from pathlib import Path
from utils.gemini_key_validator_v2 import (
    GeminiKeyValidatorV2, 
    ValidatorConfig,
    validate_keys_from_file,
    setup_logging
)


async def test_basic_validation():
    """测试基本验证功能"""
    print("\n=== 测试基本验证功能 ===")
    
    # 测试密钥（需要替换为实际密钥）
    test_keys = [
        "AIzaSyABCDEFGHIJKLMNOPQRSTUVWXYZ1234567",  # 示例格式
        "invalid_key_format",  # 无效格式
        "AIzaSy_invalid_chars!@#$%^&*()1234567",  # 包含无效字符
    ]
    
    config = ValidatorConfig(
        concurrency=5,
        timeout_sec=10,
        log_level="DEBUG"
    )
    
    async with GeminiKeyValidatorV2(config) as validator:
        # 测试格式验证
        for key in test_keys:
            is_valid = validator.validate_key_format(key)
            print(f"密钥格式验证 - {key[:20]}... : {'✅ 有效' if is_valid else '❌ 无效'}")
        
        # 测试批量验证（如果有实际密钥）
        valid_format_keys = [k for k in test_keys if validator.validate_key_format(k)]
        if valid_format_keys:
            print(f"\n开始验证 {len(valid_format_keys)} 个格式正确的密钥...")
            stats = await validator.validate_keys_batch(valid_format_keys, show_progress=False)
            print(f"验证结果: {stats}")


async def test_file_validation():
    """测试从文件验证"""
    print("\n=== 测试文件验证功能 ===")
    
    # 创建测试文件
    test_file = Path("test_keys.txt")
    test_content = """# 测试密钥文件
# 这是注释行，会被忽略

AIzaSyABCDEFGHIJKLMNOPQRSTUVWXYZ1234567
AIzaSyZYXWVUTSRQPONMLKJIHGFEDCBA9876543

# 另一个注释
invalid_key_here
"""
    
    # 写入测试文件
    test_file.write_text(test_content)
    print(f"创建测试文件: {test_file}")
    
    try:
        # 测试文件验证
        config = ValidatorConfig(
            concurrency=2,
            output_dir="test_output",
            save_backup=True
        )
        
        stats = await validate_keys_from_file(
            str(test_file), 
            config=config,
            save_results=False  # 测试时不保存结果
        )
        
        if stats:
            print(f"文件验证完成: {stats}")
    finally:
        # 清理测试文件
        if test_file.exists():
            test_file.unlink()
            print(f"删除测试文件: {test_file}")


async def test_performance():
    """测试性能和并发"""
    print("\n=== 测试性能和并发 ===")
    
    # 生成大量测试密钥（格式正确但可能无效）
    test_keys = []
    for i in range(100):
        # 生成格式正确的测试密钥
        key = f"AIzaSy{'A' * 33}"  # 简化的测试密钥
        # 修改最后几位使其不同
        key = key[:-3] + f"{i:03d}"
        test_keys.append(key)
    
    print(f"生成了 {len(test_keys)} 个测试密钥")
    
    # 测试不同并发级别
    for concurrency in [10, 50, 100]:
        config = ValidatorConfig(
            concurrency=concurrency,
            timeout_sec=5,
            max_retries=0  # 测试时不重试
        )
        
        print(f"\n测试并发级别: {concurrency}")
        async with GeminiKeyValidatorV2(config) as validator:
            import time
            start = time.time()
            
            # 注意：这会实际调用API，请谨慎使用
            # stats = await validator.validate_keys_batch(test_keys[:10], show_progress=False)
            
            # 仅测试格式验证的性能
            for key in test_keys:
                validator.validate_key_format(key)
            
            elapsed = time.time() - start
            print(f"处理 {len(test_keys)} 个密钥耗时: {elapsed:.3f} 秒")
            print(f"速度: {len(test_keys)/elapsed:.0f} 个/秒")


async def test_error_handling():
    """测试错误处理"""
    print("\n=== 测试错误处理 ===")
    
    config = ValidatorConfig(
        api_host="https://invalid-host-that-does-not-exist.com/",
        timeout_sec=2,
        max_retries=1
    )
    
    async with GeminiKeyValidatorV2(config) as validator:
        # 测试无效主机
        test_key = "AIzaSyABCDEFGHIJKLMNOPQRSTUVWXYZ1234567"
        
        try:
            result = await validator.validate_key(
                await validator.create_session(), 
                test_key
            )
            print(f"错误处理测试结果: {result}")
        except Exception as e:
            print(f"预期的错误: {type(e).__name__}: {e}")


async def main():
    """运行所有测试"""
    print("🧪 Gemini 密钥验证器 V2 测试套件")
    print("=" * 60)
    
    # 设置日志
    setup_logging("INFO")
    
    # 运行测试
    await test_basic_validation()
    await test_file_validation()
    await test_performance()
    await test_error_handling()
    
    print("\n✅ 所有测试完成!")


if __name__ == "__main__":
    asyncio.run(main())