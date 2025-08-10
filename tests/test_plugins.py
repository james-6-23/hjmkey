#!/usr/bin/env python3
"""
插件系统模块测试脚本
测试动态加载和热重载功能
"""

import os
import sys
from pathlib import Path

# 添加项目根目录到Python路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.features.plugin_system import PluginSystemFeature


def test_plugin_system():
    """测试插件系统功能"""
    print("🧪 测试插件系统...")
    
    # 创建配置
    config = {
        'PLUGIN_SYSTEM_ENABLED': True,
        'PLUGIN_DIRECTORY': 'plugins',
        'PLUGIN_HOT_RELOAD': True,
        'PLUGIN_HOT_RELOAD_INTERVAL': 5
    }
    
    # 创建插件系统实例
    plugin_system = PluginSystemFeature(config)
    
    # 测试健康检查
    print(f"✅ 健康检查: {plugin_system.is_healthy()}")
    
    # 测试降级实现
    fallback = plugin_system.get_fallback()
    print(f"🔄 降级实现: {fallback}")
    
    # 显示插件管理器状态
    if plugin_system.plugin_manager:
        print(f"🔌 插件管理器状态:")
        print(f"  插件目录: {plugin_system.plugin_manager.plugin_directory}")
        print(f"  已加载插件: {len(plugin_system.plugin_manager.plugins)}")
        print(f"  插件列表: {plugin_system.plugin_manager.list_plugins()}")
    
    print("\n✅ 插件系统测试完成")


def test_example_plugin():
    """测试示例插件"""
    print("\n🧪 测试示例插件...")
    
    # 创建配置
    config = {
        'PLUGIN_SYSTEM_ENABLED': True,
        'PLUGIN_DIRECTORY': 'plugins',
        'PLUGIN_HOT_RELOAD': True,
        'PLUGIN_HOT_RELOAD_INTERVAL': 5
    }
    
    # 创建插件系统实例
    plugin_system = PluginSystemFeature(config)
    
    # 尝试加载示例插件
    if plugin_system.plugin_manager:
        print("🔌 尝试加载示例插件...")
        success = plugin_system.plugin_manager.load_plugin('example_validator', {
            'simulation_delay': 0.1,
            'simulation_error_rate': 0.0
        })
        
        print(f"  加载结果: {'成功' if success else '失败'}")
        
        if success:
            # 获取插件信息
            plugin_info = plugin_system.plugin_manager.get_plugin_info('example_validator')
            if plugin_info:
                print(f"  插件名称: {plugin_info.name}")
                print(f"  插件版本: {plugin_info.version}")
                print(f"  插件描述: {plugin_info.description}")
                print(f"  插件类型: {plugin_info.type.value}")
            
            # 测试插件执行
            print("  执行插件测试...")
            try:
                # 这里只是示例，实际执行需要异步环境
                print("  注意: 插件执行需要异步环境，这里仅展示调用方式")
            except Exception as e:
                print(f"  执行错误: {e}")
        
        # 显示插件状态
        status = plugin_system.plugin_manager.get_plugin_status('example_validator')
        print(f"  插件状态: {status.value}")
    
    print("\n✅ 示例插件测试完成")


if __name__ == "__main__":
    # 测试插件系统基本功能
    test_plugin_system()
    
    print("\n" + "="*50 + "\n")
    
    # 测试示例插件
    test_example_plugin()