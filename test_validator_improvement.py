"""
测试验证器改进 - 验证成功率提升
"""

import asyncio
import time
import logging
from pathlib import Path
import sys

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent))

from app.core.validator_async import AsyncGeminiKeyValidator, OptimizedKeyValidator
from app.core.validator import ValidationStatus

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)s | %(name)s | %(message)s'
)

logger = logging.getLogger(__name__)


async def test_improved_validator():
    """测试改进后的验证器"""
    print("\n" + "="*60)
    print("测试改进后的验证器")
    print("="*60)
    
    # 测试密钥（使用实际的测试密钥格式）
    test_keys = [
        "AIzaSyBxZJpQpK0H4lI7YkVr_lZdj9Ns8VYK1co",  # 示例密钥
        "AIzaSyC9dbBQZDWpOHFDk7tz_DAacoWOBKBuQmY",  # 示例密钥
        "AIzaSyCCivpqHJ-TLG_4lIKyWMFQHZNBr7O7GuY",  # 示例密钥
        "invalid_key_12345",  # 无效密钥
        "AIzaSy" + "X" * 33,  # 格式正确但无效的密钥
    ]
    
    print("\n1. 创建改进的验证器")
    print("   - 使用更稳定的模型: gemini-1.5-flash")
    print("   - 降低并发数: 5")
    print("   - 增加延迟: 0.5-1.0秒")
    print("   - 添加重试机制: 最多3次")
    
    # 创建改进的验证器
    validator = AsyncGeminiKeyValidator(
        model_name="gemini-1.5-flash",
        max_concurrent=5,
        delay_range=(0.5, 1.0),
        max_retries=3
    )
    
    print("\n2. 开始验证测试密钥...")
    start_time = time.time()
    
    # 异步验证
    results = await validator.validate_batch_async(test_keys)
    
    elapsed = time.time() - start_time
    
    print(f"\n3. 验证完成")
    print(f"   总耗时: {elapsed:.2f}秒")
    print(f"   验证速度: {len(test_keys)/elapsed:.2f} keys/秒")
    
    # 统计结果
    status_counts = {}
    for result in results:
        status = result.status.value if hasattr(result.status, 'value') else str(result.status)
        status_counts[status] = status_counts.get(status, 0) + 1
    
    print("\n4. 验证结果统计:")
    for status, count in status_counts.items():
        percentage = (count / len(test_keys)) * 100
        print(f"   {status}: {count} ({percentage:.1f}%)")
    
    # 计算成功率
    valid_count = status_counts.get('VALID', 0) + status_counts.get('VALID_FREE', 0) + status_counts.get('VALID_PAID', 0)
    success_rate = (valid_count / len(test_keys)) * 100
    
    print(f"\n5. 验证成功率: {success_rate:.1f}%")
    
    # 详细结果
    print("\n6. 详细结果:")
    for i, result in enumerate(results):
        key_preview = test_keys[i][:10] + "..." if len(test_keys[i]) > 10 else test_keys[i]
        status = result.status.value if hasattr(result.status, 'value') else str(result.status)
        print(f"   [{i+1}] {key_preview}: {status} - {result.message}")
    
    return success_rate


async def test_retry_mechanism():
    """测试重试机制"""
    print("\n" + "="*60)
    print("测试重试机制")
    print("="*60)
    
    # 创建验证器
    validator = AsyncGeminiKeyValidator(
        max_retries=3,
        delay_range=(0.5, 1.0)
    )
    
    # 测试单个密钥的重试
    test_key = "AIzaSyBxZJpQpK0H4lI7YkVr_lZdj9Ns8VYK1co"
    
    print(f"\n测试密钥: {test_key[:10]}...")
    print("如果遇到限流，将自动重试最多3次")
    
    start_time = time.time()
    result = validator.validate(test_key)
    elapsed = time.time() - start_time
    
    status = result.status.value if hasattr(result.status, 'value') else str(result.status)
    print(f"\n结果: {status}")
    print(f"消息: {result.message}")
    print(f"耗时: {elapsed:.2f}秒")
    
    if result.error_code:
        print(f"错误代码: {result.error_code}")


async def compare_validators():
    """对比新旧验证器"""
    print("\n" + "="*60)
    print("对比新旧验证器配置")
    print("="*60)
    
    print("\n旧配置 (可能导致低成功率):")
    print("  - 模型: gemini-2.0-flash-exp (实验性)")
    print("  - 并发数: 10 (过高)")
    print("  - 延迟: 0.1-0.3秒 (过短)")
    print("  - 重试: 无")
    
    print("\n新配置 (优化后):")
    print("  - 模型: gemini-1.5-flash (稳定)")
    print("  - 并发数: 5 (适中)")
    print("  - 延迟: 0.5-1.0秒 (合理)")
    print("  - 重试: 最多3次 (指数退避)")
    
    print("\n改进点:")
    print("  1. 使用更稳定的模型避免实验性功能问题")
    print("  2. 降低并发数减少限流风险")
    print("  3. 增加请求间隔避免触发速率限制")
    print("  4. 添加智能重试机制处理临时失败")
    print("  5. 改进错误分类提高诊断准确性")
    print("  6. 添加付费密钥检测功能")


async def main():
    """主测试函数"""
    print("\n" + "="*60)
    print("验证器改进测试套件")
    print("="*60)
    
    try:
        # 1. 对比新旧配置
        await compare_validators()
        
        # 2. 测试改进的验证器
        success_rate = await test_improved_validator()
        
        # 3. 测试重试机制
        await test_retry_mechanism()
        
        # 总结
        print("\n" + "="*60)
        print("测试总结")
        print("="*60)
        
        if success_rate > 50:
            print(f"[OK] 验证成功率: {success_rate:.1f}% (显著改善)")
        elif success_rate > 20:
            print(f"[WARNING] 验证成功率: {success_rate:.1f}% (有所改善)")
        else:
            print(f"[ERROR] 验证成功率: {success_rate:.1f}% (需要进一步优化)")
        
        print("\n建议:")
        print("1. 使用有效的API密钥进行测试")
        print("2. 确保网络连接稳定")
        print("3. 避免在短时间内大量请求")
        print("4. 考虑使用代理避免IP限制")
        print("5. 监控日志了解具体失败原因")
        
    except Exception as e:
        print(f"\n[ERROR] 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0


if __name__ == "__main__":
    exit(asyncio.run(main()))