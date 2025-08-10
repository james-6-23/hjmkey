"""
特性管理器 - 模块化架构的核心组件
负责动态加载、管理和协调所有可选功能模块
"""

import os
import logging
from typing import Dict, Any, Optional, List
from abc import ABC, abstractmethod
import importlib
import sys
from pathlib import Path

logger = logging.getLogger(__name__)


class Feature(ABC):
    """所有功能模块的基类"""
    
    @abstractmethod
    def __init__(self, config: Dict[str, Any]):
        """
        初始化功能模块
        
        Args:
            config: 配置字典
        """
        pass
    
    @abstractmethod
    def is_healthy(self) -> bool:
        """
        检查功能模块是否正常工作
        
        Returns:
            bool: 功能是否健康
        """
        pass
    
    @abstractmethod
    def get_fallback(self):
        """
        返回功能禁用时的降级实现
        
        Returns:
            降级实现对象
        """
        pass
    
    def cleanup(self):
        """清理功能资源（可选实现）"""
        pass


class FeatureManager:
    """
    特性管理器 - 中央管理所有可选功能
    """
    
    # 功能兼容性矩阵
    COMPATIBILITY_MATRIX = {
        'async_validation': ['progress_display', 'structured_logging', 'connection_pool', 'database', 'plugins', 'monitoring'],
        'progress_display': ['async_validation', 'structured_logging', 'connection_pool', 'database', 'plugins', 'monitoring'],
        'structured_logging': ['async_validation', 'progress_display', 'connection_pool', 'database', 'plugins', 'monitoring'],
        'connection_pool': ['async_validation', 'progress_display', 'structured_logging', 'database', 'plugins', 'monitoring'],
        'database': ['async_validation', 'progress_display', 'structured_logging', 'connection_pool', 'plugins', 'monitoring'],
        'plugins': ['async_validation', 'progress_display', 'structured_logging', 'connection_pool', 'database', 'monitoring'],
        'monitoring': ['async_validation', 'progress_display', 'structured_logging', 'connection_pool', 'database', 'plugins'],
    }
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        初始化特性管理器
        
        Args:
            config: 配置字典，如果为None则从环境变量加载
        """
        self.config = config or self._load_config_from_env()
        self.features = {}
        self.failed_features = []
        self.feature_status = {}
        
        logger.info("=" * 60)
        logger.info("🚀 特性管理器初始化")
        logger.info("=" * 60)
    
    def _load_config_from_env(self) -> Dict[str, Any]:
        """从环境变量加载配置"""
        config = {}
        for key, value in os.environ.items():
            # 转换字符串布尔值为实际布尔值
            if value.lower() in ('true', 'false'):
                config[key] = value.lower() == 'true'
            # 转换数字
            elif value.isdigit():
                config[key] = int(value)
            # 尝试转换浮点数
            elif '.' in value:
                try:
                    config[key] = float(value)
                except ValueError:
                    config[key] = value
            else:
                config[key] = value
        
        logger.debug(f"从环境变量加载了 {len(config)} 个配置项")
        return config
    
    def initialize_all_features(self):
        """初始化所有基于配置的功能"""
        
        logger.info("📦 开始加载功能模块...")
        
        # 功能加载器映射
        feature_loaders = {
            'async_validation': self._load_async_validation,
            'progress_display': self._load_progress_display,
            'structured_logging': self._load_structured_logging,
            'connection_pool': self._load_connection_pool,
            'database': self._load_database,
            'plugins': self._load_plugins,
            'monitoring': self._load_monitoring,
        }
        
        # 遍历所有功能
        for feature_name, loader in feature_loaders.items():
            env_key = f'ENABLE_{feature_name.upper()}'
            
            if self.config.get(env_key, False):
                logger.info(f"🔄 正在加载功能: {feature_name}")
                try:
                    feature = loader()
                    if feature and feature.is_healthy():
                        self.features[feature_name] = feature
                        self.feature_status[feature_name] = 'active'
                        logger.info(f"  ✅ 功能 '{feature_name}' 加载成功")
                    else:
                        self.failed_features.append(feature_name)
                        self.feature_status[feature_name] = 'unhealthy'
                        logger.warning(f"  ⚠️ 功能 '{feature_name}' 健康检查失败")
                except ImportError as e:
                    self.failed_features.append(feature_name)
                    self.feature_status[feature_name] = 'missing_dependency'
                    logger.error(f"  ❌ 功能 '{feature_name}' 缺少依赖: {e}")
                except Exception as e:
                    self.failed_features.append(feature_name)
                    self.feature_status[feature_name] = 'load_error'
                    logger.error(f"  ❌ 功能 '{feature_name}' 加载失败: {e}")
            else:
                self.feature_status[feature_name] = 'disabled'
                logger.debug(f"⏭️ 功能 '{feature_name}' 已禁用")
        
        # 验证兼容性
        self._validate_compatibility()
        
        # 记录摘要
        self._log_feature_summary()
    
    def _validate_compatibility(self):
        """检查功能冲突"""
        enabled_features = list(self.features.keys())
        
        conflicts = []
        for feature in enabled_features:
            compatible_with = self.COMPATIBILITY_MATRIX.get(feature, [])
            for other_feature in enabled_features:
                if other_feature != feature and other_feature not in compatible_with:
                    conflict = tuple(sorted([feature, other_feature]))
                    if conflict not in conflicts:
                        conflicts.append(conflict)
                        logger.warning(f"⚠️ 潜在冲突: '{feature}' 可能与 '{other_feature}' 不兼容")
        
        if conflicts:
            logger.warning(f"发现 {len(conflicts)} 个潜在的功能冲突")
    
    def _log_feature_summary(self):
        """记录功能加载摘要"""
        logger.info("=" * 60)
        logger.info("📊 功能加载摘要:")
        logger.info(f"  ✅ 已加载: {list(self.features.keys())}")
        logger.info(f"  ❌ 失败: {self.failed_features}")
        logger.info(f"  📈 统计: {len(self.features)} 个已加载, {len(self.failed_features)} 个失败")
        
        # 详细状态
        logger.info("📋 详细状态:")
        for feature_name, status in self.feature_status.items():
            status_icon = {
                'active': '✅',
                'disabled': '⏸️',
                'unhealthy': '⚠️',
                'missing_dependency': '📦',
                'load_error': '❌'
            }.get(status, '❓')
            logger.info(f"  {status_icon} {feature_name}: {status}")
        
        logger.info("=" * 60)
    
    def get_feature(self, name: str) -> Optional[Any]:
        """
        获取功能实例
        
        Args:
            name: 功能名称
            
        Returns:
            功能实例，如果未启用则返回None
        """
        return self.features.get(name)
    
    def is_enabled(self, name: str) -> bool:
        """
        检查功能是否已启用
        
        Args:
            name: 功能名称
            
        Returns:
            bool: 功能是否已启用
        """
        return name in self.features
    
    def get_status(self, name: str) -> str:
        """
        获取功能状态
        
        Args:
            name: 功能名称
            
        Returns:
            str: 功能状态
        """
        return self.feature_status.get(name, 'unknown')
    
    def cleanup_all(self):
        """清理所有功能资源"""
        logger.info("🧹 清理所有功能资源...")
        for name, feature in self.features.items():
            try:
                feature.cleanup()
                logger.debug(f"  ✅ 清理功能 '{name}'")
            except Exception as e:
                logger.error(f"  ❌ 清理功能 '{name}' 失败: {e}")
    
    # ========== 功能加载器 ==========
    
    def _load_async_validation(self):
        """加载异步验证功能"""
        try:
            from .async_validation import AsyncValidationFeature
            return AsyncValidationFeature(self.config)
        except ImportError:
            # 如果模块不存在，创建一个占位实现
            logger.debug("异步验证模块未实现，使用占位器")
            return self._create_placeholder_feature("async_validation")
    
    def _load_progress_display(self):
        """加载进度显示功能"""
        try:
            from .progress_display import ProgressDisplayFeature
            return ProgressDisplayFeature(self.config)
        except ImportError:
            logger.debug("进度显示模块未实现，使用占位器")
            return self._create_placeholder_feature("progress_display")
    
    def _load_structured_logging(self):
        """加载结构化日志功能"""
        try:
            from .structured_logging import StructuredLoggingFeature
            return StructuredLoggingFeature(self.config)
        except ImportError:
            logger.debug("结构化日志模块未实现，使用占位器")
            return self._create_placeholder_feature("structured_logging")
    
    def _load_connection_pool(self):
        """加载连接池功能"""
        try:
            from .connection_pool import ConnectionPoolFeature
            return ConnectionPoolFeature(self.config)
        except ImportError:
            logger.debug("连接池模块未实现，使用占位器")
            return self._create_placeholder_feature("connection_pool")
    
    def _load_database(self):
        """加载数据库功能"""
        try:
            from .database import DatabaseFeature
            return DatabaseFeature(self.config)
        except ImportError:
            logger.debug("数据库模块未实现，使用占位器")
            return self._create_placeholder_feature("database")
    
    def _load_plugins(self):
        """加载插件系统功能"""
        try:
            from .plugin_system import PluginSystemFeature
            return PluginSystemFeature(self.config)
        except ImportError:
            logger.debug("插件系统模块未实现，使用占位器")
            return self._create_placeholder_feature("plugins")
    
    def _load_monitoring(self):
        """加载监控功能"""
        try:
            from .monitoring import MonitoringFeature
            return MonitoringFeature(self.config)
        except ImportError:
            logger.debug("监控模块未实现，使用占位器")
            return self._create_placeholder_feature("monitoring")
    
    def _create_placeholder_feature(self, name: str):
        """创建占位功能（用于未实现的模块）"""
        class PlaceholderFeature(Feature):
            def __init__(self, config):
                self.name = name
                self.config = config
            
            def is_healthy(self):
                return True  # 占位器总是"健康"的
            
            def get_fallback(self):
                return None
        
        return PlaceholderFeature(self.config)


# 创建全局实例（可选）
_feature_manager_instance = None

def get_feature_manager(config: Optional[Dict[str, Any]] = None) -> FeatureManager:
    """
    获取特性管理器的单例实例
    
    Args:
        config: 配置字典
        
    Returns:
        FeatureManager: 特性管理器实例
    """
    global _feature_manager_instance
    if _feature_manager_instance is None:
        _feature_manager_instance = FeatureManager(config)
    return _feature_manager_instance