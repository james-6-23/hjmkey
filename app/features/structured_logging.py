"""
结构化日志模块 - 增强的JSON/XML/YAML日志格式
提供多种日志格式支持和高级日志功能
"""

import asyncio
import logging
from typing import Dict, Any, Optional, List, Union
from datetime import datetime
import json
import xml.etree.ElementTree as ET
import yaml
from abc import ABC, abstractmethod
import traceback
from enum import Enum
import threading
from dataclasses import dataclass, field
from collections import deque
import os

from .feature_manager import Feature

# 创建模块特定的日志记录器
logger = logging.getLogger(__name__)


class LogLevel(Enum):
    """日志级别枚举"""
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class LogFormat(Enum):
    """日志格式枚举"""
    JSON = "json"
    XML = "xml"
    YAML = "yaml"
    TEXT = "text"


@dataclass
class LogRecord:
    """日志记录数据类"""
    timestamp: datetime
    level: LogLevel
    message: str
    module: str
    function: str
    line: int
    context: Dict[str, Any] = field(default_factory=dict)
    trace_id: Optional[str] = None
    span_id: Optional[str] = None


class LogFormatter(ABC):
    """日志格式化器抽象基类"""
    
    @abstractmethod
    def format(self, record: LogRecord) -> str:
        """格式化日志记录"""
        pass


class JSONLogFormatter(LogFormatter):
    """JSON日志格式化器"""
    
    def format(self, record: LogRecord) -> str:
        """格式化为JSON格式"""
        log_dict = {
            "timestamp": record.timestamp.isoformat(),
            "level": record.level.value,
            "message": record.message,
            "module": record.module,
            "function": record.function,
            "line": record.line,
            "context": record.context
        }
        
        if record.trace_id:
            log_dict["trace_id"] = record.trace_id
        if record.span_id:
            log_dict["span_id"] = record.span_id
        
        return json.dumps(log_dict, ensure_ascii=False)


class XMLLogFormatter(LogFormatter):
    """XML日志格式化器"""
    
    def format(self, record: LogRecord) -> str:
        """格式化为XML格式"""
        root = ET.Element("log")
        root.set("timestamp", record.timestamp.isoformat())
        root.set("level", record.level.value)
        
        message_elem = ET.SubElement(root, "message")
        message_elem.text = record.message
        
        module_elem = ET.SubElement(root, "module")
        module_elem.text = record.module
        
        function_elem = ET.SubElement(root, "function")
        function_elem.text = record.function
        
        line_elem = ET.SubElement(root, "line")
        line_elem.text = str(record.line)
        
        if record.trace_id:
            trace_elem = ET.SubElement(root, "trace_id")
            trace_elem.text = record.trace_id
        
        if record.span_id:
            span_elem = ET.SubElement(root, "span_id")
            span_elem.text = record.span_id
        
        if record.context:
            context_elem = ET.SubElement(root, "context")
            for key, value in record.context.items():
                item_elem = ET.SubElement(context_elem, "item")
                item_elem.set("key", key)
                item_elem.text = str(value)
        
        return ET.tostring(root, encoding="unicode")


class YAMLLogFormatter(LogFormatter):
    """YAML日志格式化器"""
    
    def format(self, record: LogRecord) -> str:
        """格式化为YAML格式"""
        log_dict = {
            "timestamp": record.timestamp.isoformat(),
            "level": record.level.value,
            "message": record.message,
            "module": record.module,
            "function": record.function,
            "line": record.line,
            "context": record.context
        }
        
        if record.trace_id:
            log_dict["trace_id"] = record.trace_id
        if record.span_id:
            log_dict["span_id"] = record.span_id
        
        return yaml.dump(log_dict, allow_unicode=True, default_flow_style=False)


class TextLogFormatter(LogFormatter):
    """文本日志格式化器"""
    
    def format(self, record: LogRecord) -> str:
        """格式化为文本格式"""
        context_str = ""
        if record.context:
            context_items = [f"{k}={v}" for k, v in record.context.items()]
            context_str = f" [{', '.join(context_items)}]"
        
        trace_str = ""
        if record.trace_id or record.span_id:
            trace_parts = []
            if record.trace_id:
                trace_parts.append(f"trace_id={record.trace_id}")
            if record.span_id:
                trace_parts.append(f"span_id={record.span_id}")
            trace_str = f" [{', '.join(trace_parts)}]"
        
        return (f"[{record.timestamp.isoformat()}] "
                f"{record.level.value} "
                f"{record.module}.{record.function}:{record.line} - "
                f"{record.message}{context_str}{trace_str}")


class LogHandler(ABC):
    """日志处理器抽象基类"""
    
    @abstractmethod
    async def write(self, formatted_log: str, level: LogLevel):
        """写入日志"""
        pass
    
    @abstractmethod
    async def flush(self):
        """刷新日志"""
        pass


class FileLogHandler(LogHandler):
    """文件日志处理器"""
    
    def __init__(self, filepath: str, max_size: int = 10 * 1024 * 1024, backup_count: int = 5):
        self.filepath = filepath
        self.max_size = max_size
        self.backup_count = backup_count
        self.lock = threading.Lock()
        
        # 确保目录存在
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
    
    async def write(self, formatted_log: str, level: LogLevel):
        """写入日志到文件"""
        with self.lock:
            # 检查文件大小并轮转
            if os.path.exists(self.filepath) and os.path.getsize(self.filepath) > self.max_size:
                self._rotate_files()
            
            # 写入日志
            with open(self.filepath, 'a', encoding='utf-8') as f:
                f.write(formatted_log + '\n')
    
    async def flush(self):
        """刷新文件（文件写入是同步的，所以这里不需要特殊处理）"""
        pass
    
    def _rotate_files(self):
        """轮转日志文件"""
        # 删除最旧的备份
        if os.path.exists(f"{self.filepath}.{self.backup_count}"):
            os.remove(f"{self.filepath}.{self.backup_count}")
        
        # 重命名备份文件
        for i in range(self.backup_count - 1, 0, -1):
            old_file = f"{self.filepath}.{i}"
            new_file = f"{self.filepath}.{i + 1}"
            if os.path.exists(old_file):
                if os.path.exists(new_file):
                    os.remove(new_file)
                os.rename(old_file, new_file)
        
        # 重命名当前文件为第一个备份
        if os.path.exists(self.filepath):
            os.rename(self.filepath, f"{self.filepath}.1")


class ConsoleLogHandler(LogHandler):
    """控制台日志处理器"""
    
    def __init__(self):
        self.lock = threading.Lock()
    
    async def write(self, formatted_log: str, level: LogLevel):
        """写入日志到控制台"""
        with self.lock:
            # 根据日志级别选择颜色
            color_map = {
                LogLevel.DEBUG: "\033[36m",    # 青色
                LogLevel.INFO: "\033[32m",     # 绿色
                LogLevel.WARNING: "\033[33m",  # 黄色
                LogLevel.ERROR: "\033[31m",    # 红色
                LogLevel.CRITICAL: "\033[35m"  # 紫色
            }
            
            reset_color = "\033[0m"
            color = color_map.get(level, "")
            
            print(f"{color}{formatted_log}{reset_color}")
    
    async def flush(self):
        """刷新控制台输出"""
        pass


class StructuredLoggingFeature(Feature):
    """结构化日志功能"""
    
    def __init__(self, config: Dict[str, Any]):
        """
        初始化结构化日志功能
        
        Args:
            config: 配置字典
        """
        self.config = config
        self.enabled = config.get('STRUCTURED_LOGGING_ENABLED', True)
        self.default_format = LogFormat(config.get('DEFAULT_LOG_FORMAT', 'json'))
        self.log_level = LogLevel(config.get('LOG_LEVEL', 'INFO'))
        self.log_file = config.get('LOG_FILE', 'logs/app.log')
        self.max_log_size = config.get('MAX_LOG_SIZE', 10 * 1024 * 1024)  # 10MB
        self.backup_count = config.get('BACKUP_COUNT', 5)
        
        # 初始化格式化器
        self.formatters = {
            LogFormat.JSON: JSONLogFormatter(),
            LogFormat.XML: XMLLogFormatter(),
            LogFormat.YAML: YAMLLogFormatter(),
            LogFormat.TEXT: TextLogFormatter()
        }
        
        # 初始化处理器
        self.handlers = []
        if config.get('LOG_TO_FILE', True):
            self.handlers.append(FileLogHandler(self.log_file, self.max_log_size, self.backup_count))
        if config.get('LOG_TO_CONSOLE', True):
            self.handlers.append(ConsoleLogHandler())
        
        # 存储最近的日志记录（用于调试）
        self.recent_logs = deque(maxlen=1000)
        
        logger.info("📝 结构化日志功能初始化")
        logger.info(f"  格式: {self.default_format.value}")
        logger.info(f"  级别: {self.log_level.value}")
        logger.info(f"  文件: {self.log_file}")
    
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
            logger.error(f"结构化日志功能健康检查失败: {e}")
            return False
    
    def get_fallback(self):
        """
        返回降级实现
        """
        return FallbackStructuredLogging()
    
    def cleanup(self):
        """清理资源"""
        logger.debug("结构化日志功能资源清理")
    
    async def _write_log(self, record: LogRecord, format_type: Optional[LogFormat] = None):
        """写入日志记录"""
        if not self.enabled:
            return
        
        # 获取格式化器
        formatter = self.formatters.get(format_type or self.default_format)
        if not formatter:
            logger.warning(f"未知的日志格式: {format_type}")
            formatter = self.formatters[LogFormat.TEXT]
        
        # 格式化日志
        formatted_log = formatter.format(record)
        
        # 写入所有处理器
        for handler in self.handlers:
            try:
                await handler.write(formatted_log, record.level)
            except Exception as e:
                logger.error(f"日志写入失败: {e}")
        
        # 保存到最近日志
        self.recent_logs.append(record)
    
    def log(self, level: LogLevel, message: str, context: Optional[Dict[str, Any]] = None,
            trace_id: Optional[str] = None, span_id: Optional[str] = None,
            format_type: Optional[LogFormat] = None):
        """
        记录日志
        
        Args:
            level: 日志级别
            message: 日志消息
            context: 上下文信息
            trace_id: 跟踪ID
            span_id: 跨度ID
            format_type: 日志格式
        """
        # 获取调用者信息
        import inspect
        frame = inspect.currentframe().f_back.f_back
        module = frame.f_globals.get('__name__', 'unknown')
        function = frame.f_code.co_name
        line = frame.f_lineno
        
        # 创建日志记录
        record = LogRecord(
            timestamp=datetime.now(),
            level=level,
            message=message,
            module=module,
            function=function,
            line=line,
            context=context or {},
            trace_id=trace_id,
            span_id=span_id
        )
        
        # 异步写入日志
        asyncio.create_task(self._write_log(record, format_type))
    
    def debug(self, message: str, context: Optional[Dict[str, Any]] = None,
              trace_id: Optional[str] = None, span_id: Optional[str] = None,
              format_type: Optional[LogFormat] = None):
        """记录调试日志"""
        if self.log_level.value != 'DEBUG':
            return
        self.log(LogLevel.DEBUG, message, context, trace_id, span_id, format_type)
    
    def info(self, message: str, context: Optional[Dict[str, Any]] = None,
             trace_id: Optional[str] = None, span_id: Optional[str] = None,
             format_type: Optional[LogFormat] = None):
        """记录信息日志"""
        if self.log_level.value in ['DEBUG', 'INFO']:
            self.log(LogLevel.INFO, message, context, trace_id, span_id, format_type)
    
    def warning(self, message: str, context: Optional[Dict[str, Any]] = None,
                trace_id: Optional[str] = None, span_id: Optional[str] = None,
                format_type: Optional[LogFormat] = None):
        """记录警告日志"""
        if self.log_level.value in ['DEBUG', 'INFO', 'WARNING']:
            self.log(LogLevel.WARNING, message, context, trace_id, span_id, format_type)
    
    def error(self, message: str, context: Optional[Dict[str, Any]] = None,
              trace_id: Optional[str] = None, span_id: Optional[str] = None,
              format_type: Optional[LogFormat] = None):
        """记录错误日志"""
        self.log(LogLevel.ERROR, message, context, trace_id, span_id, format_type)
    
    def critical(self, message: str, context: Optional[Dict[str, Any]] = None,
                 trace_id: Optional[str] = None, span_id: Optional[str] = None,
                 format_type: Optional[LogFormat] = None):
        """记录严重错误日志"""
        self.log(LogLevel.CRITICAL, message, context, trace_id, span_id, format_type)
    
    def exception(self, message: str, context: Optional[Dict[str, Any]] = None,
                  trace_id: Optional[str] = None, span_id: Optional[str] = None,
                  format_type: Optional[LogFormat] = None):
        """记录异常日志（包含堆栈跟踪）"""
        exc_info = traceback.format_exc()
        context = context or {}
        context['exception'] = exc_info
        self.log(LogLevel.ERROR, message, context, trace_id, span_id, format_type)
    
    def get_recent_logs(self, limit: int = 100) -> List[LogRecord]:
        """
        获取最近的日志记录
        
        Args:
            limit: 返回记录数量限制
            
        Returns:
            最近的日志记录列表
        """
        return list(self.recent_logs)[-limit:]
    
    def export_logs(self, format_type: LogFormat = LogFormat.JSON) -> str:
        """
        导出日志为指定格式
        
        Args:
            format_type: 导出格式
            
        Returns:
            格式化的日志字符串
        """
        formatter = self.formatters.get(format_type)
        if not formatter:
            raise ValueError(f"不支持的日志格式: {format_type}")
        
        logs = list(self.recent_logs)
        if format_type == LogFormat.JSON:
            return json.dumps([{
                "timestamp": log.timestamp.isoformat(),
                "level": log.level.value,
                "message": log.message,
                "module": log.module,
                "function": log.function,
                "line": log.line,
                "context": log.context,
                "trace_id": log.trace_id,
                "span_id": log.span_id
            } for log in logs], ensure_ascii=False, indent=2)
        elif format_type == LogFormat.XML:
            root = ET.Element("logs")
            for log in logs:
                log_elem = ET.SubElement(root, "log")
                log_elem.set("timestamp", log.timestamp.isoformat())
                log_elem.set("level", log.level.value)
                log_elem.set("module", log.module)
                log_elem.set("function", log.function)
                log_elem.set("line", str(log.line))
                
                message_elem = ET.SubElement(log_elem, "message")
                message_elem.text = log.message
                
                if log.context:
                    context_elem = ET.SubElement(log_elem, "context")
                    for key, value in log.context.items():
                        item_elem = ET.SubElement(context_elem, "item")
                        item_elem.set("key", key)
                        item_elem.text = str(value)
            return ET.tostring(root, encoding="unicode")
        elif format_type == LogFormat.YAML:
            log_dicts = [{
                "timestamp": log.timestamp.isoformat(),
                "level": log.level.value,
                "message": log.message,
                "module": log.module,
                "function": log.function,
                "line": log.line,
                "context": log.context,
                "trace_id": log.trace_id,
                "span_id": log.span_id
            } for log in logs]
            return yaml.dump(log_dicts, allow_unicode=True, default_flow_style=False)
        else:
            # 文本格式
            lines = []
            for log in logs:
                formatter = TextLogFormatter()
                lines.append(formatter.format(log))
            return "\n".join(lines)


class FallbackStructuredLogging:
    """结构化日志功能的降级实现"""
    
    def __init__(self):
        logger.info("🔄 使用结构化日志功能的降级实现")
    
    def log(self, level: LogLevel, message: str, context: Optional[Dict[str, Any]] = None,
            trace_id: Optional[str] = None, span_id: Optional[str] = None,
            format_type: Optional[LogFormat] = None):
        """降级的日志记录"""
        context_str = f" {context}" if context else ""
        trace_str = f" [trace_id={trace_id}, span_id={span_id}]" if trace_id or span_id else ""
        print(f"[{datetime.now().isoformat()}] {level.value} - {message}{context_str}{trace_str}")
    
    def debug(self, message: str, context: Optional[Dict[str, Any]] = None,
              trace_id: Optional[str] = None, span_id: Optional[str] = None,
              format_type: Optional[LogFormat] = None):
        """降级的调试日志"""
        self.log(LogLevel.DEBUG, message, context, trace_id, span_id, format_type)
    
    def info(self, message: str, context: Optional[Dict[str, Any]] = None,
             trace_id: Optional[str] = None, span_id: Optional[str] = None,
             format_type: Optional[LogFormat] = None):
        """降级的信息日志"""
        self.log(LogLevel.INFO, message, context, trace_id, span_id, format_type)
    
    def warning(self, message: str, context: Optional[Dict[str, Any]] = None,
                trace_id: Optional[str] = None, span_id: Optional[str] = None,
                format_type: Optional[LogFormat] = None):
        """降级的警告日志"""
        self.log(LogLevel.WARNING, message, context, trace_id, span_id, format_type)
    
    def error(self, message: str, context: Optional[Dict[str, Any]] = None,
              trace_id: Optional[str] = None, span_id: Optional[str] = None,
              format_type: Optional[LogFormat] = None):
        """降级的错误日志"""
        self.log(LogLevel.ERROR, message, context, trace_id, span_id, format_type)
    
    def critical(self, message: str, context: Optional[Dict[str, Any]] = None,
                 trace_id: Optional[str] = None, span_id: Optional[str] = None,
                 format_type: Optional[LogFormat] = None):
        """降级的严重错误日志"""
        self.log(LogLevel.CRITICAL, message, context, trace_id, span_id, format_type)
    
    def exception(self, message: str, context: Optional[Dict[str, Any]] = None,
                  trace_id: Optional[str] = None, span_id: Optional[str] = None,
                  format_type: Optional[LogFormat] = None):
        """降级的异常日志"""
        context = context or {}
        context['exception'] = traceback.format_exc()
        self.log(LogLevel.ERROR, message, context, trace_id, span_id, format_type)
    
    def get_recent_logs(self, limit: int = 100) -> List[LogRecord]:
        """降级的最近日志获取"""
        return []
    
    def export_logs(self, format_type: LogFormat = LogFormat.JSON) -> str:
        """降级的日志导出"""
        return "结构化日志功能已降级，无日志数据"