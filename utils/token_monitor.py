"""
GitHub Token 监控和管理系统
实时监控token配额状态，动态分配请求负载
"""

import asyncio
import aiohttp
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any, Tuple
import logging
from dataclasses import dataclass, field
from collections import defaultdict
import time
from rich.console import Console
from rich.table import Table
from rich.live import Live
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn
from rich.panel import Panel
from rich.layout import Layout
from rich.align import Align
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
import heapq

logger = logging.getLogger(__name__)
console = Console()


@dataclass
class TokenQuota:
    """Token配额信息"""
    token: str
    alias: str  # token别名或标识符
    limit: int = 5000  # 配额上限
    remaining: int = 5000  # 剩余请求次数
    reset_time: datetime = field(default_factory=lambda: datetime.now(timezone.utc))  # 重置时间
    used: int = 0  # 已使用次数
    success_rate: float = 1.0  # 成功率
    last_check: datetime = field(default_factory=lambda: datetime.now(timezone.utc))  # 最后检查时间
    is_active: bool = True  # 是否可用
    error_count: int = 0  # 错误计数
    
    @property
    def usage_percent(self) -> float:
        """使用率百分比"""
        if self.limit == 0:
            return 0
        return ((self.limit - self.remaining) / self.limit) * 100
    
    @property
    def health_score(self) -> float:
        """健康评分（0-100）"""
        # 基于剩余配额、成功率和错误计数计算
        quota_score = (self.remaining / max(self.limit, 1)) * 50
        success_score = self.success_rate * 30
        error_penalty = min(self.error_count * 5, 20)
        return max(0, quota_score + success_score - error_penalty)
    
    @property
    def reset_in_seconds(self) -> int:
        """距离重置还有多少秒"""
        now = datetime.now(timezone.utc)
        if self.reset_time > now:
            return int((self.reset_time - now).total_seconds())
        return 0
    
    def format_reset_time(self) -> str:
        """格式化重置时间"""
        seconds = self.reset_in_seconds
        if seconds <= 0:
            return "已重置"
        
        hours = seconds // 3600
        minutes = (seconds % 3600) // 60
        secs = seconds % 60
        
        if hours > 0:
            return f"{hours}小时{minutes}分钟"
        elif minutes > 0:
            return f"{minutes}分钟{secs}秒"
        else:
            return f"{secs}秒"


class TokenMonitor:
    """Token监控器"""
    
    def __init__(self, tokens: List[str]):
        """
        初始化Token监控器
        
        Args:
            tokens: GitHub token列表
        """
        self.tokens = tokens
        self.quotas: Dict[str, TokenQuota] = {}
        self.session: Optional[aiohttp.ClientSession] = None
        self.monitoring = False
        self.monitor_task: Optional[asyncio.Task] = None
        self._lock = asyncio.Lock()
        
        # 初始化每个token的配额信息
        for i, token in enumerate(tokens):
            alias = f"Token-{i+1:02d}"
            self.quotas[token] = TokenQuota(token=token, alias=alias)
    
    async def start(self):
        """启动监控"""
        if not self.session:
            self.session = aiohttp.ClientSession()
        
        # 初始检查所有token
        await self.check_all_tokens()
        
        # 启动监控任务
        self.monitoring = True
        self.monitor_task = asyncio.create_task(self._monitor_loop())
        
        logger.info(f"✅ Token监控器已启动，监控 {len(self.tokens)} 个token")
    
    async def stop(self):
        """停止监控"""
        self.monitoring = False
        
        if self.monitor_task:
            self.monitor_task.cancel()
            try:
                await self.monitor_task
            except asyncio.CancelledError:
                pass
        
        if self.session:
            await self.session.close()
            self.session = None
        
        logger.info("⏹️ Token监控器已停止")
    
    async def check_token_quota(self, token: str) -> Optional[TokenQuota]:
        """
        检查单个token的配额
        
        Args:
            token: GitHub token
            
        Returns:
            配额信息
        """
        if not self.session:
            self.session = aiohttp.ClientSession()
        
        headers = {
            "Authorization": f"token {token}",
            "Accept": "application/vnd.github.v3+json"
        }
        
        try:
            async with self.session.get(
                "https://api.github.com/rate_limit",
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=10)
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    core = data.get("resources", {}).get("core", {})
                    search = data.get("resources", {}).get("search", {})
                    
                    # 更新配额信息（优先使用search API的配额）
                    quota = self.quotas.get(token)
                    if quota:
                        quota.limit = search.get("limit", 30)
                        quota.remaining = search.get("remaining", 0)
                        quota.reset_time = datetime.fromtimestamp(
                            search.get("reset", time.time()),
                            tz=timezone.utc
                        )
                        quota.last_check = datetime.now(timezone.utc)
                        quota.is_active = True
                        quota.error_count = 0  # 重置错误计数
                        
                        return quota
                else:
                    # Token无效或其他错误
                    if token in self.quotas:
                        self.quotas[token].is_active = False
                        self.quotas[token].error_count += 1
                    logger.warning(f"❌ Token检查失败: {response.status}")
                    
        except Exception as e:
            if token in self.quotas:
                self.quotas[token].error_count += 1
                if self.quotas[token].error_count >= 3:
                    self.quotas[token].is_active = False
            logger.error(f"❌ 检查token配额时出错: {e}")
        
        return None
    
    async def check_all_tokens(self):
        """并发检查所有token的配额"""
        tasks = []
        for token in self.tokens:
            tasks.append(self.check_token_quota(token))
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        active_count = sum(1 for q in self.quotas.values() if q.is_active)
        total_remaining = sum(q.remaining for q in self.quotas.values() if q.is_active)
        
        logger.info(f"📊 Token状态: {active_count}/{len(self.tokens)} 可用, 总剩余配额: {total_remaining}")
    
    async def _monitor_loop(self):
        """监控循环"""
        while self.monitoring:
            try:
                # 每30秒检查一次所有token
                await asyncio.sleep(30)
                await self.check_all_tokens()
                
                # 自动重新激活错误次数较少的token
                for quota in self.quotas.values():
                    if not quota.is_active and quota.error_count < 3:
                        # 尝试重新激活
                        await self.check_token_quota(quota.token)
                        
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"监控循环错误: {e}")
    
    def get_best_token(self) -> Optional[str]:
        """
        获取最佳可用token（基于健康评分）
        
        Returns:
            最佳token，如果没有可用token则返回None
        """
        active_quotas = [q for q in self.quotas.values() if q.is_active and q.remaining > 0]
        
        if not active_quotas:
            return None
        
        # 按健康评分排序，选择最佳的
        best_quota = max(active_quotas, key=lambda q: q.health_score)
        
        # 更新使用计数
        best_quota.used += 1
        
        return best_quota.token
    
    def get_token_by_strategy(self, strategy: str = "health") -> Optional[str]:
        """
        根据策略获取token
        
        Args:
            strategy: 选择策略
                - health: 基于健康评分
                - remaining: 基于剩余配额
                - round_robin: 轮询
                - random: 随机
                
        Returns:
            选中的token
        """
        active_quotas = [q for q in self.quotas.values() if q.is_active and q.remaining > 0]
        
        if not active_quotas:
            return None
        
        if strategy == "health":
            quota = max(active_quotas, key=lambda q: q.health_score)
        elif strategy == "remaining":
            quota = max(active_quotas, key=lambda q: q.remaining)
        elif strategy == "round_robin":
            quota = min(active_quotas, key=lambda q: q.used)
        else:  # random
            import random
            quota = random.choice(active_quotas)
        
        quota.used += 1
        return quota.token
    
    def update_token_stats(self, token: str, success: bool):
        """
        更新token统计信息
        
        Args:
            token: token
            success: 请求是否成功
        """
        if token in self.quotas:
            quota = self.quotas[token]
            
            # 更新成功率（使用滑动窗口）
            if success:
                quota.success_rate = min(1.0, quota.success_rate * 0.95 + 0.05)
                quota.error_count = max(0, quota.error_count - 1)
            else:
                quota.success_rate = max(0.0, quota.success_rate * 0.95)
                quota.error_count += 1
            
            # 减少剩余配额
            quota.remaining = max(0, quota.remaining - 1)
    
    def get_status_table(self) -> Table:
        """
        获取状态表格
        
        Returns:
            Rich表格对象
        """
        table = Table(title="🔑 GitHub Token 配额状态", show_header=True, header_style="bold magenta")
        
        table.add_column("Token", style="cyan", width=12)
        table.add_column("状态", width=8)
        table.add_column("剩余/总量", justify="right", width=15)
        table.add_column("使用率", justify="right", width=10)
        table.add_column("健康度", justify="right", width=10)
        table.add_column("成功率", justify="right", width=10)
        table.add_column("重置时间", width=15)
        table.add_column("已用次数", justify="right", width=10)
        
        # 按健康评分排序
        sorted_quotas = sorted(self.quotas.values(), key=lambda q: q.health_score, reverse=True)
        
        for quota in sorted_quotas:
            # 状态图标
            if not quota.is_active:
                status = "❌ 离线"
                status_style = "red"
            elif quota.remaining == 0:
                status = "⚠️ 耗尽"
                status_style = "yellow"
            elif quota.remaining < quota.limit * 0.2:
                status = "⚡ 低"
                status_style = "yellow"
            else:
                status = "✅ 正常"
                status_style = "green"
            
            # 使用率进度条
            usage_bar = self._create_progress_bar(quota.usage_percent, 10)
            
            # 健康度进度条
            health_bar = self._create_progress_bar(quota.health_score, 10)
            
            table.add_row(
                quota.alias,
                f"[{status_style}]{status}[/{status_style}]",
                f"{quota.remaining}/{quota.limit}",
                f"{usage_bar} {quota.usage_percent:.1f}%",
                f"{health_bar} {quota.health_score:.0f}",
                f"{quota.success_rate*100:.1f}%",
                quota.format_reset_time(),
                str(quota.used)
            )
        
        return table
    
    def _create_progress_bar(self, percent: float, width: int = 10) -> str:
        """创建文本进度条"""
        filled = int(percent / 100 * width)
        bar = "█" * filled + "░" * (width - filled)
        
        if percent >= 80:
            color = "red"
        elif percent >= 50:
            color = "yellow"
        else:
            color = "green"
        
        return f"[{color}]{bar}[/{color}]"
    
    def get_summary_panel(self) -> Panel:
        """获取摘要面板"""
        active_count = sum(1 for q in self.quotas.values() if q.is_active)
        total_remaining = sum(q.remaining for q in self.quotas.values() if q.is_active)
        total_limit = sum(q.limit for q in self.quotas.values() if q.is_active)
        avg_health = sum(q.health_score for q in self.quotas.values() if q.is_active) / max(active_count, 1)
        
        content = f"""
[bold cyan]Token池状态摘要[/bold cyan]
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📊 总Token数: {len(self.tokens)}
✅ 可用Token: {active_count}
🔋 总剩余配额: {total_remaining}/{total_limit}
💪 平均健康度: {avg_health:.1f}/100
🎯 推荐策略: {"健康优先" if avg_health > 70 else "负载均衡"}
        """
        
        return Panel(content.strip(), title="📈 监控摘要", border_style="blue")


class TokenPoolOptimizer:
    """Token池优化器 - 实现动态负载均衡"""
    
    def __init__(self, monitor: TokenMonitor):
        """
        初始化优化器
        
        Args:
            monitor: Token监控器实例
        """
        self.monitor = monitor
        self.request_queue = asyncio.Queue()
        self.result_queue = asyncio.Queue()
        self.workers: List[asyncio.Task] = []
        self.worker_count = 10  # 默认工作线程数
        self.running = False
        
    async def start(self, worker_count: int = 10):
        """
        启动优化器
        
        Args:
            worker_count: 工作线程数
        """
        self.worker_count = worker_count
        self.running = True
        
        # 创建工作线程
        for i in range(worker_count):
            worker = asyncio.create_task(self._worker(f"Worker-{i+1}"))
            self.workers.append(worker)
        
        logger.info(f"🚀 Token池优化器已启动，{worker_count} 个工作线程")
    
    async def stop(self):
        """停止优化器"""
        self.running = False
        
        # 取消所有工作线程
        for worker in self.workers:
            worker.cancel()
        
        await asyncio.gather(*self.workers, return_exceptions=True)
        self.workers.clear()
        
        logger.info("⏹️ Token池优化器已停止")
    
    async def _worker(self, name: str):
        """工作线程"""
        while self.running:
            try:
                # 从队列获取请求
                request = await asyncio.wait_for(self.request_queue.get(), timeout=1.0)
                
                # 获取最佳token
                token = self.monitor.get_best_token()
                if not token:
                    # 没有可用token，等待
                    await asyncio.sleep(5)
                    await self.request_queue.put(request)  # 重新入队
                    continue
                
                # 执行请求
                result = await self._execute_request(token, request)
                
                # 更新统计
                self.monitor.update_token_stats(token, result["success"])
                
                # 返回结果
                await self.result_queue.put(result)
                
            except asyncio.TimeoutError:
                continue
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"{name} 错误: {e}")
    
    async def _execute_request(self, token: str, request: Dict[str, Any]) -> Dict[str, Any]:
        """
        执行API请求
        
        Args:
            token: GitHub token
            request: 请求参数
            
        Returns:
            请求结果
        """
        # 这里实现实际的API请求逻辑
        # 示例实现
        return {
            "success": True,
            "data": {},
            "token_used": token
        }
    
    async def submit_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """
        提交请求到优化器
        
        Args:
            request: 请求参数
            
        Returns:
            请求结果
        """
        await self.request_queue.put(request)
        result = await self.result_queue.get()
        return result


async def display_token_monitor(tokens: List[str]):
    """
    显示Token监控界面
    
    Args:
        tokens: token列表
    """
    monitor = TokenMonitor(tokens)
    await monitor.start()
    
    try:
        with Live(console=console, refresh_per_second=1) as live:
            while True:
                # 创建布局
                layout = Layout()
                layout.split_column(
                    Layout(monitor.get_summary_panel(), size=8),
                    Layout(monitor.get_status_table())
                )
                
                live.update(layout)
                await asyncio.sleep(1)
                
    except KeyboardInterrupt:
        pass
    finally:
        await monitor.stop()


def run_token_monitor(tokens: List[str]):
    """
    运行Token监控器（同步接口）
    
    Args:
        tokens: token列表
    """
    asyncio.run(display_token_monitor(tokens))


if __name__ == "__main__":
    # 测试代码
    test_tokens = [f"ghp_test_token_{i}" for i in range(17)]
    run_token_monitor(test_tokens)