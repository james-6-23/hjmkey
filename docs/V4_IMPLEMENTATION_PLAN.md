# HAJIMI KING V4.0 实施计划

## 📋 概述

本文档详细说明如何基于稳定的 V2 版本创建全新的 V4 版本，集成所有新的搜索功能，同时保持 V2 版本完全不变。

## 🎯 核心原则

1. **V2 版本保持不变** - 作为当前稳定版本，V2 的所有文件都不会被修改
2. **V4 独立运行** - V4 将有自己的文件体系，不影响 V2 的任何功能
3. **代码复用** - V4 基于 V2 的代码基础，添加新功能
4. **模块化集成** - 新的搜索功能作为独立模块集成

## 📁 文件结构规划

```
app/
├── main_v2.py                    # 保持不变
├── main_v4.py                    # 新建 - V4 主程序
├── core/
│   ├── orchestrator_v2.py        # 保持不变
│   ├── orchestrator_v4.py        # 新建 - 基于 V2 扩展
│   └── ...
└── features/
    └── extended_search/          # 新建目录
        ├── __init__.py
        ├── web_searcher.py
        ├── gitlab_searcher.py
        └── docker_searcher.py

utils/
├── token_hunter/                 # 保持不变
│   ├── github_searcher.py
│   ├── local_searcher.py
│   └── ...
└── token_hunter_v4/             # 新建目录
    ├── __init__.py
    ├── hunter_v4.py             # 扩展的 Hunter
    ├── web_searcher.py
    ├── gitlab_searcher.py
    └── integration.py

docs/
├── V4_IMPLEMENTATION_PLAN.md     # 本文档
├── V4_USER_GUIDE.md             # 新建 - 用户指南
└── V4_API_REFERENCE.md          # 新建 - API 参考
```

## 🚀 实施步骤

### 第一步：创建 V4 主程序文件

#### 1.1 创建 `app/main_v4.py`

```python
#!/usr/bin/env python3
"""
HAJIMI KING V4.0 - 扩展搜索版本
基于 V2 稳定版本，添加了 Web、GitLab、Docker 等多平台搜索功能
"""

import asyncio
import logging
import sys
import os
from pathlib import Path
from typing import List, Optional
import signal
from datetime import datetime, timezone, timedelta
import platform
import psutil
import multiprocessing

# 添加项目根目录到 Python 路径
sys.path.insert(0, str(Path(__file__).parent.parent))

# 定义北京时区
BEIJING_TZ = timezone(timedelta(hours=8))

# 导入配置服务
from app.services.config_service import get_config_service

# 导入核心组件
from app.core.orchestrator_v4 import OrchestratorV4  # 使用 V4 版本
from app.core.scanner import Scanner
from app.core.validator import KeyValidator
from app.features.feature_manager import get_feature_manager

# 导入扩展搜索功能
from utils.token_hunter_v4 import TokenHunterV4
from app.features.extended_search import ExtendedSearchManager

# 导入优化组件
from utils.security_utils import setup_secure_logging, validate_environment
from app.core.graceful_shutdown import get_shutdown_manager
from utils.token_monitor import TokenMonitor, TokenPoolOptimizer

# 设置日志
logger = logging.getLogger(__name__)

# 版本信息
VERSION = "4.0.0"
BUILD_DATE = "2025-01-12"

# ... 复制 V2 的所有函数，但修改版本相关信息 ...

def print_banner():
    """打印 V4 版本的启动横幅"""
    ascii_art = """
    ██╗  ██╗ █████╗      ██╗██╗███╗   ███╗██╗    ██╗  ██╗██╗███╗   ██╗ ██████╗ 
    ██║  ██║██╔══██╗     ██║██║████╗ ████║██║    ██║ ██╔╝██║████╗  ██║██╔════╝ 
    ███████║███████║     ██║██║██╔████╔██║██║    █████╔╝ ██║██╔██╗ ██║██║  ███╗
    ██╔══██║██╔══██║██   ██║██║██║╚██╔╝██║██║    ██╔═██╗ ██║██║╚██╗██║██║   ██║
    ██║  ██║██║  ██║╚█████╔╝██║██║ ╚═╝ ██║██║    ██║  ██╗██║██║ ╚████║╚██████╔╝
    ╚═╝  ╚═╝╚═╝  ╚═╝ ╚════╝ ╚═╝╚═╝     ╚═╝╚═╝    ╚═╝  ╚═╝╚═╝╚═╝  ╚═══╝ ╚═════╝ 
    """
    
    timestamp = datetime.now(BEIJING_TZ).strftime("%Y-%m-%d %H:%M:%S")
    
    banner = f"""
{ascii_art}
    :: HAJIMI KING :: (v{VERSION}) - Extended Search Edition
    
    ╔════════════════════════════════════════════════════════════════════════════╗
    ║                          应用程序启动信息                                    ║
    ╠════════════════════════════════════════════════════════════════════════════╣
    ║  启动时间     : {timestamp:<58} ║
    ║  应用版本     : {VERSION} (Extended Search)<45} ║
    ║  构建日期     : {BUILD_DATE:<58} ║
    ║  Python版本   : {platform.python_version():<58} ║
    ║  操作系统     : {platform.system()} {platform.release():<50} ║
    ║  新增功能     : Web搜索, GitLab搜索, Docker镜像扫描                         ║
    ╚════════════════════════════════════════════════════════════════════════════╝
    """
    
    print(banner)

def print_v4_features():
    """打印 V4 新功能"""
    features_table = """
    ╔════════════════════════════════════════════════════════════════════════════╗
    ║                          V4.0 新增功能                                       ║
    ╠════════════════════════════════════════════════════════════════════════════╣
    ║  🌐 Web平台搜索                                                             ║
    ║     - Stack Overflow 代码片段搜索                                           ║
    ║     - Pastebin 公开内容扫描                                                ║
    ║     - GitHub Gist 密钥发现                                                  ║
    ║                                                                             ║
    ║  🦊 GitLab搜索                                                              ║
    ║     - 公开仓库代码搜索                                                     ║
    ║     - 支持私有GitLab实例                                                    ║
    ║                                                                             ║
    ║  🐳 Docker镜像扫描                                                          ║
    ║     - Docker Hub 公开镜像分析                                               ║
    ║     - 环境变量密钥提取                                                      ║
    ║                                                                             ║
    ║  🔧 增强功能                                                                ║
    ║     - 统一的搜索管理器                                                      ║
    ║     - 批量并发搜索                                                          ║
    ║     - 智能去重和过滤                                                        ║
    ╚════════════════════════════════════════════════════════════════════════════╝
    """
    print(features_table)

async def run_extended_search(config):
    """运行扩展搜索功能"""
    logger.info("🔍 正在初始化扩展搜索功能...")
    
    # 检查是否启用扩展搜索
    if not config.get("EXTENDED_SEARCH_ENABLED", False):
        logger.info("ℹ️ 扩展搜索功能未启用")
        return {}
    
    # 创建扩展搜索管理器
    search_manager = ExtendedSearchManager(config)
    
    # 获取启用的搜索平台
    enabled_platforms = []
    if config.get("WEB_SEARCH_ENABLED", False):
        enabled_platforms.append("web")
    if config.get("GITLAB_SEARCH_ENABLED", False):
        enabled_platforms.append("gitlab")
    if config.get("DOCKER_SEARCH_ENABLED", False):
        enabled_platforms.append("docker")
    
    logger.info(f"✅ 启用的搜索平台: {', '.join(enabled_platforms)}")
    
    # 执行搜索
    results = await search_manager.search_all_platforms(enabled_platforms)
    
    # 显示结果统计
    total_keys = sum(len(keys) for keys in results.values())
    logger.info(f"📊 扩展搜索完成，共找到 {total_keys} 个潜在密钥")
    
    for platform, keys in results.items():
        logger.info(f"   {platform}: {len(keys)} 个密钥")
    
    return results

async def main():
    """主函数 - V4 版本"""
    # 打印启动横幅
    print_banner()
    
    # 打印 V4 新功能
    print_v4_features()
    
    # 设置日志
    setup_logging()
    
    # 打印系统资源信息
    print_system_resources()
    
    # 打印配置信息
    print_config_info()
    
    logger.info("🚀 正在初始化 HAJIMI KING V4.0...")
    
    # 验证环境
    if not validate_environment():
        logger.warning("⚠️ 环境验证存在警告，请检查配置")
    
    # 加载配置
    config = get_config_service()
    
    # 显示启动进度
    logger.info("=" * 80)
    logger.info("📋 启动检查清单:")
    logger.info(f"   ✅ GitHub 令牌: {len(config.get('GITHUB_TOKENS_LIST', []))} 个已配置")
    logger.info(f"   ✅ 令牌池策略: {config.get('TOKEN_POOL_STRATEGY', 'ADAPTIVE')}")
    logger.info(f"   ✅ 数据存储路径: {config.get('DATA_PATH', 'data')}")
    logger.info(f"   ✅ 验证模型: {config.get('VALIDATION_MODEL', 'gemini-2.0-flash-exp')}")
    logger.info(f"   ✅ 扩展搜索: {'启用' if config.get('EXTENDED_SEARCH_ENABLED', False) else '禁用'}")
    logger.info("=" * 80)
    
    # 初始化Token监控器
    token_monitor = await initialize_token_monitor(config)
    
    # 如果有token监控器，创建优化器
    token_optimizer = None
    if token_monitor:
        token_optimizer = TokenPoolOptimizer(token_monitor)
        worker_count = min(multiprocessing.cpu_count() * 2, len(config.get("GITHUB_TOKENS_LIST", [])))
        await token_optimizer.start(worker_count)
        logger.info(f"⚡ Token池优化器已启动，{worker_count} 个工作线程")
    
    # 初始化特性管理器
    feature_manager = get_feature_manager(config.get_all())
    feature_manager.initialize_all_features()
    logger.info("✅ 功能模块初始化完成")
    
    # 运行扩展搜索（如果启用）
    extended_search_results = await run_extended_search(config)
    
    # 加载查询
    queries = load_queries(config)
    
    # 如果有扩展搜索结果，添加到查询中
    if extended_search_results:
        # 将找到的密钥转换为搜索查询
        for platform, keys in extended_search_results.items():
            for key in keys[:10]:  # 每个平台最多添加10个
                queries.append(f"{key[:20]} in:file")
        
        logger.info(f"📋 已加载 {len(queries)} 个搜索查询（包含扩展搜索结果）")
    else:
        logger.info(f"📋 已加载 {len(queries)} 个搜索查询")
    
    # 获取停机管理器
    shutdown_manager = get_shutdown_manager()
    
    try:
        # 使用停机管理器的上下文
        with shutdown_manager.managed_execution():
            # 初始化协调器 V4
            logger.info("🔧 正在初始化协调器 V4...")
            orchestrator = OrchestratorV4()  # 使用 V4 版本
            
            # 设置参数
            max_loops = config.get("MAX_LOOPS", 1)
            if max_loops == "null" or max_loops == "None":
                max_loops = None
            else:
                max_loops = int(max_loops) if max_loops else 1
            
            logger.info(f"🔄 最大循环次数: {max_loops if max_loops else '无限制'}")
            
            # 运行主流程
            logger.info("=" * 80)
            logger.info("🚀 开始执行主流程 (V4 Extended)")
            logger.info("=" * 80)
            
            stats = await orchestrator.run(queries, max_loops=max_loops)
            
            # 显示结果摘要
            summary = stats.summary()
            logger.info("=" * 80)
            logger.info("✅ 处理完成")
            logger.info("=" * 80)
            
            # 结果统计表格（包含扩展搜索统计）
            result_table = f"""
    ╔════════════════════════════════════════════════════════════════════════════╗
    ║                          执行结果统计                                        ║
    ╠════════════════════════════════════════════════════════════════════════════╣
    ║  运行 ID      : {summary['run_id']:<58} ║
    ║  执行时间     : {f"{summary['duration_seconds']:.1f} 秒":<58} ║
    ║  查询进度     : {f"{summary['queries']['completed']}/{summary['queries']['planned']}":<58} ║
    ╠════════════════════════════════════════════════════════════════════════════╣
    ║                          密钥统计                                            ║
    ╠════════════════════════════════════════════════════════════════════════════╣
    ║  有效密钥     : {f"{summary['keys']['valid_total']} 个":<58} ║
    ║    - 免费版   : {f"{summary['keys']['valid_free']} 个":<58} ║
    ║    - 付费版   : {f"{summary['keys']['valid_paid']} 个":<58} ║
    ║  限流密钥     : {f"{summary['keys']['rate_limited']} 个":<58} ║
    ║  无效密钥     : {f"{summary['keys']['invalid']} 个":<58} ║
    ║  错误总数     : {f"{summary['errors']['total']} 个":<58} ║
    ╠════════════════════════════════════════════════════════════════════════════╣
    ║                          扩展搜索统计                                        ║
    ╠════════════════════════════════════════════════════════════════════════════╣
    ║  扩展搜索密钥 : {f"{len(extended_search_results)} 个平台":<58} ║
    ╚════════════════════════════════════════════════════════════════════════════╝
            """
            print(result_table)
            
            # 报告位置
            logger.info("=" * 80)
            logger.info("📁 报告已保存至:")
            logger.info(f"   {orchestrator.path_manager.current_run_dir}")
            logger.info("=" * 80)
            
    except KeyboardInterrupt:
        logger.info("\n⌨️ 用户中断执行")
    except Exception as e:
        logger.error(f"💥 致命错误: {e}", exc_info=True)
        return 1
    finally:
        # 清理资源
        if 'token_optimizer' in locals() and token_optimizer:
            await token_optimizer.stop()
            logger.info("✅ Token优化器已停止")
        
        if 'token_monitor' in locals() and token_monitor:
            await token_monitor.stop()
            logger.info("✅ Token监控器已停止")
        
        # 清理特性管理器
        if 'feature_manager' in locals():
            feature_manager.cleanup_all()
            logger.info("✅ 功能模块清理完成")
    
    logger.info("👋 感谢使用 HAJIMI KING V4！")
    return 0

# ... 复制 V2 的其他函数 ...

if __name__ == "__main__":
    run()
```

### 第二步：创建扩展搜索模块

#### 2.1 创建目录结构

```bash
mkdir -p app/features/extended_search
mkdir -p utils/token_hunter_v4
```

#### 2.2 创建 `app/features/extended_search/__init__.py`

```python
"""
扩展搜索功能模块
提供 Web、GitLab、Docker 等平台的搜索功能
"""

from .manager import ExtendedSearchManager
from .web_searcher import WebSearcher
from .gitlab_searcher import GitLabSearcher
from .docker_searcher import DockerSearcher

__all__ = [
    'ExtendedSearchManager',
    'WebSearcher',
    'GitLabSearcher',
    'DockerSearcher'
]
```

#### 2.3 创建 `app/features/extended_search/manager.py`

```python
"""
扩展搜索管理器
统一管理所有扩展搜索功能
"""

import asyncio
import logging
from typing import Dict, List, Any
from concurrent.futures import ThreadPoolExecutor

from .web_searcher import WebSearcher
from .gitlab_searcher import GitLabSearcher
from .docker_searcher import DockerSearcher

logger = logging.getLogger(__name__)


class ExtendedSearchManager:
    """扩展搜索管理器"""
    
    def __init__(self, config: Dict[str, Any]):
        """
        初始化管理器
        
        Args:
            config: 配置字典
        """
        self.config = config
        self.executor = ThreadPoolExecutor(max_workers=10)
        
        # 初始化搜索器
        proxy = self._get_proxy_config()
        
        self.web_searcher = WebSearcher(proxy=proxy)
        self.gitlab_searcher = GitLabSearcher(
            access_token=config.get("GITLAB_ACCESS_TOKEN"),
            proxy=proxy
        )
        self.docker_searcher = DockerSearcher()
        
        logger.info("✅ 扩展搜索管理器初始化完成")
    
    def _get_proxy_config(self) -> Dict[str, str]:
        """获取代理配置"""
        proxy_str = self.config.get("PROXY", "")
        if proxy_str:
            return {
                'http': proxy_str,
                'https': proxy_str
            }
        return None
    
    async def search_all_platforms(self, platforms: List[str]) -> Dict[str, List[str]]:
        """
        搜索所有指定平台
        
        Args:
            platforms: 平台列表 ['web', 'gitlab', 'docker']
            
        Returns:
            搜索结果字典
        """
        results = {}
        tasks = []
        
        if 'web' in platforms:
            tasks.append(self._search_web())
        
        if 'gitlab' in platforms:
            tasks.append(self._search_gitlab())
        
        if 'docker' in platforms:
            tasks.append(self._search_docker())
        
        # 并发执行所有搜索
        if tasks:
            search_results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # 处理结果
            platform_names = []
            if 'web' in platforms:
                platform_names.append('web')
            if 'gitlab' in platforms:
                platform_names.append('gitlab')
            if 'docker' in platforms:
                platform_names.append('docker')
            
            for i, result in enumerate(search_results):
                if isinstance(result, Exception):
                    logger.error(f"搜索 {platform_names[i]} 失败: {result}")
                    results[platform_names[i]] = []
                else:
                    results[platform_names[i]] = result
        
        return results
    
    async def _search_web(self) -> List[str]:
        """搜索Web平台"""
        loop = asyncio.get_event_loop()
        
        # 在线程池中执行同步搜索
        web_results = await loop.run_in_executor(
            self.executor,
            self.web_searcher.search_all_platforms,
            20  # max_results_per_platform
        )
        
        # 合并所有平台的结果
        all_tokens = []
        for platform, tokens in web_results.items():
            all_tokens.extend(tokens)
        
        return all_tokens
    
    async def _search_gitlab(self) -> List[str]:
        """搜索GitLab"""
        loop = asyncio.get_event_loop()
        
        return await loop.run_in_executor(
            self.executor,
            self.gitlab_searcher.search,
            "AIzaSy",  # query
            50  # max_results
        )
    
    async def _search_docker(self) -> List[str]:
        """搜索Docker镜像"""
        loop = asyncio.get_event_loop()
        
        # 搜索热门镜像
        popular_images = [
            "node:latest",
            "python:latest",
            "nginx:latest",
            "mysql:latest",
            "redis:latest"
        ]
        
        all_tokens = []
        for image in popular_images:
            try:
                tokens = await loop.run_in_executor(
                    self.executor,
                    self.docker_searcher.search_image,
                    image
                )
                all_tokens.extend(tokens)
            except Exception as e:
                logger.error(f"搜索Docker镜像 {image} 失败: {e}")
        
        return all_tokens
    
    def cleanup(self):
        """清理资源"""
        self.executor.shutdown(wait=False)
```

### 第三步：创建协调器 V4

#### 3.1 创建 `app/core/orchestrator_v4.py`

```python
"""
协调器 V4 - 扩展搜索版本
基于 V2 协调器，添加了扩展搜索功能的集成
"""

# 复制 orchestrator_v2.py 的所有内容
# 然后添加以下修改：

from app.core.orchestrator_v2 import OrchestratorV2
from app.features.extended_search import ExtendedSearchManager

class OrchestratorV4(OrchestratorV2):
    """
    协调器 V4 - 继承自 V2，添加扩展搜索功能
    """
    
    def __init__(self):
        """初始化 V4 协调器"""
        super().__init__()
        
        # 版本信息
        self.version = "4.0.0"
        
        # 扩展搜索管理器
        self.extended_search_manager = None
        
        logger.info("✅ Orchestrator V4 initialized with extended search support")
    
    async def run(self, queries: List[str], max_loops: Optional[int] = None) -> RunStats:
        """
        运行主协调流程（V4 版本）
        
        Args:
            queries: 搜索查询列表
            max_loops: 最大循环次数
            
        Returns:
            运行统计
        """
        # 初始化扩展搜索（如果启用）
        config = get_config_service()
        if config.get("EXTENDED_SEARCH_ENABLED", False):
            self.extended_search_manager = ExtendedSearchManager(config.get_all())
            
            # 执行预搜索
            logger.info("🔍 执行扩展平台预搜索...")
            extended_results = await self.extended_search_manager.search_all_platforms(
                ['web', 'gitlab', 'docker']
            )
            
            # 将结果添加到统计
            for platform, tokens in extended_results.items():
                self.stats.add_extended_search_results(platform, len(tokens))
        
        # 调用父类的 run 方法
        return await super().run(queries, max_loops)
    
    def _cleanup_resources(self):
        """清理资源（V4 版本）"""
        super()._cleanup_resources()
        
        # 清理扩展搜索管理器
        if self.extended_search_manager:
            self.extended_search_manager.cleanup()
            logger.info("✅ Extended search manager cleaned up")
```

### 第四步：创建 Token Hunter V4

#### 4.1 创建 `utils/token_hunter_v4/__init__.py`

```python
"""
Token Hunter V4 - 扩展版本
支持 Web、GitLab、Docker 等平台搜索
"""

from .hunter_v4 import TokenHunterV4
from .web_searcher import WebSearcher
from .gitlab_searcher import GitLabSearcher
from .docker_searcher import DockerSearcher

# 导入原始版本的组件
from utils.token_hunter import (
    TokenManager,
    TokenValidator,
    TokenValidationResult,
    NoValidTokenError,
    NoQuotaError
)

__all__ = [
    'TokenHunterV4',
    'WebSearcher',
    'GitLabSearcher',
    'DockerSearcher',
    'TokenManager',
    'TokenValidator',
    'TokenValidationResult',
    'NoValidTokenError',
    'NoQuotaError'
]
```

#### 4.2 创建 `utils/token_hunter_v4/hunter_v4.py`

```python
"""
Token Hunter V4 主模块
扩展了原始 TokenHunter，添加了更多搜索平台
"""

from typing import Dict, Any, List, Optional
import logging

# 导入原始 TokenHunter
from utils.token_hunter.hunter import TokenHunter

# 导入新的搜索器
from .web_searcher import WebSearcher
from .gitlab_searcher import GitLabSearcher
from .docker_searcher import DockerSearcher

logger = logging.getLogger(__name__)


class TokenHunterV4(TokenHunter):
    """
    Token Hunter V4 - 扩展版本
    """
    
    def __init__(
        self,
        github_token: Optional[str] = None,
        proxy: Optional[Dict[str, str]] = None,
        tokens_file: str = "data/github_tokens.txt",
        auto_save: bool = True
    ):
        """
        初始化 Token Hunter V4
        
        继承原始 TokenHunter 的所有功能，并添加新的搜索器
        """
        super().__init__(github_token, proxy, tokens_file, auto_save)
        
        # 添加新的搜索器
        self.web_searcher = WebSearcher(proxy)
        self.gitlab_searcher = GitLabSearcher(proxy=proxy)
        self.docker_searcher = DockerSearcher()
        
        logger.info("🎯 Token Hunter V4 初始化完成 - 支持扩展搜索")
    
    def hunt_tokens(
        self,
        mode: str = 'all',
        validate: bool = True,
        max_results: int = 100
    ) -> Dict[str, Any]:
        """
        搜索tokens（V4 版本）
        
        支持的模式：
        - 'github': GitHub搜索
        - 'local': 本地搜索
        - 'web': Web平台搜索
        - 'gitlab': GitLab搜索
        - 'docker': Docker镜像搜索
        - 'extended': 所有扩展搜索（web + gitlab + docker）
        - 'all': 所有搜索
        
        Args:
            mode: 搜索模式
            validate: 是否