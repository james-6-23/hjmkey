#!/usr/bin/env python3
"""
测试 Token Pool 状态更新
验证配额是否正确更新
"""

import sys
import time
import logging
from pathlib import Path

# 添加项目根目录到 Python 路径
sys.path.insert(0, str(Path(__file__).parent))

from utils.token_pool import TokenPool, TokenSelectionStrategy
from utils.github_client_v2 import create_github_client_v2
from app.services.config_service import get_config_service

# 设置日志
logging.basicConfig(
    level=logging.DEBUG,  # 使用 DEBUG 级别查看详细信息
    format='%(asctime)s | %(levelname)s | %(name)s | %(message)s'
)
logger = logging.getLogger(__name__)


def test_token_pool_update():
    """测试 Token Pool 状态更新"""
    logger.info("=" * 60)
    logger.info("🔍 测试 Token Pool 状态更新")
    logger.info("=" * 60)
    
    # 获取配置的 tokens
    config = get_config_service()
    tokens = config.get("GITHUB_TOKENS_LIST", [])
    
    if not tokens:
        logger.error("❌ 没有配置 GitHub tokens")
        return False
    
    logger.info(f"📋 找到 {len(tokens)} 个 tokens")
    
    # 创建 GitHub 客户端 V2
    client = create_github_client_v2(tokens, strategy="ADAPTIVE")
    
    # 显示初始状态
    initial_status = client.token_pool.get_pool_status()
    logger.info("\n📊 初始 Token Pool 状态:")
    logger.info(f"  Total tokens: {initial_status['total_tokens']}")
    logger.info(f"  Total limit: {initial_status['total_limit']}")
    logger.info(f"  Total remaining: {initial_status['total_remaining']}")
    logger.info(f"  Healthy: {initial_status['healthy']}")
    logger.info(f"  Limited: {initial_status['limited']}")
    logger.info(f"  Exhausted: {initial_status['exhausted']}")
    
    # 显示每个 token 的详细状态
    logger.info("\n📝 Token 详细状态:")
    for i, (token, metrics) in enumerate(client.token_pool.metrics.items(), 1):
        masked = token[:20] + "..." + token[-4:]
        logger.info(f"  Token-{i:02d}: {metrics.remaining}/{metrics.limit} (健康度: {metrics.health_score:.1f})")
    
    # 执行一个测试搜索
    logger.info("\n🔍 执行测试搜索...")
    test_query = "test in:file"
    
    # 模拟 API 调用
    token = client.token_pool.select_token()
    if token:
        logger.info(f"  选中 token: ...{token[-4:]}")
        
        # 模拟响应头（实际使用时从 GitHub API 获取）
        mock_response = {
            'status_code': 200,
            'headers': {
                'X-RateLimit-Limit': '30',
                'X-RateLimit-Remaining': '25',  # 模拟使用了 5 个配额
                'X-RateLimit-Reset': str(int(time.time()) + 3600)
            },
            'response_time': 0.5
        }
        
        # 更新 token 状态
        logger.info("  更新 token 状态...")
        client.token_pool.update_token_status(token, mock_response)
        
        # 显示更新后的状态
        updated_status = client.token_pool.get_pool_status()
        logger.info("\n📊 更新后的 Token Pool 状态:")
        logger.info(f"  Total remaining: {initial_status['total_remaining']} -> {updated_status['total_remaining']}")
        
        # 显示变化的 token
        for i, (t, metrics) in enumerate(client.token_pool.metrics.items(), 1):
            if t == token:
                logger.info(f"  Token-{i:02d} 更新: {metrics.remaining}/{metrics.limit}")
                break
        
        # 验证配额是否减少
        if updated_status['total_remaining'] < initial_status['total_remaining']:
            logger.info("✅ Token 配额正确更新！")
            return True
        else:
            logger.warning("⚠️ Token 配额没有变化")
            return False
    else:
        logger.error("❌ 无法选择 token")
        return False


def test_real_api_call():
    """测试真实的 API 调用"""
    logger.info("\n" + "=" * 60)
    logger.info("🌐 测试真实 API 调用")
    logger.info("=" * 60)
    
    config = get_config_service()
    tokens = config.get("GITHUB_TOKENS_LIST", [])
    
    if not tokens:
        logger.error("❌ 没有配置 GitHub tokens")
        return False
    
    # 创建客户端
    client = create_github_client_v2(tokens, strategy="ADAPTIVE")
    
    # 记录初始状态
    initial_status = client.token_pool.get_pool_status()
    logger.info(f"初始配额: {initial_status['total_remaining']}/{initial_status['total_limit']}")
    
    # 执行真实搜索（只搜索1页）
    logger.info("执行真实搜索...")
    result = client.search_for_keys("test in:file language:python", max_retries=1)
    
    if result:
        logger.info(f"搜索成功，找到 {len(result.get('items', []))} 个结果")
        
        # 显示更新后的状态
        final_status = client.token_pool.get_pool_status()
        logger.info(f"最终配额: {final_status['total_remaining']}/{final_status['total_limit']}")
        
        # 计算使用的配额
        used = initial_status['total_remaining'] - final_status['total_remaining']
        if used > 0:
            logger.info(f"✅ 使用了 {used} 个配额")
            return True
        else:
            logger.warning("⚠️ 配额没有变化")
            return False
    else:
        logger.error("❌ 搜索失败")
        return False


def main():
    """主测试函数"""
    logger.info("🚀 开始 Token Pool 状态测试")
    logger.info("=" * 60)
    
    # 1. 测试模拟更新
    if not test_token_pool_update():
        logger.error("模拟更新测试失败")
        return 1
    
    # 2. 测试真实 API 调用
    try:
        if not test_real_api_call():
            logger.error("真实 API 调用测试失败")
            return 1
    except Exception as e:
        logger.error(f"真实 API 调用测试异常: {e}")
        return 1
    
    logger.info("\n" + "=" * 60)
    logger.info("🎉 所有测试通过！")
    logger.info("=" * 60)
    logger.info("\n📝 总结：")
    logger.info("1. Token Pool 状态更新机制正常")
    logger.info("2. 配额追踪功能正常")
    logger.info("3. GitHub API 集成正常")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())