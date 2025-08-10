#!/usr/bin/env python3
"""
HAJIMI KING V2.0 - 主程序
集成所有优化组件的生产就绪版本
"""

import asyncio
import logging
import sys
import os
from pathlib import Path
from typing import List, Optional
import signal
from datetime import datetime
import platform
import psutil  # 用于系统资源监控
import multiprocessing

# 添加项目根目录到 Python 路径
sys.path.insert(0, str(Path(__file__).parent.parent))

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

# 设置日志
logger = logging.getLogger(__name__)

# 版本信息
VERSION = "2.0.0"
BUILD_DATE = "2025-01-10"


def print_banner():
    """打印 Spring Boot 风格的启动横幅"""
    # ASCII 艺术字
    ascii_art = """
    ██╗  ██╗ █████╗      ██╗██╗███╗   ███╗██╗    ██╗  ██╗██╗███╗   ██╗ ██████╗ 
    ██║  ██║██╔══██╗     ██║██║████╗ ████║██║    ██║ ██╔╝██║████╗  ██║██╔════╝ 
    ███████║███████║     ██║██║██╔████╔██║██║    █████╔╝ ██║██╔██╗ ██║██║  ███╗
    ██╔══██║██╔══██║██   ██║██║██║╚██╔╝██║██║    ██╔═██╗ ██║██║╚██╗██║██║   ██║
    ██║  ██║██║  ██║╚█████╔╝██║██║ ╚═╝ ██║██║    ██║  ██╗██║██║ ╚████║╚██████╔╝
    ╚═╝  ╚═╝╚═╝  ╚═╝ ╚════╝ ╚═╝╚═╝     ╚═╝╚═╝    ╚═╝  ╚═╝╚═╝╚═╝  ╚═══╝ ╚═════╝ 
    """
    
    # 获取当前时间戳
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    # 获取配置信息
    config = get_config_service()
    environment = config.get("ENVIRONMENT", "development")
    data_path = config.get("DATA_PATH", "./data")
    
    # 构建 banner
    banner = f"""
{ascii_art}
    :: HAJIMI KING :: (v{VERSION})
    
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
    ╚════════════════════════════════════════════════════════════════════════════╝
    """
    
    print(info_table)


def setup_logging():
    """设置日志系统"""
    config = get_config_service()
    
    # 日志级别
    log_level = config.get("LOG_LEVEL", "INFO")
    log_format = config.get("LOG_FORMAT", "text")
    
    # 基础配置
    logging.basicConfig(
        level=getattr(logging, log_level.upper()),
        format='%(asctime)s | %(levelname)s | %(name)s | %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # 设置安全日志（自动脱敏）
    setup_secure_logging()
    
    # 如果启用结构化日志
    if log_format == "json":
        import json
        
        class JSONFormatter(logging.Formatter):
            def format(self, record):
                log_obj = {
                    "timestamp": datetime.utcnow().isoformat(),
                    "level": record.levelname,
                    "logger": record.name,
                    "message": record.getMessage(),
                    "module": record.module,
                    "function": record.funcName,
                    "line": record.lineno
                }
                return json.dumps(log_obj)
        
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
            f.write("# HAJIMI KING V2.0 - 搜索查询配置\n")
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
    
    logger.info("🚀 正在初始化 HAJIMI KING V2.0...")
    
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
            
            # 运行主流程
            logger.info("=" * 80)
            logger.info("🚀 开始执行主流程")
            logger.info("=" * 80)
            
            stats = await orchestrator.run(queries, max_loops=max_loops)
            
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
    ║                          密钥统计                                            ║
    ╠════════════════════════════════════════════════════════════════════════════╣
    ║  有效密钥     : {f"{summary['keys']['valid_total']} 个":<58} ║
    ║    - 免费版   : {f"{summary['keys']['valid_free']} 个":<58} ║
    ║    - 付费版   : {f"{summary['keys']['valid_paid']} 个":<58} ║
    ║  限流密钥     : {f"{summary['keys']['rate_limited']} 个":<58} ║
    ║  无效密钥     : {f"{summary['keys']['invalid']} 个":<58} ║
    ║  错误总数     : {f"{summary['errors']['total']} 个":<58} ║
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
    
    logger.info("👋 感谢使用 HAJIMI KING！")
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
        exit_code = 1
    
    sys.exit(exit_code)


if __name__ == "__main__":
    run()