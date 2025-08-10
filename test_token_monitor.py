#!/usr/bin/env python3
"""
测试Token监控系统
演示Token池的实时监控和动态负载均衡
"""

import asyncio
import sys
from pathlib import Path
from typing import List
import logging

# 添加项目根目录到Python路径
sys.path.insert(0, str(Path(__file__).parent))

from utils.token_monitor import TokenMonitor, TokenPoolOptimizer
from app.services.config_service import get_config_service
from rich.console import Console
from rich.live import Live
from rich.layout import Layout
from rich.panel import Panel
from rich.table import Table
import psutil
import multiprocessing

# 设置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)s | %(name)s | %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)
console = Console()


def get_system_info() -> Panel:
    """获取系统信息面板"""
    cpu_count = multiprocessing.cpu_count()
    cpu_percent = psutil.cpu_percent(interval=0.1)
    memory = psutil.virtual_memory()
    memory_gb = memory.total / (1024**3)
    memory_used_gb = memory.used / (1024**3)
    
    # 网络IO
    net_io = psutil.net_io_counters()
    bytes_sent_mb = net_io.bytes_sent / (1024**2)
    bytes_recv_mb = net_io.bytes_recv / (1024**2)
    
    content = f"""
[bold cyan]系统资源状态[/bold cyan]
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🖥️  CPU: {cpu_count} 核心 | 使用率: {cpu_percent:.1f}%
💾 内存: {memory_gb:.1f} GB | 已用: {memory_used_gb:.1f} GB ({memory.percent:.1f}%)
🌐 网络: 发送 {bytes_sent_mb:.1f} MB | 接收 {bytes_recv_mb:.1f} MB
⚡ 优化建议: {"使用异步处理" if cpu_count >= 4 else "使用线程池"}
    """
    
    return Panel(content.strip(), title="💻 系统资源", border_style="green")


async def simulate_api_requests(monitor: TokenMonitor, optimizer: TokenPoolOptimizer):
    """模拟API请求以展示负载均衡"""
    logger.info("🚀 开始模拟API请求...")
    
    # 模拟100个并发请求
    requests = []
    for i in range(100):
        request = {
            "id": i,
            "type": "search",
            "query": f"test_query_{i}"
        }
        requests.append(optimizer.submit_request(request))
    
    # 等待所有请求完成
    results = await asyncio.gather(*requests, return_exceptions=True)
    
    success_count = sum(1 for r in results if isinstance(r, dict) and r.get("success"))
    logger.info(f"✅ 请求完成: {success_count}/100 成功")


async def main():
    """主函数"""
    console.print("[bold magenta]🎯 HAJIMI KING Token监控系统[/bold magenta]")
    console.print("=" * 80)
    
    # 加载配置
    config = get_config_service()
    tokens = config.get("GITHUB_TOKENS_LIST", [])
    
    if not tokens:
        console.print("[red]❌ 错误: 没有找到GitHub tokens[/red]")
        console.print("请在 data/github_tokens.txt 文件中添加tokens（每行一个）")
        return
    
    console.print(f"[green]✅ 检测到 {len(tokens)} 个GitHub tokens[/green]")
    console.print("正在初始化监控系统...")
    
    # 创建监控器
    monitor = TokenMonitor(tokens)
    await monitor.start()
    
    # 创建优化器
    optimizer = TokenPoolOptimizer(monitor)
    worker_count = min(multiprocessing.cpu_count() * 2, len(tokens))
    await optimizer.start(worker_count)
    
    console.print(f"[green]✅ Token池优化器已启动，{worker_count} 个工作线程[/green]")
    console.print("=" * 80)
    
    # 初始检查
    console.print("[yellow]📊 正在检查所有token的配额状态...[/yellow]")
    await monitor.check_all_tokens()
    
    try:
        # 创建实时显示
        with Live(console=console, refresh_per_second=2, screen=True) as live:
            while True:
                # 创建布局
                layout = Layout()
                
                # 分割布局
                layout.split_column(
                    Layout(get_system_info(), size=8),
                    Layout(monitor.get_summary_panel(), size=10),
                    Layout(monitor.get_status_table())
                )
                
                # 更新显示
                live.update(layout)
                
                # 每5秒检查一次token状态
                await asyncio.sleep(5)
                await monitor.check_all_tokens()
                
    except KeyboardInterrupt:
        console.print("\n[yellow]⌨️ 用户中断，正在清理...[/yellow]")
    finally:
        # 清理资源
        await optimizer.stop()
        await monitor.stop()
        console.print("[green]✅ 清理完成[/green]")


async def demo_mode():
    """演示模式 - 使用模拟数据"""
    console.print("[bold magenta]🎯 Token监控系统 - 演示模式[/bold magenta]")
    console.print("=" * 80)
    
    # 创建模拟tokens
    demo_tokens = [f"ghp_demo_token_{i:02d}" for i in range(17)]
    console.print(f"[green]✅ 创建了 {len(demo_tokens)} 个演示tokens[/green]")
    
    # 创建监控器
    monitor = TokenMonitor(demo_tokens)
    
    # 模拟配额数据
    import random
    for token in demo_tokens:
        quota = monitor.quotas[token]
        quota.limit = 5000
        quota.remaining = random.randint(100, 5000)
        quota.success_rate = random.uniform(0.8, 1.0)
        quota.used = random.randint(0, 1000)
        quota.is_active = random.random() > 0.1  # 90%的token是活跃的
    
    try:
        # 创建实时显示
        with Live(console=console, refresh_per_second=1, screen=True) as live:
            while True:
                # 创建布局
                layout = Layout()
                
                # 分割布局
                layout.split_column(
                    Layout(get_system_info(), size=8),
                    Layout(monitor.get_summary_panel(), size=10),
                    Layout(monitor.get_status_table())
                )
                
                # 更新显示
                live.update(layout)
                
                # 模拟使用（随机更新一些token的状态）
                for _ in range(random.randint(1, 5)):
                    token = random.choice(demo_tokens)
                    quota = monitor.quotas[token]
                    if quota.is_active and quota.remaining > 0:
                        quota.remaining -= 1
                        quota.used += 1
                        # 随机成功或失败
                        success = random.random() > 0.1
                        monitor.update_token_stats(token, success)
                
                await asyncio.sleep(1)
                
    except KeyboardInterrupt:
        console.print("\n[yellow]⌨️ 演示结束[/yellow]")


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Token监控系统测试")
    parser.add_argument("--demo", action="store_true", help="使用演示模式（模拟数据）")
    args = parser.parse_args()
    
    if args.demo:
        # 演示模式
        asyncio.run(demo_mode())
    else:
        # 正常模式
        asyncio.run(main())