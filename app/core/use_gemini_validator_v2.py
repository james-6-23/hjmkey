"""
使用 Gemini Validator V2 的简单集成方案
直接修改 orchestrator_v2.py 的导入即可使用
"""

import logging
from pathlib import Path
import sys

# 添加项目根目录到Python路径
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from app.core.gemini_validator_adapter import create_gemini_validator

logger = logging.getLogger(__name__)


def patch_orchestrator_v2():
    """
    修补 orchestrator_v2.py 以使用新的高性能验证器
    这个函数展示了如何修改 orchestrator_v2.py
    """
    
    # 在 orchestrator_v2.py 的 __init__ 方法中，替换验证器初始化部分：
    # 
    # 原代码（第93-100行）：
    # ```python
    # if validator:
    #     self.validator = validator
    # else:
    #     # 创建异步验证器，支持并发验证
    #     async_validator = AsyncGeminiKeyValidator(
    #         max_concurrent=20,  # 增加并发数
    #         delay_range=(0.05, 0.1)  # 更短的延迟
    #     )
    #     self.validator = OptimizedKeyValidator(async_validator)
    # ```
    # 
    # 替换为：
    # ```python
    # if validator:
    #     self.validator = validator
    # else:
    #     # 使用高性能的 Gemini Validator V2
    #     from app.core.gemini_validator_adapter import create_gemini_validator
    #     self.validator = create_gemini_validator(concurrency=50)
    # ```
    
    print("""
    ✅ 集成步骤：
    
    1. 打开 app/core/orchestrator_v2.py
    
    2. 在文件顶部添加导入：
       from app.core.gemini_validator_adapter import create_gemini_validator
    
    3. 找到第93-100行的验证器初始化代码
    
    4. 替换为：
       if validator:
           self.validator = validator
       else:
           # 使用高性能的 Gemini Validator V2
           self.validator = create_gemini_validator(concurrency=50)
    
    5. 在 _check_if_paid_key 方法中（第361行），可以利用验证器的付费检测：
       def _check_if_paid_key(self, key: str) -> bool:
           if hasattr(self.validator, 'check_if_paid_key'):
               return self.validator.check_if_paid_key(key)
           # ... 原有的检测逻辑作为后备
    
    6. 在 _cleanup_resources 方法中（第424行），添加验证器清理：
       # 清理验证器资源
       if hasattr(self.validator, 'cleanup'):
           asyncio.create_task(self.validator.cleanup())
    
    完成！现在 orchestrator 将使用高性能的并发验证器。
    """)


def create_optimized_orchestrator():
    """
    创建使用优化验证器的 Orchestrator 实例
    """
    from app.core.scanner import Scanner
    from app.core.orchestrator_v2 import OrchestratorV2
    from app.core.gemini_validator_adapter import create_gemini_validator
    
    # 创建高性能验证器
    validator = create_gemini_validator(concurrency=100)  # 100并发
    
    # 创建 orchestrator
    orchestrator = OrchestratorV2(
        scanner=Scanner(),
        validator=validator
    )
    
    logger.info("✅ Created optimized orchestrator with Gemini Validator V2")
    logger.info(f"   Concurrency: 100 keys")
    logger.info(f"   Expected performance: 10-20 keys/second")
    
    return orchestrator


async def benchmark_validators():
    """
    对比新旧验证器的性能
    """
    import time
    from app.core.validator import KeyValidator
    from app.core.gemini_validator_adapter import create_gemini_validator
    
    # 测试密钥
    test_keys = [
        f"AIzaSy{'A' * 33}",  # 模拟密钥格式
        f"AIzaSy{'B' * 33}",
        f"AIzaSy{'C' * 33}",
        f"AIzaSy{'D' * 33}",
        f"AIzaSy{'E' * 33}",
    ] * 2  # 10个密钥
    
    print("\n" + "="*60)
    print("🏁 验证器性能对比测试")
    print("="*60)
    
    # 测试原始验证器
    print("\n1️⃣ 原始验证器（串行）:")
    old_validator = KeyValidator()
    start_time = time.time()
    old_results = old_validator.validate_batch(test_keys[:5])  # 只测5个避免太慢
    old_time = time.time() - start_time
    print(f"   验证 5 个密钥耗时: {old_time:.2f} 秒")
    print(f"   速度: {5/old_time:.1f} keys/秒")
    
    # 测试新验证器
    print("\n2️⃣ Gemini Validator V2（并发）:")
    new_validator = create_gemini_validator(concurrency=50)
    start_time = time.time()
    new_results = await new_validator.validate_batch_async(test_keys)
    new_time = time.time() - start_time
    await new_validator.cleanup()
    print(f"   验证 10 个密钥耗时: {new_time:.2f} 秒")
    print(f"   速度: {10/new_time:.1f} keys/秒")
    
    # 性能提升
    speedup = (5/old_time) / (10/new_time) * 2  # 归一化比较
    print(f"\n🚀 性能提升: {speedup:.1f}x")
    print("="*60)


# 示例：如何在主程序中使用
async def example_main():
    """
    示例主程序
    """
    # 设置日志
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s | %(levelname)s | %(name)s | %(message)s'
    )
    
    # 创建优化的 orchestrator
    orchestrator = create_optimized_orchestrator()
    
    # 测试查询
    queries = [
        "AIzaSy in:file extension:env",
        "AIzaSy in:file filename:config",
    ]
    
    # 运行
    print("\n🚀 开始运行优化的 Orchestrator...")
    stats = await orchestrator.run(queries, max_loops=1)
    
    print(f"\n✅ 运行完成!")
    print(f"   有效密钥: {stats.by_status.get('VALID_FREE', 0) + stats.by_status.get('VALID_PAID', 0)}")
    print(f"   验证速度: 预计 10-20 keys/秒")


if __name__ == "__main__":
    import asyncio
    
    # 显示集成步骤
    patch_orchestrator_v2()
    
    # 运行性能测试
    print("\n按 Enter 运行性能测试...")
    input()
    
    asyncio.run(benchmark_validators())
    
    # 运行示例
    print("\n按 Enter 运行示例程序...")
    input()
    
    asyncio.run(example_main())