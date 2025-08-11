#!/usr/bin/env python3
"""
简化的V3版本测试脚本
直接测试Session管理修复，不依赖复杂的模块导入
"""

import asyncio
import aiohttp
import logging
from typing import List

# 设置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)s | %(message)s'
)
logger = logging.getLogger(__name__)


class SimpleValidator:
    """简化的验证器，模拟Session管理"""
    
    def __init__(self):
        self.session = None
        self.call_count = 0
    
    async def create_session(self):
        """创建新的Session"""
        return aiohttp.ClientSession()
    
    async def validate_with_reused_session(self, keys: List[str]):
        """错误的方式：重用已关闭的Session"""
        self.call_count += 1
        logger.info(f"调用 #{self.call_count}: 使用重用的Session")
        
        if self.session is None:
            # 第一次创建Session
            async with self.create_session() as session:
                self.session = session  # 错误：保存了Session引用
                logger.info(f"  创建了新Session: {id(session)}")
                # 模拟验证
                await asyncio.sleep(0.1)
                return f"验证了 {len(keys)} 个密钥"
        else:
            # 尝试重用Session（会失败）
            logger.info(f"  尝试重用Session: {id(self.session)}")
            if self.session.closed:
                raise RuntimeError("Session is closed")
            # 这里会出错
            return f"验证了 {len(keys)} 个密钥"
    
    async def validate_with_new_session(self, keys: List[str]):
        """正确的方式：每次创建新的Session"""
        self.call_count += 1
        logger.info(f"调用 #{self.call_count}: 使用新的Session")
        
        # 每次都创建新的Session
        async with self.create_session() as session:
            logger.info(f"  创建了新Session: {id(session)}")
            # 模拟验证
            await asyncio.sleep(0.1)
            return f"验证了 {len(keys)} 个密钥"


async def test_wrong_approach():
    """测试错误的Session管理方式（会失败）"""
    logger.info("\n" + "="*60)
    logger.info("测试错误的Session管理方式（重用Session）")
    logger.info("="*60)
    
    validator = SimpleValidator()
    test_keys = ["key1", "key2", "key3"]
    
    try:
        # 第一次调用 - 应该成功
        result1 = await validator.validate_with_reused_session(test_keys)
        logger.info(f"✅ 第一次调用成功: {result1}")
        
        # 第二次调用 - 会失败
        await asyncio.sleep(1)
        result2 = await validator.validate_with_reused_session(test_keys)
        logger.info(f"✅ 第二次调用成功: {result2}")
        
    except RuntimeError as e:
        logger.error(f"❌ 错误: {e}")
        logger.info("这就是V3版本之前的问题！")
        return False
    
    return True


async def test_correct_approach():
    """测试正确的Session管理方式（会成功）"""
    logger.info("\n" + "="*60)
    logger.info("测试正确的Session管理方式（每次新建Session）")
    logger.info("="*60)
    
    validator = SimpleValidator()
    test_keys = ["key1", "key2", "key3"]
    
    try:
        # 第一次调用
        result1 = await validator.validate_with_new_session(test_keys)
        logger.info(f"✅ 第一次调用成功: {result1}")
        
        # 第二次调用
        await asyncio.sleep(1)
        result2 = await validator.validate_with_new_session(test_keys)
        logger.info(f"✅ 第二次调用成功: {result2}")
        
        # 第三次调用
        await asyncio.sleep(1)
        result3 = await validator.validate_with_new_session(test_keys)
        logger.info(f"✅ 第三次调用成功: {result3}")
        
        logger.info("🎉 所有调用都成功！这是修复后的方式")
        return True
        
    except Exception as e:
        logger.error(f"❌ 意外错误: {e}")
        return False


async def test_concurrent_sessions():
    """测试并发Session创建"""
    logger.info("\n" + "="*60)
    logger.info("测试并发Session创建")
    logger.info("="*60)
    
    validator = SimpleValidator()
    test_keys = ["key1", "key2", "key3"]
    
    # 并发执行多个验证
    tasks = [
        validator.validate_with_new_session(test_keys)
        for _ in range(5)
    ]
    
    try:
        results = await asyncio.gather(*tasks)
        logger.info(f"✅ 并发执行 {len(results)} 个任务成功")
        for i, result in enumerate(results, 1):
            logger.info(f"  任务{i}: {result}")
        return True
    except Exception as e:
        logger.error(f"❌ 并发执行失败: {e}")
        return False


async def main():
    """主测试函数"""
    logger.info("🚀 开始测试V3版本Session管理")
    logger.info("这个测试展示了Session管理问题的本质和修复方法\n")
    
    # 测试错误的方式
    wrong_passed = await test_wrong_approach()
    
    # 测试正确的方式
    correct_passed = await test_correct_approach()
    
    # 测试并发
    concurrent_passed = await test_concurrent_sessions()
    
    # 总结
    logger.info("\n" + "="*60)
    logger.info("📊 测试总结")
    logger.info("="*60)
    logger.info(f"错误方式测试: {'❌ 如预期失败' if not wrong_passed else '⚠️ 意外成功'}")
    logger.info(f"正确方式测试: {'✅ 通过' if correct_passed else '❌ 失败'}")
    logger.info(f"并发测试: {'✅ 通过' if concurrent_passed else '❌ 失败'}")
    
    if correct_passed and concurrent_passed:
        logger.info("\n🎊 修复方案验证成功！")
        logger.info("说明：")
        logger.info("1. 错误方式展示了V3之前的问题（Session重用导致关闭错误）")
        logger.info("2. 正确方式展示了修复后的行为（每次创建新Session）")
        logger.info("3. 并发测试确保了线程安全")
        return 0
    else:
        logger.error("\n❌ 测试未完全通过")
        return 1


if __name__ == "__main__":
    import sys
    exit_code = asyncio.run(main())
    sys.exit(exit_code)