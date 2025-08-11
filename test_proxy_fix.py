"""
测试代理配置修复
"""

import os
import sys
import logging
from pathlib import Path

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent))

from utils.github_client_v2 import GitHubClientV2, create_github_client_v2
from utils.token_pool import TokenPool, TokenSelectionStrategy

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)s | %(name)s | %(message)s'
)

logger = logging.getLogger(__name__)


def test_proxy_detection():
    """测试代理检测功能"""
    print("\n" + "="*60)
    print("测试 1: 代理配置检测")
    print("="*60)
    
    # 显示当前环境变量
    http_proxy = os.getenv('HTTP_PROXY') or os.getenv('http_proxy')
    https_proxy = os.getenv('HTTPS_PROXY') or os.getenv('https_proxy')
    no_proxy = os.getenv('NO_PROXY') or os.getenv('no_proxy')
    
    print(f"HTTP_PROXY: {http_proxy or '未设置'}")
    print(f"HTTPS_PROXY: {https_proxy or '未设置'}")
    print(f"NO_PROXY: {no_proxy or '未设置'}")
    
    # 创建测试令牌池
    test_tokens = ["test_token_1", "test_token_2"]
    token_pool = TokenPool(test_tokens, strategy=TokenSelectionStrategy.ROUND_ROBIN)
    
    # 测试自动检测
    print("\n测试自动代理检测...")
    client = GitHubClientV2(token_pool)
    
    if client.proxy_config:
        print("[OK] 检测到代理配置:")
        for key, value in client.proxy_config.items():
            print(f"  {key}: {value}")
    else:
        print("[INFO] 未检测到代理配置")
    
    client.close()
    
    # 测试手动配置
    print("\n测试手动代理配置...")
    manual_proxy = {
        'http': 'http://manual-proxy:8080',
        'https': 'https://manual-proxy:8080'
    }
    
    client2 = GitHubClientV2(token_pool, proxy_config=manual_proxy)
    
    if client2.proxy_config:
        print("[OK] 手动配置的代理:")
        for key, value in client2.proxy_config.items():
            print(f"  {key}: {value}")
    
    client2.close()
    
    print("\n[OK] 代理检测测试完成")


def test_proxy_in_requests():
    """测试代理是否在请求中生效"""
    print("\n" + "="*60)
    print("测试 2: 代理在请求中的应用")
    print("="*60)
    
    # 设置测试代理
    test_proxy = os.getenv('HTTP_PROXY')
    
    if not test_proxy:
        print("[WARNING] 未设置 HTTP_PROXY，跳过实际请求测试")
        print("提示: 可以设置 HTTP_PROXY 环境变量后重新运行")
        return
    
    print(f"使用代理: {test_proxy}")
    
    # 创建客户端
    test_tokens = ["invalid_token_for_test"]
    client = create_github_client_v2(test_tokens, strategy="ROUND_ROBIN")
    
    # 检查 session 代理配置
    print("\nSession 代理配置:")
    if client.session.proxies:
        for key, value in client.session.proxies.items():
            print(f"  {key}: {value}")
    else:
        print("  未配置")
    
    print("\n[OK] 代理应用测试完成")
    
    client.close()


def test_factory_function():
    """测试工厂函数的代理支持"""
    print("\n" + "="*60)
    print("测试 3: 工厂函数代理支持")
    print("="*60)
    
    test_tokens = ["test_token"]
    
    # 测试不带代理
    print("创建不带代理的客户端...")
    client1 = create_github_client_v2(test_tokens)
    print(f"代理配置: {client1.proxy_config or '无'}")
    client1.close()
    
    # 测试带代理
    print("\n创建带代理的客户端...")
    proxy_config = {
        'http': 'http://test-proxy:3128',
        'https': 'http://test-proxy:3128'
    }
    client2 = create_github_client_v2(test_tokens, proxy_config=proxy_config)
    print(f"代理配置: {client2.proxy_config}")
    client2.close()
    
    print("\n[OK] 工厂函数测试完成")


def main():
    """主测试函数"""
    print("\n" + "="*60)
    print("GitHub 客户端代理配置测试")
    print("="*60)
    
    try:
        # 运行测试
        test_proxy_detection()
        test_proxy_in_requests()
        test_factory_function()
        
        print("\n" + "="*60)
        print("[OK] 所有代理测试完成!")
        print("="*60)
        
        # 提供设置代理的示例
        print("\n[TIP] 如何设置代理:")
        print("Windows PowerShell:")
        print('  $env:HTTP_PROXY="http://your-proxy:port"')
        print('  $env:HTTPS_PROXY="http://your-proxy:port"')
        print("\nWindows CMD:")
        print('  set HTTP_PROXY=http://your-proxy:port')
        print('  set HTTPS_PROXY=http://your-proxy:port')
        print("\nLinux/Mac:")
        print('  export HTTP_PROXY="http://your-proxy:port"')
        print('  export HTTPS_PROXY="http://your-proxy:port"')
        
    except Exception as e:
        print(f"\n[ERROR] 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0


if __name__ == "__main__":
    exit(main())