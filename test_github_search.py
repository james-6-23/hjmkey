"""
测试GitHub搜索功能是否正常工作
"""

import sys
from pathlib import Path

# 添加项目根目录到Python路径
sys.path.insert(0, str(Path(__file__).parent))

from utils.github_client_v2 import create_github_client_v2
from app.services.config_service import ConfigService

def test_github_search():
    """测试GitHub搜索功能"""
    print("🔍 测试GitHub搜索功能...")
    
    # 1. 初始化配置服务
    config = ConfigService()
    tokens = config.get("GITHUB_TOKENS_LIST", [])
    
    if not tokens:
        print("❌ 没有可用的GitHub tokens")
        return
    
    print(f"✅ 加载了 {len(tokens)} 个tokens")
    
    # 2. 创建GitHub客户端 V2
    github_client = create_github_client_v2(tokens, strategy="ADAPTIVE")
    print("✅ GitHub客户端 V2 初始化成功")
    
    # 3. 执行一个简单的搜索测试
    test_query = "AIzaSy in:file filename:.env"
    print(f"🔍 执行测试搜索: {test_query}")
    
    try:
        result = github_client.search_for_keys(test_query)
        
        if result and "items" in result:
            item_count = len(result["items"])
            total_count = result.get("total_count", 0)
            print(f"✅ 搜索成功！找到 {item_count} 个结果（总计 {total_count} 个）")
            
            # 显示前3个结果
            if item_count > 0:
                print("\n前3个搜索结果：")
                for i, item in enumerate(result["items"][:3], 1):
                    repo = item.get("repository", {}).get("full_name", "unknown")
                    path = item.get("path", "unknown")
                    print(f"  {i}. {repo} - {path}")
        else:
            print("⚠️ 搜索返回空结果")
            
    except Exception as e:
        print(f"❌ 搜索失败: {e}")

def main():
    """主函数"""
    print("🎯 GitHub搜索功能测试")
    print("=" * 50)
    
    test_github_search()
    
    print("\n" + "=" * 50)
    print("✅ 测试完成")

if __name__ == "__main__":
    main()