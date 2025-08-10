"""
智能密钥同步管理器
实现基于密钥类型的自动分组同步功能
"""

import logging
from typing import List, Dict, Set, Optional
from dataclasses import dataclass, field
from enum import Enum

from utils.sync_utils import sync_utils
from app.services.config_service import get_config_service

logger = logging.getLogger(__name__)


class KeyType(Enum):
    """密钥类型枚举"""
    VALID = "valid"          # 有效密钥
    RATE_LIMITED = "429"      # 429限流密钥
    PAID = "paid"            # 付费版密钥
    FREE = "free"            # 免费版密钥
    UNKNOWN = "unknown"      # 未知类型


@dataclass
class KeyGroup:
    """密钥分组"""
    name: str                           # 组名
    key_types: Set[KeyType]            # 该组接受的密钥类型
    keys: Set[str] = field(default_factory=set)  # 密钥集合
    
    def add_key(self, key: str) -> bool:
        """添加密钥到组"""
        if key not in self.keys:
            self.keys.add(key)
            return True
        return False
    
    def clear(self):
        """清空组内密钥"""
        self.keys.clear()


class SmartSyncManager:
    """
    智能同步管理器
    根据密钥类型自动分配到不同的GPT Load组
    """
    
    def __init__(self):
        """初始化智能同步管理器"""
        self.config_service = get_config_service()
        
        # 加载配置
        self._load_config()
        
        # 初始化分组
        self._init_groups()
        
        # 密钥类型缓存
        self.key_type_cache: Dict[str, KeyType] = {}
        
        logger.info(f"🤖 智能同步管理器初始化完成")
        if self.enabled:
            logger.info(f"   ✅ 智能分组已启用")
            logger.info(f"   📊 配置的分组策略:")
            for group_name, group in self.groups.items():
                types_str = ", ".join([t.value for t in group.key_types])
                logger.info(f"      {group_name}: {types_str}")
        else:
            logger.info(f"   ⚠️ 智能分组未启用")
    
    def _load_config(self):
        """加载配置"""
        # 是否启用智能分组
        self.enabled = self.config_service.get("GPT_LOAD_SMART_GROUP_ENABLED", False)
        
        # 分组配置
        self.group_config = {
            "valid": self.config_service.get("GPT_LOAD_GROUP_VALID", "production"),
            "429": self.config_service.get("GPT_LOAD_GROUP_429", "rate_limited"),
            "paid": self.config_service.get("GPT_LOAD_GROUP_PAID", "paid"),
            "free": self.config_service.get("GPT_LOAD_GROUP_FREE", "free"),
        }
        
        # 是否将429密钥也发送到valid组
        self.send_429_to_valid = self.config_service.get("GPT_LOAD_429_TO_VALID", True)
        
        # 是否将付费密钥也发送到valid组
        self.send_paid_to_valid = self.config_service.get("GPT_LOAD_PAID_TO_VALID", True)
    
    def _init_groups(self):
        """初始化分组"""
        self.groups: Dict[str, KeyGroup] = {}
        
        if not self.enabled:
            return
        
        # Valid组 - 接收所有有效密钥
        valid_types = {KeyType.VALID}
        if self.send_429_to_valid:
            valid_types.add(KeyType.RATE_LIMITED)
        if self.send_paid_to_valid:
            valid_types.add(KeyType.PAID)
        
        self.groups[self.group_config["valid"]] = KeyGroup(
            name=self.group_config["valid"],
            key_types=valid_types
        )
        
        # 429专属组 - 只接收429密钥
        self.groups[self.group_config["429"]] = KeyGroup(
            name=self.group_config["429"],
            key_types={KeyType.RATE_LIMITED}
        )
        
        # Paid专属组 - 只接收付费密钥
        self.groups[self.group_config["paid"]] = KeyGroup(
            name=self.group_config["paid"],
            key_types={KeyType.PAID}
        )
        
        # Free组 - 只接收免费密钥
        self.groups[self.group_config["free"]] = KeyGroup(
            name=self.group_config["free"],
            key_types={KeyType.FREE}
        )
    
    def classify_key(self, key: str, key_type: KeyType) -> None:
        """
        对密钥进行分类
        
        Args:
            key: API密钥
            key_type: 密钥类型
        """
        if not self.enabled:
            return
        
        # 缓存密钥类型
        self.key_type_cache[key] = key_type
        
        # 根据类型分配到对应的组
        for group in self.groups.values():
            if key_type in group.key_types:
                if group.add_key(key):
                    logger.debug(f"🏷️ 密钥 {key[:10]}... 添加到组 {group.name}")
    
    def sync_to_gpt_load(self, 
                        valid_keys: List[str] = None,
                        rate_limited_keys: List[str] = None,
                        paid_keys: List[str] = None,
                        free_keys: List[str] = None) -> bool:
        """
        智能同步密钥到GPT Load
        
        Args:
            valid_keys: 有效密钥列表
            rate_limited_keys: 429密钥列表
            paid_keys: 付费密钥列表
            free_keys: 免费密钥列表
            
        Returns:
            是否同步成功
        """
        if not self.enabled:
            # 如果未启用智能分组，使用传统方式同步所有密钥
            all_keys = []
            if valid_keys:
                all_keys.extend(valid_keys)
            if rate_limited_keys:
                all_keys.extend(rate_limited_keys)
            if paid_keys:
                all_keys.extend(paid_keys)
            if free_keys:
                all_keys.extend(free_keys)
            
            if all_keys:
                logger.info(f"🔄 传统模式：同步 {len(all_keys)} 个密钥到GPT Load")
                sync_utils.add_keys_to_queue(all_keys)
            return True
        
        # 智能分组模式
        logger.info(f"🤖 智能分组模式：开始分类同步")
        
        # 清空现有分组
        for group in self.groups.values():
            group.clear()
        
        # 分类密钥
        if valid_keys:
            for key in valid_keys:
                self.classify_key(key, KeyType.VALID)
        
        if rate_limited_keys:
            for key in rate_limited_keys:
                self.classify_key(key, KeyType.RATE_LIMITED)
        
        if paid_keys:
            for key in paid_keys:
                self.classify_key(key, KeyType.PAID)
        
        if free_keys:
            for key in free_keys:
                self.classify_key(key, KeyType.FREE)
        
        # 同步各组到GPT Load
        success = True
        for group_name, group in self.groups.items():
            if group.keys:
                logger.info(f"📤 同步 {len(group.keys)} 个密钥到组 '{group_name}'")
                
                # 临时修改GPT Load的目标组名
                original_groups = sync_utils.gpt_load_group_names
                sync_utils.gpt_load_group_names = [group_name]
                
                try:
                    # 同步到指定组
                    sync_utils.add_keys_to_queue(list(group.keys))
                    logger.info(f"   ✅ 成功添加到 '{group_name}' 组队列")
                except Exception as e:
                    logger.error(f"   ❌ 同步到 '{group_name}' 组失败: {e}")
                    success = False
                finally:
                    # 恢复原始组名配置
                    sync_utils.gpt_load_group_names = original_groups
        
        # 显示同步统计
        self._log_sync_stats()
        
        return success
    
    def _log_sync_stats(self):
        """记录同步统计"""
        logger.info(f"📊 智能同步统计:")
        
        total_keys = 0
        for group_name, group in self.groups.items():
            count = len(group.keys)
            if count > 0:
                logger.info(f"   {group_name}: {count} 个密钥")
                total_keys += count
        
        logger.info(f"   总计: {total_keys} 个密钥")
    
    def batch_sync_with_types(self, keys_by_type: Dict[KeyType, List[str]]) -> bool:
        """
        批量同步带类型的密钥
        
        Args:
            keys_by_type: 按类型分组的密钥字典
            
        Returns:
            是否同步成功
        """
        return self.sync_to_gpt_load(
            valid_keys=keys_by_type.get(KeyType.VALID, []),
            rate_limited_keys=keys_by_type.get(KeyType.RATE_LIMITED, []),
            paid_keys=keys_by_type.get(KeyType.PAID, []),
            free_keys=keys_by_type.get(KeyType.FREE, [])
        )
    
    def get_group_for_key(self, key: str) -> Optional[str]:
        """
        获取密钥应该属于的组名
        
        Args:
            key: API密钥
            
        Returns:
            组名，如果未找到返回None
        """
        key_type = self.key_type_cache.get(key)
        if not key_type:
            return None
        
        for group_name, group in self.groups.items():
            if key_type in group.key_types:
                return group_name
        
        return None


# 创建全局实例
smart_sync_manager = SmartSyncManager()