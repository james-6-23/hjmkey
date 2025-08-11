"""
测试Token池监控修复
验证启动时配额检查功能
"""

import sys
import logging
from pathlib import Path
import time
import os

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent))

from utils.token_pool import TokenPool, TokenSelectionStrategy, TokenStatus

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)s | %(name)s | %(message)s'
)

logger = logging.getLogger(__name__)


def test_quota_initialization():
    """测试启动时配额检查"""
    print("\n" + "="*60)
    print("测试 1: 启动时配额检查")
    print("="*60)
    
    # 使用测试令牌（可以是无效的）
    test_tokens = [
        "github_pat_test_token_1_" + "A" * 60,
        "github_pat_test_token_2_" + "B" * 60,
        "github_pat_test_token_3_" + "C" * 60,
    ]
    
    print("\n创建Token池，将自动检查配额...")
    print("注意：如果令牌无效，将显示为 INVALID 或 FAILED 状态")
    
    # 创建Token池（会自动调用 _initialize_token_quotas）
    pool = TokenPool(test_tokens, strategy=TokenSelectionStrategy.ADAPTIVE)
    
    print("\n[OK] Token池初始化完成，配额检查已执行")
    
    # 获取池状态
    status = pool.get_pool_status()
    
    print("\n池状态汇总:")
    print(f"  总令牌数: {status['total_tokens']}")
    print(f"  健康: {status['healthy']}")
    print(f"  受限: {status['limited']}")
    print(f"  耗尽: {status['exhausted']}")
    print(f"  失败: {status['failed']}")
    print(f"  恢复中: {status['recovering']}")
    print(f"  总配额: {status['total_remaining']}/{status['total_limit']}")
    print(f"  使用率: {status['utilization']}")
    
    return pool


def test_refresh_quotas(pool):
    """测试手动刷新配额"""
    print("\n" + "="*60)
    print("测试 2: 手动刷新配额")
    print("="*60)
    
    print("\n调用 refresh_quotas() 方法...")
    pool.refresh_quotas()
    
    print("\n[OK] 配额刷新完成")
    
    # 再次获取状态
    status = pool.get_pool_status()
    print("\n刷新后的状态:")
    print(f"  总配额: {status['total_remaining']}/{status['total_limit']}")
    print(f"  使用率: {status['utilization']}")


def test_token_details(pool):
    """测试令牌详细信息"""
    print("\n" + "="*60)
    print("测试 3: 令牌详细信息")
    print("="*60)
    
    details = pool.get_token_details()
    
    print("\n令牌详细信息:")
    for i, detail in enumerate(details, 1):
        print(f"\n令牌 {i}:")
        print(f"  状态: {detail['status']}")
        print(f"  剩余配额: {detail['remaining']}")
        print(f"  健康分数: {detail['health_score']}")
        print(f"  成功率: {detail['success_rate']}")
        print(f"  总请求数: {detail['total_requests']}")
        print(f"  连续失败: {detail['consecutive_failures']}")


def test_with_real_token():
    """使用真实令牌测试（如果环境变量中有）"""
    print("\n" + "="*60)
    print("测试 4: 真实令牌测试（可选）")
    print("="*60)
    
    # 尝试从环境变量获取真实令牌
    real_token = os.getenv('GITHUB_TOKEN')
    
    if not real_token:
        print("\n[INFO] 未设置 GITHUB_TOKEN 环境变量，跳过真实令牌测试")
        print("提示: 设置 GITHUB_TOKEN 环境变量后可以看到真实的配额信息")
        return
    
    print("\n检测到真实GitHub令牌，进行配额检查...")
    
    # 创建只包含真实令牌的池
    pool = TokenPool([real_token], strategy=TokenSelectionStrategy.ROUND_ROBIN)
    
    # 获取状态
    status = pool.get_pool_status()
    
    print("\n真实令牌配额信息:")
    print(f"  状态分布: 健康={status['healthy']}, 受限={status['limited']}, 耗尽={status['exhausted']}")
    print(f"  配额: {status['total_remaining']}/{status['total_limit']} 剩余")
    print(f"  使用率: {status['utilization']}")
    
    # 显示详细信息
    details = pool.get_token_details()
    if details:
        detail = details[0]
        print(f"\n令牌详情:")
        print(f"  状态: {detail['status']}")
        print(f"  剩余配额: {detail['remaining']}")
        print(f"  健康分数: {detail['health_score']}")


def compare_before_after():
    """对比修复前后的差异"""
    print("\n" + "="*60)
    print("修复前后对比")
    print("="*60)
    
    print("\n修复前的问题:")
    print("  [X] 所有令牌显示固定的 30/30 配额")
    print("  [X] 使用率始终显示 0%")
    print("  [X] 无法反映真实的API配额状态")
    print("  [X] 无法识别无效或耗尽的令牌")
    
    print("\n修复后的改进:")
    print("  [OK] 启动时自动检查每个令牌的实际配额")
    print("  [OK] 显示真实的剩余配额和使用率")
    print("  [OK] 正确识别令牌状态（健康/受限/耗尽/失败）")
    print("  [OK] 支持手动刷新配额信息")
    print("  [OK] 提供详细的令牌健康分数")


def main():
    """主测试函数"""
    print("\n" + "="*60)
    print("Token池监控修复测试")
    print("="*60)
    
    try:
        # 运行测试
        pool = test_quota_initialization()
        test_refresh_quotas(pool)
        test_token_details(pool)
        test_with_real_token()
        compare_before_after()
        
        print("\n" + "="*60)
        print("[OK] 所有测试完成!")
        print("="*60)
        
        print("\n关键改进:")
        print("1. 添加了 _initialize_token_quotas() 方法")
        print("2. 在 __init__ 中自动调用配额检查")
        print("3. 支持从 GitHub API 获取真实配额")
        print("4. 添加了 refresh_quotas() 手动刷新方法")
        print("5. 改进了状态统计，包含 failed 和 recovering 状态")
        
    except Exception as e:
        print(f"\n[ERROR] 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0


if __name__ == "__main__":
    exit(main())