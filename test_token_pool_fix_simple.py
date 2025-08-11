#!/usr/bin/env python3
"""
测试 TokenPool 配额显示修复
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.token_pool import TokenPool
from datetime import datetime, timedelta

def test_quota_display_fix():
    """测试配额显示修复"""
    print("[TEST] Testing TokenPool quota display fix")
    print("=" * 50)
    
    # 创建测试令牌
    test_tokens = [
        "test_token_1",
        "test_token_2",
        "test_token_3"
    ]
    
    # 创建测试池
    pool = TokenPool(test_tokens)
    
    # 获取初始状态
    status = pool.get_pool_status()
    print("\n1. Initial status:")
    print(f"   Total tokens: {status['total_tokens']}")
    print(f"   Remaining quota: {status['total_remaining']}")
    print(f"   Total limit: {status['total_limit']}")
    print(f"   Utilization: {status['utilization']}")
    
    # 模拟使用配额
    print("\n2. Simulating quota usage:")
    # 通过 metrics 访问令牌信息
    pool.metrics[test_tokens[0]].remaining = 25
    print(f"   Token 1: remaining 25")
    pool.metrics[test_tokens[1]].remaining = 15
    print(f"   Token 2: remaining 15")
    pool.metrics[test_tokens[2]].remaining = 5
    print(f"   Token 3: remaining 5")
    
    # 获取更新后的状态
    status = pool.get_pool_status()
    print("\n3. Updated status:")
    print(f"   Total tokens: {status['total_tokens']}")
    print(f"   Remaining quota: {status['total_remaining']}")
    print(f"   Total limit: {status['total_limit']}")
    print(f"   Utilization: {status['utilization']}")
    
    # 验证修复
    print("\n4. Verifying fix:")
    if status['total_remaining'] <= status['total_limit']:
        print("   [PASS] Remaining <= Limit (fix successful)")
    else:
        print("   [FAIL] Remaining > Limit (fix failed)")
        
    # 从 utilization 字符串中提取百分比
    utilization_pct = float(status['utilization'].rstrip('%'))
    if utilization_pct >= 0:
        print("   [PASS] Utilization >= 0 (no negative percentage)")
    else:
        print("   [FAIL] Utilization < 0 (negative percentage)")
    
    # 测试极端情况：剩余配额大于限制
    print("\n5. Testing edge case: remaining > limit")
    pool.metrics[test_tokens[0]].remaining = 100  # 大于限制的30
    pool.metrics[test_tokens[1]].remaining = 200  # 大于限制的30
    pool.metrics[test_tokens[2]].remaining = 300  # 大于限制的30
    
    status = pool.get_pool_status()
    print(f"   Set remaining to: 100, 200, 300 (limits are 30 each)")
    print(f"   Actual remaining: {status['total_remaining']}")
    print(f"   Total limit: {status['total_limit']}")
    print(f"   Utilization: {status['utilization']}")
    
    if status['total_remaining'] == status['total_limit']:
        print("   [PASS] Remaining capped at limit")
    else:
        print("   [FAIL] Remaining not properly capped")
        
    utilization_pct = float(status['utilization'].rstrip('%'))
    if utilization_pct == 0:
        print("   [PASS] Utilization is 0% when remaining >= limit")
    else:
        print("   [FAIL] Utilization calculation error")
    
    print("\n" + "=" * 50)
    print("Test completed!")

if __name__ == "__main__":
    test_quota_display_fix()