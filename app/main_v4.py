#!/usr/bin/env python3
"""
HAJIMI KING V4.0 - 主程序
集成扩展搜索功能的增强版本
"""

import asyncio
import logging
import sys
import os
from pathlib import Path
from typing import List, Optional, Dict, Any
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
from app.core.orchestrator_v2 import OrchestratorV2
from app.core.scanner import Scanner
from app.core.validator import KeyValidator
from app.features.feature_manager import get_feature_manager

# 导入优化组件
from utils.security_utils import setup_secure_logging, validate_environment
from app.core.graceful_shutdown import get_shutdown_manager
from utils.token_monitor import TokenMonitor, TokenPoolOptimizer

# 导入 V4 特有组件
from app.features.extended_search.manager import ExtendedSearchManager
from utils.token_hunter_v4.hunter_v4 import TokenHunterV4

# 设置日志
logger = logging.getLogger(__name__)

# 版本信息
VERSION = "4.0.0"
BUILD_DATE = "2025-01-12"


def print_banner():
    """打印 Spring Boot 风格的启动横幅"""
    # ASCII 艺术字 - V4 版本
    ascii_art = """
    ██╗  ██╗ █████╗      ██╗██╗███╗   ███╗██╗    ██╗  ██╗██╗███╗   ██╗ ██████╗     ██╗   ██╗██╗  ██╗
    ██║  ██║██╔══██╗     ██║██║████╗ ████║██║    ██║ ██╔╝██║████╗  ██║██╔════╝     ██║   ██║██║  ██║
    ███████║███████║     ██║██║██╔████╔██║██║    █████╔╝ ██║██╔██╗ ██║██║  ███╗    ██║   ██║███████║
    ██╔══██║██╔══██║██   ██║██║██║╚██╔╝██║██║    ██╔═██╗ ██║██║╚██╗██║██║   ██║    ╚██╗ ██╔╝╚════██║
    ██║  ██║██║  ██║╚█████╔╝██║██║ ╚═╝ ██║██║    ██║  ██╗██║██║ ╚████║╚██████╔╝     ╚████╔╝      ██║
    ╚═╝  ╚═╝╚═╝  ╚═╝ ╚════╝ ╚═╝╚═╝     ╚═╝╚═╝    ╚═╝  ╚═╝╚═╝╚═╝  ╚═══╝ ╚═════╝       ╚═══╝       ╚═╝
    """
    
    # 获取当前时间戳（北京时间）
    timestamp = datetime.now(BEIJING_TZ).strftime("%Y-%m-%d %H:%M:%S")
    
    # 获取配置信息
    config = get_config_service()
    environment = config.get("ENVIRONMENT", "development")
    
    # 构建 banner
    banner = f"""
{ascii_art}
    :: HAJIMI KING :: (v{VERSION}) - Extended Search Edition
    
    ╔════════════════════════════════════════════════════════════════════════════╗
    ║                          应用程序启动信息                                    ║
    ╠════════════════════════════════════════════════════════════════════════════╣
    ║  启动时间     : {timestamp:<58} ║
    ║  应用版本     : {VERSION:<58} ║
    ║  构建日期     : {BUILD_DATE:<58} ║
    ║  Python版本   : {platform.python_version():<58} ║
    ║  操作系统     : {platform.system()} {platform.release():<50} ║
    ╚════════════════════════════════════════════════════════════════════════════╝
    """
    
    print(banner)


def print_system_resources():
    """打印系统资源信息"""
    # 获取系统资源信息
    cpu_count = multiprocessing.cpu_count()
    cpu_percent = psutil.cpu_percent(interval=1)
    memory = psutil.virtual_memory()
    memory_gb = memory.total / (1024**3)
    memory_used_gb = memory.used / (1024**3)
    memory_percent = memory.percent
    
    # 检查网络连接
    net_io = psutil.net_io_counters()
    net_speed = "高速" if net_io.bytes_sent + net_io.bytes_recv > 1000000 else "正常"
    
    # GPU信息（如果可用）
    gpu_status = "未检测到"
    try:
        import GPUtil
        gpus = GPUtil.getGPUs()
        if gpus:
            gpu_status = f"{len(gpus)} 个GPU可用"
    except:
        pass
    
    resource_table = f"""
    ╔════════════════════════════════════════════════════════════════════════════╗
    ║                          系统资源状态                                        ║
    ╠════════════════════════════════════════════════════════════════════════════╣
    ║  CPU核心数    : {f"{cpu_count} 核":<58} ║
    ║  CPU使用率    : {f"{cpu_percent:.1f}%":<58} ║
    ║  内存容量     : {f"{memory_gb:.1f} GB (已用 {memory_used_gb:.1f} GB, {memory_percent:.1f}%)":<58} ║
    ║  GPU状态      : {gpu_status:<58} ║
    ║  网络带宽     : {net_speed:<58} ║
    ╚════════════════════════════════════════════════════════════════════════════╝
    """
    print(resource_table)


def print_config_info():
    """打印配置信息表格"""
    config = get_config_service()
    
    # 获取配置值
    environment = config.get("ENVIRONMENT", "development")
    github_tokens = len(config.get("GITHUB_TOKENS_LIST", []))
    token_strategy = config.get("TOKEN_POOL_STRATEGY", "ADAPTIVE")
    data_path = config.get("DATA_PATH", "./data")
    database_enabled = "启用" if config.get("ENABLE_DATABASE", True) else "禁用"
    database_type = config.get("DATABASE_TYPE", "sqlite")
    async_enabled = "启用" if config.get("ENABLE_ASYNC", True) else "禁用"
    monitoring = "启用" if config.get("ENABLE_MONITORING", False) else "禁用"
    validation_model = config.get("VALIDATION_MODEL", "gemini-2.0-flash-exp")
    plaintext = "允许" if config.get("ALLOW_PLAINTEXT", True) else "加密"
    
    # V4 特有配置
    extended_search = "启用" if config.get("ENABLE_EXTENDED_SEARCH", True) else "禁用"
    web_search = "启用" if config.get("ENABLE_WEB_SEARCH", True) else "禁用"
    gitlab_search = "启用" if config.get("ENABLE_GITLAB_SEARCH", True) else "禁用"
    docker_search = "启用" if config.get("ENABLE_DOCKER_SEARCH", True) else "禁用"
    
    # 端口信息
    metrics_port = config.get("METRICS_PORT", 9090) if config.get("ENABLE_MONITORING", False) else "N/A"
    
    info_table = f"""
    ╔════════════════════════════════════════════════════════════════════════════╗
    ║                          核心配置信息                                        ║
    ╠════════════════════════════════════════════════════════════════════════════╣
    ║  运行环境     : {environment:<58} ║
    ║  数据目录     : {data_path:<58} ║
    ║  GitHub令牌   : {f"{github_tokens} 个已配置":<58} ║
    ║  令牌策略     : {token_strategy:<58} ║
    ║  验证模型     : {validation_model:<58} ║
    ║  密钥存储     : {plaintext:<58} ║
    ╠════════════════════════════════════════════════════════════════════════════╣
    ║                          功能状态                                            ║
    ╠════════════════════════════════════════════════════════════════════════════╣
    ║  数据库       : {f"{database_enabled} ({database_type})":<58} ║
    ║  异步处理     : {async_enabled:<58} ║
    ║  系统监控     : {monitoring:<58} ║
    ║  监控端口     : {str(metrics_port):<58} ║
    ╠════════════════════════════════════════════════════════════════════════════╣
    ║                          V4 扩展功能                                         ║
    ╠════════════════════════════════════════════════════════════════════════════╣
    ║  扩展搜索     : {extended_search:<58} ║
    ║  Web搜索      : {web_search:<58} ║
    ║  GitLab搜索   : {gitlab_search:<58} ║
    ║  Docker搜索   : {docker_search:<58} ║
    ╚════════════════════════════════════════════════════════════════════════════╝
    """
    
    print(info_table)


def setup_logging():
    """设置日志系统"""
    config = get_config_service()
    
    # 日志级别
    log_level = config.get("LOG_LEVEL", "INFO")
    log_format = config.get("LOG_FORMAT", "text")
    
    # 自定义格式化器，使用北京时间
    class BeijingFormatter(logging.Formatter):
        def formatTime(self, record, datefmt=None):
            # 转换为北京时间
            dt = datetime.fromtimestamp(record.created, BEIJING_TZ)
            if datefmt:
                return dt.strftime(datefmt)
            else:
                return dt.strftime('%Y-%m-%d %H:%M:%S')
    
    # 基础配置
    logging.basicConfig(
        level=getattr(logging, log_level.upper()),
        format='%(asctime)s | %(levelname)s | %(name)s | %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # 应用北京时间格式化器到所有处理器
    formatter = BeijingFormatter(
        '%(asctime)s | %(levelname)s | %(name)s | %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    for handler in logging.root.handlers:
        handler.setFormatter(formatter)
    
    # 设置安全日志（自动脱敏）
    setup_secure_logging()
    
    # 如果启用结构化日志
    if log_format == "json":
        import json
        
        class JSONFormatter(logging.Formatter):
            def format(self, record):
                # 使用北京时间
                beijing_time = datetime.now(BEIJING_TZ)
                log_obj = {
                    "timestamp": beijing_time.isoformat(),
                    "level": record.levelname,
                    "logger": record.name,
                    "message": record.getMessage(),
                    "module": record.module,
                    "function": record.funcName,
                    "line": record.lineno
                }
                return json.dumps(log_obj, ensure_ascii=False)
        
        # 应用到所有处理器
        for handler in logging.root.handlers:
            handler.setFormatter(JSONFormatter())


def load_queries(config) -> List[str]:
    """
    加载搜索查询
    
    Args:
        config: 配置服务
        
    Returns:
        查询列表
    """
    queries = []
    
    # 从配置文件加载
    default_queries = config.get("DEFAULT_QUERIES", "")
    if default_queries:
        queries.extend([q.strip() for q in default_queries.split("\n") if q.strip()])
    
    # 从查询文件加载
    queries_file = Path(config.get("DATA_PATH", "data")) / "queries.txt"
    if queries_file.exists():
        with open(queries_file, 'r', encoding='utf-8') as f:
            file_queries = [line.strip() for line in f if line.strip() and not line.startswith('#')]
            queries.extend(file_queries)
    
    # 如果没有查询，使用默认
    if not queries:
        logger.info("📝 未找到查询配置，使用默认查询")
        queries = [
            "AIzaSy in:file",
            "AIzaSy in:file filename:.env",
            "AIzaSy in:file filename:config"
        ]
        
        # 保存默认查询到文件
        queries_file.parent.mkdir(parents=True, exist_ok=True)
        with open(queries_file, 'w', encoding='utf-8') as f:
            f.write("# HAJIMI KING V4.0 - 搜索查询配置\n")
            f.write("# 每行一个查询，以 # 开头的行将被忽略\n\n")
            for query in queries:
                f.write(f"{query}\n")
        logger.info(f"💾 已创建默认查询文件: {queries_file}")
    
    return queries


async def initialize_token_monitor(config) -> Optional[TokenMonitor]:
    """
    初始化Token监控器
    
    Args:
        config: 配置服务
        
    Returns:
        TokenMonitor实例或None
    """
    tokens = config.get("GITHUB_TOKENS_LIST", [])
    if not tokens:
        logger.warning("⚠️ 没有配置GitHub tokens，跳过token监控")
        return None
    
    logger.info(f"🔍 正在初始化Token监控器，共 {len(tokens)} 个token...")
    
    # 创建监控器
    monitor = TokenMonitor(tokens)
    await monitor.start()
    
    # 检查所有token
    logger.info("📊 正在检查所有token的配额状态...")
    await monitor.check_all_tokens()
    
    # 显示初始状态
    from rich.console import Console
    console = Console()
    console.print(monitor.get_summary_panel())
    console.print(monitor.get_status_table())
    
    return monitor


async def initialize_extended_search(config) -> Optional[ExtendedSearchManager]:
    """
    初始化扩展搜索管理器
    
    Args:
        config: 配置服务
        
    Returns:
        ExtendedSearchManager实例或None
    """
    if not config.get("ENABLE_EXTENDED_SEARCH", True):
        logger.info("ℹ️ 扩展搜索功能已禁用")
        return None
    
    logger.info("🔍 正在初始化扩展搜索管理器...")
    
    # 创建管理器
    manager = ExtendedSearchManager()
    
    # 初始化各个搜索器
    initialized_count = 0
    
    if config.get("ENABLE_WEB_SEARCH", True):
        await manager.initialize_searcher("web")
        initialized_count += 1
        logger.info("   ✅ Web搜索器已初始化")
    
    if config.get("ENABLE_GITLAB_SEARCH", True):
        await manager.initialize_searcher("gitlab")
        initialized_count += 1
        logger.info("   ✅ GitLab搜索器已初始化")
    
    if config.get("ENABLE_DOCKER_SEARCH", True):
        await manager.initialize_searcher("docker")
        initialized_count += 1
        logger.info("   ✅ Docker搜索器已初始化")
    
    logger.info(f"✅ 扩展搜索管理器初始化完成，共 {initialized_count} 个搜索器")
    
    return manager


async def run_v4_search(queries: List[str], extended_search_manager: ExtendedSearchManager) -> Dict[str, Any]:
    """
    运行 V4 扩展搜索
    
    Args:
        queries: 查询列表
        extended_search_manager: 扩展搜索管理器
        
    Returns:
        搜索结果统计
    """
    logger.info("=" * 80)
    logger.info("🚀 开始执行 V4 扩展搜索")
    logger.info("=" * 80)
    
    # 创建 TokenHunterV4 实例
    hunter = TokenHunterV4(extended_search_manager)
    
    # 执行搜索
    results = await hunter.hunt_tokens(queries)
    
    # 统计结果
    stats = {
        "total_results": 0,
        "by_source": {},
        "by_type": {},
        "valid_keys": 0,
        "invalid_keys": 0
    }
    
    for result in results:
        stats["total_results"] += 1
        
        # 按来源统计
        source = result.get("source", "unknown")
        stats["by_source"][source] = stats["by_source"].get(source, 0) + 1
        
        # 按类型统计
        key_type = result.get("key_type", "unknown")
        stats["by_type"][key_type] = stats["by_type"].get(key_type, 0) + 1
        
        # 有效性统计
        if result.get("is_valid", False):
            stats["valid_keys"] += 1
        else:
            stats["invalid_keys"] += 1
    
    # 显示结果统计
    logger.info("=" * 80)
    logger.info("📊 V4 扩展搜索结果统计:")
    logger.info(f"   总结果数: {stats['total_results']}")
    logger.info(f"   有效密钥: {stats['valid_keys']}")
    logger.info(f"   无效密钥: {stats['invalid_keys']}")
    logger.info("   按来源分布:")
    for source, count in stats["by_source"].items():
        logger.info(f"     - {source}: {count}")
    logger.info("   按类型分布:")
    for key_type, count in stats["by_type"].items():
        logger.info(f"     - {key_type}: {count}")
    logger.info("=" * 80)
    
    return stats


async def main():
    """主函数"""
    # 打印启动横幅
    print_banner()
    
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
    logger.info(f"   ✅ 密钥存储模式: {'明文' if config.get('ALLOW_PLAINTEXT', True) else '加密'}")
    logger.info(f"   ✅ 异步模式: {'启用' if config.get('ENABLE_ASYNC', True) else '禁用'}")
    logger.info(f"   ✅ 扩展搜索: {'启用' if config.get('ENABLE_EXTENDED_SEARCH', True) else '禁用'}")
    logger.info("=" * 80)
    
    # 初始化Token监控器
    token_monitor = await initialize_token_monitor(config)
    
    # 如果有token监控器，创建优化器
    token_optimizer = None
    if token_monitor:
        token_optimizer = TokenPoolOptimizer(token_monitor)
        # 根据CPU核心数设置工作线程数
        worker_count = min(multiprocessing.cpu_count() * 2, len(config.get("GITHUB_TOKENS_LIST", [])))
        await token_optimizer.start(worker_count)
        logger.info(f"⚡ Token池优化器已启动，{worker_count} 个工作线程")
    
    # 初始化特性管理器
    feature_manager = get_feature_manager(config.get_all())
    feature_manager.initialize_all_features()
    logger.info("✅ 功能模块初始化完成")
    
    # 初始化扩展搜索管理器
    extended_search_manager = await initialize_extended_search(config)
    
    # 加载查询
    queries = load_queries(config)
    logger.info(f"📋 已加载 {len(queries)} 个搜索查询")
    for i, query in enumerate(queries[:5], 1):  # 显示前5个
        logger.info(f"   {i}. {query[:50]}{'...' if len(query) > 50 else ''}")
    if len(queries) > 5:
        logger.info(f"   ... 以及其他 {len(queries) - 5} 个查询")
    
    # 获取停机管理器
    shutdown_manager = get_shutdown_manager()
    
    try:
        # 使用停机管理器的上下文
        with shutdown_manager.managed_execution():
            # 初始化协调器
            logger.info("🔧 正在初始化协调器...")
            orchestrator = OrchestratorV2()
            
            # 设置参数
            max_loops = config.get("MAX_LOOPS", 1)
            if max_loops == "null" or max_loops == "None":
                max_loops = None
            else:
                max_loops = int(max_loops) if max_loops else 1
            
            logger.info(f"🔄 最大循环次数: {max_loops if max_loops else '无限制'}")
            
            # 运行主流程（GitHub搜索）
            logger.info("=" * 80)
            logger.info("🚀 开始执行主流程（GitHub搜索）")
            logger.info("=" * 80)
            
            stats = await orchestrator.run(queries, max_loops=max_loops)
            
            # 如果启用了扩展搜索，运行 V4 搜索
            v4_stats = None
            if extended_search_manager:
                v4_stats = await run_v4_search(queries, extended_search_manager)
            
            # 显示结果摘要
            summary = stats.summary()
            logger.info("=" * 80)
            logger.info("✅ 处理完成")
            logger.info("=" * 80)
            
            # 结果统计表格
            result_table = f"""
    ╔════════════════════════════════════════════════════════════════════════════╗
    ║                          执行结果统计                                        ║
    ╠════════════════════════════════════════════════════════════════════════════╣
    ║  运行 ID      : {summary['run_id']:<58} ║
    ║  执行时间     : {f"{summary['duration_seconds']:.1f} 秒":<58} ║
    ║  查询进度     : {f"{summary['queries']['completed']}/{summary['queries']['planned']}":<58} ║
    ╠════════════════════════════════════════════════════════════════════════════╣
    ║                          GitHub 密钥统计                                     ║
    ╠════════════════════════════════════════════════════════════════════════════╣
    ║  有效密钥     : {f"{summary['keys']['valid_total']} 个":<58} ║
    ║    - 免费版   : {f"{summary['keys']['valid_free']} 个":<58} ║
    ║    - 付费版   : {f"{summary['keys']['valid_paid']} 个":<58} ║
    ║  限流密钥     : {f"{summary['keys']['rate_limited']} 个":<58} ║
    ║  无效密钥     : {f"{summary['keys']['invalid']} 个":<58} ║
    ║  错误总数     : {f"{summary['errors']['total']} 个":<58} ║"""
            
            # 如果有 V4 统计，添加到表格
            if v4_stats:
                result_table += f"""
    ╠════════════════════════════════════════════════════════════════════════════╣
    ║                          扩展搜索统计                                        ║
    ╠════════════════════════════════════════════════════════════════════════════╣
    ║  总结果数     : {f"{v4_stats['total_results']} 个":<58} ║
    ║  有效密钥     : {f"{v4_stats['valid_keys']} 个":<58} ║
    ║  无效密钥     : {f"{v4_stats['invalid_keys']} 个":<58} ║"""
            
            result_table += """
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
        if 'extended_search_manager' in locals() and extended_search_manager:
            await extended_search_manager.cleanup()
            logger.info("✅ 扩展搜索管理器已清理")
        
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


def signal_handler(signum, frame):
    """信号处理器"""
    signal_name = signal.Signals(signum).name
    logger.info(f"\n📡 接收到信号: {signal_name}")
    
    # 请求优雅停机
    shutdown_manager = get_shutdown_manager()
    shutdown_manager.request_shutdown(f"Signal {signal_name}")
    
    # 给一些时间完成停机
    import time
    time.sleep(2)
    
    # 如果还没停止，强制退出
    if not shutdown_manager._shutdown_complete.is_set():
        logger.warning("⚠️ 强制退出...")
        sys.exit(1)


def run():
    """运行入口"""
    # 注册信号处理器
    if sys.platform != "win32":
        signal.signal(signal.SIGTERM, signal_handler)
        signal.signal(signal.SIGHUP, signal_handler)
    signal.signal(signal.SIGINT, signal_handler)
    
    # 运行主程序
    try:
        exit_code = asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("\n⌨️ 程序被中断")
        exit_code = 130  # 标准的 Ctrl+C 退出码
    except Exception as e:
        logger.error(f"💥 未处理的异常: {e}", exc_info=True)
        