"""
插件系统模块 - 动态加载和热重载
提供插件的动态加载、卸载和热重载功能
"""

import asyncio
import logging
from typing import Dict, Any, Optional, List, Callable, Type, Union
from datetime import datetime
import importlib
import importlib.util
import sys
import os
import traceback
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
import threading
from collections import defaultdict
import hashlib
import time

from .feature_manager import Feature

logger = logging.getLogger(__name__)


class PluginType(Enum):
    """插件类型枚举"""
    VALIDATION = "validation"      # 验证插件
    PROCESSING = "processing"      # 处理插件
    OUTPUT = "output"             # 输出插件
    EXTENSION = "extension"       # 扩展插件
    CUSTOM = "custom"             # 自定义插件


class PluginStatus(Enum):
    """插件状态枚举"""
    LOADED = "loaded"             # 已加载
    UNLOADED = "unloaded"         # 已卸载
    ERROR = "error"               # 错误
    DISABLED = "disabled"         # 已禁用
    HOT_RELOADING = "hot_reloading"  # 热重载中


@dataclass
class PluginInfo:
    """插件信息数据类"""
    name: str
    version: str
    description: str
    type: PluginType
    author: str = ""
    license: str = ""
    dependencies: List[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)


class Plugin(ABC):
    """插件基类"""
    
    def __init__(self, config: Dict[str, Any]):
        """
        初始化插件
        
        Args:
            config: 插件配置
        """
        self.config = config
        self.name = self.__class__.__name__
        self.enabled = config.get('enabled', True)
        self.logger = logging.getLogger(f"plugin.{self.name}")
    
    @abstractmethod
    async def initialize(self):
        """初始化插件"""
        pass
    
    @abstractmethod
    async def execute(self, data: Any, context: Dict[str, Any]) -> Any:
        """
        执行插件功能
        
        Args:
            data: 输入数据
            context: 执行上下文
            
        Returns:
            处理结果
        """
        pass
    
    @abstractmethod
    async def cleanup(self):
        """清理插件资源"""
        pass
    
    def get_info(self) -> PluginInfo:
        """获取插件信息"""
        return PluginInfo(
            name=self.name,
            version="1.0.0",
            description="Base plugin",
            type=PluginType.CUSTOM
        )


class PluginManager:
    """插件管理器"""
    
    def __init__(self, plugin_directory: str = "plugins"):
        self.plugin_directory = plugin_directory
        self.plugins: Dict[str, Plugin] = {}
        self.plugin_info: Dict[str, PluginInfo] = {}
        self.plugin_status: Dict[str, PluginStatus] = {}
        self.plugin_configs: Dict[str, Dict[str, Any]] = {}
        self.file_hashes: Dict[str, str] = {}
        self.plugin_lock = threading.RLock()
        
        # 确保插件目录存在
        os.makedirs(plugin_directory, exist_ok=True)
        
        logger.info(f"🔌 插件管理器初始化 (目录: {plugin_directory})")
    
    def load_plugin(self, plugin_name: str, config: Optional[Dict[str, Any]] = None) -> bool:
        """
        加载插件
        
        Args:
            plugin_name: 插件名称
            config: 插件配置
            
        Returns:
            bool: 是否加载成功
        """
        with self.plugin_lock:
            try:
                # 检查插件是否已加载
                if plugin_name in self.plugins:
                    logger.warning(f"插件 {plugin_name} 已经加载")
                    return True
                
                # 构建插件文件路径
                plugin_file = os.path.join(self.plugin_directory, f"{plugin_name}.py")
                if not os.path.exists(plugin_file):
                    logger.error(f"插件文件不存在: {plugin_file}")
                    self.plugin_status[plugin_name] = PluginStatus.ERROR
                    return False
                
                # 计算文件哈希用于热重载检测
                file_hash = self._calculate_file_hash(plugin_file)
                self.file_hashes[plugin_file] = file_hash
                
                # 动态导入插件模块
                spec = importlib.util.spec_from_file_location(plugin_name, plugin_file)
                module = importlib.util.module_from_spec(spec)
                
                # 添加到系统模块中
                sys.modules[plugin_name] = module
                spec.loader.exec_module(module)
                
                # 查找插件类
                plugin_class = None
                for attr_name in dir(module):
                    attr = getattr(module, attr_name)
                    if (isinstance(attr, type) and 
                        issubclass(attr, Plugin) and 
                        attr != Plugin):
                        plugin_class = attr
                        break
                
                if not plugin_class:
                    logger.error(f"插件文件 {plugin_name} 中未找到Plugin子类")
                    self.plugin_status[plugin_name] = PluginStatus.ERROR
                    return False
                
                # 创建插件实例
                plugin_config = config or self.plugin_configs.get(plugin_name, {})
                plugin_instance = plugin_class(plugin_config)
                
                # 初始化插件
                asyncio.create_task(plugin_instance.initialize())
                
                # 注册插件
                self.plugins[plugin_name] = plugin_instance
                self.plugin_info[plugin_name] = plugin_instance.get_info()
                self.plugin_status[plugin_name] = PluginStatus.LOADED
                
                logger.info(f"✅ 插件 {plugin_name} 加载成功")
                return True
                
            except Exception as e:
                logger.error(f"插件 {plugin_name} 加载失败: {e}")
                self.plugin_status[plugin_name] = PluginStatus.ERROR
                return False
    
    def unload_plugin(self, plugin_name: str) -> bool:
        """
        卸载插件
        
        Args:
            plugin_name: 插件名称
            
        Returns:
            bool: 是否卸载成功
        """
        with self.plugin_lock:
            try:
                if plugin_name not in self.plugins:
                    logger.warning(f"插件 {plugin_name} 未加载")
                    return True
                
                # 清理插件资源
                plugin = self.plugins[plugin_name]
                asyncio.create_task(plugin.cleanup())
                
                # 移除插件
                del self.plugins[plugin_name]
                del self.plugin_info[plugin_name]
                self.plugin_status[plugin_name] = PluginStatus.UNLOADED
                
                logger.info(f"⏏️ 插件 {plugin_name} 卸载成功")
                return True
                
            except Exception as e:
                logger.error(f"插件 {plugin_name} 卸载失败: {e}")
                self.plugin_status[plugin_name] = PluginStatus.ERROR
                return False
    
    def reload_plugin(self, plugin_name: str) -> bool:
        """
        重新加载插件（热重载）
        
        Args:
            plugin_name: 插件名称
            
        Returns:
            bool: 是否重载成功
        """
        with self.plugin_lock:
            try:
                logger.info(f"🔄 热重载插件: {plugin_name}")
                self.plugin_status[plugin_name] = PluginStatus.HOT_RELOADING
                
                # 卸载插件
                if not self.unload_plugin(plugin_name):
                    return False
                
                # 重新加载插件
                return self.load_plugin(plugin_name, self.plugin_configs.get(plugin_name))
                
            except Exception as e:
                logger.error(f"插件 {plugin_name} 热重载失败: {e}")
                self.plugin_status[plugin_name] = PluginStatus.ERROR
                return False
    
    def _calculate_file_hash(self, file_path: str) -> str:
        """计算文件哈希值"""
        hash_md5 = hashlib.md5()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_md5.update(chunk)
        return hash_md5.hexdigest()
    
    def check_for_changes(self):
        """检查插件文件变更（用于热重载）"""
        with self.plugin_lock:
            for plugin_name, plugin in self.plugins.items():
                plugin_file = os.path.join(self.plugin_directory, f"{plugin_name}.py")
                if os.path.exists(plugin_file):
                    current_hash = self._calculate_file_hash(plugin_file)
                    if current_hash != self.file_hashes.get(plugin_file):
                        logger.info(f"🔍 检测到插件 {plugin_name} 文件变更")
                        self.reload_plugin(plugin_name)
                        self.file_hashes[plugin_file] = current_hash
    
    def get_plugin(self, plugin_name: str) -> Optional[Plugin]:
        """
        获取插件实例
        
        Args:
            plugin_name: 插件名称
            
        Returns:
            Plugin: 插件实例，如果不存在则返回None
        """
        return self.plugins.get(plugin_name)
    
    def is_loaded(self, plugin_name: str) -> bool:
        """
        检查插件是否已加载
        
        Args:
            plugin_name: 插件名称
            
        Returns:
            bool: 插件是否已加载
        """
        return plugin_name in self.plugins
    
    def get_plugin_status(self, plugin_name: str) -> PluginStatus:
        """
        获取插件状态
        
        Args:
            plugin_name: 插件名称
            
        Returns:
            PluginStatus: 插件状态
        """
        return self.plugin_status.get(plugin_name, PluginStatus.UNLOADED)
    
    def list_plugins(self) -> List[str]:
        """
        列出所有插件
        
        Returns:
            List[str]: 插件名称列表
        """
        return list(self.plugins.keys())
    
    def get_plugin_info(self, plugin_name: str) -> Optional[PluginInfo]:
        """
        获取插件信息
        
        Args:
            plugin_name: 插件名称
            
        Returns:
            PluginInfo: 插件信息
        """
        return self.plugin_info.get(plugin_name)
    
    async def execute_plugin(self, plugin_name: str, data: Any, 
                           context: Optional[Dict[str, Any]] = None) -> Any:
        """
        执行插件
        
        Args:
            plugin_name: 插件名称
            data: 输入数据
            context: 执行上下文
            
        Returns:
            插件执行结果
        """
        plugin = self.get_plugin(plugin_name)
        if not plugin:
            raise ValueError(f"插件 {plugin_name} 未找到")
        
        if not plugin.enabled:
            raise ValueError(f"插件 {plugin_name} 已禁用")
        
        context = context or {}
        context['plugin_name'] = plugin_name
        context['execution_time'] = datetime.now()
        
        try:
            result = await plugin.execute(data, context)
            logger.debug(f"✅ 插件 {plugin_name} 执行成功")
            return result
        except Exception as e:
            logger.error(f"插件 {plugin_name} 执行失败: {e}")
            raise


class PluginSystemFeature(Feature):
    """插件系统功能"""
    
    def __init__(self, config: Dict[str, Any]):
        """
        初始化插件系统功能
        
        Args:
            config: 配置字典
        """
        self.config = config
        self.enabled = config.get('PLUGIN_SYSTEM_ENABLED', True)
        self.plugin_directory = config.get('PLUGIN_DIRECTORY', 'plugins')
        self.hot_reload_enabled = config.get('PLUGIN_HOT_RELOAD', True)
        self.hot_reload_interval = config.get('PLUGIN_HOT_RELOAD_INTERVAL', 5)  # 秒
        
        # 初始化插件管理器
        self.plugin_manager = PluginManager(self.plugin_directory)
        
        # 启动后台任务
        self.background_tasks = []
        
        # 加载默认插件
        self._load_default_plugins()
        
        logger.info("🔌 插件系统功能初始化")
        logger.info(f"  目录: {self.plugin_directory}")
        logger.info(f"  热重载: {'启用' if self.hot_reload_enabled else '禁用'}")
    
    def start_background_tasks(self):
        """启动后台任务"""
        if self.enabled and self.hot_reload_enabled:
            # 启动热重载检查任务
            hot_reload_task = asyncio.create_task(self._check_hot_reload())
            self.background_tasks.append(hot_reload_task)
            
            logger.debug("🔄 插件系统后台任务已启动")
    
    def _start_background_tasks(self):
        """启动后台任务 (兼容性方法)"""
        self.start_background_tasks()
    
    async def _check_hot_reload(self):
        """定期检查插件文件变更"""
        while True:
            try:
                await asyncio.sleep(self.hot_reload_interval)
                if self.enabled and self.hot_reload_enabled:
                    self.plugin_manager.check_for_changes()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"热重载检查失败: {e}")
    
    def _load_default_plugins(self):
        """加载默认插件"""
        # 在实际实现中，这里会加载配置中指定的默认插件
        logger.debug("📋 加载默认插件配置")
    
    def is_healthy(self) -> bool:
        """
        检查功能是否健康
        
        Returns:
            bool: 功能是否健康
        """
        try:
            # 简单的健康检查
            return self.enabled
        except Exception as e:
            logger.error(f"插件系统功能健康检查失败: {e}")
            return False
    
    def get_fallback(self):
        """
        返回降级实现
        """
        return FallbackPluginSystem()
    
    def cleanup(self):
        """清理资源"""
        # 取消后台任务
        for task in self.background_tasks:
            if not task.done():
                task.cancel()
        self.background_tasks.clear()
        
        # 清理所有插件
        for plugin_name in list(self.plugin_manager.plugins.keys()):
            try:
                asyncio.create_task(self.plugin_manager.unload_plugin(plugin_name))
            except Exception as e:
                logger