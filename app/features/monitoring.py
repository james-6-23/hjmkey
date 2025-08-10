"""
监控告警模块 - 系统健康和性能洞察
提供Prometheus指标收集和告警功能
"""

import asyncio
import logging
from typing import Dict, Any, Optional, List, Callable
from datetime import datetime, timedelta
import time
from abc import ABC, abstractmethod
import json
from collections import defaultdict, deque
import threading
from dataclasses import dataclass, field
from enum import Enum

from .feature_manager import Feature

logger = logging.getLogger(__name__)


class MetricType(Enum):
    """指标类型枚举"""
    COUNTER = "counter"
    GAUGE = "gauge"
    HISTOGRAM = "histogram"
    SUMMARY = "summary"


@dataclass
class Metric:
    """指标数据类"""
    name: str
    type: MetricType
    value: Any
    labels: Dict[str, str] = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)
    description: str = ""


class MetricsCollector(ABC):
    """指标收集器抽象基类"""
    
    @abstractmethod
    def increment_counter(self, name: str, value: float = 1.0, labels: Dict[str, str] = None):
        """增加计数器"""
        pass
    
    @abstractmethod
    def set_gauge(self, name: str, value: float, labels: Dict[str, str] = None):
        """设置仪表盘值"""
        pass
    
    @abstractmethod
    def observe_histogram(self, name: str, value: float, labels: Dict[str, str] = None):
        """观察直方图值"""
        pass
    
    @abstractmethod
    def get_metrics(self) -> List[Metric]:
        """获取所有指标"""
        pass


class InMemoryMetricsCollector(MetricsCollector):
    """内存指标收集器实现"""
    
    def __init__(self):
        self.metrics = {}
        self.histograms = defaultdict(list)
        self.lock = threading.Lock()
    
    def increment_counter(self, name: str, value: float = 1.0, labels: Dict[str, str] = None):
        """增加计数器"""
        key = self._get_key(name, labels)
        with self.lock:
            if key not in self.metrics:
                self.metrics[key] = {
                    'name': name,
                    'type': MetricType.COUNTER,
                    'value': 0.0,
                    'labels': labels or {},
                    'description': f"Counter for {name}"
                }
            self.metrics[key]['value'] += value
    
    def set_gauge(self, name: str, value: float, labels: Dict[str, str] = None):
        """设置仪表盘值"""
        key = self._get_key(name, labels)
        with self.lock:
            self.metrics[key] = {
                'name': name,
                'type': MetricType.GAUGE,
                'value': value,
                'labels': labels or {},
                'description': f"Gauge for {name}"
            }
    
    def observe_histogram(self, name: str, value: float, labels: Dict[str, str] = None):
        """观察直方图值"""
        key = self._get_key(name, labels)
        with self.lock:
            self.histograms[key].append(value)
            # 限制历史记录大小
            if len(self.histograms[key]) > 1000:
                self.histograms[key] = self.histograms[key][-1000:]
    
    def get_metrics(self) -> List[Metric]:
        """获取所有指标"""
        with self.lock:
            metrics = list(self.metrics.values())
            # 添加直方图统计信息
            for key, values in self.histograms.items():
                if values:
                    name = key.split('{')[0] if '{' in key else key
                    labels_str = key.split('{')[1].rstrip('}') if '{' in key else ""
                    labels = dict(item.split('=') for item in labels_str.split(',') if '=' in item) if labels_str else {}
                    
                    metrics.append({
                        'name': f"{name}_count",
                        'type': MetricType.GAUGE,
                        'value': len(values),
                        'labels': labels,
                        'description': f"Histogram count for {name}"
                    })
                    
                    metrics.append({
                        'name': f"{name}_sum",
                        'type': MetricType.GAUGE,
                        'value': sum(values),
                        'labels': labels,
                        'description': f"Histogram sum for {name}"
                    })
                    
                    if values:
                        metrics.append({
                            'name': f"{name}_avg",
                            'type': MetricType.GAUGE,
                            'value': sum(values) / len(values),
                            'labels': labels,
                            'description': f"Histogram average for {name}"
                        })
            return metrics
    
    def _get_key(self, name: str, labels: Dict[str, str] = None) -> str:
        """生成指标键"""
        if labels:
            label_str = ",".join([f"{k}={v}" for k, v in sorted(labels.items())])
            return f"{name}{{{label_str}}}"
        return name


class AlertRule(ABC):
    """告警规则抽象基类"""
    
    @abstractmethod
    def evaluate(self, metrics: List[Metric]) -> bool:
        """评估是否触发告警"""
        pass
    
    @abstractmethod
    def get_alert_message(self) -> str:
        """获取告警消息"""
        pass


class HighErrorRateAlert(AlertRule):
    """高错误率告警"""
    
    def __init__(self, threshold: float = 0.1, window_minutes: int = 5):
        self.threshold = threshold
        self.window_minutes = window_minutes
    
    def evaluate(self, metrics: List[Metric]) -> bool:
        """评估错误率是否超过阈值"""
        error_count = 0
        total_count = 0
        
        for metric in metrics:
            if metric['name'] == 'requests_total' and 'status' in metric['labels']:
                total_count += metric['value']
                if metric['labels']['status'].startswith('5'):
                    error_count += metric['value']
        
        if total_count > 0:
            error_rate = error_count / total_count
            return error_rate > self.threshold
        return False
    
    def get_alert_message(self) -> str:
        return f"🚨 高错误率告警: 错误率超过 {self.threshold * 100}%"


class HighLatencyAlert(AlertRule):
    """高延迟告警"""
    
    def __init__(self, threshold_seconds: float = 5.0):
        self.threshold_seconds = threshold_seconds
    
    def evaluate(self, metrics: List[Metric]) -> bool:
        """评估延迟是否超过阈值"""
        for metric in metrics:
            if metric['name'] == 'request_duration_avg':
                return metric['value'] > self.threshold_seconds
        return False
    
    def get_alert_message(self) -> str:
        return f"🐢 高延迟告警: 平均响应时间超过 {self.threshold_seconds} 秒"


class MonitoringFeature(Feature):
    """监控告警功能"""
    
    def __init__(self, config: Dict[str, Any]):
        """
        初始化监控功能
        
        Args:
            config: 配置字典
        """
        self.config = config
        self.enabled = config.get('MONITORING_ENABLED', True)
        self.metrics_export_interval = config.get('METRICS_EXPORT_INTERVAL', 60)  # 秒
        self.alert_check_interval = config.get('ALERT_CHECK_INTERVAL', 30)  # 秒
        
        # 初始化指标收集器
        self.metrics_collector = InMemoryMetricsCollector()
        
        # 初始化告警规则
        self.alert_rules = [
            HighErrorRateAlert(
                threshold=config.get('ERROR_RATE_THRESHOLD', 0.1),
                window_minutes=config.get('ERROR_RATE_WINDOW', 5)
            ),
            HighLatencyAlert(
                threshold_seconds=config.get('LATENCY_THRESHOLD', 5.0)
            )
        ]
        
        # 存储最近的告警
        self.recent_alerts = deque(maxlen=100)
        
        # 启动后台任务
        self.background_tasks = []
        if self.enabled:
            self._start_background_tasks()
        
        logger.info("📊 监控功能初始化")
    
    def _start_background_tasks(self):
        """启动后台监控任务"""
        # 启动指标导出任务
        metrics_task = asyncio.create_task(self._export_metrics_periodically())
        self.background_tasks.append(metrics_task)
        
        # 启动告警检查任务
        alert_task = asyncio.create_task(self._check_alerts_periodically())
        self.background_tasks.append(alert_task)
        
        logger.debug("🔄 后台监控任务已启动")
    
    async def _export_metrics_periodically(self):
        """定期导出指标"""
        while True:
            try:
                await asyncio.sleep(self.metrics_export_interval)
                if self.enabled:
                    self._export_metrics()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"指标导出失败: {e}")
    
    async def _check_alerts_periodically(self):
        """定期检查告警"""
        while True:
            try:
                await asyncio.sleep(self.alert_check_interval)
                if self.enabled:
                    await self._check_alerts()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"告警检查失败: {e}")
    
    def _export_metrics(self):
        """导出指标（模拟）"""
        metrics = self.metrics_collector.get_metrics()
        logger.debug(f"📤 导出 {len(metrics)} 个指标")
        # 在实际实现中，这里会将指标发送到Prometheus或其他监控系统
    
    async def _check_alerts(self):
        """检查告警规则"""
        metrics = self.metrics_collector.get_metrics()
        for rule in self.alert_rules:
            try:
                if rule.evaluate(metrics):
                    alert_msg = rule.get_alert_message()
                    self._trigger_alert(alert_msg)
            except Exception as e:
                logger.error(f"告警规则评估失败: {e}")
    
    def _trigger_alert(self, message: str):
        """触发告警"""
        alert = {
            'message': message,
            'timestamp': datetime.now(),
            'severity': 'warning'
        }
        self.recent_alerts.append(alert)
        logger.warning(message)
        
        # 在实际实现中，这里会发送告警到Slack、邮件或其他通知系统
    
    def is_healthy(self) -> bool:
        """
        检查功能是否健康
        
        Returns:
            bool: 功能是否健康
        """
        try:
            # 简单的健康检查
            return self.enabled
        except Exception as e:
            logger.error(f"监控功能健康检查失败: {e}")
            return False
    
    def get_fallback(self):
        """
        返回降级实现
        """
        return FallbackMonitoring()
    
    def cleanup(self):
        """清理资源"""
        # 取消后台任务
        for task in self.background_tasks:
            if not task.done():
                task.cancel()
        self.background_tasks.clear()
        logger.debug("监控功能资源已清理")
    
    # ========== 指标收集方法 ==========
    
    def increment_requests_total(self, method: str, endpoint: str, status: str):
        """增加请求总数计数器"""
        self.metrics_collector.increment_counter(
            'requests_total',
            labels={'method': method, 'endpoint': endpoint, 'status': status}
        )
    
    def observe_request_duration(self, duration: float, method: str, endpoint: str):
        """观察请求持续时间"""
        self.metrics_collector.observe_histogram(
            'request_duration_seconds',
            duration,
            labels={'method': method, 'endpoint': endpoint}
        )
    
    def set_active_connections(self, count: int):
        """设置活跃连接数"""
        self.metrics_collector.set_gauge('active_connections', count)
    
    def increment_validation_attempts(self, token_type: str, result: str):
        """增加验证尝试计数器"""
        self.metrics_collector.increment_counter(
            'validation_attempts_total',
            labels={'token_type': token_type, 'result': result}
        )
    
    def set_token_pool_size(self, size: int, token_type: str):
        """设置token池大小"""
        self.metrics_collector.set_gauge(
            'token_pool_size',
            size,
            labels={'token_type': token_type}
        )
    
    # ========== 获取监控数据 ==========
    
    def get_metrics_text(self) -> str:
        """获取Prometheus格式的指标文本"""
        metrics = self.metrics_collector.get_metrics()
        lines = []
        
        for metric in metrics:
            # 添加注释
            if metric.get('description'):
                lines.append(f"# HELP {metric['name']} {metric['description']}")
            
            # 添加类型
            lines.append(f"# TYPE {metric['name']} {metric['type'].value}")
            
            # 添加值
            if metric['labels']:
                label_str = ",".join([f'{k}="{v}"' for k, v in metric['labels'].items()])
                lines.append(f"{metric['name']}{{{label_str}}} {metric['value']}")
            else:
                lines.append(f"{metric['name']} {metric['value']}")
        
        return "\n".join(lines)
    
    def get_recent_alerts(self, limit: int = 10) -> List[Dict]:
        """获取最近的告警"""
        return list(self.recent_alerts)[-limit:]
    
    def get_system_stats(self) -> Dict[str, Any]:
        """获取系统统计信息"""
        metrics = self.metrics_collector.get_metrics()
        
        # 计算一些聚合统计
        stats = {
            'timestamp': datetime.now().isoformat(),
            'total_requests': 0,
            'error_rate': 0.0,
            'avg_response_time': 0.0,
            'active_alerts': len(self.recent_alerts)
        }
        
        # 计算请求总数和错误率
        total_requests = 0
        error_requests = 0
        for metric in metrics:
            if metric['name'] == 'requests_total':
                total_requests += metric['value']
                if 'status' in metric['labels'] and metric['labels']['status'].startswith('5'):
                    error_requests += metric['value']
        
        stats['total_requests'] = total_requests
        if total_requests > 0:
            stats['error_rate'] = error_requests / total_requests
        
        # 计算平均响应时间
        for metric in metrics:
            if metric['name'] == 'request_duration_avg':
                stats['avg_response_time'] = metric['value']
                break
        
        return stats


class FallbackMonitoring:
    """监控功能的降级实现"""
    
    def __init__(self):
        logger.info("🔄 使用监控功能的降级实现")
    
    def increment_requests_total(self, method: str, endpoint: str, status: str):
        """降级的请求计数"""
        logger.debug(f"📈 请求计数 (降级): {method} {endpoint} {status}")
    
    def observe_request_duration(self, duration: float, method: str, endpoint: str):
        """降级的请求持续时间观察"""
        logger.debug(f"⏱️ 请求持续时间 (降级): {duration}s for {method} {endpoint}")
    
    def set_active_connections(self, count: int):
        """降级的活跃连接设置"""
        logger.debug(f"🔌 活跃连接 (降级): {count}")
    
    def increment_validation_attempts(self, token_type: str, result: str):
        """降级的验证尝试计数"""
        logger.debug(f"🔍 验证尝试 (降级): {token_type} -> {result}")
    
    def set_token_pool_size(self, size: int, token_type: str):
        """降级的token池大小设置"""
        logger.debug(f"🔑 Token池大小 (降级): {size} for {token_type}")
    
    def get_metrics_text(self) -> str:
        """降级的指标文本获取"""
        return "# 监控功能已降级，无指标数据"
    
    def get_recent_alerts(self, limit: int = 10) -> List[Dict]:
        """降级的最近告警获取"""
        return []
    
    def get_system_stats(self) -> Dict[str, Any]:
        """降级的系统统计获取"""
        return {
            'timestamp': datetime.now().isoformat(),
            'message': '监控功能已降级'
        }