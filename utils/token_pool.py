
"""
Token Pool 智能调度模块 - 优化 GitHub API 令牌使用
"""

import time
import logging
import random
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum, auto
import threading
from collections import deque

logger = logging.getLogger(__name__)


class TokenStatus(Enum):
    """令牌状态"""
    HEALTHY = auto()      # 健康
    LIMITED = auto()      # 接近限制
    EXHAUSTED = auto()    # 已耗尽
    RECOVERING = auto()   # 恢复中
    FAILED = auto()       # 失败（多次错误）


@dataclass
class TokenMetrics:
    """令牌指标"""
    token: str
    status: TokenStatus = TokenStatus.HEALTHY
    remaining: int = 30  # 剩余配额
    limit: int = 30      # 配额上限
    reset_time: float = 0  # 重置时间戳
    
    # 使用统计
    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    rate_limit_hits: int = 0
    
    # 性能指标
    last_used: float = 0
    avg_response_time: float = 0
    response_times: deque = field(default_factory=lambda: deque(maxlen=10))
    
    # 错误跟踪
    consecutive_failures: int = 0
    last_error: Optional[str] = None
    last_error_time: float = 0
    
    @property
    def success_rate(self) -> float:
        """计算成功率"""
        if self.total_requests == 0:
            return 1.0
        return self.successful_requests / self.total_requests
    
    @property
    def health_score(self) -> float:
        """
        计算健康分数 (0-100)
        考虑因素：剩余配额、成功率、响应时间
        """
        # 配额分数 (40%)
        quota_score = (self.remaining / max(self.limit, 1)) * 40
        
        # 成功率分数 (40%)
        success_score = self.success_rate * 40
        
        # 响应时间分数 (20%)
        if self.avg_response_time == 0:
            response_score = 20
        elif self.avg_response_time < 1:
            response_score = 20
        elif self.avg_response_time < 3:
            response_score = 15
        elif self.avg_response_time < 5:
            response_score = 10
        else:
            response_score = 5
        
        # 惩罚连续失败
        penalty = min(self.consecutive_failures * 10, 50)
        
        return max(0, quota_score + success_score + response_score - penalty)
    
    def update_response_time(self, response_time: float) -> None:
        """更新响应时间"""
        self.response_times.append(response_time)
        if self.response_times:
            self.avg_response_time = sum(self.response_times) / len(self.response_times)
    
    def record_success(self, response_time: float = 0) -> None:
        """记录成功请求"""
        self.total_requests += 1
        self.successful_requests += 1
        self.consecutive_failures = 0
        self.last_used = time.time()
        if response_time > 0:
            self.update_response_time(response_time)
    
    def record_failure(self, error: str = None) -> None:
        """记录失败请求"""
        self.total_requests += 1
        self.failed_requests += 1
        self.consecutive_failures += 1
        self.last_error = error
        self.last_error_time = time.time()
        self.last_used = time.time()
    
    def record_rate_limit(self) -> None:
        """记录限流"""
        self.rate_limit_hits += 1
        self.status = TokenStatus.EXHAUSTED
    
    def update_quota(self, remaining: int, reset_time: int = None) -> None:
        """更新配额信息"""
        self.remaining = remaining
        if reset_time:
            self.reset_time = reset_time
        
        # 更新状态
        if remaining == 0:
            self.status = TokenStatus.EXHAUSTED
        elif remaining < 5:
            self.status = TokenStatus.LIMITED
        elif self.status == TokenStatus.EXHAUSTED and remaining > 10:
            self.status = TokenStatus.RECOVERING
        elif remaining > 20:
            self.status = TokenStatus.HEALTHY
    
    def is_available(self) -> bool:
        """检查是否可用"""
        # 检查是否已恢复
        if self.status == TokenStatus.EXHAUSTED:
            if time.time() >= self.reset_time:
                self.status = TokenStatus.RECOVERING
                self.remaining = self.limit  # 假设已重置
                return True
            return False
        
        # 连续失败太多
        if self.consecutive_failures >= 5:
            # 冷却期
            cooldown = min(60 * self.consecutive_failures, 300)  # 最多5分钟
            if time.time() - self.last_error_time < cooldown:
                return False
        
        return self.status != TokenStatus.FAILED


class TokenSelectionStrategy(Enum):
    """令牌选择策略"""
    ROUND_ROBIN = auto()     # 轮询
    LEAST_USED = auto()      # 最少使用
    BEST_QUOTA = auto()      # 最多配额
    HEALTH_SCORE = auto()    # 健康分数
    ADAPTIVE = auto()        # 自适应


class TokenPool:
    """令牌池管理器"""
    
    def __init__(self, tokens: List[str], strategy: TokenSelectionStrategy = TokenSelectionStrategy.ADAPTIVE):
        """
        初始化令牌池
        
        Args:
            tokens: 令牌列表
            strategy: 选择策略
        """
        # 去重令牌列表
        unique_tokens = []
        seen = set()
        duplicate_count = 0
        
        for token in tokens:
            token = token.strip()
            if token and token not in seen:
                unique_tokens.append(token)
                seen.add(token)
            elif token in seen:
                duplicate_count += 1
                logger.warning(f"⚠️ 发现重复的GitHub令牌，已自动去重")
        
        if duplicate_count > 0:
            logger.info(f"📋 去重统计：移除了 {duplicate_count} 个重复令牌")
            
        self.tokens = unique_tokens
        self.strategy = strategy
        
        # 初始化配额信息（使用更合理的默认值）
        self.metrics: Dict[str, TokenMetrics] = {}
        for token in self.tokens:
            metrics = TokenMetrics(token=token)
            # GitHub搜索API默认配额是30次/分钟
            metrics.limit = 30
            metrics.remaining = 30
            self.metrics[token] = metrics
        
        # 轮询索引
        self._round_robin_index = 0
        
        # 线程锁
        self._lock = threading.RLock()
        
        # 全局速率限制
        self._global_rate_limiter = RateLimiter(max_qps=10)  # 每秒最多10个请求
        
        # 统计
        self.total_selections = 0
        self.strategy_stats = {s: 0 for s in TokenSelectionStrategy}
        
        logger.info(f"🎯 Token pool initialized with {len(self.tokens)} tokens")
        logger.info(f"   Strategy: {strategy.name}")
        
        # 启动时检查实际配额
        self._initialize_token_quotas()
    
    def _initialize_token_quotas(self):
        """
        启动时检查所有令牌的实际配额
        """
        import requests
        
        logger.info("🔍 Checking actual token quotas from GitHub API...")
        
        for i, token in enumerate(self.tokens):
            try:
                # 调用 GitHub API 检查配额
                headers = {
                    "Authorization": f"token {token}",
                    "Accept": "application/vnd.github.v3+json"
                }
                
                response = requests.get(
                    "https://api.github.com/rate_limit",
                    headers=headers,
                    timeout=5
                )
                
                if response.status_code == 200:
                    data = response.json()
                    
                    # 获取搜索API的配额信息
                    search_limit = data.get('resources', {}).get('search', {})
                    core_limit = data.get('resources', {}).get('core', {})
                    
                    # 更新指标
                    metrics = self.metrics[token]
                    old_limit = metrics.limit
                    old_remaining = metrics.remaining
                    
                    metrics.limit = search_limit.get('limit', 30)
                    metrics.remaining = search_limit.get('remaining', 30)
                    metrics.reset_time = search_limit.get('reset', 0)
                    
                    # 计算使用率
                    used = metrics.limit - metrics.remaining
                    usage_rate = (used / metrics.limit * 100) if metrics.limit > 0 else 0
                    
                    # 更新状态
                    metrics.update_quota(metrics.remaining, metrics.reset_time)
                    
                    # 只在配额与默认值不同时记录
                    if metrics.limit != old_limit or metrics.remaining != old_remaining:
                        logger.info(
                            f"   Token {i+1}: {metrics.remaining}/{metrics.limit} "
                            f"({usage_rate:.1f}% used) - {metrics.status.name}"
                        )
                    
                elif response.status_code == 401:
                    # 无效令牌
                    self.metrics[token].status = TokenStatus.FAILED
                    logger.warning(f"   Token {i+1}: INVALID (401 Unauthorized)")
                    
                elif response.status_code == 403:
                    # 可能是限流
                    self.metrics[token].status = TokenStatus.EXHAUSTED
                    self.metrics[token].remaining = 0
                    logger.warning(f"   Token {i+1}: EXHAUSTED (403 Forbidden)")
                    
                else:
                    logger.debug(f"   Token {i+1}: Check failed (HTTP {response.status_code})")
                
                # 避免过快请求
                if i < len(self.tokens) - 1:
                    time.sleep(0.2)
                    
            except requests.exceptions.RequestException as e:
                logger.debug(f"   Token {i+1}: Network error during quota check - {type(e).__name__}")
            except Exception as e:
                logger.debug(f"   Token {i+1}: Unexpected error - {type(e).__name__}")
        
        # 统计汇总
        healthy = sum(1 for m in self.metrics.values() if m.status == TokenStatus.HEALTHY)
        limited = sum(1 for m in self.metrics.values() if m.status == TokenStatus.LIMITED)
        exhausted = sum(1 for m in self.metrics.values() if m.status == TokenStatus.EXHAUSTED)
        failed = sum(1 for m in self.metrics.values() if m.status == TokenStatus.FAILED)
        
        total_remaining = sum(m.remaining for m in self.metrics.values())
        total_limit = sum(m.limit for m in self.metrics.values())
        
        logger.info(f"📊 Token pool quota check complete:")
        logger.info(f"   Healthy: {healthy}, Limited: {limited}, Exhausted: {exhausted}, Failed: {failed}")
        logger.info(f"   Total quota: {total_remaining}/{total_limit} remaining")
    
    def refresh_quotas(self):
        """
        手动刷新所有令牌的配额信息
        """
        logger.info("🔄 Refreshing token quotas...")
        self._initialize_token_quotas()
    
    def select_token(self) -> Optional[str]:
        """
        选择最佳令牌
        
        Returns:
            选中的令牌，如果没有可用令牌则返回 None
        """
        with self._lock:
            # 全局速率限制
            self._global_rate_limiter.wait_if_needed()
            
            # 获取可用令牌
            available_tokens = [
                token for token, metrics in self.metrics.items()
                if metrics.is_available()
            ]
            
            if not available_tokens:
                # 尝试恢复耗尽的令牌
                self._try_recover_tokens()
                available_tokens = [
                    token for token, metrics in self.metrics.items()
                    if metrics.is_available()
                ]
                
                if not available_tokens:
                    logger.warning("⚠️ No available tokens in pool")
                    return None
            
            # 根据策略选择
            if self.strategy == TokenSelectionStrategy.ADAPTIVE:
                selected = self._adaptive_select(available_tokens)
            else:
                selected = self._select_by_strategy(available_tokens, self.strategy)
            
            # 更新统计
            self.total_selections += 1
            
            logger.debug(f"Selected token: {selected[:20]}... (strategy: {self.strategy.name})")
            return selected
    
    def _select_by_strategy(self, tokens: List[str], strategy: TokenSelectionStrategy) -> str:
        """根据指定策略选择令牌"""
        if strategy == TokenSelectionStrategy.ROUND_ROBIN:
            selected = tokens[self._round_robin_index % len(tokens)]
            self._round_robin_index += 1
            
        elif strategy == TokenSelectionStrategy.LEAST_USED:
            selected = min(tokens, key=lambda t: self.metrics[t].total_requests)
            
        elif strategy == TokenSelectionStrategy.BEST_QUOTA:
            selected = max(tokens, key=lambda t: self.metrics[t].remaining)
            
        elif strategy == TokenSelectionStrategy.HEALTH_SCORE:
            selected = max(tokens, key=lambda t: self.metrics[t].health_score)
            
        else:
            selected = random.choice(tokens)
        
        self.strategy_stats[strategy] += 1
        return selected
    
    def _adaptive_select(self, tokens: List[str]) -> str:
        """
        自适应选择策略
        根据当前情况动态选择最佳策略
        """
        # 分析当前状况
        avg_remaining = sum(self.metrics[t].remaining for t in tokens) / len(tokens)
        min_remaining = min(self.metrics[t].remaining for t in tokens)
        
        # 如果配额紧张，优先选择配额多的
        if avg_remaining < 10 or min_remaining < 5:
            strategy = TokenSelectionStrategy.BEST_QUOTA
        
        # 如果有失败较多的令牌，使用健康分数
        elif any(self.metrics[t].consecutive_failures > 2 for t in tokens):
            strategy = TokenSelectionStrategy.HEALTH_SCORE
        
        # 正常情况下，使用最少使用策略保持平衡
        else:
            strategy = TokenSelectionStrategy.LEAST_USED
        
        return self._select_by_strategy(tokens, strategy)
    
    def _try_recover_tokens(self) -> None:
        """尝试恢复耗尽的令牌"""
        current_time = time.time()
        recovered = 0
        
        for token, metrics in self.metrics.items():
            if metrics.status == TokenStatus.EXHAUSTED:
                if current_time >= metrics.reset_time:
                    metrics.status = TokenStatus.RECOVERING
                    metrics.remaining = metrics.limit
                    recovered += 1
                    logger.info(f"♻️ Token recovered: {token[:20]}...")
        
        if recovered > 0:
            logger.info(f"✅ Recovered {recovered} tokens")
    
    def update_token_status(self, token: str, response: Dict[str, Any]) -> None:
        """
        更新令牌状态（从响应头）
        
        Args:
            token: 令牌
            response: 响应信息（包含 headers）
        """
        if token not in self.metrics:
            return
        
        with self._lock:
            metrics = self.metrics[token]
            
            # 更新配额
            headers = response.get('headers', {})
            remaining = headers.get('X-RateLimit-Remaining')
            reset_time = headers.get('X-RateLimit-Reset')
            
            if remaining is not None:
                metrics.update_quota(int(remaining), int(reset_time) if reset_time else None)
            
            # 更新状态
            status_code = response.get('status_code', 200)
            response_time = response.get('response_time', 0)
            
            if status_code == 200:
                metrics.record_success(response_time)
            elif status_code in (403, 429):
                metrics.record_rate_limit()
            else:
                metrics.record_failure(f"HTTP {status_code}")
    
    def get_pool_status(self) -> Dict[str, Any]:
        """获取池状态摘要"""
        with self._lock:
            healthy = sum(1 for m in self.metrics.values() if m.status == TokenStatus.HEALTHY)
            limited = sum(1 for m in self.metrics.values() if m.status == TokenStatus.LIMITED)
            exhausted = sum(1 for m in self.metrics.values() if m.status == TokenStatus.EXHAUSTED)
            failed = sum(1 for m in self.metrics.values() if m.status == TokenStatus.FAILED)
            recovering = sum(1 for m in self.metrics.values() if m.status == TokenStatus.RECOVERING)
            
            total_remaining = sum(m.remaining for m in self.metrics.values())
            total_limit = sum(m.limit for m in self.metrics.values())
            
            # 修复配额显示问题：确保剩余配额不超过总配额
            if total_remaining > total_limit:
                total_remaining = total_limit
            
            # 修复使用率计算：防止负数和异常值
            if total_limit > 0:
                utilization_pct = max(0, min(100, (total_limit - total_remaining) / total_limit * 100))
                utilization_str = f"{utilization_pct:.1f}%"
            else:
                utilization_str = "0.0%"
            
            # 计算总请求数和错误数
            total_requests = sum(m.total_requests for m in self.metrics.values())
            total_errors = sum(m.failed_requests for m in self.metrics.values())
            
            return {
                "total_tokens": len(self.tokens),
                "healthy": healthy,
                "limited": limited,
                "exhausted": exhausted,
                "failed": failed,
                "recovering": recovering,
                "total_remaining": total_remaining,
                "total_limit": total_limit,
                "utilization": utilization_str,
                "total_requests": total_requests,
                "total_errors": total_errors,
                "total_selections": self.total_selections,
                "strategy_usage": dict(self.strategy_stats)
            }
    
    def get_token_details(self) -> List[Dict[str, Any]]:
        """获取所有令牌的详细信息"""
        with self._lock:
            details = []
            for token, metrics in self.metrics.items():
                details.append({
                    "token": token[:20] + "...",  # 脱敏
                    "status": metrics.status.name,
                    "remaining": metrics.remaining,
                    "health_score": f"{metrics.health_score:.1f}",
                    "success_rate": f"{metrics.success_rate:.1%}",
                    "total_requests": metrics.total_requests,
                    "consecutive_failures": metrics.consecutive_failures
                })
            
            # 按健康分数排序
            details.sort(key=lambda x: float(x["health_score"]), reverse=True)
            return details


class RateLimiter:
    """速率限制器"""
    
    def __init__(self, max_qps: float = 10):
        """
        初始化速率限制器
        
        Args:
            max_qps: 每秒最大请求数
        """
        self.max_qps = max_qps
        self.min_interval = 1.0 / max_qps
        self.last_request_time = 0
        self._lock = threading.Lock()
    
    def wait_if_needed(self) -> float:
        """
        如果需要则等待
        
        Returns:
            等待的时间（秒）
        """
        with self._lock:
            current_time = time.time()
            time_since_last = current_time - self.last_request_time
            
            if time_since_last < self.min_interval:
                wait_time = self.min_interval - time_since_last
                # 添加小的随机抖动
                wait_time += random.uniform(0, 0.1)
                time.sleep(wait_time)
                self.last_request_time = time.time()
                return wait_time
            else:
                self.last_request_time = current_time
                return 0


class CircuitBreaker:
    """熔断器"""
    
    def __init__(self, failure_threshold: int = 5, recovery_timeout: float = 60):
        """
        初始化熔断器
        
        Args:
            failure_threshold: 失败阈值
            recovery_timeout: 恢复超时（秒）
        """
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.failure_count = 0
        self.last_failure_time = 0
        self.state = "CLOSED"  # CLOSED, OPEN, HALF_OPEN
        self._lock = threading.Lock()
    
    def call(self, func, *args, **kwargs):
        """
        通过熔断器调用函数
        
        Args:
            func: 要调用的函数
            *args, **kwargs: 函数参数
            
        Returns:
            函数结果
            
        Raises:
            Exception: 如果熔断器打开或函数失败
        """
        with self._lock:
            # 检查熔断器状态
            if self.state == "OPEN":
                # 检查是否可以尝试恢复
                if time.time() - self.last_failure_time > self.recovery_timeout:
                    self.state = "HALF_OPEN"
                    logger.info("🔌 Circuit breaker: HALF_OPEN (attempting recovery)")
                else:
                    raise Exception("Circuit breaker is OPEN")
            
            try:
                # 执行函数
                result = func(*args, **kwargs)
                
                # 成功，重置失败计数
                if self.state == "HALF_OPEN":
                    self.state = "CLOSED"
                    logger.info("✅ Circuit breaker: CLOSED (recovered)")
                
                self.failure_count = 0
                return result
                
            except Exception as e:
                # 失败，增加计数
                self.failure_count += 1
                self.last_failure_time = time.time()
                
                # 检查是否需要打开熔断器
                if self.failure_count >= self.failure_threshold:
                    self.state = "OPEN"
                    logger.warning(f"⚡ Circuit breaker: OPEN (failures: {self.failure_count})")
                
                raise e


# 使用示例
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    
    # 测试令牌
    test_tokens = [
        "github_pat_11AAAAAAA" + "A" * 74,
        "github_pat_11BBBBBBBB" + "B" * 74,
        "github_pat_11CCCCCCCC" + "C" * 74,
    ]
    
    # 创建令牌池
    pool = TokenPool(test_tokens, strategy=TokenSelectionStrategy.ADAPTIVE)
    
    # 模拟使用
    for i in range(10):
        token = pool.select_token()
        if token:
            # 模拟响应
            response = {
                'status_code': 200 if random.random() > 0.1 else 429,
                'headers': {
                    'X-RateLimit-Remaining': random.randint(0, 30),
                    'X-RateLimit-Reset': int(time.time() + 3600)
                },
                'response_time': random.uniform(0.5, 3.0)
            }
            
            pool.update_token_status(token, response)
    
    # 显示状态
    print("\n📊 Pool Status:")
    status = pool.get_pool_status()
    for key, value in status.items():
        print(f"  {key}: {value}")
    
    print("\n📋 Token Details:")
    for detail in pool.get_token_details():
        print(f"  {detail}")