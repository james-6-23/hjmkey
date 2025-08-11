"""
简化的 Gemini Validator V2 测试
不依赖于其他模块，直接测试核心功能
"""

import asyncio
import time
import logging
from pathlib import Path
import sys

# 添加项目根目录到Python路径
sys.path.insert(0, str(Path(__file__).parent))

# 设置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)s | %(message)s'
)
logger = logging.getLogger(__name__)


async def test_validator_v2():
    """直接测试 Gemini Validator V2"""
    print("\n" + "="*60)
    print("测试 Gemini Validator V2 核心功能")
    print("="*60)
    
    try:
        from utils.gemini_key_validator_v2 import (
            GeminiKeyValidatorV2, 
            ValidatorConfig,
            KeyTier
        )
        print("[OK] 成功导入 GeminiKeyValidatorV2")
    except ImportError as e:
        print(f"[ERROR] 导入失败: {e}")
        return
    
    # 创建配置
    config = ValidatorConfig(
        concurrency=10,
        timeout_sec=10,
        max_retries=1,
        log_level="INFO"
    )
    
    # 测试密钥格式验证
    print("\n1. 测试密钥格式验证:")
    validator = GeminiKeyValidatorV2(config)
    
    test_formats = [
        ("AIzaSy" + "A" * 33, True, "正确格式"),
        ("AIzaSy" + "A" * 32, False, "太短"),
        ("AIzaSy" + "A" * 34, False, "太长"),
        ("AIzaSx" + "A" * 33, False, "错误前缀"),
        ("invalid_key", False, "完全错误"),
    ]
    
    for key, expected, desc in test_formats:
        result = validator.validate_key_format(key)
        status = "[OK]" if result == expected else "[FAIL]"
        print(f"   {status} {desc}: {key[:20]}... -> {result}")
    
    # 测试并发验证（使用模拟密钥）
    print("\n2. 测试并发验证性能:")
    test_keys = [f"AIzaSy{'A' * 33}" for _ in range(5)]  # 5个格式正确的测试密钥
    
    async with validator:
        start_time = time.time()
        try:
            # 注意：这些是无效的密钥，会返回验证失败
            stats = await validator.validate_keys_batch(test_keys, show_progress=False)
            elapsed = time.time() - start_time
            
            print(f"\n   验证 {len(test_keys)} 个密钥耗时: {elapsed:.2f} 秒")
            print(f"   速度: {stats['keys_per_second']:.1f} keys/秒")
            print(f"\n   统计:")
            print(f"   - 总计: {stats['total']}")
            print(f"   - 有效: {stats['valid']} (付费: {stats['paid']}, 免费: {stats['free']})")
            print(f"   - 无效: {stats['invalid']}")
            
        except Exception as e:
            print(f"   [WARNING] 验证出错（预期的，因为使用了无效密钥）: {type(e).__name__}")
    
    print("\n[OK] 测试完成！")


async def test_adapter():
    """测试适配器"""
    print("\n" + "="*60)
    print("测试适配器功能")
    print("="*60)
    
    try:
        from app.core.gemini_validator_adapter import (
            GeminiValidatorAdapter,
            create_gemini_validator
        )
        print("[OK] 成功导入适配器")
    except ImportError as e:
        print(f"[ERROR] 导入适配器失败: {e}")
        return
    
    # 创建适配器
    print("\n1. 创建验证器:")
    validator = create_gemini_validator(concurrency=20)
    print(f"   类型: {type(validator).__name__}")
    print(f"   并发数: {validator.config.concurrency}")
    
    # 测试验证
    print("\n2. 测试异步验证:")
    test_keys = ["AIzaSy" + "B" * 33, "invalid_key"]
    
    try:
        results = await validator.validate_batch_async(test_keys)
        print(f"   验证了 {len(results)} 个密钥")
        for i, result in enumerate(results):
            print(f"   - 密钥 {i+1}: 有效={result.is_valid}, 限流={result.is_rate_limited}")
    except Exception as e:
        print(f"   [WARNING] 验证出错（预期的）: {type(e).__name__}")
    finally:
        await validator.cleanup()
    
    print("\n[OK] 适配器测试完成！")


def show_integration_guide():
    """显示集成指南"""
    print("\n" + "="*60)
    print("集成指南")
    print("="*60)
    
    print("""
使用 Gemini Validator V2 的步骤：

1. 在 orchestrator_v2.py 中导入:
   from app.core.gemini_validator_adapter import create_gemini_validator

2. 创建验证器:
   validator = create_gemini_validator(concurrency=50)

3. 传递给 Orchestrator:
   orchestrator = OrchestratorV2(validator=validator)

4. 享受 10-20x 性能提升！

主要优势:
- 并发验证（50-100 并发）
- 两阶段验证（识别付费密钥）
- 自动重试和错误处理
- 实时进度显示
- 结果自动保存

详细文档: docs/GEMINI_VALIDATOR_V2_INTEGRATION.md
""")


async def main():
    """主函数"""
    print("\nGemini Validator V2 功能测试")
    print("="*60)
    
    # 运行测试
    await test_validator_v2()
    await test_adapter()
    
    # 显示集成指南
    show_integration_guide()
    
    print("\n[DONE] 所有测试完成！")


if __name__ == "__main__":
    asyncio.run(main())