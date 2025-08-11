"""
验证器性能测试
比较串行验证和并发验证的性能差异
"""

import asyncio
import time
import logging
from typing import List

# 设置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)s | %(message)s'
)
logger = logging.getLogger(__name__)

# 导入验证器
from app.core.validator import GeminiKeyValidator
from app.core.validator_async import AsyncGeminiKeyValidator, OptimizedKeyValidator


def generate_test_keys(count: int) -> List[str]:
    """生成测试密钥"""
    # 生成格式正确但可能无效的测试密钥
    keys = []
    for i in range(count):
        # AIzaSy + 33个字符
        key = f"AIzaSy{'X' * 30}{i:03d}"
        keys.append(key)
    return keys


def test_serial_validation(keys: List[str]):
    """测试串行验证性能"""
    logger.info("=" * 60)
    logger.info("🐌 测试串行验证（原始方法）")
    logger.info("=" * 60)
    
    # 使用原始验证器
    validator = GeminiKeyValidator(delay_range=(0.5, 1.5))
    
    start_time = time.time()
    results = validator.validate_batch(keys)
    elapsed = time.time() - start_time
    
    # 统计结果
    valid_count = sum(1 for r in results if r.is_valid)
    invalid_count = len(results) - valid_count
    
    logger.info(f"✅ 完成验证 {len(keys)} 个密钥")
    logger.info(f"   有效: {valid_count}, 无效: {invalid_count}")
    logger.info(f"⏱️  耗时: {elapsed:.2f} 秒")
    logger.info(f"🚀 速度: {len(keys)/elapsed:.2f} 个/秒")
    
    return elapsed


async def test_async_validation(keys: List[str]):
    """测试异步并发验证性能"""
    logger.info("=" * 60)
    logger.info("⚡ 测试异步并发验证（优化方法）")
    logger.info("=" * 60)
    
    # 使用异步验证器
    async_validator = AsyncGeminiKeyValidator(
        max_concurrent=20,
        delay_range=(0.05, 0.1)
    )
    validator = OptimizedKeyValidator(async_validator)
    
    start_time = time.time()
    results = await validator.validate_batch_async(keys)
    elapsed = time.time() - start_time
    
    # 统计结果
    valid_count = sum(1 for r in results if r.is_valid)
    invalid_count = len(results) - valid_count
    
    logger.info(f"✅ 完成验证 {len(keys)} 个密钥")
    logger.info(f"   有效: {valid_count}, 无效: {invalid_count}")
    logger.info(f"⏱️  耗时: {elapsed:.2f} 秒")
    logger.info(f"🚀 速度: {len(keys)/elapsed:.2f} 个/秒")
    
    return elapsed


async def compare_performance():
    """比较性能差异"""
    # 测试不同数量的密钥
    test_sizes = [5, 10, 20]
    
    logger.info("🔬 密钥验证器性能对比测试")
    logger.info("=" * 60)
    
    for size in test_sizes:
        logger.info(f"\n📊 测试 {size} 个密钥的验证性能")
        
        # 生成测试密钥
        keys = generate_test_keys(size)
        
        # 测试串行验证
        serial_time = test_serial_validation(keys[:5])  # 只测试前5个避免太慢
        
        # 测试异步验证
        async_time = await test_async_validation(keys)
        
        # 计算性能提升
        if serial_time > 0:
            # 基于5个密钥的串行时间推算完整时间
            estimated_serial_time = serial_time * (size / 5)
            speedup = estimated_serial_time / async_time
            logger.info(f"\n🎯 性能提升: {speedup:.1f}x")
            logger.info(f"   预计串行耗时: {estimated_serial_time:.2f} 秒")
            logger.info(f"   实际并发耗时: {async_time:.2f} 秒")
            logger.info(f"   节省时间: {estimated_serial_time - async_time:.2f} 秒")


async def test_real_validation():
    """测试真实密钥验证（需要有效密钥）"""
    logger.info("\n" + "=" * 60)
    logger.info("🔑 测试真实密钥验证")
    logger.info("=" * 60)
    
    # 这里可以放入真实的测试密钥
    real_keys = [
        # "AIzaSyXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX",  # 替换为真实密钥
    ]
    
    if not real_keys:
        logger.info("⚠️  没有配置真实密钥，跳过真实验证测试")
        return
    
    validator = OptimizedKeyValidator(AsyncGeminiKeyValidator())
    
    start_time = time.time()
    results = await validator.validate_batch_async(real_keys)
    elapsed = time.time() - start_time
    
    for i, result in enumerate(results):
        logger.info(f"密钥 {i+1}: {result.status.value} - {result.message}")
    
    logger.info(f"\n⏱️  验证 {len(real_keys)} 个真实密钥耗时: {elapsed:.2f} 秒")


async def main():
    """主测试函数"""
    try:
        # 性能对比测试
        await compare_performance()
        
        # 真实密钥测试（可选）
        await test_real_validation()
        
        logger.info("\n✅ 所有测试完成！")
        
    except Exception as e:
        logger.error(f"测试失败: {e}")
        raise


if __name__ == "__main__":
    # 运行测试
    asyncio.run(main())