"""
协调器 V2 - 集成所有优化组件的增强版
包含统一统计、安全机制、优雅停机、原子写入、TokenPool等
"""

import asyncio
import time
import logging
import sys
from typing import List, Dict, Any, Optional, Set
from datetime import datetime
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor

# 添加项目根目录到Python路径
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

# 导入新组件
from app.core.stats import RunStats, KeyStatus, StatsManager
from app.core.graceful_shutdown import (
    GracefulShutdownManager, 
    OrchestratorState, 
    StateMachine
)
from app.core.scanner import Scanner, ScanResult
from app.core.validator import KeyValidator
from utils.file_utils import PathManager, AtomicFileWriter, RunArtifactManager
from utils.security_utils import (
    mask_key, 
    SecureKeyStorage, 
    setup_secure_logging,
    validate_environment
)
from utils.token_pool import TokenPool, TokenSelectionStrategy
from utils.github_client_v2 import create_github_client_v2
from app.services.config_service import get_config_service

logger = logging.getLogger(__name__)


class OrchestratorV2:
    """
    增强版协调器 - 集成所有优化
    """
    
    def __init__(self, scanner: Scanner = None, validator: KeyValidator = None):
        """
        初始化协调器 V2
        
        Args:
            scanner: 扫描器实例
            validator: 验证器实例
        """
        # 设置安全日志
        setup_secure_logging()
        validate_environment()
        
        # 初始化路径管理器
        self.path_manager = PathManager()
        self.run_id = self.path_manager.set_run_id()
        
        logger.info("=" * 60)
        logger.info("🚀 HAJIMI KING V2.0 - ENHANCED ORCHESTRATOR")
        logger.info(f"📁 Run ID: {self.run_id}")
        logger.info(f"📂 Run Directory: {self.path_manager.current_run_dir}")
        logger.info("=" * 60)
        
        # 初始化统计管理器
        self.stats_manager = StatsManager(self.path_manager.data_root)
        self.stats = self.stats_manager.create_run()
        
        # 初始化状态机和停机管理器
        self.state_machine = StateMachine(OrchestratorState.IDLE)
        self.shutdown_manager = GracefulShutdownManager(self.state_machine)
        
        # 注册停机回调
        self.shutdown_manager.register_cleanup(self._cleanup_resources)
        self.shutdown_manager.register_finalize(self._finalize_run)
        
        # 初始化文件管理器
        self.writer = AtomicFileWriter()
        self.artifact_manager = RunArtifactManager(self.path_manager)
        
        # 简化：直接使用明文存储（日志中脱敏即可）
        self.secure_storage = None  # 不再使用复杂的加密存储
        
        # 初始化扫描器和验证器
        self.scanner = scanner or Scanner()
        self.validator = validator or KeyValidator()
        
        # 初始化 GitHub 客户端和 TokenPool
        self._init_github_client()
        
        # 线程池（根据CPU核心数调整）
        import multiprocessing
        max_workers = min(multiprocessing.cpu_count() * 2, 20)
        self._executor = ThreadPoolExecutor(max_workers=max_workers)
        logger.info(f"🔧 Thread pool initialized with {max_workers} workers")
        
        # 运行标志
        self.running = False
        
        logger.info("✅ Orchestrator V2 initialized successfully")
    
    def _init_github_client(self):
        """初始化 GitHub 客户端和 TokenPool"""
        config_service = get_config_service()
        tokens = config_service.get("GITHUB_TOKENS_LIST", [])
        
        if not tokens:
            logger.warning("⚠️ No GitHub tokens available")
            self.github_client = None
            return

        # 创建增强的 GitHub 客户端 V2 (内置TokenPool)
        strategy = config_service.get("TOKEN_POOL_STRATEGY", "ADAPTIVE")
        self.github_client = create_github_client_v2(tokens, strategy=strategy)
        
        logger.info(f"✅ GitHub client initialized with {len(tokens)} tokens")
        logger.info(f"   Token pool strategy: {strategy}")
    
    async def run(self, queries: List[str], max_loops: Optional[int] = None) -> RunStats:
        """
        运行主协调流程
        
        Args:
            queries: 搜索查询列表
            max_loops: 最大循环次数
            
        Returns:
            运行统计
        """
        try:
            # 使用停机管理器的上下文
            with self.shutdown_manager.managed_execution():
                # 转换到初始化状态
                self.state_machine.transition_to(OrchestratorState.INITIALIZING)
                
                # 设置运行参数
                self.running = True
                self.stats.queries_planned = len(queries)
                
                # 保存初始检查点
                self._save_checkpoint("initial")
                
                # 转换到扫描状态
                self.state_machine.transition_to(OrchestratorState.SCANNING)
                
                # 主循环
                loop_count = 0
                while self.running and (max_loops is None or loop_count < max_loops):
                    loop_count += 1
                    
                    # 检查停机请求
                    if self.shutdown_manager.is_shutdown_requested():
                        logger.info("🛑 Shutdown requested, stopping...")
                        break
                    
                    logger.info(f"🔄 Loop #{loop_count} - {datetime.now().strftime('%H:%M:%S')}")
                    
                    # 处理查询
                    await self._process_queries(queries)
                    
                    # 检查是否完成
                    if self._all_queries_processed(queries):
                        logger.info("✅ All queries processed")
                        break
                    
                    # 保存检查点
                    self._save_checkpoint(f"loop_{loop_count}")
                    
                    # 循环间延迟
                    if self.running and (max_loops is None or loop_count < max_loops):
                        await asyncio.sleep(10)
                
                # 转换到最终化状态
                self.state_machine.transition_to(OrchestratorState.FINALIZING)
                
        except Exception as e:
            logger.error(f"💥 Orchestrator error: {e}")
            self.stats.add_error(type(e).__name__, str(e))
            self.state_machine.transition_to(OrchestratorState.ERROR)
            raise
        
        finally:
            self.running = False
            
        return self.stats
    
    async def _process_queries(self, queries: List[str]):
        """串行处理查询列表（一个接一个）"""
        # 过滤未处理的查询
        pending_queries = []
        for query in queries:
            if self.scanner.should_skip_query(query):
                logger.info(f"⏭️ Skipping processed query: {query}")
            else:
                pending_queries.append(query)
        
        if not pending_queries:
            logger.info("✅ All queries completed")
            return
        
        logger.info(f"📋 Pending queries: {len(pending_queries)}")
        logger.info("=" * 60)
        
        # 串行处理每个查询（一个接一个）
        for i, query in enumerate(pending_queries, 1):
            if not self.running or self.shutdown_manager.is_shutdown_requested():
                break
            
            logger.info(f"🔍 [{i}/{len(pending_queries)}] Processing query: {query}")
            logger.info("-" * 60)
            
            try:
                await self._process_single_query(query)
                self.stats.mark_query_complete(success=True)
            except Exception as e:
                logger.error(f"❌ Query failed: {query} - {e}")
                self.stats.mark_query_complete(success=False)
                self.stats.add_error("query_error", str(e), {"query": query})
            
            logger.info("=" * 60)
    
    async def _process_single_query(self, query: str):
        """处理单个查询"""
        query_start_time = time.time()
        
        if not self.github_client:
            logger.error("❌ GitHub client not initialized")
            return
        
        # 记录查询开始时的统计
        start_stats = {
            'valid_free': self.stats.by_status[KeyStatus.VALID_FREE],
            'valid_paid': self.stats.by_status[KeyStatus.VALID_PAID],
            'rate_limited': self.stats.by_status[KeyStatus.RATE_LIMITED],
            'invalid': self.stats.by_status[KeyStatus.INVALID]
        }
        
        # 执行搜索 - V2版本已经内置TokenPool管理
        start_time = time.time()
        search_result = self.github_client.search_for_keys(query)
        response_time = time.time() - start_time
        
        if not search_result or not search_result.get("items"):
            logger.info(f"📭 No results found")
            return
        
        items = search_result["items"]
        logger.info(f"📦 Found {len(items)} files")
        
        # 转换到验证状态
        if self.state_machine.state != OrchestratorState.VALIDATING:
            self.state_machine.transition_to(OrchestratorState.VALIDATING)
        
        # 处理项目
        for item in items:
            if not self.running or self.shutdown_manager.is_shutdown_requested():
                break
            
            await self._process_item(item)
        
        # 标记查询完成
        self.scanner.filter.add_processed_query(query)
        
        # 转回扫描状态（只有在不是FINALIZING时才转换）
        if self.state_machine.state != OrchestratorState.FINALIZING:
            self.state_machine.transition_to(OrchestratorState.SCANNING)
        
        # 显示查询完成后的统计
        self._log_query_summary(query, start_stats, time.time() - query_start_time)
    
    async def _process_item(self, item: Dict[str, Any]):
        """处理单个项目"""
        # 使用扫描器处理
        result = self.scanner.process_search_item(item)
        
        if result.skipped_items > 0:
            return
        
        # 获取文件内容
        content = self.github_client.get_file_content(item)
        if not content:
            return
        
        # 提取密钥
        keys = self.scanner.extract_keys_from_content(content)
        if not keys:
            return
        
        logger.info(f"🔑 Found {len(keys)} suspected keys")
        
        # 批量并发验证密钥
        validation_results = await self._validate_keys_concurrent(keys)
        
        for val_result in validation_results:
            # 使用脱敏日志
            masked_key = mask_key(val_result.key)
            
            if val_result.is_valid:
                # 判断是否付费
                is_paid = self._check_if_paid_key(val_result.key)
                status = KeyStatus.VALID_PAID if is_paid else KeyStatus.VALID_FREE
                
                self.stats.mark_key(val_result.key, status)
                logger.info(f"✅ VALID ({status.name}): {masked_key}")
                
                # 实时保存有效密钥到文件
                self._save_key_to_file(val_result.key, status)
                
            elif val_result.is_rate_limited:
                self.stats.mark_key(val_result.key, KeyStatus.RATE_LIMITED)
                logger.warning(f"⚠️ RATE LIMITED: {masked_key}")
                
                # 实时保存限流密钥到文件
                self._save_key_to_file(val_result.key, KeyStatus.RATE_LIMITED)
                
            else:
                self.stats.mark_key(val_result.key, KeyStatus.INVALID)
                logger.info(f"❌ INVALID: {masked_key}")
                
                # 实时保存无效密钥到文件（可选）
                self._save_key_to_file(val_result.key, KeyStatus.INVALID)
        
        # 更新处理统计
        self.stats.items_processed += 1
    
    def _check_if_paid_key(self, key: str) -> bool:
        """检查是否为付费密钥"""
        try:
            import google.generativeai as genai
            genai.configure(api_key=key)
            
            # 尝试访问付费模型
            paid_models = ["gemini-1.5-pro", "gemini-1.5-flash"]
            for model_name in paid_models:
                try:
                    model = genai.GenerativeModel(model_name)
                    response = model.generate_content(
                        "1",
                        generation_config=genai.types.GenerationConfig(
                            max_output_tokens=1,
                            temperature=0
                        )
                    )
                    return True
                except:
                    continue
            return False
        except:
            return False
    
    def _all_queries_processed(self, queries: List[str]) -> bool:
        """检查是否所有查询都已处理"""
        for query in queries:
            normalized = self.scanner.normalize_query(query)
            if normalized not in self.scanner.filter.processed_queries:
                return False
        return True
    
    def _save_checkpoint(self, label: str = ""):
        """保存检查点"""
        try:
            # 获取token pool状态，但需要处理不可序列化的对象
            token_pool_status = None
            if self.github_client and hasattr(self.github_client, 'token_pool'):
                pool_status = self.github_client.token_pool.get_pool_status()
                # 转换strategy_usage中的枚举为字符串
                if 'strategy_usage' in pool_status:
                    pool_status['strategy_usage'] = {
                        str(k): v for k, v in pool_status['strategy_usage'].items()
                    }
                token_pool_status = pool_status
            
            checkpoint_data = {
                "label": label,
                "timestamp": datetime.now().isoformat(),
                "run_id": self.run_id,
                "state": self.state_machine.state.name,
                "stats": self.stats.summary(),
                "processed_queries": list(self.scanner.filter.processed_queries),
                "token_pool_status": token_pool_status
            }
            
            self.artifact_manager.save_checkpoint(checkpoint_data)
            logger.debug(f"💾 Checkpoint saved: {label}")
            
        except Exception as e:
            logger.error(f"Failed to save checkpoint: {e}")
    
    def _cleanup_resources(self):
        """清理资源"""
        logger.info("🧹 Cleaning up resources...")
        
        # 关闭线程池
        if hasattr(self, '_executor'):
            self._executor.shutdown(wait=False)
        
        # 保存 TokenPool 状态
        if self.github_client and hasattr(self.github_client, 'token_pool'):
            pool_status = self.github_client.token_pool.get_pool_status()
            # 转换枚举为字符串以便序列化
            if 'strategy_usage' in pool_status:
                pool_status['strategy_usage'] = {
                    str(k): v for k, v in pool_status['strategy_usage'].items()
                }
            try:
                self.artifact_manager.save_artifact("token_pool_final.json", pool_status)
            except Exception as e:
                logger.error(f"Failed to save token pool status: {e}")
    
    def _finalize_run(self):
        """最终化运行"""
        logger.info("📝 Finalizing run...")
        
        # 完成统计
        self.stats.finalize()
        
        # 保存密钥（由于secure_storage为None，直接保存到文件）
        keys_by_status = {
            status.name: self.stats.get_keys_list(status)
            for status in KeyStatus
        }
        
        # 保存密钥摘要到文件（替代secure_storage）
        try:
            summary_file = self.path_manager.current_run_dir / "keys_summary.json"
            import json
            with open(summary_file, 'w', encoding='utf-8') as f:
                # 创建脱敏的摘要
                masked_summary = {}
                for status_name, keys in keys_by_status.items():
                    masked_summary[status_name] = {
                        'count': len(keys),
                        'keys': [mask_key(k) for k in keys[:5]]  # 只显示前5个脱敏密钥
                    }
                json.dump(masked_summary, f, indent=2, ensure_ascii=False)
            logger.info(f"💾 Keys summary saved to {summary_file}")
        except Exception as e:
            logger.error(f"Failed to save keys summary: {e}")
        
        # 保存最终报告
        try:
            self.artifact_manager.save_final_report(self.stats.summary())
        except Exception as e:
            logger.error(f"Failed to save final report: {e}")
        
        # 显示最终统计
        self._log_final_stats()
    
    def _log_final_stats(self):
        """记录最终统计"""
        summary = self.stats.summary()
        
        logger.info("=" * 60)
        logger.info("📊 FINAL STATISTICS")
        logger.info("=" * 60)
        logger.info(f"Run ID: {summary['run_id']}")
        logger.info(f"Duration: {summary['duration_seconds']:.1f} seconds")
        logger.info(f"Queries: {summary['queries']['completed']}/{summary['queries']['planned']}")
        logger.info(f"Items processed: {summary['processing']['items_processed']}")
        logger.info(f"Valid keys (total/free/paid): {summary['keys']['valid_total']}/{summary['keys']['valid_free']}/{summary['keys']['valid_paid']}")
        logger.info(f"Rate limited: {summary['keys']['rate_limited']}")
        logger.info(f"Invalid: {summary['keys']['invalid']}")
        logger.info(f"Data loss: {summary['data_quality']['data_loss_ratio']}")
        logger.info(f"Errors: {summary['errors']['total']}")
        logger.info("=" * 60)
        
        # TokenPool 统计
        if self.github_client and hasattr(self.github_client, 'token_pool'):
            pool_status = self.github_client.token_pool.get_pool_status()
            used_quota = pool_status['total_limit'] - pool_status['total_remaining']
            utilization_pct = (used_quota / pool_status['total_limit'] * 100) if pool_status['total_limit'] > 0 else 0

            logger.info("📊 Token池统计")
            logger.info(f"Total tokens: {pool_status['total_tokens']}")
            logger.info(f"Healthy/Limited/Exhausted: {pool_status['healthy']}/{pool_status['limited']}/{pool_status['exhausted']}")
            logger.info(f"Quota used: {used_quota}/{pool_status['total_limit']} ({utilization_pct:.1f}%)")
            logger.info("=" * 60)


    def _save_key_to_file(self, key: str, status: KeyStatus):
        """实时保存密钥到TXT文件（明文）"""
        try:
            # 确定文件路径 - 直接保存在data目录下，方便访问
            if status == KeyStatus.VALID_FREE:
                filename = "keys_valid_free.txt"
            elif status == KeyStatus.VALID_PAID:
                filename = "keys_valid_paid.txt"
            elif status == KeyStatus.RATE_LIMITED:
                filename = "keys_rate_limited.txt"
            elif status == KeyStatus.INVALID:
                filename = "keys_invalid.txt"
            else:
                return
            
            # 构建路径 - 保存在 data/keys/ 目录下
            keys_dir = self.path_manager.data_root / "keys"
            keys_dir.mkdir(parents=True, exist_ok=True)
            file_path = keys_dir / filename
            
            # 同时保存到运行目录（用于记录）
            run_file_path = self.path_manager.current_run_dir / "keys" / filename
            run_file_path.parent.mkdir(parents=True, exist_ok=True)
            
            # 追加写入密钥（明文）
            for path in [file_path, run_file_path]:
                with open(path, 'a', encoding='utf-8') as f:
                    f.write(f"{key}\n")
                    f.flush()  # 立即刷新到磁盘
            
            # 日志中显示脱敏版本
            masked_key = mask_key(key)
            logger.info(f"💾 Key saved to {filename}: {masked_key}")
            
        except Exception as e:
            logger.error(f"Failed to save key: {e}")
    
    def _log_query_summary(self, query: str, start_stats: Dict, duration: float):
        """记录查询完成后的摘要"""
        # 计算新增的密钥
        new_valid_free = self.stats.by_status[KeyStatus.VALID_FREE] - start_stats['valid_free']
        new_valid_paid = self.stats.by_status[KeyStatus.VALID_PAID] - start_stats['valid_paid']
        new_rate_limited = self.stats.by_status[KeyStatus.RATE_LIMITED] - start_stats['rate_limited']
        new_invalid = self.stats.by_status[KeyStatus.INVALID] - start_stats['invalid']
        
        logger.info("=" * 60)
        logger.info(f"📊 QUERY SUMMARY: {query[:50]}...")
        logger.info("=" * 60)
        logger.info(f"⏱️  Duration: {duration:.1f} seconds")
        logger.info(f"🔑 Keys found in this query:")
        logger.info(f"   Valid (Free): +{new_valid_free}")
        logger.info(f"   Valid (Paid): +{new_valid_paid}")
        logger.info(f"   Rate Limited: +{new_rate_limited}")
        logger.info(f"   Invalid: +{new_invalid}")
        logger.info(f"📈 Total keys so far:")
        logger.info(f"   Valid (Free): {self.stats.by_status[KeyStatus.VALID_FREE]}")
        logger.info(f"   Valid (Paid): {self.stats.by_status[KeyStatus.VALID_PAID]}")
        logger.info(f"   Rate Limited: {self.stats.by_status[KeyStatus.RATE_LIMITED]}")
        logger.info(f"   Invalid: {self.stats.by_status[KeyStatus.INVALID]}")
        
        # Token Pool 状态 - 从GitHub客户端获取
        if self.github_client and hasattr(self.github_client, 'token_pool'):
            pool_status = self.github_client.token_pool.get_pool_status()
            # 计算实际使用的配额
            used_quota = pool_status['total_limit'] - pool_status['total_remaining']
            utilization_pct = (used_quota / pool_status['total_limit'] * 100) if pool_status['total_limit'] > 0 else 0

            # 显示美化的状态框
            logger.info("╔" + "═" * 58 + "╗")

            # 状态行
            status_text = (
                f"{pool_status['healthy']} OK, "
                f"{pool_status['limited']} Limited, "
                f"{pool_status['exhausted']} Exhausted"
            )
            status_pad = max(
                0,
                10
                - len(str(pool_status['healthy']))
                - len(str(pool_status['limited']))
                - len(str(pool_status['exhausted']))
            )
            logger.info(f"║ 🎯 Token Status: {status_text}{' ' * status_pad} ║")

            # 配额行（先拼好文本再算长度）
            quota_text = f"{pool_status['total_remaining']}/{pool_status['total_limit']} ({utilization_pct:.1f}% used)"
            quota_pad = max(0, 25 - len(quota_text))
            logger.info(f"║    Quota: {quota_text}{' ' * quota_pad} ║")

            logger.info("╚" + "═" * 58 + "╝")
    
    async def _validate_keys_concurrent(self, keys: List[str]) -> List[Any]:
        """并发验证密钥"""
        # 直接使用批量验证（内部已经优化）
        return self.validator.validate_batch(keys)


async def main():
    """主函数示例"""
    # 初始化协调器
    orchestrator = OrchestratorV2()
    
    # 测试查询
    queries = [
        "AIzaSy in:file",
        "AIzaSy in:file filename:.env",
        "AIzaSy in:file filename:config"
    ]
    
    # 运行
    stats = await orchestrator.run(queries, max_loops=1)
    
    # 显示结果
    print(f"\n✅ Run completed: {stats.run_id}")
    print(f"   Valid keys found: {stats.by_status[KeyStatus.VALID_FREE] + stats.by_status[KeyStatus.VALID_PAID]}")


if __name__ == "__main__":
    import asyncio
    
    # 设置日志
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s | %(levelname)s | %(name)s | %(message)s'
    )
    
    # 运行
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Program interrupted")