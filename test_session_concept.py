#!/usr/bin/env python3
"""
Session管理概念验证
展示V3版本Session管理问题的本质和修复方法
不依赖任何外部库
"""

import asyncio
import logging

# 设置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)s | %(message)s'
)
logger = logging.getLogger(__name__)


class MockSession:
    """模拟的Session对象"""
    
    def __init__(self, session_id):
        self.id = session_id
        self.closed = False
        logger.info(f"  📂 创建Session #{self.id}")
    
    def close(self):
        """关闭Session"""
        self.closed = True
        logger.info(f"  📪 关闭Session #{self.id}")
    
    def use(self):
        """使用Session"""
        if self.closed:
            raise RuntimeError(f"Session #{self.id} is closed")
        logger.info(f"  ✅ 使用Session #{self.id}")
        return f"Session #{self.id} 工作正常"


class WrongValidator:
    """错误的验证器实现（重用Session）- 模拟V3之前的问题"""
    
    def __init__(self):
        self.session = None
        self.session_counter = 0
    
    async def validate(self, keys):
        """错误：尝试重用已关闭的Session"""
        if self.session is None:
            # 第一次创建Session
            self.session_counter += 1
            self.session = MockSession(self.session_counter)
            
            # 模拟async with语句的行为
            try:
                result = self.session.use()
                await asyncio.sleep(0.1)  # 模拟异步操作
                return f"验证了 {len(keys)} 个密钥 - {result}"
            finally:
                # async with结束时会关闭Session
                self.session.close()
                # 但我们错误地保留了引用！
        else:
            # 尝试重用已关闭的Session（会失败）
            result = self.session.use()  # 这里会抛出异常
            return f"验证了 {len(keys)} 个密钥 - {result}"


class CorrectValidator:
    """正确的验证器实现（每次创建新Session）- 修复后的版本"""
    
    def __init__(self):
        self.session_counter = 0
    
    async def validate(self, keys):
        """正确：每次创建新的Session"""
        # 每次都创建新的Session
        self.session_counter += 1
        session = MockSession(self.session_counter)
        
        # 模拟async with语句的行为
        try:
            result = session.use()
            await asyncio.sleep(0.1)  # 模拟异步操作
            return f"验证了 {len(keys)} 个密钥 - {result}"
        finally:
            # async with结束时关闭Session
            session.close()
            # Session引用会被垃圾回收，不会被重用


async def test_wrong_approach():
    """测试错误的Session管理（会失败）"""
    logger.info("\n" + "="*60)
    logger.info("🔴 测试错误的Session管理（重用已关闭的Session）")
    logger.info("="*60)
    
    validator = WrongValidator()
    test_keys = ["key1", "key2", "key3"]
    
    # 第一次调用 - 会成功
    logger.info("\n第1次调用:")
    try:
        result = await validator.validate(test_keys)
        logger.info(f"  ✅ 成功: {result}")
    except Exception as e:
        logger.error(f"  ❌ 失败: {e}")
        return False
    
    # 第二次调用 - 会失败
    logger.info("\n第2次调用:")
    try:
        result = await validator.validate(test_keys)
        logger.info(f"  ✅ 成功: {result}")
        return True  # 如果成功了，说明没有问题
    except RuntimeError as e:
        logger.error(f"  ❌ 失败: {e}")
        logger.info("\n💡 这就是V3版本之前的问题！")
        logger.info("   Session在第一次使用后被关闭，但验证器仍保留引用")
        logger.info("   第二次调用时尝试使用已关闭的Session导致错误")
        return False  # 预期的失败


async def test_correct_approach():
    """测试正确的Session管理（会成功）"""
    logger.info("\n" + "="*60)
    logger.info("🟢 测试正确的Session管理（每次创建新Session）")
    logger.info("="*60)
    
    validator = CorrectValidator()
    test_keys = ["key1", "key2", "key3"]
    
    for i in range(3):
        logger.info(f"\n第{i+1}次调用:")
        try:
            result = await validator.validate(test_keys)
            logger.info(f"  ✅ 成功: {result}")
        except Exception as e:
            logger.error(f"  ❌ 失败: {e}")
            return False
    
    logger.info("\n🎉 所有调用都成功！每次都使用新的Session")
    return True


async def test_concurrent():
    """测试并发场景"""
    logger.info("\n" + "="*60)
    logger.info("🔵 测试并发Session创建")
    logger.info("="*60)
    
    validator = CorrectValidator()
    test_keys = ["key1", "key2", "key3"]
    
    # 创建5个并发任务
    tasks = []
    for i in range(5):
        tasks.append(validator.validate(test_keys))
    
    logger.info("\n启动5个并发验证任务...")
    try:
        results = await asyncio.gather(*tasks)
        logger.info(f"\n✅ 所有并发任务成功完成")
        for i, result in enumerate(results, 1):
            logger.info(f"  任务{i}: {result}")
        return True
    except Exception as e:
