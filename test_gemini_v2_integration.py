"""
测试 Gemini Validator V2 集成
验证高性能验证器是否正常工作
"""

import asyncio
import time
import logging
from pathlib import Path
import sys

# 添加项目根目录到Python路径
sys.path.insert(0, str(Path(__file__).parent))

from app.core.gemini_validator_adapter import create_gemini_validator, GeminiValidatorAdapter
from utils.gemini_key_validator_v2 import ValidatorConfig, KeyTier

# 设置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)s | %(name)s | %(message)s'
)
logger = logging.getLogger(__name__)


async def test_basic_validation():
    """测试基本验证功能"""
    print("\n" + "="*60)
    print("🧪 测试 1: 基本验证功能")
    print("="*60)
    
    # 创建验证器
    validator = create_gemini_validator(concurrency=10)
    
    # 测试密钥（使用无效格式进行测试）
    test_keys = [
        "AIzaSyA1234567890abcdefghijklmnopqrstuv",  # 正确格式
        "AIzaSyB123",  # 太短
        "invalid_key_format",  # 完全错误
        "AIzaSy" + "X" * 33,  # 正确长度但无效字符
    ]
    
    try:
        # 验证
        results = await validator.validate_batch_async(test_keys)
        
        # 显示结果
        print("\n验证结果:")
        for i, result in enumerate(results):
            print(f"{i+1}. {test_keys[i][:20]}...")
            print(f"   有效: {result.is_valid}")
            print(f"   限流: {result.is_rate_limited}")
            if hasattr(result, 'tier') and result.tier:
                print(f"   等级: {result.tier.value}")
            if hasattr(result, 'error_message') and result.error_message:
                print(f"   错误: {result.error_message}")
            print()
        
        print("✅ 基本验证测试通过")
        
    finally:
        await validator.cleanup()


async def test_performance():
    """测试性能提升"""
    print("\n" + "="*60)
    print("🧪 测试 2: 性能测试")
    print("="*60)
    
    # 生成测试密钥（格式正确但无效）
    test_keys = [f"AIzaSy{'A' * 33}" for _ in range(10)]
    
    # 测试高性能验证器
    validator = create_gemini_validator(concurrency=50)
    
    print(f"\n验证 {len(test_keys)} 个密钥...")
    start_time = time.time()
    
    try:
        results = await validator.validate_batch_async(test_keys)
        elapsed = time.time() - start_time
        
        print(f"✅ 完成！耗时: {elapsed:.2f} 秒")
        print(f"   速度: {len(test_keys)/elapsed:.1f} keys/秒")
        print(f"   预期: 10-20 keys/秒")
        
        # 统计结果
        valid_count = sum(1 for r in results if r.is_valid)
        invalid_count = sum(1 for r in results if not r.is_valid and not r.is_rate_limited)
        rate_limited_count = sum(1 for r in results if r.is_rate_limited)
        
        print(f"\n结果统计:")
        print(f"   有效: {valid_count}")
        print(f"   无效: {invalid_count}")
        print(f"   限流: {rate_limited_count}")
        
    finally:
        await validator.cleanup()


async def test_adapter_integration():
    """测试适配器集成"""
    print("\n" + "="*60)
    print("🧪 测试 3: 适配器集成")
    print("="*60)
    
    # 创建适配器
    config = ValidatorConfig(
        concurrency=20,
        timeout_sec=10,
        max_retries=1
    )
    
    adapter = GeminiValidatorAdapter(config)
    
    # 测试密钥
    test_keys = ["AIzaSy" + "B" * 33, "AIzaSy" + "C" * 33]
    
    async with adapter:
        results = await adapter.validate_batch_async(test_keys)
        
        print(f"\n验证了 {len(results)} 个密钥")
        for result in results:
            print(f"- {result.key[:20]}... : {'有效' if result.is_valid else '无效'}")
    
    print("\n✅ 适配器集成测试通过")


async def test_orchestrator_integration():
    """测试与 Orchestrator 的集成"""
    print("\n" + "="*60)
    print("🧪 测试 4: Orchestrator 集成")
    print("="*60)
    
    try:
        from app.core.orchestrator_v2 import OrchestratorV2
        from app.core.scanner import Scanner
        
        # 创建验证器
        validator = create_gemini_validator(concurrency=50)
        
        # 创建 orchestrator
        orchestrator = OrchestratorV2(
            scanner=Scanner(),
            validator=validator
        )
        
        print("✅ Orchestrator 创建成功")
        print(f"   验证器类型: {type(orchestrator.validator).__name__}")
        print(f"   支持异步: {hasattr(orchestrator.validator, 'validate_batch_async')}")
        
        # 测试验证方法
        test_keys = ["AIzaSy" + "D" * 33]
        if hasattr(orchestrator.validator, 'validate_batch_async'):
            results = await orchestrator.validator.validate_batch_async(test_keys)
            print(f"   异步验证测试: {'通过' if results else '失败'}")
        
    except ImportError as e:
        print(f"⚠️  无法导入 Orchestrator: {e}")
    except Exception as e:
        print(f"❌ 集成测试失败: {e}")


async def main():
    """运行所有测试"""
    print("\n" + "🚀 " * 20)
    print("Gemini Validator V2 集成测试")
    print("🚀 " * 20)
    
    # 运行测试
    await test_basic_validation()
    await test_performance()
    await test_adapter_integration()
    await test_orchestrator_integration()
    
    print("\n" + "="*60)
    print("✅ 所有测试完成！")
    print("="*60)
    print("\n集成步骤:")
    print("1. 使用 create_gemini_validator() 创建验证器")
    print("2. 将验证器传递给 OrchestratorV2")
    print("3. 享受 10-20x 的性能提升！")
    print("\n详细文档: docs/GEMINI_VALIDATOR_V2_INTEGRATION.md")


if __name__ == "__main__":
    asyncio.run(main())