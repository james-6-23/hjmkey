"""
Gemini 密钥验证工具
用于验证 Gemini API 密钥的有效性和类型（免费/付费）
"""

import asyncio
import sys
from pathlib import Path
from utils.gemini_key_validator_v2 import (
    GeminiKeyValidatorV2,
    ValidatorConfig,
    validate_keys_from_file,
    setup_logging
)


async def validate_single_key(api_key: str):
    """验证单个密钥"""
    print(f"\n验证密钥: {api_key[:10]}...")
    
    config = ValidatorConfig(
        concurrency=1,
        timeout_sec=30,
        max_retries=2
    )
    
    validator = GeminiKeyValidatorV2(config)
    
    try:
        async with validator.create_session() as session:
            result = await validator.validate_key(session, api_key)
            
            print(f"\n验证结果:")
            print(f"  密钥: {result.key[:10]}...")
            print(f"  状态: {result.tier.value}")
            if result.error_message:
                print(f"  错误: {result.error_message}")
            
            if result.tier.value == "paid":
                print("  ✅ 这是一个付费版密钥！")
            elif result.tier.value == "free":
                print("  ✅ 这是一个免费版密钥")
            else:
                print("  ❌ 密钥无效")
                
    finally:
        await validator.connector.close()


async def validate_file(file_path: str):
    """验证文件中的密钥"""
    print(f"\n验证文件: {file_path}")
    
    config = ValidatorConfig(
        concurrency=50,  # 并发验证
        timeout_sec=20,
        max_retries=2,
        output_dir="validation_results"  # 结果保存目录
    )
    
    stats = await validate_keys_from_file(
        file_path,
        config=config,
        save_results=True
    )
    
    if stats:
        print("\n" + "="*60)
        print("验证结果统计:")
        print(f"  总计验证: {stats['total']} 个")
        print(f"  有效密钥: {stats['valid']} 个")
        print(f"    💎 付费版: {stats['paid']} 个")
        print(f"    🆓 免费版: {stats['free']} 个")
        print(f"  ❌ 无效密钥: {stats['invalid']} 个")
        print(f"  ⏱️  验证耗时: {stats['elapsed_time']:.2f} 秒")
        print(f"  🚀 验证速度: {stats['keys_per_second']:.2f} 个/秒")
        print("="*60)
        print(f"\n结果已保存到 validation_results 目录")


def main():
    """主函数"""
    # 设置日志
    setup_logging("INFO")
    
    print("🔍 Gemini 密钥验证工具 V2")
    print("="*60)
    
    if len(sys.argv) < 2:
        print("\n使用方法:")
        print("  验证单个密钥: python validate_gemini_keys.py <API密钥>")
        print("  验证文件: python validate_gemini_keys.py <密钥文件路径>")
        print("\n示例:")
        print("  python validate_gemini_keys.py AIzaSyABCDEFGHIJKLMNOPQRSTUVWXYZ1234567")
        print("  python validate_gemini_keys.py keys.txt")
        return
    
    arg = sys.argv[1]
    
    # 判断是文件还是密钥
    if Path(arg).exists():
        # 是文件
        asyncio.run(validate_file(arg))
    elif arg.startswith("AIzaSy") and len(arg) == 39:
        # 是密钥
        asyncio.run(validate_single_key(arg))
    else:
        print(f"\n❌ 错误: '{arg}' 既不是有效的文件路径，也不是有效的 API 密钥格式")
        print("   Gemini API 密钥应该以 'AIzaSy' 开头，总长度为 39 个字符")


if __name__ == "__main__":
    main()