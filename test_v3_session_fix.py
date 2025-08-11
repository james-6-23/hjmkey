#!/usr/bin/env python3
"""
测试V3版本Session管理修复
验证是否解决了"RuntimeError: Session is closed"错误
"""

import asyncio
import logging
import sys
from pathlib import Path

# 添加项目根目录到Python路径
sys.path.insert(0, str(Path(__file__).parent))

# 直接导入需要的类，避免导入整个模块
try:
    # 尝试直接导入
    from app.core.gemini_validator_adapter import OptimizedOrchestratorValidator
except ImportError as e:
    print(f"导入错误: {e}")
    print("尝试安装缺失的依赖...")
    import subprocess
    subprocess.run([sys.executable, "-m", "pip", "install", "google-generativeai", "aiohttp"], check=False)
    
    # 再次尝试导入
    try:
        from app.core.gemini_validator_adapter import OptimizedOrchestratorValidator
    except ImportError as e2:
        print(f"仍然无法导入: {e2}")
        print("\n请手动安装依赖:")
        print("pip install google-generativeai aiohttp")
        sys.exit(1)

# 设置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)s | %(name)s | %(message)s'
)
logger = logging.getLogger(__name__)


async def test_multiple_validations():
    """测试多次验证是否会出现Session关闭错误"""
    
    # 创建验证器
    validator = OptimizedOrchestratorValidator(concurrency=10)
    
    # 测试密钥（这些是无效的示例密钥）
    test_keys = [
        "AIzaSyA1234567890abcdefghijklmnopqrstuv",
        "AIzaSyB1234567890abcdefghijklmnopqrstuv",
        "AIzaSyC1234567890abcdefghijklmnopqrstuv",
    ]
    
    try:
        logger.info("=" * 60)
        logger.info("🧪 开始测试V3 Session管理修复")
        logger.info("=" * 60)
        
        # 测试1：第一次验证
        logger.info("\n📝 测试1：第一次验证")
        logger.info("-" * 40)
        try:
            results1 = await validator.validate_batch_async(test_keys)
            logger.info(f"✅ 第一次验证成功，验证了 {len(results1)} 个密钥")
            for i, result in enumerate(results1, 1):
                logger.info(f"   密钥{i}: valid={result.is_valid}, rate_limited={result.is_rate_limited}")
        except Exception as e:
            logger.error(f"❌ 第一次验证失败: {e}")
            return False
        
        # 等待一下
        await asyncio.sleep(2)
        
        # 测试2：第二次验证（这是之前会失败的地方）
        logger.info("\n📝 测试2：第二次验证（之前会出现Session closed错误）")
        logger.info("-" * 40)
        try:
            results2 = await validator.validate_batch_async(test_keys)
            logger.info(f"✅ 第二次验证成功，验证了 {len(results2)} 个密钥")
            for i, result in enumerate(results2, 1):
                logger.info(f"   密钥{i}: valid={result.is_valid}, rate_limited={result.is_rate_limited}")
        except Exception as e:
            logger.error(f"❌ 第二次验证失败: {e}")
            if "Session is closed" in str(e):
                logger.error("⚠️ Session管理问题仍然存在！")
            return False
        
        # 等待一下
        await asyncio.sleep(2)
        
        # 测试3：第三次验证
        logger.info("\n📝 测试3：第三次验证")
        logger.info("-" * 40)
        try:
            results3 = await validator.validate_batch_async(test_keys)
            logger.info(f"✅ 第三次验证成功，验证了 {len(results3)} 个密钥")
            for i, result in enumerate(results3, 1):
                logger.info(f"   密钥{i}: valid={result.is_valid}, rate_limited={result.is_rate_limited}")
        except Exception as e:
            logger.error(f"❌ 第三次验证失败: {e}")
            return False
        
        logger.info("\n" + "=" * 60)
        logger.info("🎉 所有测试通过！Session管理问题已修复")
        logger.info("=" * 60)
        return True
        
    finally:
        # 清理资源
        await validator.cleanup()
        logger.info("🧹 资源已清理")


async def test_concurrent_validations():
    """测试并发验证"""
    logger.info("\n" + "=" * 60)
    logger.info("🧪 测试并发验证")
    logger.info("=" * 60)
    
    # 创建验证器
    validator = OptimizedOrchestratorValidator(concurrency=10)
    
    # 测试密钥
    test_keys = [
        ["AIzaSyA1234567890abcdefghijklmnopqrstuv"],
        ["AIzaSyB1234567890abcdefghijklmnopqrstuv"],
        ["AIzaSyC1234567890abcdefghijklmnopqrstuv"],
    ]
    
    try:
        # 并发执行多个验证
        tasks = [validator.validate_batch_async(keys) for keys in test_keys]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # 检查结果
        success_count = 0
        for i, result in enumerate(results, 1):
            if isinstance(result, Exception):
                logger.error(f"❌ 并发验证{i}失败: {result}")
                if "Session is closed" in str(result):
                    logger.error("⚠️ Session管理问题在并发场景下仍然存在！")
            else:
                logger.info(f"✅ 并发验证{i}成功")
                success_count += 1
        
        if success_count == len(results):
            logger.info("🎉 并发验证测试通过！")
            return True
        else:
            logger.error(f"⚠️ 并发验证测试失败: {success_count}/{len(results)} 成功")
            return False
            
    finally:
        await validator.cleanup()


async def main():
    """主测试函数"""
    logger.info("🚀 开始测试V3版本Session管理修复")
    
    # 运行顺序验证测试
    sequential_passed = await test_multiple_validations()
    
    # 运行并发验证测试
    concurrent_passed = await test_concurrent_validations()
    
    # 总结
    logger.info("\n" + "=" * 60)
    logger.info("📊 测试总结")
    logger.info("=" * 60)
    logger.info(f"顺序验证测试: {'✅ 通过' if sequential_passed else '❌ 失败'}")
    logger.info(f"并发验证测试: {'✅ 通过' if concurrent_passed else '❌ 失败'}")
    
    if sequential_passed and concurrent_passed:
        logger.info("\n🎊 所有测试通过！V3版本Session管理问题已完全修复")
        return 0
    else:
        logger.error("\n❌ 部分测试失败，需要进一步调试")
        return 1


if __name__ == "__main__":
    # 运行测试
    exit_code = asyncio.run(main())
    sys.exit(exit_code)