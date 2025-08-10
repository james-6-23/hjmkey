"""
示例验证插件
演示如何创建自定义验证插件
"""

import asyncio
import logging
from typing import Any, Dict
from app.features.plugin_system import Plugin, PluginInfo, PluginType


class ExampleValidatorPlugin(Plugin):
    """示例验证插件"""
    
    def __init__(self, config: Dict[str, Any]):
        """
        初始化插件
        
        Args:
            config: 插件配置
        """
        super().__init__(config)
        self.logger = logging.getLogger("plugin.example_validator")
        self.simulation_delay = config.get("simulation_delay", 0.1)
        self.simulation_error_rate = config.get("simulation_error_rate", 0.0)
        
        self.logger.info("ExampleValidatorPlugin 初始化完成")
    
    async def initialize(self):
        """初始化插件"""
        self.logger.info("ExampleValidatorPlugin 初始化中...")
        # 模拟初始化过程
        await asyncio.sleep(0.1)
        self.logger.info("ExampleValidatorPlugin 初始化完成")
    
    async def execute(self, data: Any, context: Dict[str, Any]) -> Any:
        """
        执行插件功能
        
        Args:
            data: 输入数据（token）
            context: 执行上下文
            
        Returns:
            验证结果
        """
        token = data
        self.logger.debug(f"验证Token: {token[:10]}...")
        
        # 模拟验证延迟
        await asyncio.sleep(self.simulation_delay)
        
        # 模拟验证结果
        is_valid = len(token) > 20  # 简单的验证逻辑
        
        # 模拟错误率
        import random
        if random.random() < self.simulation_error_rate:
            raise Exception("模拟验证错误")
        
        result = {
            "token": token,
            "is_valid": is_valid,
            "plugin": "example_validator",
            "timestamp": context.get("execution_time", "unknown")
        }
        
        self.logger.debug(f"验证完成: {token[:10]}... -> {'有效' if is_valid else '无效'}")
        return result
    
    async def cleanup(self):
        """清理插件资源"""
        self.logger.info("ExampleValidatorPlugin 清理资源")
        # 模拟清理过程
        await asyncio.sleep(0.05)
        self.logger.info("ExampleValidatorPlugin 资源清理完成")
    
    def get_info(self) -> PluginInfo:
        """获取插件信息"""
        return PluginInfo(
            name="ExampleValidatorPlugin",
            version="1.0.0",
            description="示例验证插件，演示插件系统功能",
            type=PluginType.VALIDATION,
            author="Hajimi King Team",
            license="MIT"
        )


# 导出插件类
__all__ = ["ExampleValidatorPlugin"]