"""
扫描器模块
负责执行GitHub代码搜索和密钥提取
"""

import re
from typing import List, Dict, Any, Optional, Set, Tuple
from dataclasses import dataclass, field
from datetime import datetime, timedelta
import logging

from app.core.container import inject

logger = logging.getLogger(__name__)


@dataclass
class ScanResult:
    """扫描结果数据类"""
    query: str
    total_items: int = 0
    processed_items: int = 0
    valid_keys: List[str] = field(default_factory=list)
    rate_limited_keys: List[str] = field(default_factory=list)
    skipped_items: int = 0
    errors: List[str] = field(default_factory=list)
    
    def add_valid_key(self, key: str) -> None:
        """添加有效密钥"""
        if key not in self.valid_keys:
            self.valid_keys.append(key)
            
    def add_rate_limited_key(self, key: str) -> None:
        """添加被限流的密钥"""
        if key not in self.rate_limited_keys:
            self.rate_limited_keys.append(key)
            
    def merge(self, other: 'ScanResult') -> None:
        """合并另一个扫描结果"""
        self.total_items += other.total_items
        self.processed_items += other.processed_items
        self.valid_keys.extend(other.valid_keys)
        self.rate_limited_keys.extend(other.rate_limited_keys)
        self.skipped_items += other.skipped_items
        self.errors.extend(other.errors)


@dataclass
class ScanFilter:
    """扫描过滤器配置"""
    date_range_days: int = 730
    file_path_blacklist: List[str] = field(default_factory=list)
    scanned_shas: Set[str] = field(default_factory=set)
    processed_queries: Set[str] = field(default_factory=set)
    last_scan_time: Optional[datetime] = None
    
    def should_skip_item(self, item: Dict[str, Any]) -> Tuple[bool, str]:
        """
        检查是否应该跳过处理此item
        
        Returns:
            tuple: (should_skip, reason)
        """
        # 检查增量扫描时间
        if self.last_scan_time and item.get("repository"):
            repo_pushed_at = item["repository"].get("pushed_at")
            if repo_pushed_at:
                try:
                    repo_pushed_dt = datetime.strptime(repo_pushed_at, "%Y-%m-%dT%H:%M:%SZ")
                    if repo_pushed_dt <= self.last_scan_time:
                        return True, "time_filter"
                except Exception:
                    pass
        
        # 检查SHA是否已扫描
        if item.get("sha") in self.scanned_shas:
            return True, "sha_duplicate"
        
        # 检查仓库年龄
        if item.get("repository"):
            repo_pushed_at = item["repository"].get("pushed_at")
            if repo_pushed_at:
                try:
                    repo_pushed_dt = datetime.strptime(repo_pushed_at, "%Y-%m-%dT%H:%M:%SZ")
                    if repo_pushed_dt < datetime.utcnow() - timedelta(days=self.date_range_days):
                        return True, "age_filter"
                except Exception:
                    pass
        
        # 检查文档和示例文件
        lowercase_path = item.get("path", "").lower()
        if any(token in lowercase_path for token in self.file_path_blacklist):
            return True, "doc_filter"
        
        return False, ""
    
    def add_scanned_sha(self, sha: str) -> None:
        """添加已扫描的SHA"""
        if sha:
            self.scanned_shas.add(sha)
            
    def add_processed_query(self, query: str) -> None:
        """添加已处理的查询"""
        if query:
            self.processed_queries.add(query)
            
    def update_scan_time(self) -> None:
        """更新扫描时间"""
        self.last_scan_time = datetime.utcnow()


class Scanner:
    """
    扫描器类
    负责执行搜索和密钥提取
    """
    
    # Gemini API密钥正则表达式
    KEY_PATTERN = re.compile(r'(AIzaSy[A-Za-z0-9\-_]{33})')
    
    # 占位符和示例密钥特征
    PLACEHOLDER_INDICATORS = [
        "...",
        "YOUR_",
        "EXAMPLE_",
        "PLACEHOLDER",
        "XXX",
        "<your",
        "test_",
        "demo_"
    ]
    
    def __init__(self, scan_filter: Optional[ScanFilter] = None):
        """
        初始化扫描器
        
        Args:
            scan_filter: 扫描过滤器配置
        """
        self.filter = scan_filter or ScanFilter()
        self.skip_stats = {
            "time_filter": 0,
            "sha_duplicate": 0,
            "age_filter": 0,
            "doc_filter": 0
        }
        
    def extract_keys_from_content(self, content: str) -> List[str]:
        """
        从内容中提取API密钥
        
        Args:
            content: 文件内容
            
        Returns:
            提取的密钥列表
        """
        if not content:
            return []
            
        # 使用正则表达式查找所有匹配的密钥
        matches = self.KEY_PATTERN.findall(content)
        
        # 过滤占位符密钥
        filtered_keys = []
        for key in matches:
            if not self._is_placeholder_key(key, content):
                filtered_keys.append(key)
        
        # 去重并返回
        return list(set(filtered_keys))
    
    def _is_placeholder_key(self, key: str, content: str) -> bool:
        """
        检查密钥是否为占位符或示例密钥
        
        Args:
            key: 密钥字符串
            content: 包含密钥的内容上下文
            
        Returns:
            是否为占位符密钥
        """
        # 获取密钥周围的上下文（前后各50个字符）
        key_index = content.find(key)
        if key_index == -1:
            return False
            
        context_start = max(0, key_index - 50)
        context_end = min(len(content), key_index + len(key) + 50)
        context = content[context_start:context_end].upper()
        
        # 检查上下文中是否包含占位符标识
        for indicator in self.PLACEHOLDER_INDICATORS:
            if indicator.upper() in context:
                return True
                
        # 检查密钥本身是否包含重复字符（可能是示例）
        # 例如：AIzaSyAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA
        if len(set(key[7:])) < 5:  # 跳过前缀，检查后续字符的多样性
            return True
            
        return False
    
    def normalize_query(self, query: str) -> str:
        """
        标准化查询字符串
        
        Args:
            query: 原始查询字符串
            
        Returns:
            标准化后的查询字符串
        """
        # 移除多余空格
        query = " ".join(query.split())
        
        # 解析查询组件
        parts = []
        i = 0
        while i < len(query):
            if query[i] == '"':
                # 处理引号内的字符串
                end_quote = query.find('"', i + 1)
                if end_quote != -1:
                    parts.append(query[i:end_quote + 1])
                    i = end_quote + 1
                else:
                    parts.append(query[i])
                    i += 1
            elif query[i] == ' ':
                i += 1
            else:
                # 处理普通词
                start = i
                while i < len(query) and query[i] != ' ':
                    i += 1
                parts.append(query[start:i])
        
        # 分类并排序查询组件
        quoted_strings = []
        language_parts = []
        filename_parts = []
        path_parts = []
        other_parts = []
        
        for part in parts:
            if part.startswith('"') and part.endswith('"'):
                quoted_strings.append(part)
            elif part.startswith('language:'):
                language_parts.append(part)
            elif part.startswith('filename:'):
                filename_parts.append(part)
            elif part.startswith('path:'):
                path_parts.append(part)
            elif part.strip():
                other_parts.append(part)
        
        # 按照固定顺序组合
        normalized_parts = []
        normalized_parts.extend(sorted(quoted_strings))
        normalized_parts.extend(sorted(other_parts))
        normalized_parts.extend(sorted(language_parts))
        normalized_parts.extend(sorted(filename_parts))
        normalized_parts.extend(sorted(path_parts))
        
        return " ".join(normalized_parts)
    
    def should_skip_query(self, query: str) -> bool:
        """
        检查查询是否应该跳过
        
        Args:
            query: 查询字符串
            
        Returns:
            是否应该跳过
        """
        normalized = self.normalize_query(query)
        return normalized in self.filter.processed_queries
    
    def process_search_item(self, item: Dict[str, Any]) -> ScanResult:
        """
        处理单个搜索结果项
        
        Args:
            item: GitHub搜索结果项
            
        Returns:
            扫描结果
        """
        result = ScanResult(query="")
        
        # 检查是否应该跳过
        should_skip, skip_reason = self.filter.should_skip_item(item)
        if should_skip:
            self.skip_stats[skip_reason] = self.skip_stats.get(skip_reason, 0) + 1
            result.skipped_items = 1
            logger.debug(f"Skipping item: {item.get('path', 'unknown')} - reason: {skip_reason}")
            return result
        
        # 记录已扫描的SHA
        if item.get("sha"):
            self.filter.add_scanned_sha(item["sha"])
        
        result.processed_items = 1
        return result
    
    def get_skip_stats_summary(self) -> str:
        """
        获取跳过统计摘要
        
        Returns:
            统计摘要字符串
        """
        total_skipped = sum(self.skip_stats.values())
        if total_skipped == 0:
            return "No items skipped"
            
        parts = []
        for reason, count in self.skip_stats.items():
            if count > 0:
                parts.append(f"{reason}: {count}")
                
        return f"Skipped {total_skipped} items - {', '.join(parts)}"
    
    def reset_skip_stats(self) -> None:
        """重置跳过统计"""
        self.skip_stats = {
            "time_filter": 0,
            "sha_duplicate": 0,
            "age_filter": 0,
            "doc_filter": 0
        }