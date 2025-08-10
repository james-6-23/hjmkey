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
from utils.github_client import GitHubClient
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
        
        # 初始化安全存储
        self.secure_storage = SecureKeyStorage(
            self.path_manager.current_run_dir,
            allow_plaintext=get_config_service().get("ALLOW_PLAINTEXT", False)
        )
        
        # 初始化扫描器和验证器
        self.scanner = scanner or Scanner()
        self.validator = validator or KeyValidator()
        
        # 初始化 GitHub 客户端和 TokenPool
        self._init_github_client()
        
        # 线程池
        self._executor = ThreadPoolExecutor(max_workers=5)
        
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
            self.token_pool = None
            return
        
        # 创建 TokenPool
        strategy = config_service.get("TOKEN_POOL_STRATEGY", "ADAPTIVE")
        strategy_enum = TokenSelectionStrategy[strategy.upper()]
        self.token_pool = TokenPool(tokens, strategy=strategy_enum)
        
        # 创建增强的 GitHub 客户端（稍后实现）
        self.github_client = GitHubClient(tokens)
        
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
        """处理查询列表"""
        for query in queries:
            if not self.running or self.shutdown_manager.is_shutdown_requested():
                break
            
            # 检查是否已处理
            if self.scanner.should_skip_query(query):
                logger.info(f"⏭️ Skipping processed query: {query}")
                continue
            
            try:
                await self._process_single_query(query)
                self.stats.mark_query_complete(success=True)
            except Exception as e:
                logger.error(f"❌ Query failed: {query} - {e}")
                self.stats.mark_query_complete(success=False)
                self.stats.add_error("query_error", str(e), {"query": query})
    
    async def _process_single_query(self, query: str):
        """处理单个查询"""
        logger.info(f"🔍 Processing query: {query}")
        
        if not self.github_client or not self.token_pool:
            logger.error("❌ GitHub client not initialized")
            return
        
        # 从 TokenPool 获取令牌
        token = self.token_pool.select_token()
        if not token:
            logger.error("❌ No available tokens")
            return
        
        # 使用脱敏日志
        logger.info(f"🔑 Using token: {mask_key(token)}")
        
        # 执行搜索（这里需要修改 GitHubClient 来支持单个 token）
        # 暂时使用原有方式
        start_time = time.time()
        search_result = self.github_client.search_for_keys(query)
        response_time = time.time() - start_time
        
        # 更新 TokenPool 状态
        self.token_pool.update_token_status(token, {
            'status_code': 200 if search_result else 500,
            'headers': {},  # 需要从 GitHubClient 获取
            'response_time': response_time
        })
        
        if not search_result or not search_result.get("items"):
            logger.info(f"📭 No items found for query: {query}")
            return
        
        items = search_result["items"]
        logger.info(f"📦 Found {len(items)} items")
        
        # 转换到验证状态
        self.state_machine.transition_to(OrchestratorState.VALIDATING)
        
        # 处理项目
        for item in items:
            if not self.running or self.shutdown_manager.is_shutdown_requested():
                break
            
            await self._process_item(item)
        
        # 标记查询完成
        self.scanner.filter.add_processed_query(query)
        
        # 转回扫描状态
        self.state_machine.transition_to(OrchestratorState.SCANNING)
    
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
        
        # 验证密钥
        validation_results = self.validator.validate_batch(keys)
        
        for val_result in validation_results:
            # 使用脱敏日志
            masked_key = mask_key(val_result.key)
            
            if val_result.is_valid:
                # 判断是否付费
                is_paid = self._check_if_paid_key(val_result.key)
                status = KeyStatus.VALID_PAID if is_paid else KeyStatus.VALID_FREE
                
                self.stats.mark_key(val_result.key, status)
                logger.info(f"✅ VALID ({status.name}): {masked_key}")
                
            elif val_result.is_rate_limited:
                self.stats.mark_key(val_result.key, KeyStatus.RATE_LIMITED)
                logger.warning(f"⚠️ RATE LIMITED: {masked_key}")
                
            else:
                self.stats.mark_key(val_result.key, KeyStatus.INVALID)
                logger.info(f"❌ INVALID: {masked_key}")
        
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
            checkpoint_data = {
                "label": label,
                "timestamp": datetime.now().isoformat(),
                "run_id": self.run_id,
                "state": self.state_machine.state.name,
                "stats": self.stats.summary(),
                "processed_queries": list(self.scanner.filter.processed_queries),
                "token_pool_status": self.token_pool.get_pool_status() if self.token_pool else None
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
        if self.token_pool:
            pool_status = self.token_pool.get_pool_status()
            self.artifact_manager.save_artifact("token_pool_final.json", pool_status)
    
    def _finalize_run(self):
        """最终化运行"""
        logger.info("📝 Finalizing run...")
        
        # 完成统计
        self.stats.finalize()
        
        # 保存密钥（安全存储）
        keys_by_status = {
            status.name: self.stats.get_keys_list(status)
            for status in KeyStatus
        }
        self.secure_storage.save_keys(keys_by_status)
        self.secure_storage.save_masked_summary(keys_by_status)
        
        # 保存最终报告
        self.artifact_manager.save_final_report(self.stats.summary())
        
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
        if self.token_pool:
            pool_status = self.token_pool.get_pool_status()
            logger.info("📊 TOKEN POOL STATISTICS")
            logger.info(f"Total tokens: {pool_status['total_tokens']}")
            logger.info(f"Healthy/Limited/Exhausted: {pool_status['healthy']}/{pool_status['limited']}/{pool_status['exhausted']}")
            logger.info(f"Utilization: {pool_status['utilization']}")
            logger.info("=" * 60)


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