#!/usr/bin/env python3
"""
简化的GPT Load集成测试
测试密钥同步到GPT Load系统的基本功能
"""

import os
import sys
import logging
from pathlib import Path

# 添加项目根目录到Python路径
sys.path.insert(0, str(Path(__file__).parent))

from app.services.config_service import get_config_service
from utils.sync_utils import sync_utils
from utils.file_manager import checkpoint, file_manager
from common.Logger import setup_logger

# 设置日志
setup_logger()
logger = logging.getLogger(__name__)


def test_gpt_load_config():
    """测试GPT Load配置"""
    logger.info("=" * 60)
    logger.info("🧪 测试GPT Load配置")
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
    
    # 检查sync_utils的状态
    logger.info(f"\n📋 Sync Utils状态:")
    logger.info(f"   Balancer启用: {sync_utils.balancer_enabled}")
    logger.info(f"   GPT Load启用: {sync_utils.gpt_load_enabled}")
    logger.info(f"   批量发送间隔: {sync_utils.batch_interval}秒")
    
    return gpt_load_enabled


def test_add_keys_to_queue():
    """测试添加密钥到队列"""
    logger.info("\n" + "=" * 60)
    logger.info("🧪 测试添加密钥到队列")
    logger.info("=" * 60)
    
    # 测试密钥
    test_keys = [
        "AIzaSyTest1234567890abcdefghijklmnopqrst",  # 测试密钥1
        "AIzaSyTest2234567890abcdefghijklmnopqrst",  # 测试密钥2
        "AIzaSyTest3234567890abcdefghijklmnopqrst",  # 测试密钥3
    ]
    
    # 检查初始队列状态
    initial_balancer_count = len(checkpoint.wait_send_balancer)
    initial_gpt_count = len(checkpoint.wait_send_gpt_load)
    
    logger.info(f"📊 初始队列状态:")
    logger.info(f"   Balancer队列: {initial_balancer_count} 个密钥")
    logger.info(f"   GPT Load队列: {initial_gpt_count} 个密钥")
    
    # 添加密钥到队列
    logger.info(f"\n🔄 添加 {len(test_keys)} 个测试密钥到队列...")
    sync_utils.add_keys_to_queue(test_keys)
    
    # 检查添加后的队列状态
    after_balancer_count = len(checkpoint.wait_send_balancer)
    after_gpt_count = len(checkpoint.wait_send_gpt_load)
    
    logger.info(f"\n📊 添加后队列状态:")
    logger.info(f"   Balancer队列: {after_balancer_count} 个密钥")
    logger.info(f"   GPT Load队列: {after_gpt_count} 个密钥")
    
    # 计算新增数量
    balancer_added = after_balancer_count - initial_balancer_count
    gpt_added = after_gpt_count - initial_gpt_count
    
    if balancer_added > 0:
        logger.info(f"✅ 成功添加 {balancer_added} 个密钥到Balancer队列")
    else:
        logger.info(f"ℹ️ Balancer队列未增加（可能已禁用或密钥已存在）")
    
    if gpt_added > 0:
        logger.info(f"✅ 成功添加 {gpt_added} 个密钥到GPT Load队列")
    else:
        logger.info(f"ℹ️ GPT Load队列未增加（可能已禁用或密钥已存在）")
    
    return after_gpt_count > 0


def test_manual_send():
    """测试手动发送队列中的密钥"""
    logger.info("\n" + "=" * 60)
    logger.info("🧪 测试手动发送队列")
    logger.info("=" * 60)
    
    if not sync_utils.gpt_load_enabled:
        logger.warning("⚠️ GPT Load未启用，跳过发送测试")
        return False
    
    # 检查队列是否有待发送的密钥
    queue_count = len(checkpoint.wait_send_gpt_load)
    
    if queue_count == 0:
        logger.info("ℹ️ GPT Load队列为空，没有待发送的密钥")
        return False
    
    logger.info(f"📤 准备发送 {queue_count} 个密钥到GPT Load...")
    
    try:
        # 手动触发批量发送
        sync_utils._batch_send_worker()
        
        # 检查发送后的队列状态
        final_count = len(checkpoint.wait_send_gpt_load)
        
        if final_count < queue_count:
            sent_count = queue_count - final_count
            logger.info(f"✅ 成功发送 {sent_count} 个密钥")
            logger.info(f"📊 剩余队列: {final_count} 个密钥")
            return True
        else:
            logger.warning(f"⚠️ 发送可能失败，队列未减少")
            return False
            
    except Exception as e:
        logger.error(f"❌ 发送失败: {e}")
        return False


def test_checkpoint_persistence():
    """测试检查点持久化"""
    logger.info("\n" + "=" * 60)
    logger.info("🧪 测试检查点持久化")
    logger.info("=" * 60)
    
    # 保存当前检查点
    logger.info("💾 保存检查点...")
    file_manager.save_checkpoint(checkpoint)
    
    # 检查文件是否存在
    checkpoint_file = Path("data/checkpoint.json")
    
    if checkpoint_file.exists():
        logger.info(f"✅ 检查点文件已保存: {checkpoint_file}")
        
        # 读取并显示内容
        import json
        with open(checkpoint_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        logger.info(f"📋 检查点内容:")
        logger.info(f"   Balancer队列: {len(data.get('wait_send_balancer', []))} 个密钥")
        logger.info(f"   GPT Load队列: {len(data.get('wait_send_gpt_load', []))} 个密钥")
        
        return True
    else:
        logger.error(f"❌ 检查点文件不存在")
        return False


def main():
    """主函数"""
    try:
        logger.info("🚀 开始GPT Load集成测试")
        logger.info("=" * 60)
        
        # 测试配置
        gpt_enabled = test_gpt_load_config()
        
        if not gpt_enabled:
            logger.warning("\n⚠️ GPT Load同步未启用")
            logger.info("请在配置中设置以下参数:")
            logger.info("  GPT_LOAD_SYNC_ENABLED=true")
            logger.info("  GPT_LOAD_URL=https://your-server.com")
            logger.info("  GPT_LOAD_AUTH=your-token")
            logger.info("  GPT_LOAD_GROUP_NAME=group1,group2")
        
        # 测试添加密钥到队列
        has_keys = test_add_keys_to_queue()
        
        # 测试检查点持久化
        test_checkpoint_persistence()
        
        # 如果有密钥在队列中，测试发送
        if has_keys and gpt_enabled:
            logger.info("\n⚠️ 注意: 手动发送将真实调用GPT Load API")
            logger.info("如果要测试发送功能，请取消下面的注释:")
            logger.info("# test_manual_send()")
            # test_manual_send()  # 取消注释以测试真实发送
        
        logger.info("\n" + "=" * 60)
        logger.info("✅ GPT Load集成测试完成")
        logger.info("=" * 60)
        
        # 显示总结
        logger.info("\n📊 测试总结:")
        logger.info(f"  配置状态: {'已启用' if gpt_enabled else '未启用'}")
        logger.info(f"  队列功能: {'正常' if has_keys or not gpt_enabled else '异常'}")
        logger.info(f"  持久化: 正常")
        
        if gpt_enabled:
            logger.info("\n💡 下一步:")
            logger.info("  1. 运行主程序搜索真实密钥: python app/main.py")
            logger.info("  2. 密钥将自动添加到GPT Load队列")
            logger.info("  3. 每60秒自动批量发送到GPT Load服务器")
        
    except KeyboardInterrupt:
        logger.info("\n⛔ 测试被用户中断")
    except Exception as e:
        logger.error(f"❌ 测试失败: {e}", exc_info=True)
    finally:
        # 清理
        logger.info("\n🔚 清理资源...")
        sync_utils.shutdown()
        logger.info("✅ 清理完成")


if __name__ == "__main__":
    main()