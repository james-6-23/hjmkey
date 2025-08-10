#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试密钥脱敏功能
"""

import json
import logging
from pathlib import Path
import sys
import io

# 设置标准输出编码
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# 添加项目根目录到Python路径
sys.path.insert(0, str(Path(__file__).parent))

from utils.security import KeyMasker, SecureLogger, SecureFileManager


def test_key_masking():
    """测试密钥脱敏功能"""
    print("=" * 60)
    print("🔒 测试密钥脱敏功能")
    print("=" * 60)
    
    masker = KeyMasker()
    
    # 测试不同类型的密钥
    test_keys = [
        ("AIzaSyBx3K9sdPqM1x2y3F4z5A6b7C8d9E0fGhI", "Gemini API Key"),
        ("sk-proj-1234567890abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMN", "OpenAI API Key"),
        ("ghp_1234567890abcdefghijklmnopqrstuvwxyz", "GitHub Token"),
        ("Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIn0", "Bearer Token"),
        ("short", "短密钥"),
        ("", "空密钥"),
    ]
    
    print("\n📝 单个密钥脱敏测试:")
    for key, description in test_keys:
        masked = masker.mask(key)
        print(f"  {description:20} | 原始长度: {len(key):3} | 脱敏后: {masked}")
    
    # 测试自定义显示长度
    print("\n📝 自定义显示长度:")
    test_key = "AIzaSyBx3K9sdPqM1x2y3F4z5A6b7C8d9E0fGhI"
    print(f"  原始密钥: {test_key}")
    print(f"  默认脱敏 (6,4): {masker.mask(test_key)}")
    print(f"  自定义 (10,6): {masker.mask(test_key, 10, 6)}")
    print(f"  自定义 (3,3): {masker.mask(test_key, 3, 3)}")


def test_text_masking():
    """测试文本中的密钥脱敏"""
    print("\n" + "=" * 60)
    print("📄 测试文本脱敏功能")
    print("=" * 60)
    
    masker = KeyMasker()
    
    # 包含多个密钥的文本
    text = """
    配置信息:
    Gemini API Key: AIzaSyBx3K9sdPqM1x2y3F4z5A6b7C8d9E0fGhI
    GitHub Token: ghp_1234567890abcdefghijklmnopqrstuvwxyz
    Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9
    OpenAI Key: sk-proj-1234567890abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMN
    """
    
    print("\n原始文本:")
    print(text)
    
    masked_text = masker.mask_in_text(text)
    print("\n脱敏后文本:")
    print(masked_text)


def test_dict_masking():
    """测试字典脱敏"""
    print("\n" + "=" * 60)
    print("📦 测试字典脱敏功能")
    print("=" * 60)
    
    masker = KeyMasker()
    
    # 测试数据
    config = {
        "api_key": "AIzaSyBx3K9sdPqM1x2y3F4z5A6b7C8d9E0fGhI",
        "github_token": "ghp_1234567890abcdefghijklmnopqrstuvwxyz",
        "database": {
            "password": "super_secret_password",
            "host": "localhost",
            "port": 5432
        },
        "tokens": [
            "sk-proj-1234567890abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMN",
            "AIzaSyDx4L5mdQrN2x3y4F5z6A7b8C9d0E1fGhJ"
        ],
        "public_info": "This is public information"
    }
    
    print("\n原始配置:")
    print(json.dumps(config, indent=2, ensure_ascii=False))
    
    masked_config = masker.mask_dict(config)
    print("\n脱敏后配置:")
    print(json.dumps(masked_config, indent=2, ensure_ascii=False))


def test_secure_logger():
    """测试安全日志记录器"""
    print("\n" + "=" * 60)
    print("📝 测试安全日志记录器")
    print("=" * 60)
    
    # 设置日志
    logging.basicConfig(
        level=logging.INFO,
        format='%(levelname)s - %(message)s'
    )
    
    logger = logging.getLogger("test")
    secure_logger = SecureLogger(logger)
    
    # 测试各种日志级别
    api_key = "AIzaSyBx3K9sdPqM1x2y3F4z5A6b7C8d9E0fGhI"
    
    print("\n使用安全日志记录器:")
    secure_logger.info(f"找到有效密钥: {api_key}")
    secure_logger.warning(f"密钥被限流: {api_key}")
    secure_logger.error(f"密钥验证失败: {api_key}")
    
    # 测试字典参数
    config = {
        "api_key": api_key,
        "status": "valid"
    }
    secure_logger.info("配置信息", config)


def test_key_identifier():
    """测试密钥标识符生成"""
    print("\n" + "=" * 60)
    print("🔑 测试密钥标识符")
    print("=" * 60)
    
    masker = KeyMasker()
    
    keys = [
        "AIzaSyBx3K9sdPqM1x2y3F4z5A6b7C8d9E0fGhI",
        "AIzaSyBx3K9sdPqM1x2y3F4z5A6b7C8d9E0fGhJ",  # 仅最后一位不同
        "sk-proj-1234567890abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMN"
    ]
    
    print("\n密钥标识符（用于安全存储和比较）:")
    for key in keys:
        identifier = masker.get_key_identifier(key)
        hash_value = masker.hash_key(key)
        print(f"  标识符: {identifier}")
        print(f"  完整哈希: {hash_value}")
        print()


def test_secure_file_manager():
    """测试安全文件管理器"""
    print("\n" + "=" * 60)
    print("💾 测试安全文件管理器")
    print("=" * 60)
    
    manager = SecureFileManager()
    
    # 测试密钥
    keys = [
        "AIzaSyBx3K9sdPqM1x2y3F4z5A6b7C8d9E0fGhI",
        "sk-proj-1234567890abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMN",
        "ghp_1234567890abcdefghijklmnopqrstuvwxyz"
    ]
    
    # 保存脱敏密钥列表
    test_file = Path("test_secure_keys.txt")
    manager.save_keys_secure(keys, test_file)
    print(f"\n✅ 安全密钥列表已保存到: {test_file}")
    
    # 读取并显示内容
    print("\n文件内容:")
    with open(test_file, 'r', encoding='utf-8') as f:
        content = f.read()
        print(content)
    
    # 创建安全报告
    stats = {
        "total_keys": len(keys),
        "valid_keys": keys[:2],
        "invalid_key": keys[2],
        "api_endpoint": "https://api.example.com",
        "timestamp": "2024-01-10 12:00:00"
    }
    
    report_file = Path("test_secure_report.json")
    manager.create_secure_report(stats, report_file)
    print(f"\n✅ 安全报告已保存到: {report_file}")
    
    # 清理测试文件
    test_file.unlink(missing_ok=True)
    report_file.unlink(missing_ok=True)
    print("\n🧹 测试文件已清理")


def main():
    """主函数"""
    print("🚀 开始密钥脱敏功能测试\n")
    
    # 运行所有测试
    test_key_masking()
    test_text_masking()
    test_dict_masking()
    test_secure_logger()
    test_key_identifier()
    test_secure_file_manager()
    
    print("\n" + "=" * 60)
    print("✅ 所有测试完成！")
    print("=" * 60)
    
    print("\n📊 测试总结:")
    print("  ✅ 单个密钥脱敏")
    print("  ✅ 文本中密钥自动识别和脱敏")
    print("  ✅ 字典递归脱敏")
    print("  ✅ 安全日志记录")
    print("  ✅ 密钥标识符生成")
    print("  ✅ 安全文件存储")
    
    print("\n💡 密钥脱敏功能已准备就绪，可以集成到主程序中使用！")


if __name__ == "__main__":
    main()