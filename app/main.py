"""
Hajimi King - 重构版主入口
模块化架构的应用程序入口点
"""

import sys
import asyncio
import logging
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, Any
import os

# 添加项目根目录到Python路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.core.container import DIContainer, get_container
from app.core.orchestrator import Orchestrator, OrchestrationConfig
from app.core.scanner import Scanner, ScanFilter
from app.core.validator import KeyValidatorFactory
from app.services.config_service import ConfigService
from app.services.interfaces import IConfigService

# 导入模块化功能
try:
    from app.features.feature_manager import get_feature_manager, FeatureManager
    FEATURES_AVAILABLE = True
except ImportError:
    FEATURES_AVAILABLE = False
    print("⚠️  模块化功能不可用，使用基础功能")

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)s | %(name)s | %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

logger = logging.getLogger(__name__)


class Application:
    """
    主应用程序类
    负责初始化和运行整个系统
    """
    
    def __init__(self):
        """初始化应用程序"""
        self.container: Optional[DIContainer] = None
        self.config_service: Optional[IConfigService] = None
        self.orchestrator: Optional[Orchestrator] = None
        self.feature_manager: Optional[FeatureManager] = None
        
    def setup(self) -> None:
        """
        设置应用程序
        配置依赖注入容器和所有服务
        """
        logger.info("=" * 60)
        logger.info("🚀 HAJIMI KING V2.0 - INITIALIZING")
        logger.info("=" * 60)
        
        # 1. 获取DI容器
        self.container = get_container()
        
        # 2. 注册配置服务
        self.config_service = ConfigService()
        self.container.register_singleton(IConfigService, self.config_service)
        
        # 3. 验证配置
        if not self.config_service.validate():
            logger.error("❌ Configuration validation failed")
            sys.exit(1)
        
        # 4. 确保数据目录存在
        self.config_service.ensure_data_dirs()
        
        # 5. 初始化特性管理器（如果可用）
        if FEATURES_AVAILABLE:
            try:
                self.feature_manager = get_feature_manager()
                self.feature_manager.initialize_all_features()
                logger.info("✅ Feature manager initialized")
            except Exception as e:
                logger.error(f"❌ Feature manager initialization failed: {e}")
                self.feature_manager = None
        else:
            logger.info("⏭️  Feature manager not available, skipping initialization")
        
        # 6. 显示配置信息
        self._display_config()
        
        # 7. 设置组件
        self._setup_components()
        
        logger.info("✅ Application setup complete")
        logger.info("=" * 60)
    
    def _display_config(self) -> None:
        """显示配置信息"""
        logger.info("📋 CONFIGURATION:")
        
        tokens = self.config_service.get("GITHUB_TOKENS_LIST", [])
        logger.info(f"  🔑 GitHub tokens: {len(tokens)} configured")
        
        proxies = self.config_service.get("PROXY_LIST", [])
        if proxies:
            logger.info(f"  🌐 Proxies: {len(proxies)} configured")
        else:
            logger.info("  🌐 Proxies: Not configured")
        
        logger.info(f"  📁 Data path: {self.config_service.get('DATA_PATH')}")
        logger.info(f"  📅 Date filter: {self.config_service.get('DATE_RANGE_DAYS')} days")
        logger.info(f"  🤖 Validation model: {self.config_service.get('HAJIMI_CHECK_MODEL')}")
        
        if self.config_service.get("GEMINI_BALANCER_SYNC_ENABLED"):
            logger.info(f"  🔗 Gemini Balancer: Enabled")
        else:
            logger.info(f"  🔗 Gemini Balancer: Disabled")
        
        if self.config_service.get("GPT_LOAD_SYNC_ENABLED"):
            logger.info(f"  🔗 GPT Load: Enabled")
        else:
            logger.info(f"  🔗 GPT Load: Disabled")
    
    def _setup_components(self) -> None:
        """设置核心组件"""
        # 1. 创建扫描过滤器
        scan_filter = ScanFilter(
            date_range_days=self.config_service.get("DATE_RANGE_DAYS", 730),
            file_path_blacklist=self.config_service.get("FILE_PATH_BLACKLIST_LIST", [])
        )
        
        # 2. 创建扫描器
        scanner = Scanner(scan_filter)
        self.container.register_singleton(Scanner, scanner)
        
        # 3. 创建验证器
        validator = KeyValidatorFactory.create(
            "gemini",
            model_name=self.config_service.get("HAJIMI_CHECK_MODEL"),
            proxy_config=self.config_service.get_random_proxy()
        )
        
        # 4. 创建协调器配置
        orchestration_config = OrchestrationConfig(
            max_concurrent_searches=self.config_service.get("MAX_CONCURRENT_SEARCHES", 5),
            max_concurrent_validations=self.config_service.get("MAX_CONCURRENT_VALIDATIONS", 10),
            batch_size=self.config_service.get("BATCH_SIZE", 20),
            checkpoint_interval=self.config_service.get("CHECKPOINT_INTERVAL", 20),
            loop_delay=self.config_service.get("LOOP_DELAY", 10),
            enable_async=True  # 启用异步模式
        )
        
        # 5. 创建协调器
        self.orchestrator = Orchestrator(
            scanner=scanner,
            validator=validator,
            config=orchestration_config
        )
        self.container.register_singleton(Orchestrator, self.orchestrator)
    
    def _load_queries(self) -> list:
        """
        加载搜索查询
        
        Returns:
            查询列表
        """
        queries = []
        queries_file = self.config_service.get_data_path(
            self.config_service.get("QUERIES_FILE", "queries.txt")
        )
        
        if not queries_file.exists():
            # 创建默认查询文件
            self._create_default_queries_file(queries_file)
        
        try:
            with open(queries_file, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#'):
                        queries.append(line)
            
            logger.info(f"📋 Loaded {len(queries)} search queries from {queries_file}")
        except Exception as e:
            logger.error(f"Failed to load queries: {e}")
        
        return queries
    
    def _create_default_queries_file(self, queries_file: Path) -> None:
        """
        创建默认查询文件
        
        Args:
            queries_file: 查询文件路径
        """
        default_content = """# GitHub搜索查询配置文件
# 每行一个查询语句，支持GitHub搜索语法
# 以#开头的行为注释，空行会被忽略

# 基础API密钥搜索
AIzaSy in:file
AIzaSy in:file filename:.env
AIzaSy in:file filename:config
"""
        
        try:
            queries_file.parent.mkdir(parents=True, exist_ok=True)
            with open(queries_file, 'w', encoding='utf-8') as f:
                f.write(default_content)
            logger.info(f"Created default queries file: {queries_file}")
        except Exception as e:
            logger.error(f"Failed to create default queries file: {e}")
    
    async def run(self) -> None:
        """
        运行应用程序主循环
        """
        try:
            # 加载查询
            queries = self._load_queries()
            if not queries:
                logger.error("❌ No queries to process")
                return
            
            # 运行协调器
            stats = await self.orchestrator.run(queries)
            
            # 显示最终统计
            logger.info("=" * 60)
            logger.info("🏁 APPLICATION COMPLETED")
            logger.info(f"  Total time: {stats.elapsed_time:.2f} seconds")
            logger.info(f"  Processing rate: {stats.processing_rate:.2f} items/second")
            logger.info("=" * 60)
            
        except asyncio.CancelledError:
            logger.info("⛔ Application cancelled")
            if self.orchestrator:
                self.orchestrator.stop()
        except KeyboardInterrupt:
            logger.info("⛔ Application interrupted by user")
            if self.orchestrator:
                self.orchestrator.stop()
        except Exception as e:
            logger.error(f"💥 Application error: {e}", exc_info=True)
        finally:
            await self.cleanup()
    
    async def cleanup(self) -> None:
        """清理资源"""
        logger.info("🧹 Cleaning up resources...")
        
        # 清理特性管理器
        if self.feature_manager:
            try:
                self.feature_manager.cleanup_all()
                logger.info("✅ Feature manager cleanup complete")
            except Exception as e:
                logger.error(f"❌ Feature manager cleanup failed: {e}")
        
        # 停止协调器
        if self.orchestrator:
            self.orchestrator.stop()
        
        # 清理容器
        if self.container:
            self.container.clear()
        
        # 在退出前验证所有找到的有效密钥
        await self._validate_keys_on_exit()
        
        logger.info("✅ Cleanup complete")
    
    async def _validate_keys_on_exit(self) -> None:
        """
        在程序退出时验证所有有效密钥
        识别哪些是付费版本
        """
        try:
            from utils.gemini_key_validator import validate_keys_from_file
            from datetime import datetime
            import glob
            
            # 查找今天的有效密钥文件
            date_str = datetime.now().strftime('%Y%m%d')
            valid_keys_pattern = f"data/keys/keys_valid_{date_str}.txt"
            
            files = glob.glob(valid_keys_pattern)
            if not files:
                logger.info("没有找到今天的有效密钥文件，跳过验证")
                return
            
            logger.info("=" * 60)
            logger.info("🔍 程序退出，开始验证所有有效密钥...")
            logger.info("=" * 60)
            
            # 验证每个文件中的密钥
            for file_path in files:
                logger.info(f"📋 验证文件: {file_path}")
                results = await validate_keys_from_file(file_path, concurrency=10)
                
                if results:
                    logger.info("=" * 60)
                    logger.info("📊 验证完成统计:")
                    logger.info(f"   总计验证: {results['total']} 个")
                    logger.info(f"   💎 付费版: {results['paid']} 个")
                    logger.info(f"   🆓 免费版: {results['free']} 个")
                    logger.info(f"   ❌ 无效: {results['invalid']} 个")
                    logger.info(f"   ⏱️ 耗时: {results['elapsed_time']:.2f} 秒")
                    logger.info("=" * 60)
                    
        except Exception as e:
            logger.error(f"验证密钥时出错: {e}")


def main():
    """主函数"""
    # 打印启动横幅
    print("""
    ╔═══════════════════════════════════════════════════════════╗
    ║                                                           ║
    ║     🎪  HAJIMI KING V2.0  🏆                            ║
    ║     Refactored Architecture Edition                      ║
    ║                                                           ║
    ╚═══════════════════════════════════════════════════════════╝
    """)
    
    # 创建并运行应用程序
    app = Application()
    
    try:
        # 设置应用程序
        app.setup()
        
        # 运行主循环
        asyncio.run(app.run())
        
    except KeyboardInterrupt:
        logger.info("\n⛔ Program interrupted by user (Ctrl+C)")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()