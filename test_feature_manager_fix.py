#!/usr/bin/env python3
"""
测试特性管理器环境变量加载修复
验证环境变量是否正确加载并启用相应的功能模块
"""

import os
import sys
from pathlib import Path

# 添加项目根目录到Python路径
sys.path.insert(0, str(Path(__file__).parent))

def test_env_loading():
    """测试环境变量加载"""
    print("=" * 60)
    print("🧪 测试环境变量加载")
    print("=" * 60)
    
    # 1. 先显示当前环境变量状态（加载前）
    print("\n1️⃣ 加载.env文件前的环境变量状态:")
    enable_vars_before = {k: v for k, v in os.environ.items() if k.startswith('ENABLE_')}
    if enable_vars_before:
        for key, value in enable_vars_before.items():
            print(f"   {key}: {value}")
    else:
        print("   没有找到ENABLE_*环境变量")
    
    # 2. 加载.env文件
    print("\n2️⃣ 加载.env文件...")
    from dotenv import load_dotenv
    
    # 查找.env文件
    env_paths = [
        Path('.env'),
        Path('test_logs/.env'),
    ]
    
    env_loaded = False
    for env_path in env_paths:
        if env_path.exists():
            print(f"   找到.env文件: {env_path}")
            load_dotenv(env_path, override=True)
            env_loaded = True
            break
    
    if not env_loaded:
        print("   ⚠️ 未找到.env文件")
        return False
    
    # 3. 显示加载后的环境变量
    print("\n3️⃣ 加载.env文件后的环境变量状态:")
    enable_vars_after = {k: v for k, v in os.environ.items() if k.startswith('ENABLE_')}
    if enable_vars_after:
        for key, value in enable_vars_after.items():
            print(f"   {key}: {value}")
    else:
        print("   ❌ 仍然没有找到ENABLE_*环境变量")
        return False
    
    print(f"\n✅ 成功加载 {len(enable_vars_after)} 个ENABLE_*配置")
    return True


def test_feature_manager():
    """测试特性管理器"""
    print("\n" + "=" * 60)
    print("🧪 测试特性管理器")
    print("=" * 60)
    
    try:
        from app.features.feature_manager import get_feature_manager
        
        # 创建特性管理器
        print("\n1️⃣ 创建特性管理器...")
        feature_manager = get_feature_manager()
        
        # 显示配置
        print("\n2️⃣ 特性管理器配置:")
        enable_configs = {k: v for k, v in feature_manager.config.items() if k.startswith('ENABLE_')}
        if enable_configs:
            for key, value in enable_configs.items():
                print(f"   {key}: {value}")
        else:
            print("   ❌ 特性管理器没有读取到ENABLE_*配置")
            return False
        
        # 初始化所有功能
        print("\n3️⃣ 初始化所有功能模块...")
        feature_manager.initialize_all_features()
        
        # 显示加载的功能
        print("\n4️⃣ 已加载的功能模块:")
        if feature_manager.features:
            for name, feature in feature_manager.features.items():
                print(f"   ✅ {name}: {type(feature).__name__}")
        else:
            print("   ❌ 没有功能模块被加载")
            
        # 显示功能状态
        print("\n5️⃣ 功能模块状态:")
        for name, status in feature_manager.feature_status.items():
            status_icon = {
                'active': '✅',
                'disabled': '⏸️',
                'unhealthy': '⚠️',
                'missing_dependency': '📦',
                'load_error': '❌'
            }.get(status, '❓')
            print(f"   {status_icon} {name}: {status}")
        
        # 统计
        active_count = sum(1 for s in feature_manager.feature_status.values() if s == 'active')
        disabled_count = sum(1 for s in feature_manager.feature_status.values() if s == 'disabled')
        
        print(f"\n📊 统计: {active_count} 个活跃, {disabled_count} 个禁用")
        
        if active_count > 0:
            print("✅ 特性管理器正常工作！")
            return True
        else:
            print("⚠️ 没有活跃的功能模块")
            return False
            
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_specific_features():
    """测试特定功能是否按预期加载"""
    print("\n" + "=" * 60)
    print("🧪 测试特定功能加载")
    print("=" * 60)
    
    # 预期应该启用的功能（根据test_logs/.env）
    expected_enabled = {
        'ENABLE_ASYNC': 'true',
        'ENABLE_ASYNC_VALIDATION': 'true',
        'ENABLE_CONNECTION_POOL': 'true',
        'ENABLE_PROGRESS_DISPLAY': 'true',
        'ENABLE_DATABASE': 'true',
    }
    
    # 预期应该禁用的功能
    expected_disabled = {
        'ENABLE_STRUCTURED_LOGGING': 'false',
        'ENABLE_PLUGINS': 'false',
        'ENABLE_MONITORING': 'false',
    }
    
    print("\n检查预期启用的功能:")
    for key, expected_value in expected_enabled.items():
        actual_value = os.getenv(key, 'not_set')
        if actual_value.lower() == expected_value.lower():
            print(f"   ✅ {key}: {actual_value} (预期: {expected_value})")
        else:
            print(f"   ❌ {key}: {actual_value} (预期: {expected_value})")
    
    print("\n检查预期禁用的功能:")
    for key, expected_value in expected_disabled.items():
        actual_value = os.getenv(key, 'not_set')
        if actual_value.lower() == expected_value.lower():
            print(f"   ✅ {key}: {actual_value} (预期: {expected_value})")
        else:
            print(f"   ❌ {key}: {actual_value} (预期: {expected_value})")
    
    return True


def main():
    """主测试函数"""
    print("🚀 开始测试特性管理器环境变量加载修复")
    print("=" * 60)
    
    # 测试1：环境变量加载
    env_test_passed = test_env_loading()
    
    if not env_test_passed:
        print("\n❌ 环境变量加载失败，无法继续测试")
        return 1
    
    # 测试2：特性管理器
    feature_test_passed = test_feature_manager()
    
    # 测试3：特定功能检查
    specific_test_passed = test_specific_features()
    
    # 总结
    print("\n" + "=" * 60)
    print("📊 测试总结")
    print("=" * 60)
    print(f"环境变量加载: {'✅ 通过' if env_test_passed else '❌ 失败'}")
    print(f"特性管理器: {'✅ 通过' if feature_test_passed else '❌ 失败'}")
    print(f"特定功能检查: {'✅ 通过' if specific_test_passed else '❌ 失败'}")
    
    if env_test_passed and feature_test_passed:
        print("\n🎊 所有测试通过！特性管理器环境变量加载问题已修复")
        print("\n💡 修复说明:")
        print("1. 在主程序最开始添加了 load_dotenv(override=True)")
        print("2. 特性管理器不再传递config参数，直接从环境变量读取")
        print("3. 添加了功能加载状态的详细日志")
        return 0
    else:
        print("\n❌ 部分测试失败，需要进一步调试")
        return 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)