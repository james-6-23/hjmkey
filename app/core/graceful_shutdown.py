"""
优雅停机模块 - 状态机管理、信号处理、资源清理
"""

import asyncio
import signal
import logging
import sys
from enum import Enum, auto
from typing import Optional, Callable, Dict, Any, List, Set
from datetime import datetime
from pathlib import Path
import threading
from contextlib import contextmanager

logger = logging.getLogger(__name__)


class OrchestratorState(Enum):
    """协调器状态枚举"""
    IDLE = auto()        # 空闲
    INITIALIZING = auto() # 初始化中
    SCANNING = auto()    # 扫描中
    VALIDATING = auto()  # 验证中
    FINALIZING = auto()  # 最终化中
    STOPPED = auto()     # 已停止
    ERROR = auto()       # 错误状态


class StateTransition:
    """状态转换规则"""
    ALLOWED_TRANSITIONS = {
        OrchestratorState.IDLE: [
            OrchestratorState.INITIALIZING,
            OrchestratorState.STOPPED
        ],
        OrchestratorState.INITIALIZING: [
            OrchestratorState.SCANNING,
            OrchestratorState.ERROR,
            OrchestratorState.STOPPED
        ],
        OrchestratorState.SCANNING: [
            OrchestratorState.VALIDATING,
            OrchestratorState.FINALIZING,
            OrchestratorState.ERROR,
            OrchestratorState.STOPPED
        ],
        OrchestratorState.VALIDATING: [
            OrchestratorState.SCANNING,  # 可以回到扫描
            OrchestratorState.FINALIZING,
            OrchestratorState.ERROR,
            OrchestratorState.STOPPED
        ],
        OrchestratorState.FINALIZING: [
            OrchestratorState.STOPPED
        ],
        OrchestratorState.ERROR: [
            OrchestratorState.FINALIZING,
            OrchestratorState.STOPPED
        ],
        OrchestratorState.STOPPED: []  # 终态，不能转换
    }
    
    @classmethod
    def can_transition(cls, from_state: OrchestratorState, to_state: OrchestratorState) -> bool:
        """
        检查状态转换是否允许
        
        Args:
            from_state: 源状态
            to_state: 目标状态
            
        Returns:
            是否允许转换
        """
        allowed = cls.ALLOWED_TRANSITIONS.get(from_state, [])
        return to_state in allowed


class StateMachine:
    """状态机"""
    
    def __init__(self, initial_state: OrchestratorState = OrchestratorState.IDLE):
        """
        初始化状态机
        
        Args:
            initial_state: 初始状态
        """
        self._state = initial_state
        self._state_lock = threading.RLock()
        self._transition_callbacks: Dict[OrchestratorState, List[Callable]] = {}
        self._state_history: List[tuple] = []  # (state, timestamp)
        
        # 记录初始状态
        self._record_state_change(initial_state)
        
        logger.info(f"🎯 State machine initialized: {initial_state.name}")
    
    @property
    def state(self) -> OrchestratorState:
        """获取当前状态"""
        with self._state_lock:
            return self._state
    
    def transition_to(self, new_state: OrchestratorState, force: bool = False) -> bool:
        """
        转换到新状态
        
        Args:
            new_state: 新状态
            force: 是否强制转换（忽略规则）
            
        Returns:
            是否成功转换
        """
        with self._state_lock:
            old_state = self._state
            
            # 检查是否允许转换
            if not force and not StateTransition.can_transition(old_state, new_state):
                logger.warning(
                    f"❌ State transition not allowed: {old_state.name} -> {new_state.name}"
                )
                return False
            
            # 执行转换
            self._state = new_state
            self._record_state_change(new_state)
            
            logger.info(f"🔄 State transition: {old_state.name} -> {new_state.name}")
            
            # 触发回调
            self._trigger_callbacks(new_state)
            
            return True
    
    def _record_state_change(self, state: OrchestratorState) -> None:
        """记录状态变化"""
        self._state_history.append((state, datetime.now()))
    
    def _trigger_callbacks(self, state: OrchestratorState) -> None:
        """触发状态转换回调"""
        callbacks = self._transition_callbacks.get(state, [])
        for callback in callbacks:
            try:
                callback(state)
            except Exception as e:
                logger.error(f"Callback error for state {state.name}: {e}")
    
    def on_state_enter(self, state: OrchestratorState, callback: Callable) -> None:
        """
        注册状态进入回调
        
        Args:
            state: 状态
            callback: 回调函数
        """
        if state not in self._transition_callbacks:
            self._transition_callbacks[state] = []
        self._transition_callbacks[state].append(callback)
    
    def is_in_state(self, *states: OrchestratorState) -> bool:
        """检查是否在指定状态之一"""
        with self._state_lock:
            return self._state in states
    
    def get_state_duration(self) -> float:
        """获取当前状态持续时间（秒）"""
        if not self._state_history:
            return 0.0
        
        last_change = self._state_history[-1][1]
        return (datetime.now() - last_change).total_seconds()
    
    def get_history(self) -> List[tuple]:
        """获取状态历史"""
        with self._state_lock:
            return self._state_history.copy()


class GracefulShutdownManager:
    """优雅停机管理器"""
    
    def __init__(self, state_machine: Optional[StateMachine] = None):
        """
        初始化停机管理器
        
        Args:
            state_machine: 状态机（可选）
        """
        self.state_machine = state_machine or StateMachine()
        self._shutdown_requested = threading.Event()
        self._shutdown_complete = threading.Event()
        self._active_tasks: Set[asyncio.Task] = set()
        self._cleanup_callbacks: List[Callable] = []
        self._finalize_callbacks: List[Callable] = []
        
        # 注册信号处理器
        self._register_signal_handlers()
        
        logger.info("🛡️ Graceful shutdown manager initialized")
    
    def _register_signal_handlers(self) -> None:
        """注册信号处理器"""
        if sys.platform != "win32":
            # Unix 信号
            signal.signal(signal.SIGTERM, self._signal_handler)
            signal.signal(signal.SIGINT, self._signal_handler)
            signal.signal(signal.SIGHUP, self._signal_handler)
        else:
            # Windows 只支持部分信号
            signal.signal(signal.SIGINT, self._signal_handler)
            signal.signal(signal.SIGTERM, self._signal_handler)
    
    def _signal_handler(self, signum, frame) -> None:
        """信号处理器"""
        signal_name = signal.Signals(signum).name
        logger.info(f"📡 Received signal: {signal_name}")
        
        # 请求停机
        self.request_shutdown(f"Signal {signal_name}")
    
    def request_shutdown(self, reason: str = "User request") -> None:
        """
        请求停机
        
        Args:
            reason: 停机原因
        """
        if self._shutdown_requested.is_set():
            logger.warning("⚠️ Shutdown already requested")
            return
        
        logger.info(f"🛑 Shutdown requested: {reason}")
        self._shutdown_requested.set()
        
        # 尝试转换到 FINALIZING 状态
        if self.state_machine:
            current_state = self.state_machine.state
            if current_state not in [OrchestratorState.FINALIZING, OrchestratorState.STOPPED]:
                self.state_machine.transition_to(OrchestratorState.FINALIZING)
    
    def is_shutdown_requested(self) -> bool:
        """检查是否请求了停机"""
        return self._shutdown_requested.is_set()
    
    def register_task(self, task: asyncio.Task) -> None:
        """
        注册活动任务
        
        Args:
            task: 异步任务
        """
        self._active_tasks.add(task)
        task.add_done_callback(self._active_tasks.discard)
    
    def register_cleanup(self, callback: Callable) -> None:
        """
        注册清理回调
        
        Args:
            callback: 清理回调函数
        """
        self._cleanup_callbacks.append(callback)
    
    def register_finalize(self, callback: Callable) -> None:
        """
        注册最终化回调
        
        Args:
            callback: 最终化回调函数
        """
        self._finalize_callbacks.append(callback)
    
    async def wait_for_tasks(self, timeout: float = 30.0) -> bool:
        """
        等待所有任务完成
        
        Args:
            timeout: 超时时间（秒）
            
        Returns:
            是否所有任务都完成了
        """
        if not self._active_tasks:
            return True
        
        logger.info(f"⏳ Waiting for {len(self._active_tasks)} active tasks...")
        
        try:
            # 等待所有任务完成或超时
            done, pending = await asyncio.wait(
                self._active_tasks,
                timeout=timeout,
                return_when=asyncio.ALL_COMPLETED
            )
            
            if pending:
                logger.warning(f"⚠️ {len(pending)} tasks still pending after {timeout}s")
                
                # 取消剩余任务
                for task in pending:
                    task.cancel()
                
                # 再等待一小段时间让任务响应取消
                await asyncio.wait(pending, timeout=5.0)
                
                return False
            
            logger.info("✅ All tasks completed")
            return True
            
        except Exception as e:
            logger.error(f"Error waiting for tasks: {e}")
            return False
    
    async def execute_cleanup(self) -> None:
        """执行清理回调"""
        logger.info(f"🧹 Executing {len(self._cleanup_callbacks)} cleanup callbacks...")
        
        for callback in self._cleanup_callbacks:
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback()
                else:
                    callback()
            except Exception as e:
                logger.error(f"Cleanup callback error: {e}")
    
    async def execute_finalize(self) -> None:
        """执行最终化回调"""
        logger.info(f"📝 Executing {len(self._finalize_callbacks)} finalize callbacks...")
        
        for callback in self._finalize_callbacks:
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback()
                else:
                    callback()
            except Exception as e:
                logger.error(f"Finalize callback error: {e}")
    
    async def shutdown(self, timeout: float = 30.0) -> None:
        """
        执行优雅停机
        
        Args:
            timeout: 超时时间（秒）
        """
        logger.info("=" * 60)
        logger.info("🛑 GRACEFUL SHUTDOWN INITIATED")
        logger.info("=" * 60)
        
        # 1. 转换到 FINALIZING 状态
        if self.state_machine:
            self.state_machine.transition_to(OrchestratorState.FINALIZING, force=True)
        
        # 2. 等待活动任务
        await self.wait_for_tasks(timeout)
        
        # 3. 执行清理
        await self.execute_cleanup()
        
        # 4. 执行最终化
        await self.execute_finalize()
        
        # 5. 转换到 STOPPED 状态
        if self.state_machine:
            self.state_machine.transition_to(OrchestratorState.STOPPED)
        
        # 6. 标记完成
        self._shutdown_complete.set()
        
        logger.info("=" * 60)
        logger.info("✅ GRACEFUL SHUTDOWN COMPLETE")
        logger.info("=" * 60)
    
    def wait_for_shutdown(self, timeout: Optional[float] = None) -> bool:
        """
        等待停机完成（同步）
        
        Args:
            timeout: 超时时间
            
        Returns:
            是否完成
        """
        return self._shutdown_complete.wait(timeout)
    
    @contextmanager
    def managed_execution(self):
        """
        受管理的执行上下文
        
        Usage:
            with shutdown_manager.managed_execution():
                # 执行代码
                pass
        """
        try:
            # 进入上下文
            if self.state_machine:
                self.state_machine.transition_to(OrchestratorState.INITIALIZING)
            
            yield self
            
        except KeyboardInterrupt:
            logger.info("⌨️ Keyboard interrupt received")
            self.request_shutdown("Keyboard interrupt")
            
        except Exception as e:
            logger.error(f"💥 Unhandled exception: {e}")
            if self.state_machine:
                self.state_machine.transition_to(OrchestratorState.ERROR)
            raise
            
        finally:
            # 确保执行停机流程
            if not self._shutdown_complete.is_set():
                # 同步执行异步停机
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    asyncio.create_task(self.shutdown())
                else:
                    loop.run_until_complete(self.shutdown())


# 全局实例
_shutdown_manager: Optional[GracefulShutdownManager] = None


def get_shutdown_manager() -> GracefulShutdownManager:
    """获取全局停机管理器"""
    global _shutdown_manager
    if _shutdown_manager is None:
        _shutdown_manager = GracefulShutdownManager()
    return _shutdown_manager


# 使用示例
if __name__ == "__main__":
    import time
    
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s | %(levelname)s | %(name)s | %(message)s'
    )
    
    async def example_task(n: int):
        """示例任务"""
        for i in range(n):
            if get_shutdown_manager().is_shutdown_requested():
                logger.info(f"Task {n} interrupted at {i}")
                break
            await asyncio.sleep(1)
            logger.info(f"Task {n}: step {i+1}/{n}")
    
    async def main():
        """主函数"""
        manager = get_shutdown_manager()
        
        # 注册清理和最终化回调
        manager.register_cleanup(lambda: logger.info("🧹 Cleaning up resources..."))
        manager.register_finalize(lambda: logger.info("📝 Saving final report..."))
        
        with manager.managed_execution():
            # 转换到扫描状态
            manager.state_machine.transition_to(OrchestratorState.SCANNING)
            
            # 创建一些任务
            tasks = [
                asyncio.create_task(example_task(5)),
                asyncio.create_task(example_task(10)),
                asyncio.create_task(example_task(15))
            ]
            
            # 注册任务
            for task in tasks:
                manager.register_task(task)
            
            # 等待任务或停机信号
            await asyncio.gather(*tasks, return_exceptions=True)
    
    # 运行
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Program interrupted")