
"""
测试 TokenPool 配额显示修复
"""

import sys
from pathlib import Path

# 添加项目根目录到Python路径
sys.path.insert(0, str(Path(__file__).parent))

from utils.token_pool import TokenPool, TokenSelectionStrategy


def test_quota_display_fix():
    """测试配额显示修复"""
    print("[TEST] 测试 TokenPool 配额显示修复")
    print("=" * 50)
    
    # 创建测试令牌
    test_tokens = [
        "github_pat_11AAAAAAA" + "A" * 74,
        "github_pat_11BBBBBBBB" + "B" * 74,
        "github_pat_11CCCCCCCC" + "C" * 74,
    ]
    
    # 创建令牌池
    pool = TokenPool(test_tokens, strategy=TokenSelectionStrategy.ADAPTIVE)
    
    # 显示初始状态
    print("1. 初始状态:")
    status = pool.get_pool_status()
    print(f"   总令牌数: {status['total_tokens']}")
    print(f"   剩余配额: {status['total_remaining']}")
    print(f"   总配额: {status['total_limit']}")
    print(f"   使用率: {status['utilization']}")
    
    # 模拟一些配额更新
    print("\n2. 模拟配额更新:")
    for i, token in enumerate(test_tokens):
        # 模拟不同的配额状态
        remaining = [25, 15, 5][i]  # 不同的剩余配额
        response = {
            'status_code': 200,
            'headers': {
                'X-RateLimit-Remaining': remaining,
                'X-RateLimit-Reset': 3600
            },
            'response_time': 1.0
        }
        pool.update_token_status(token, response)
        print(f"   更新令牌 {i+1}: 剩余 {remaining}")
    
    # 显示更新后的状态
    print("\n3. 更新后状态:")
    status = pool.get_pool_status()
    print(f"   总令牌数: {status['total_tokens']}")
    print(f"   剩余配额: {status['total_remaining']}")
    print(f"   总配额: {status['total_limit']}")
    print(f"   使用率: {status['utilization']}")
    
    # 验证修复
    print("\n4. 验证修复:")
    if status['total_remaining'] <= status['total_limit']:
        print("   ✅ 剩余配额 <= 总配额 (修复成功)")
    else:
        print("   ❌ 剩余配额 > 总配额 (修复失败)")
    
    if not status['utilization'].startswith('-'):
        print("   ✅ 使用率非负数 (修复成功)")
    else:
        print("   ❌ 使用率为负数 (修复失败)")
    print("\n5. 详细信息:")
    details = pool.get_token_details()
    for detail in details:
        print(f"   令牌: {detail['token']}")
        print(f"     剩余: {detail['remaining']}")
        print(f"     状态: {detail['status']}")
        print(f"     健康度: {detail['health_score']}")
    
    print("\n[SUCCESS] 测试完成!")


if __name__ == "__main__":
    test_quota_display_fix()