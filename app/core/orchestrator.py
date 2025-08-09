"""
协调器模块
负责协调整个扫描、验证和同步流程
"""

import asyncio
import time
import logging
import sys
from typing import List, Dict, Any, Optional, Set
from dataclasses import dataclass, field
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

# 添加项目根目录到Python路径
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from app.core.scanner import Scanner, ScanResult, ScanFilter
from app.core.validator import KeyValidator, ValidationResult, ValidationStatus
from app.core.container import inject
from app.services.config_service import get_config_service
from utils.github_client import GitHubClient

logger = logging.getLogger(__name__)


@dataclass
class OrchestrationConfig:
    """协调器配置"""
    max_concurrent_searches: int = 5
    max_concurrent_validations: int = 10
    batch_size: int = 20
    checkpoint_interval: int = 20
    loop_delay: int = 10
    enable_async: bool = True


@dataclass
class OrchestrationStats:
    """协调统计信息"""
    total_queries_processed: int = 0
    total_items_processed: int = 0
    total_keys_found: int = 0
    total_valid_keys: int = 0
    total_rate_limited_keys: int = 0
    total_errors: int = 0
    start_time: datetime = field(default_factory=datetime.now)
    
    @property
    def elapsed_time(self) -> float:
        """获取运行时间（秒）"""
        return (datetime.now() - self.start_time).total_seconds()
    
    @property
    def processing_rate(self) -> float:
        """获取处理速率（项/秒）"""
        if self.elapsed_time > 0:
            return self.total_items_processed / self.elapsed_time
        return 0
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "total_queries_processed": self.total_queries_processed,
            "total_items_processed": self.total_items_processed,
            "total_keys_found": self.total_keys_found,
            "total_valid_keys": self.total_valid_keys,
            "total_rate_limited_keys": self.total_rate_limited_keys,
            "total_errors": self.total_errors,
            "elapsed_time": self.elapsed_time,
            "processing_rate": self.processing_rate,
            "start_time": self.start_time.isoformat()
        }


class Orchestrator:
    """
    主协调器
    负责协调扫描、验证和同步的整体流程
    """
    
    def __init__(
        self,
        scanner: Scanner,
        validator: KeyValidator,
        config: Optional[OrchestrationConfig] = None
    ):
        """
        初始化协调器
        
        Args:
            scanner: 扫描器实例
            validator: 验证器实例
            config: 协调器配置
        """
        self.scanner = scanner
        self.validator = validator
        self.config = config or OrchestrationConfig()
        self.stats = OrchestrationStats()
        self.running = False
        self._executor = ThreadPoolExecutor(max_workers=self.config.max_concurrent_searches)
        
        # 初始化GitHub客户端
        config_service = get_config_service()
        tokens = config_service.get("GITHUB_TOKENS_LIST", [])
        if tokens:
            self.github_client = GitHubClient(tokens)
            logger.info(f"✅ GitHub客户端初始化成功，使用 {len(tokens)} 个tokens")
        else:
            self.github_client = None
            logger.warning("⚠️ 没有可用的GitHub tokens，搜索功能将无法使用")
        
    async def run(self, queries: List[str], max_loops: Optional[int] = None) -> OrchestrationStats:
        """
        运行主协调流程
        
        Args:
            queries: 搜索查询列表
            max_loops: 最大循环次数（None表示无限循环）
            
        Returns:
            协调统计信息
        """
        self.running = True
        loop_count = 0
        
        logger.info("=" * 60)
        logger.info("🚀 ORCHESTRATOR STARTING")
        logger.info("=" * 60)
        logger.info(f"⏰ Started at: {self.stats.start_time.strftime('%Y-%m-%d %H:%M:%S')}")
        logger.info(f"🔍 Queries to process: {len(queries)}")
        logger.info(f"⚙️ Async mode: {'Enabled' if self.config.enable_async else 'Disabled'}")
        logger.info("=" * 60)
        
        try:
            while self.running and (max_loops is None or loop_count < max_loops):
                loop_count += 1
                logger.info(f"🔄 Loop #{loop_count} - {datetime.now().strftime('%H:%M:%S')}")
                
                # 重置扫描器统计
                self.scanner.reset_skip_stats()
                
                # 处理查询
                if self.config.enable_async:
                    await self._process_queries_async(queries)
                else:
                    self._process_queries_sync(queries)
                
                # 显示循环统计
                self._log_loop_stats(loop_count)
                
                # 检查是否所有查询都已处理
                if self._all_queries_processed(queries):
                    logger.info("✅ All queries processed, stopping orchestrator")
                    break
                
                # 循环间延迟
                if self.running and (max_loops is None or loop_count < max_loops):
                    logger.info(f"💤 Sleeping for {self.config.loop_delay} seconds...")
                    await asyncio.sleep(self.config.loop_delay)
                    
        except KeyboardInterrupt:
            logger.info("⛔ Interrupted by user")
        except Exception as e:
            logger.error(f"💥 Orchestrator error: {e}")
            self.stats.total_errors += 1
        finally:
            self.running = False
            self._log_final_stats()
            
        return self.stats
    
    async def _process_queries_async(self, queries: List[str]) -> None:
        """
        异步处理查询列表
        
        Args:
            queries: 查询列表
        """
        # 创建异步任务
        tasks = []
        semaphore = asyncio.Semaphore(self.config.max_concurrent_searches)
        
        for query in queries:
            if self.scanner.should_skip_query(query):
                logger.info(f"⏭️ Skipping already processed query: {query}")
                continue
                
            task = self._process_single_query_async(query, semaphore)
            tasks.append(task)
        
        # 等待所有任务完成
        if tasks:
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # 处理结果
            for result in results:
                if isinstance(result, Exception):
                    logger.error(f"Query processing error: {result}")
                    self.stats.total_errors += 1
    
    async def _process_single_query_async(self, query: str, semaphore: asyncio.Semaphore) -> None:
        """
        异步处理单个查询
        
        Args:
            query: 查询字符串
            semaphore: 并发控制信号量
        """
        async with semaphore:
            # 这里应该调用异步的GitHub客户端
            # 由于原代码中的GitHub客户端是同步的，我们在线程池中运行
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(
                self._executor,
                self._process_single_query_sync,
                query
            )
    
    def _process_queries_sync(self, queries: List[str]) -> None:
        """
        同步处理查询列表
        
        Args:
            queries: 查询列表
        """
        for query in queries:
            if not self.running:
                break
                
            if self.scanner.should_skip_query(query):
                logger.info(f"⏭️ Skipping already processed query: {query}")
                continue
                
            self._process_single_query_sync(query)
    
    def _process_single_query_sync(self, query: str) -> None:
        """
        同步处理单个查询
        
        Args:
            query: 查询字符串
        """
        try:
            logger.info(f"🔍 Processing query: {query}")
            
            # 标准化查询
            normalized_query = self.scanner.normalize_query(query)
            
            # 调用GitHub客户端进行搜索
            if not self.github_client:
                logger.error("❌ GitHub客户端未初始化，无法执行搜索")
                return
            
            search_result = self.github_client.search_for_keys(query)
            
            if not search_result or not search_result.get("items"):
                logger.info(f"📭 No items found for query: {query}")
                self.scanner.filter.add_processed_query(normalized_query)
                self.stats.total_queries_processed += 1
                return
            
            items = search_result["items"]
            query_stats = {
                "valid_keys": 0,
                "rate_limited_keys": 0,
                "processed_items": 0
            }
            
            # 处理搜索结果项
            for i, item in enumerate(items, 1):
                if not self.running:
                    break
                    
                # 定期保存检查点
                if i % self.config.checkpoint_interval == 0:
                    self._save_checkpoint()
                    logger.info(f"📈 Progress: {i}/{len(items)} items processed")
                
                # 处理单个项
                result = self._process_item(item)
                
                # 更新统计
                query_stats["processed_items"] += result.processed_items
                query_stats["valid_keys"] += len(result.valid_keys)
                query_stats["rate_limited_keys"] += len(result.rate_limited_keys)
                
                self.stats.total_items_processed += result.processed_items
                self.stats.total_keys_found += len(result.valid_keys) + len(result.rate_limited_keys)
                self.stats.total_valid_keys += len(result.valid_keys)
                self.stats.total_rate_limited_keys += len(result.rate_limited_keys)
            
            # 记录查询完成
            self.scanner.filter.add_processed_query(normalized_query)
            self.stats.total_queries_processed += 1
            
            # 记录查询统计
            logger.info(
                f"✅ Query complete - Processed: {query_stats['processed_items']}, "
                f"Valid: {query_stats['valid_keys']}, "
                f"Rate limited: {query_stats['rate_limited_keys']}"
            )
            
            # 显示跳过统计
            skip_summary = self.scanner.get_skip_stats_summary()
            if skip_summary != "No items skipped":
                logger.info(f"📊 {skip_summary}")
                
        except Exception as e:
            logger.error(f"Error processing query '{query}': {e}")
            self.stats.total_errors += 1
    
    def _process_item(self, item: Dict[str, Any]) -> ScanResult:
        """
        处理单个搜索结果项
        
        Args:
            item: 搜索结果项
            
        Returns:
            扫描结果
        """
        # 使用扫描器处理项
        result = self.scanner.process_search_item(item)
        
        if result.skipped_items > 0:
            return result
        
        # 获取文件内容
        if not self.github_client:
            logger.error("❌ GitHub客户端未初始化，无法获取文件内容")
            return result
        
        content = self.github_client.get_file_content(item)
        
        if not content:
            logger.warning(f"⚠️ Failed to fetch content for: {item.get('path', 'unknown')}")
            return result
        
        # 提取密钥
        keys = self.scanner.extract_keys_from_content(content)
        
        if not keys:
            return result
        
        logger.info(f"🔑 Found {len(keys)} suspected key(s), validating...")
        
        # 验证密钥
        validation_results = self.validator.validate_batch(keys)
        
        for val_result in validation_results:
            if val_result.is_valid:
                result.add_valid_key(val_result.key)
                logger.info(f"✅ VALID: {val_result.key[:10]}...")
            elif val_result.is_rate_limited:
                result.add_rate_limited_key(val_result.key)
                logger.warning(f"⚠️ RATE LIMITED: {val_result.key[:10]}...")
            else:
                logger.info(f"❌ INVALID: {val_result.key[:10]}... - {val_result.status.value}")
        
        return result
    
    
    def _save_checkpoint(self) -> None:
        """保存检查点"""
        # 这里应该调用文件管理器保存检查点
        # 暂时只记录日志
        logger.debug("Checkpoint saved")
    
    def _all_queries_processed(self, queries: List[str]) -> bool:
        """
        检查是否所有查询都已处理
        
        Args:
            queries: 查询列表
            
        Returns:
            是否全部处理完成
        """
        for query in queries:
            normalized = self.scanner.normalize_query(query)
            if normalized not in self.scanner.filter.processed_queries:
                return False
        return True
    
    def _log_loop_stats(self, loop_count: int) -> None:
        """
        记录循环统计信息
        
        Args:
            loop_count: 循环计数
        """
        logger.info(
            f"🏁 Loop #{loop_count} complete - "
            f"Processed: {self.stats.total_items_processed} items | "
            f"Valid keys: {self.stats.total_valid_keys} | "
            f"Rate limited: {self.stats.total_rate_limited_keys}"
        )
    
    def _log_final_stats(self) -> None:
        """记录最终统计信息"""
        logger.info("=" * 60)
        logger.info("📊 FINAL STATISTICS")
        logger.info("=" * 60)
        logger.info(f"Total queries processed: {self.stats.total_queries_processed}")
        logger.info(f"Total items processed: {self.stats.total_items_processed}")
        logger.info(f"Total keys found: {self.stats.total_keys_found}")
        logger.info(f"Total valid keys: {self.stats.total_valid_keys}")
        logger.info(f"Total rate limited keys: {self.stats.total_rate_limited_keys}")
        logger.info(f"Total errors: {self.stats.total_errors}")
        logger.info(f"Elapsed time: {self.stats.elapsed_time:.2f} seconds")
        logger.info(f"Processing rate: {self.stats.processing_rate:.2f} items/second")
        logger.info("=" * 60)
    
    def stop(self) -> None:
        """停止协调器"""
        self.running = False
        logger.info("🛑 Orchestrator stop requested")
    
    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        return self.stats.to_dict()