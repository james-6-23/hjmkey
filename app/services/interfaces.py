"""
服务层接口定义
定义所有服务的抽象接口
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional, Set
from dataclasses import dataclass
from datetime import datetime


@dataclass
class SearchResult:
    """搜索结果数据类"""
    query: str
    total_count: int
    items: List[Dict[str, Any]]
    incomplete_results: bool = False
    error: Optional[str] = None


@dataclass
class Checkpoint:
    """检查点数据类"""
    last_scan_time: Optional[datetime] = None
    scanned_shas: Set[str] = None
    processed_queries: Set[str] = None
    wait_send_balancer: Set[str] = None
    wait_send_gpt_load: Set[str] = None
    
    def __post_init__(self):
        if self.scanned_shas is None:
            self.scanned_shas = set()
        if self.processed_queries is None:
            self.processed_queries = set()
        if self.wait_send_balancer is None:
            self.wait_send_balancer = set()
        if self.wait_send_gpt_load is None:
            self.wait_send_gpt_load = set()


class IGitHubService(ABC):
    """GitHub服务接口"""
    
    @abstractmethod
    def search_code(self, query: str, page: int = 1, per_page: int = 100) -> SearchResult:
        """
        搜索GitHub代码
        
        Args:
            query: 搜索查询
            page: 页码
            per_page: 每页结果数
            
        Returns:
            搜索结果
        """
        pass
    
    @abstractmethod
    def get_file_content(self, repo: str, path: str, ref: Optional[str] = None) -> Optional[str]:
        """
        获取文件内容
        
        Args:
            repo: 仓库名称 (owner/repo)
            path: 文件路径
            ref: 分支/标签/提交SHA (可选)
            
        Returns:
            文件内容，如果失败返回None
        """
        pass
    
    @abstractmethod
    def get_rate_limit(self) -> Dict[str, Any]:
        """
        获取API速率限制信息
        
        Returns:
            速率限制信息
        """
        pass


class IStorageService(ABC):
    """存储服务接口"""
    
    @abstractmethod
    def save_valid_keys(self, keys: List[str], metadata: Optional[Dict[str, Any]] = None) -> None:
        """
        保存有效密钥
        
        Args:
            keys: 密钥列表
            metadata: 元数据（可选）
        """
        pass
    
    @abstractmethod
    def save_rate_limited_keys(self, keys: List[str], metadata: Optional[Dict[str, Any]] = None) -> None:
        """
        保存被限流的密钥
        
        Args:
            keys: 密钥列表
            metadata: 元数据（可选）
        """
        pass
    
    @abstractmethod
    def load_checkpoint(self) -> Checkpoint:
        """
        加载检查点
        
        Returns:
            检查点数据
        """
        pass
    
    @abstractmethod
    def save_checkpoint(self, checkpoint: Checkpoint) -> None:
        """
        保存检查点
        
        Args:
            checkpoint: 检查点数据
        """
        pass
    
    @abstractmethod
    def get_search_queries(self) -> List[str]:
        """
        获取搜索查询列表
        
        Returns:
            查询列表
        """
        pass


class ISyncService(ABC):
    """同步服务接口"""
    
    @abstractmethod
    def sync_to_balancer(self, keys: List[str]) -> bool:
        """
        同步密钥到Gemini Balancer
        
        Args:
            keys: 密钥列表
            
        Returns:
            是否成功
        """
        pass
    
    @abstractmethod
    def sync_to_gpt_load(self, keys: List[str]) -> bool:
        """
        同步密钥到GPT Load
        
        Args:
            keys: 密钥列表
            
        Returns:
            是否成功
        """
        pass
    
    @abstractmethod
    def add_to_queue(self, keys: List[str]) -> None:
        """
        添加密钥到同步队列
        
        Args:
            keys: 密钥列表
        """
        pass
    
    @abstractmethod
    def process_queue(self) -> Dict[str, int]:
        """
        处理同步队列
        
        Returns:
            处理结果统计
        """
        pass


class IConfigService(ABC):
    """配置服务接口"""
    
    @abstractmethod
    def get(self, key: str, default: Any = None) -> Any:
        """
        获取配置值
        
        Args:
            key: 配置键
            default: 默认值
            
        Returns:
            配置值
        """
        pass
    
    @abstractmethod
    def set(self, key: str, value: Any) -> None:
        """
        设置配置值
        
        Args:
            key: 配置键
            value: 配置值
        """
        pass
    
    @abstractmethod
    def get_all(self) -> Dict[str, Any]:
        """
        获取所有配置
        
        Returns:
            配置字典
        """
        pass
    
    @abstractmethod
    def reload(self) -> None:
        """重新加载配置"""
        pass
    
    @abstractmethod
    def validate(self) -> bool:
        """
        验证配置
        
        Returns:
            配置是否有效
        """
        pass