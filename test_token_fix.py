"""
测试脚本，验证Token Hunter修复是否正常工作
"""

import os
import sys
from pathlib import Path

# 添加项目根目录到Python路径
sys.path.insert(0, str(Path(__file__).parent))

# 简单测试TokenManager功能
def test_token_manager():
    """测试TokenManager功能"""
    print("🔍 测试TokenManager功能...")
    
    # 1. 检查tokens文件是否存在
    tokens_file = "data/github_tokens.txt"
    if os.path.exists(tokens_file):
        print(f"✅ Tokens文件存在: {tokens_file}")
        
        # 2. 尝试加载tokens
        try:
            from utils.token_hunter.manager import TokenManager
            manager = TokenManager(tokens_file)
            print(f"✅ 成功加载Token管理器，包含 {len(manager.tokens)} 个tokens")
            
            if manager.tokens:
                # 3. 尝试获取一个token
                token = manager.get_next_token()
                print(f"✅ 成功获取token: {token[:10]}...")
            else:
                print("⚠️ Tokens文件为空")
        except Exception as e:
            print(f"❌ 加载Token管理器失败: {e}")
    else:
        print(f"❌ Tokens文件不存在: {tokens_file}")

def test_config_service():
    """测试配置服务"""
    print("\n🔍 测试配置服务...")
    
    try:
        from app.services.config_service import ConfigService
        config = ConfigService()
        tokens = config.get("GITHUB_TOKENS_LIST", [])
        print(f"✅ 配置服务加载了 {len(tokens)} 个tokens")
        
        if tokens:
            print(f"✅ 第一个token: {tokens[0][:10]}...")
        else:
            print("⚠️ 配置服务中没有加载到tokens")
    except Exception as e:
        print(f"❌ 配置服务测试失败: {e}")

def main():
    """主函数"""
    print("🎯 Token Hunter修复验证测试")
    print("=" * 50)
    
    test_token_manager()
    test_config_service()
    
    print("\n" + "=" * 50)
    print("✅ 测试完成")

if __name__ == "__main__":
    main()