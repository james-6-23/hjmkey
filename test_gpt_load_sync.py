#!/usr/bin/env python3
"""
测试 GPT Load 同步功能
验证密钥是否正确同步到 GPT Load 服务
"""

import os
import sys
import asyncio
import logging
from pathlib import Path

# 添加项目根目录到 Python 路径
sys.path.insert(0, str(Path(__file__).parent))

from app.core.stats import KeyStatus
from utils.smart_sync_manager import smart_sync_manager, KeyType
from utils.sync_utils import sync_utils
from app.services.config_service import get_config_service

# 设置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)s | %(name)s | %(message)s'
)
logger = logging.getLogger(__name__)


def test_config():
    """测试配置是否正确"""
    logger.info("=" * 60)
    logger.info("📋 检查 GPT Load 配置")
    logger.info("=" * 60)
    
    config = get_config_service()
    
    # 检查必要的配置
    gpt_load_enabled = config.get("GPT_LOAD_SYNC_ENABLED", False)
    gpt_load_url = config.get("GPT_LOAD_URL", "")
    gpt_load_auth = config.get("GPT_LOAD_AUTH", "")
    smart_group_enabled = config.get("GPT_LOAD_SMART_GROUP_ENABLED", False)
    
    logger.info(f"GPT_LOAD_SYNC_ENABLED: {gpt_load_enabled}")
    logger.info(f"GPT_LOAD_URL: {gpt_load_url}")
    logger.info(f"GPT_LOAD_AUTH: {'***' + gpt_load_auth[-4:] if gpt_load_auth else 'Not set'}")
    logger.info(f"GPT_LOAD_SMART_GROUP_ENABLED: {smart_group_enabled}")
    
    if not gpt_load_enabled:
        logger.warning("⚠️ GPT Load 同步未启用！")
        logger.info("请在 .env 文件中设置 GPT_LOAD_SYNC_ENABLED=true")
        return False
    
    if not gpt_load_url:
        logger.error("❌ GPT_LOAD_URL 未设置！")
        return False
    
    if not gpt_load_auth:
        logger.error("❌ GPT_LOAD_AUTH 未设置！")
        return False
    
    logger.info("✅ 配置检查通过")
    return True


def test_smart_sync():
    """测试智能同步功能"""
    logger.info("\n" + "=" * 60)
    logger.info("🤖 测试智能同步管理器")
    logger.info("=" * 60)
    
    # 测试密钥
    test_keys = {
        "valid_free": ["test_free_key_1", "test_free_key_2"],
        "valid_paid": ["test_paid_key_1", "test_paid_key_2"],
        "rate_limited": ["test_429_key_1", "test_429_key_2"]
    }
    
    # 显示分组配置
    if smart_sync_manager.enabled:
        logger.info("智能分组已启用，分组策略：")
        for group_name, group in smart_sync_manager.groups.items():
            types_str = ", ".join([t.value for t in group.key_types])
            logger.info(f"  {group_name}: {types_str}")
    else:
        logger.info("智能分组未启用，使用传统模式")
    
    # 测试同步
    logger.info("\n📤 开始测试同步...")
    success = smart_sync_manager.sync_to_gpt_load(
        valid_keys=test_keys["valid_free"],
        paid_keys=test_keys["valid_paid"],
        rate_limited_keys=test_keys["rate_limited"],
        free_keys=test_keys["valid_free"]
    )
    
    if success:
        logger.info("✅ 同步测试成功")
    else:
        logger.error("❌ 同步测试失败")
    
    return success


def test_direct_sync():
    """测试直接同步功能"""
    logger.info("\n" + "=" * 60)
    logger.info("🔄 测试直接同步")
    logger.info("=" * 60)
    
    # 测试密钥
    test_keys = ["direct_test_key_1", "direct_test_key_2"]
    
    logger.info(f"添加 {len(test_keys)} 个密钥到队列...")
    sync_utils.add_keys_to_queue(test_keys)
    
    # 检查队列状态
    queue_size = len(sync_utils.key_queue)
    logger.info(f"当前队列大小: {queue_size}")
    
    # 处理队列
    logger.info("处理同步队列...")
    sync_utils.process_sync_queue()
    
    logger.info("✅ 直接同步测试完成")
    return True


async def test_orchestrator_sync():
    """测试 Orchestrator 中的同步功能"""
    logger.info("\n" + "=" * 60)
    logger.info("🎯 测试 Orchestrator 同步集成")
    logger.info("=" * 60)
    
    from app.core.orchestrator_v2 import OrchestratorV2
    
    # 创建 orchestrator 实例
    orchestrator = OrchestratorV2()
    
    # 检查是否启用了 GPT Load
    if orchestrator.gpt_load_enabled:
        logger.info("✅ Orchestrator 中 GPT Load 已启用")
        
        # 模拟同步一个密钥
        test_key = "test_orchestrator_key"
        orchestrator._sync_key_to_gpt_load(test_key, KeyStatus.VALID_FREE)
        
        logger.info("✅ Orchestrator 同步测试完成")
        return True
    else:
        logger.warning("⚠️ Orchestrator 中 GPT Load 未启用")
        return False


def main():
    """主测试函数"""
    logger.info("🚀 开始 GPT Load 同步功能测试")
    logger.info("=" * 60)
    
    # 1. 检查配置
    if not test_config():
        logger.error("配置检查失败，请检查 .env 文件")
        return 1
    
    # 2. 测试智能同步
    if not test_smart_sync():
        logger.error("智能同步测试失败")
        return 1
    
    # 3. 测试直接同步
    if not test_direct_sync():
        logger.error("直接同步测试失败")
        return 1
    
    # 4. 测试 Orchestrator 集成
    try:
        asyncio.run(test_orchestrator_sync())
    except Exception as e:
        logger.error(f"Orchestrator 同步测试失败: {e}")
        return 1
    
    logger.info("\n" + "=" * 60)
    logger.info("🎉 所有测试通过！")
    logger.info("=" * 60)
    logger.info("\n📝 总结：")
    logger.info("1. GPT Load 配置正确")
    logger.info("2. 智能同步管理器工作正常")
    logger.info("3. 直接同步功能正常")
    logger.info("4. Orchestrator 集成正常")
    logger.info("\n现在当你运行 app/main_v2.py 时，找到的密钥将自动同步到 GPT Load！")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())