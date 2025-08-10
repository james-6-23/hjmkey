"""
进度显示模块 - 实时进度跟踪和可视化
提供丰富的进度显示功能，增强用户体验
"""

import asyncio
import logging
from typing import Dict, Any, Optional, Callable, Union
from datetime import datetime, timedelta
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
import threading
from collections import deque

from .feature_manager import Feature

logger = logging.getLogger(__name__)


class ProgressStyle(Enum):
    """进度显示样式枚举"""
    BAR = "bar"          # 进度条
    SPINNER = "spinner"  # 旋转器
    PERCENTAGE = "percentage"  # 百分比
    ETA = "eta"          # 预计完成时间
    CUSTOM = "custom"    # 自定义


@dataclass
class ProgressState:
    """进度状态数据类"""
    current: int = 0
    total: int = 100
    description: str = ""
    start_time: datetime = field(default_factory=datetime.now)
    last_update: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)
    completed: bool = False


class ProgressRenderer(ABC):
    """进度渲染器抽象基类"""
    
    @abstractmethod
    def render(self, state: ProgressState) -> str:
        """渲染进度显示"""
        pass


class ProgressBarRenderer(ProgressRenderer):
    """进度条渲染器"""
    
    def __init__(self, width: int = 50, char: str = "█", empty_char: str = "░"):
        self.width = width
        self.char = char
        self.empty_char = empty_char
    
    def render(self, state: ProgressState) -> str:
        """渲染进度条"""
        if state.total <= 0:
            percentage = 0
        else:
            percentage = min(1.0, state.current / state.total)
        
        filled_width = int(self.width * percentage)
        bar = self.char * filled_width + self.empty_char * (self.width - filled_width)
        
        # 计算ETA
        elapsed = (state.last_update - state.start_time).total_seconds()
        if elapsed > 0 and state.current > 0:
            rate = state.current / elapsed
            remaining = state.total - state.current
            if rate > 0:
                eta_seconds = remaining / rate
                eta = str(timedelta(seconds=int(eta_seconds)))
            else:
                eta = "未知"
        else:
            eta = "计算中..."
        
        return f"{state.description} |{bar}| {state.current}/{state.total} ({percentage:.1%}) ETA: {eta}"


class SpinnerRenderer(ProgressRenderer):
    """旋转器渲染器"""
    
    def __init__(self, chars: str = "⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏"):
        self.chars = chars
        self.index = 0
    
    def render(self, state: ProgressState) -> str:
        """渲染旋转器"""
        char = self.chars[self.index % len(self.chars)]
        self.index += 1
        
        # 计算速率
        elapsed = (state.last_update - state.start_time).total_seconds()
        if elapsed > 0:
            rate = state.current / elapsed
            rate_str = f" ({rate:.1f}/s)"
        else:
            rate_str = ""
        
        return f"{char} {state.description} {state.current}{rate_str}"


class PercentageRenderer(ProgressRenderer):
    """百分比渲染器"""
    
    def render(self, state: ProgressState) -> str:
        """渲染百分比"""
        if state.total <= 0:
            percentage = 0
        else:
            percentage = min(1.0, state.current / state.total)
        
        return f"{state.description} {percentage:.1%} ({state.current}/{state.total})"


class ETARenderer(ProgressRenderer):
    """预计完成时间渲染器"""
    
    def render(self, state: ProgressState) -> str:
        """渲染ETA"""
        elapsed = (state.last_update - state.start_time).total_seconds()
        if elapsed > 0 and state.current > 0:
            rate = state.current / elapsed
            remaining = state.total - state.current
            if rate > 0:
                eta_seconds = remaining / rate
                eta = str(timedelta(seconds=int(eta_seconds)))
                completion_time = datetime.now() + timedelta(seconds=eta_seconds)
                completion_str = completion_time.strftime("%H:%M:%S")
            else:
                eta = "未知"
                completion_str = "未知"
        else:
            eta = "计算中..."
            completion_str = "计算中..."
        
        return f"{state.description} 预计完成: {completion_str} (剩余: {eta})"


class ProgressDisplayFeature(Feature):
    """进度显示功能"""
    
    def __init__(self, config: Dict[str, Any]):
        """
        初始化进度显示功能
        
        Args:
            config: 配置字典
        """
        self.config = config
        self.enabled = config.get('PROGRESS_DISPLAY_ENABLED', True)
        self.update_interval = config.get('PROGRESS_UPDATE_INTERVAL', 0.1)  # 秒
        self.default_style = ProgressStyle(config.get('DEFAULT_PROGRESS_STYLE', 'bar'))
        self.refresh_rate = config.get('PROGRESS_REFRESH_RATE', 10)  # 每秒刷新次数
        
        # 初始化渲染器
        self.renderers = {
            ProgressStyle.BAR: ProgressBarRenderer(
                width=config.get('PROGRESS_BAR_WIDTH', 50),
                char=config.get('PROGRESS_BAR_CHAR', '█'),
                empty_char=config.get('PROGRESS_EMPTY_CHAR', '░')
            ),
            ProgressStyle.SPINNER: SpinnerRenderer(
                chars=config.get('PROGRESS_SPINNER_CHARS', '⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏')
            ),
            ProgressStyle.PERCENTAGE: PercentageRenderer(),
            ProgressStyle.ETA: ETARenderer()
        }
        
        # 存储活动的进度显示器
        self.active_progresses = {}
        self.progress_lock = threading.Lock()
        
        # 启动刷新任务
        self.refresh_task = None
        if self.enabled:
            self.refresh_task = asyncio.create_task(self._refresh_display())
        
        logger.info("📊 进度显示功能初始化")
        logger.info(f"  样式: {self.default_style.value}")
        logger.info(f"  刷新率: {self.refresh_rate} Hz")
    
    def is_healthy(self) -> bool:
        """
        检查功能是否健康
        
        Returns:
            bool: 功能是否健康
        """
        try:
            # 简单的健康检查
            return self.enabled and (self.refresh_task is None or not self.refresh_task.done())
        except Exception as e:
            logger.error(f"进度显示功能健康检查失败: {e}")
            return False
    
    def get_fallback(self):
        """
        返回降级实现
        """
        return FallbackProgressDisplay()
    
    def cleanup(self):
        """清理资源"""
        if self.refresh_task and not self.refresh_task.done():
            self.refresh_task.cancel()
        logger.debug("进度显示功能资源已清理")
    
    async def _refresh_display(self):
        """定期刷新显示"""
        while True:
            try:
                await asyncio.sleep(1.0 / self.refresh_rate)
                if self.enabled:
                    self._update_display()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"进度显示刷新失败: {e}")
    
    def _update_display(self):
        """更新显示（在控制台中）"""
        with self.progress_lock:
            # 在实际实现中，这里会更新控制台显示
            # 由于这是一个简化版本，我们只记录日志
            if self.active_progresses:
                logger.debug(f"🔄 更新 {len(self.active_progresses)} 个进度显示器")
    
    def create_progress(self, total: int, description: str = "", 
                       style: Optional[ProgressStyle] = None,
                       on_complete: Optional[Callable] = None) -> 'ProgressTracker':
        """
        创建进度跟踪器
        
        Args:
            total: 总量
            description: 描述
            style: 显示样式
            on_complete: 完成时的回调函数
            
        Returns:
            ProgressTracker: 进度跟踪器实例
        """
        if not self.enabled:
            return FallbackProgressTracker(total, description, on_complete)
        
        style = style or self.default_style
        tracker = ProgressTracker(
            total=total,
            description=description,
            style=style,
            renderer=self.renderers.get(style),
            on_complete=on_complete,
            feature=self
        )
        
        with self.progress_lock:
            self.active_progresses[id(tracker)] = tracker
        
        return tracker
    
    def remove_progress(self, tracker_id: int):
        """移除进度跟踪器"""
        with self.progress_lock:
            if tracker_id in self.active_progresses:
                del self.active_progresses[tracker_id]
    
    def get_active_progress_count(self) -> int:
        """获取活动进度显示器数量"""
        with self.progress_lock:
            return len(self.active_progresses)
    
    def get_progress_summary(self) -> Dict[str, Any]:
        """获取进度摘要"""
        with self.progress_lock:
            total_current = sum(p.state.current for p in self.active_progresses.values())
            total_total = sum(p.state.total for p in self.active_progresses.values())
            
            return {
                'active_count': len(self.active_progresses),
                'total_current': total_current,
                'total_total': total_total,
                'overall_percentage': total_total / total_current if total_total > 0 else 0
            }


class ProgressTracker:
    """进度跟踪器"""
    
    def __init__(self, total: int, description: str, style: ProgressStyle,
                 renderer: Optional[ProgressRenderer], on_complete: Optional[Callable],
                 feature: ProgressDisplayFeature):
        self.state = ProgressState(total=total, description=description)
        self.style = style
        self.renderer = renderer
        self.on_complete = on_complete
        self.feature = feature
        self.tracker_id = id(self)
        self.last_render_time = 0
        self.render_interval = 1.0 / feature.refresh_rate
        
        logger.debug(f"🆕 创建进度跟踪器: {description} (总量: {total})")
    
    def update(self, advance: int = 1, description: Optional[str] = None):
        """
        更新进度
        
        Args:
            advance: 增加的进度量
            description: 新的描述（可选）
        """
        if self.state.completed:
            return
        
        self.state.current += advance
        self.state.last_update = datetime.now()
        
        if description is not None:
            self.state.description = description
        
        # 检查是否完成
        if self.state.current >= self.state.total:
            self.state.current = self.state.total
            self.state.completed = True
            if self.on_complete:
                try:
                    self.on_complete()
                except Exception as e:
                    logger.error(f"完成回调执行失败: {e}")
            
            # 从活动列表中移除
            self.feature.remove_progress(self.tracker_id)
        
        # 渲染显示
        self._render()
    
    def _render(self):
        """渲染进度显示"""
        if self.renderer and self.feature.enabled:
            current_time = time.time()
            if current_time - self.last_render_time >= self.render_interval:
                try:
                    display_text = self.renderer.render(self.state)
                    logger.info(f"📊 {display_text}")
                    self.last_render_time = current_time
                except Exception as e:
                    logger.error(f"进度渲染失败: {e}")
    
    def set_description(self, description: str):
        """设置描述"""
        self.state.description = description
    
    def reset(self, total: Optional[int] = None):
        """重置进度"""
        self.state.current = 0
        if total is not None:
            self.state.total = total
        self.state.start_time = datetime.now()
        self.state.last_update = datetime.now()
        self.state.completed = False
    
    def get_percentage(self) -> float:
        """获取完成百分比"""
        if self.state.total <= 0:
            return 0.0
        return min(1.0, self.state.current / self.state.total)
    
    def get_elapsed_time(self) -> float:
        """获取已用时间（秒）"""
        return (self.state.last_update - self.state.start_time).total_seconds()


class FallbackProgressDisplay:
    """进度显示功能的降级实现"""
    
    def __init__(self):
        logger.info("🔄 使用进度显示功能的降级实现")
    
    def create_progress(self, total: int, description: str = "", 
                       style: Optional[ProgressStyle] = None,
                       on_complete: Optional[Callable] = None) -> 'FallbackProgressTracker':
        """创建降级的进度跟踪器"""
        logger.debug(f"🔄 进度显示已降级: {description} (总量: {total})")
        return FallbackProgressTracker(total, description, on_complete)
    
    def get_active_progress_count(self) -> int:
        """获取活动进度显示器数量（降级实现）"""
        return 0
    
    def get_progress_summary(self) -> Dict[str, Any]:
        """获取进度摘要（降级实现）"""
        return {
            'active_count': 0,
            'message': '进度显示功能已降级'
        }


class FallbackProgressTracker:
    """降级的进度跟踪器"""
    
    def __init__(self, total: int, description: str, on_complete: Optional[Callable]):
        self.total = total
        self.description = description
        self.current = 0
        self.on_complete = on_complete
        self.start_time = time.time()
        logger.debug(f"🔄 降级进度跟踪器: {description}")
    
    def update(self, advance: int = 1, description: Optional[str] = None):
        """更新进度（降级实现）"""
        self.current += advance
        if description:
            self.description = description
        
        # 记录日志而不是显示进度
        percentage = (self.current / self.total) * 100 if self.total > 0 else 0
        logger.debug(f"🔄 进度更新: {self.description} {self.current}/{self.total} ({percentage:.1f}%)")
        
        # 检查是否完成
        if self.current >= self.total:
            if self.on_complete:
                try:
                    self.on_complete()
                except Exception as e:
                    logger.error(f"完成回调执行失败: {e}")
    
    def set_description(self, description: str):
        """设置描述（降级实现）"""
        self.description = description
        logger.debug(f"🔄 进度描述更新: {description}")
    
    def reset(self, total: Optional[int] = None):
        """重置进度（降级实现）"""
        self.current = 0
        if total is not None:
            self.total = total
        self.start_time = time.time()
        logger.debug("🔄 进度已重置")
    
    def get_percentage(self) -> float:
        """获取完成百分比（降级实现）"""
        if self.total <= 0:
            return 0.0
        return min(1.0, self.current / self.total)
    
    def get_elapsed_time(self) -> float:
        """获取已用时间（降级实现）"""
        return time.time() - self.start_time