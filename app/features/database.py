"""
数据库支持模块 - 多后端数据持久化
提供SQLite、PostgreSQL、MySQL等多种数据库支持
"""

import asyncio
import logging
from typing import Dict, Any, Optional, List, Union, Callable
from datetime import datetime
from abc import ABC, abstractmethod
import json
import sqlite3
import threading
from contextlib import contextmanager
from dataclasses import dataclass, field
from enum import Enum

from .feature_manager import Feature

logger = logging.getLogger(__name__)


class DatabaseType(Enum):
    """数据库类型枚举"""
    SQLITE = "sqlite"
    POSTGRESQL = "postgresql"
    MYSQL = "mysql"
    MEMORY = "memory"


@dataclass
class DatabaseConfig:
    """数据库配置数据类"""
    type: DatabaseType
    host: str = "localhost"
    port: int = 5432
    database: str = "app"
    username: str = "user"
    password: str = ""
    connection_string: str = ""
    pool_size: int = 10
    timeout: int = 30


class DatabaseConnection(ABC):
    """数据库连接抽象基类"""
    
    @abstractmethod
    def execute(self, query: str, params: Optional[tuple] = None) -> Any:
        """执行SQL查询"""
        pass
    
    @abstractmethod
    def executemany(self, query: str, params_list: List[tuple]) -> Any:
        """执行批量SQL查询"""
        pass
    
    @abstractmethod
    def fetchone(self, query: str, params: Optional[tuple] = None) -> Optional[Dict[str, Any]]:
        """获取单行结果"""
        pass
    
    @abstractmethod
    def fetchall(self, query: str, params: Optional[tuple] = None) -> List[Dict[str, Any]]:
        """获取所有结果"""
        pass
    
    @abstractmethod
    def commit(self):
        """提交事务"""
        pass
    
    @abstractmethod
    def rollback(self):
        """回滚事务"""
        pass
    
    @abstractmethod
    def close(self):
        """关闭连接"""
        pass


class SQLiteConnection(DatabaseConnection):
    """SQLite数据库连接实现"""
    
    def __init__(self, database_path: str, timeout: int = 30):
        self.database_path = database_path
        self.timeout = timeout
        self.connection = None
        self._connect()
    
    def _connect(self):
        """建立数据库连接"""
        try:
            self.connection = sqlite3.connect(
                self.database_path, 
                timeout=self.timeout,
                check_same_thread=False  # 允许跨线程使用
            )
            self.connection.row_factory = sqlite3.Row  # 使结果像字典一样
            logger.debug(f"🔗 SQLite连接已建立: {self.database_path}")
        except Exception as e:
            logger.error(f"SQLite连接失败: {e}")
            raise
    
    def execute(self, query: str, params: Optional[tuple] = None) -> Any:
        """执行SQL查询"""
        if not self.connection:
            self._connect()
        
        try:
            cursor = self.connection.execute(query, params or ())
            return cursor
        except Exception as e:
            logger.error(f"SQLite执行失败: {e}")
            raise
    
    def executemany(self, query: str, params_list: List[tuple]) -> Any:
        """执行批量SQL查询"""
        if not self.connection:
            self._connect()
        
        try:
            cursor = self.connection.executemany(query, params_list)
            return cursor
        except Exception as e:
            logger.error(f"SQLite批量执行失败: {e}")
            raise
    
    def fetchone(self, query: str, params: Optional[tuple] = None) -> Optional[Dict[str, Any]]:
        """获取单行结果"""
        cursor = self.execute(query, params)
        row = cursor.fetchone()
        return dict(row) if row else None
    
    def fetchall(self, query: str, params: Optional[tuple] = None) -> List[Dict[str, Any]]:
        """获取所有结果"""
        cursor = self.execute(query, params)
        rows = cursor.fetchall()
        return [dict(row) for row in rows]
    
    def commit(self):
        """提交事务"""
        if self.connection:
            self.connection.commit()
    
    def rollback(self):
        """回滚事务"""
        if self.connection:
            self.connection.rollback()
    
    def close(self):
        """关闭连接"""
        if self.connection:
            self.connection.close()
            self.connection = None
            logger.debug("🔒 SQLite连接已关闭")


class DatabaseFeature(Feature):
    """数据库支持功能"""
    
    def __init__(self, config: Dict[str, Any]):
        """
        初始化数据库功能
        
        Args:
            config: 配置字典
        """
        self.config = config
        self.enabled = config.get('DATABASE_ENABLED', True)
        self.db_type = DatabaseType(config.get('DATABASE_TYPE', 'sqlite'))
        self.db_config = self._parse_config(config)
        
        # 初始化连接池
        self.connection_pool = []
        self.pool_size = self.db_config.pool_size
        self.pool_lock = threading.Lock()
        
        # 初始化数据库模式
        if self.enabled:
            self._initialize_database()
        
        logger.info("🗄️ 数据库功能初始化")
        logger.info(f"  类型: {self.db_type.value}")
        logger.info(f"  数据库: {self.db_config.database}")
        logger.info(f"  连接池大小: {self.pool_size}")
    
    def _parse_config(self, config: Dict[str, Any]) -> DatabaseConfig:
        """解析数据库配置"""
        return DatabaseConfig(
            type=self.db_type,
            host=config.get('DATABASE_HOST', 'localhost'),
            port=config.get('DATABASE_PORT', 5432),
            database=config.get('DATABASE_NAME', 'app'),
            username=config.get('DATABASE_USERNAME', 'user'),
            password=config.get('DATABASE_PASSWORD', ''),
            connection_string=config.get('DATABASE_CONNECTION_STRING', ''),
            pool_size=config.get('DATABASE_POOL_SIZE', 10),
            timeout=config.get('DATABASE_TIMEOUT', 30)
        )
    
    def _initialize_database(self):
        """初始化数据库模式"""
        try:
            # 获取连接
            connection = self._get_connection()
            
            # 创建必要的表
            self._create_tables(connection)
            
            # 返回连接到池中
            self._return_connection(connection)
            
            logger.info("✅ 数据库初始化完成")
        except Exception as e:
            logger.error(f"数据库初始化失败: {e}")
            raise
    
    def _create_tables(self, connection: DatabaseConnection):
        """创建必要的表"""
        # 创建tokens表
        create_tokens_table = """
        CREATE TABLE IF NOT EXISTS tokens (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            token TEXT UNIQUE NOT NULL,
            type TEXT NOT NULL,
            is_valid BOOLEAN DEFAULT FALSE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            metadata TEXT
        )
        """
        
        # 创建验证记录表
        create_validation_table = """
        CREATE TABLE IF NOT EXISTS validation_records (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            token_id INTEGER,
            status TEXT NOT NULL,
            response_time REAL,
            error_message TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (token_id) REFERENCES tokens (id)
        )
        """
        
        # 创建统计表
        create_stats_table = """
        CREATE TABLE IF NOT EXISTS statistics (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            metric_name TEXT NOT NULL,
            value REAL NOT NULL,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            metadata TEXT
        )
        """
        
        try:
            connection.execute(create_tokens_table)
            connection.execute(create_validation_table)
            connection.execute(create_stats_table)
            connection.commit()
            logger.debug("📋 数据库表创建完成")
        except Exception as e:
            logger.error(f"数据库表创建失败: {e}")
            connection.rollback()
            raise
    
    def _get_connection(self) -> DatabaseConnection:
        """从连接池获取连接"""
        with self.pool_lock:
            if self.connection_pool:
                return self.connection_pool.pop()
        
        # 创建新连接
        return self._create_connection()
    
    def _create_connection(self) -> DatabaseConnection:
        """创建新的数据库连接"""
        if self.db_type == DatabaseType.SQLITE:
            return SQLiteConnection(
                database_path=self.db_config.database,
                timeout=self.db_config.timeout
            )
        else:
            # 其他数据库类型的实现将在实际项目中添加
            raise NotImplementedError(f"数据库类型 {self.db_type.value} 尚未实现")
    
    def _return_connection(self, connection: DatabaseConnection):
        """将连接返回到连接池"""
        with self.pool_lock:
            if len(self.connection_pool) < self.pool_size:
                self.connection_pool.append(connection)
            else:
                # 连接池已满，关闭连接
                connection.close()
    
    @contextmanager
    def get_db_connection(self):
        """获取数据库连接的上下文管理器"""
        connection = None
        try:
            connection = self._get_connection()
            yield connection
        except Exception as e:
            if connection:
                connection.rollback()
            raise
        finally:
            if connection:
                try:
                    connection.commit()
                except Exception as e:
                    logger.error(f"提交事务失败: {e}")
                self._return_connection(connection)
    
    def is_healthy(self) -> bool:
        """
        检查功能是否健康
        
        Returns:
            bool: 功能是否健康
        """
        try:
            with self.get_db_connection() as connection:
                # 执行简单的健康检查查询
                if self.db_type == DatabaseType.SQLITE:
                    connection.execute("SELECT 1")
                else:
                    connection.execute("SELECT 1")
                return True
        except Exception as e:
            logger.error(f"数据库健康检查失败: {e}")
            return False
    
    def get_fallback(self):
        """
        返回降级实现
        """
        return FallbackDatabase()
    
    def cleanup(self):
        """清理资源"""
        logger.debug("🧹 清理数据库连接...")
        with self.pool_lock:
            for connection in self.connection_pool:
                try:
                    connection.close()
                except Exception as e:
                    logger.error(f"关闭连接失败: {e}")
            self.connection_pool.clear()
        logger.debug("✅ 数据库连接已清理")
    
    # ========== 数据库操作方法 ==========
    
    def save_token(self, token: str, token_type: str, is_valid: bool = False, 
                   metadata: Optional[Dict[str, Any]] = None) -> int:
        """
        保存token到数据库
        
        Args:
            token: Token字符串
            token_type: Token类型
            is_valid: 是否有效
            metadata: 元数据
            
        Returns:
            int: 插入的记录ID
        """
        if not self.enabled:
            return 0
        
        with self.get_db_connection() as connection:
            insert_query = """
            INSERT OR REPLACE INTO tokens (token, type, is_valid, metadata)
            VALUES (?, ?, ?, ?)
            """
            
            metadata_json = json.dumps(metadata) if metadata else None
            
            cursor = connection.execute(insert_query, (token, token_type, is_valid, metadata_json))
            connection.commit()
            
            token_id = cursor.lastrowid
            logger.debug(f"💾 Token已保存: {token[:10]}... (ID: {token_id})")
            return token_id
    
    def get_token(self, token: str) -> Optional[Dict[str, Any]]:
        """
        获取token信息
        
        Args:
            token: Token字符串
            
        Returns:
            Dict[str, Any]: Token信息，如果不存在则返回None
        """
        if not self.enabled:
            return None
        
        with self.get_db_connection() as connection:
            select_query = "SELECT * FROM tokens WHERE token = ?"
            return connection.fetchone(select_query, (token,))
    
    def get_valid_tokens(self, token_type: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        获取有效的tokens
        
        Args:
            token_type: Token类型过滤
            
        Returns:
            List[Dict[str, Any]]: 有效的tokens列表
        """
        if not self.enabled:
            return []
        
        with self.get_db_connection() as connection:
            if token_type:
                select_query = "SELECT * FROM tokens WHERE is_valid = TRUE AND type = ?"
                return connection.fetchall(select_query, (token_type,))
            else:
                select_query = "SELECT * FROM tokens WHERE is_valid = TRUE"
                return connection.fetchall(select_query)
    
    def save_validation_record(self, token_id: int, status: str, 
                              response_time: Optional[float] = None,
                              error_message: Optional[str] = None) -> int:
        """
        保存验证记录
        
        Args:
            token_id: Token ID
            status: 验证状态
            response_time: 响应时间
            error_message: 错误信息
            
        Returns:
            int: 插入的记录ID
        """
        if not self.enabled:
            return 0
        
        with self.get_db_connection() as connection:
            insert_query = """
            INSERT INTO validation_records (token_id, status, response_time, error_message)
            VALUES (?, ?, ?, ?)
            """
            
            cursor = connection.execute(insert_query, (token_id, status, response_time, error_message))
            connection.commit()
            
            record_id = cursor.lastrowid
            logger.debug(f"📝 验证记录已保存 (ID: {record_id})")
            return record_id
    
    def get_validation_statistics(self) -> Dict[str, Any]:
        """
        获取验证统计信息
        
        Returns:
            Dict[str, Any]: 统计信息
        """
        if not self.enabled:
            return {}
        
        with self.get_db_connection() as connection:
            # 获取总验证次数
            total_query = "SELECT COUNT(*) as total FROM validation_records"
            total_result = connection.fetchone(total_query)
            total_validations = total_result['total'] if total_result else 0
            
            # 获取成功验证次数
            success_query = "SELECT COUNT(*) as success FROM validation_records WHERE status = 'success'"
            success_result = connection.fetchone(success_query)
            success_count = success_result['success'] if success_result else 0
            
            # 获取平均响应时间
            avg_time_query = "SELECT AVG(response_time) as avg_time FROM validation_records WHERE response_time IS NOT NULL"
            avg_time_result = connection.fetchone(avg_time_query)
            avg_response_time = avg_time_result['avg_time'] if avg_time_result and avg_time_result['avg_time'] else 0
            
            # 按状态分组统计
            status_query = "SELECT status, COUNT(*) as count FROM validation_records GROUP BY status"
            status_results = connection.fetchall(status_query)
            status_stats = {row['status']: row['count'] for row in status_results}
            
            return {
                'total_validations': total_validations,
                'successful_validations': success_count,
                'success_rate': success_count / total_validations if total_validations > 0 else 0,
                'average_response_time': avg_response_time,
                'status_breakdown': status_stats
            }
    
    def save_statistics(self, metric_name: str, value: float, 
                        metadata: Optional[Dict[str, Any]] = None) -> int:
        """
        保存统计信息
        
        Args:
            metric_name: 指标名称
            value: 指标值
            metadata: 元数据
            
        Returns:
            int: 插入的记录ID
        """
        if not self.enabled:
            return 0
        
        with self.get_db_connection() as connection:
            insert_query = """
            INSERT INTO statistics (metric_name, value, metadata)
            VALUES (?, ?, ?)
            """
            
            metadata_json = json.dumps(metadata) if metadata else None
            
            cursor = connection.execute(insert_query, (metric_name, value, metadata_json))
            connection.commit()
            
            record_id = cursor.lastrowid
            logger.debug(f"📊 统计数据已保存: {metric_name} = {value} (ID: {record_id})")
            return record_id
    
    def get_statistics(self, metric_name: Optional[str] = None, 
                      limit: int = 100) -> List[Dict[str, Any]]:
        """
        获取统计信息
        
        Args:
            metric_name: 指标名称过滤
            limit: 返回记录数量限制
            
        Returns:
            List[Dict[str, Any]]: 统计信息列表
        """
        if not self.enabled:
            return []
        
        with self.get_db_connection() as connection:
            if metric_name:
                select_query = """
                SELECT * FROM statistics 
                WHERE metric_name = ? 
                ORDER BY timestamp DESC 
                LIMIT ?
                """
                return connection.fetchall(select_query, (metric_name, limit))
            else:
                select_query = """
                SELECT * FROM statistics 
                ORDER BY timestamp DESC 
                LIMIT ?
                """
                return connection.fetchall(select_query, (limit,))


class FallbackDatabase:
    """数据库功能的降级实现"""
    
    def __init__(self):
        logger.info("🔄 使用数据库功能的降级实现")
        self.data_store = {}  # 内存数据存储
    
    @contextmanager
    def get_db_connection(self):
        """降级的数据库连接"""
        logger.debug("🗄️ 使用内存数据存储（降级实现）")
        yield self
    
    def save_token(self, token: str, token_type: str, is_valid: bool = False, 
                   metadata: Optional[Dict[str, Any]] = None) -> int:
        """降级的token保存"""
        logger.debug(f"💾 Token保存到内存 (降级): {token[:10]}...")
        self.data_store[f"token_{token}"] = {
            'token': token,
            'type': token_type,
            'is_valid': is_valid,
            'metadata': metadata,
            'created_at': datetime.now().isoformat()
        }
        return hash(token) % 1000000  # 模拟ID
    
    def get_token(self, token: str) -> Optional[Dict[str, Any]]:
        """降级的token获取"""
        logger.debug(f"🔍 从内存获取Token (降级): {token[:10]}...")
        return self.data_store.get(f"token_{token}")
    
    def get_valid_tokens(self, token_type: Optional[str] = None) -> List[Dict[str, Any]]:
        """降级的有效tokens获取"""
        logger.debug("📋 获取有效Tokens (降级)")
        valid_tokens = []
        for key, value in self.data_store.items():
            if key.startswith("token_") and value.get('is_valid', False):
                if token_type is None or value.get('type') == token_type:
                    valid_tokens.append(value)
        return valid_tokens
    
    def save_validation_record(self, token_id: int, status: str, 
                              response_time: Optional[float] = None,
                              error_message: Optional[str] = None) -> int:
        """降级的验证记录保存"""
        logger.debug(f"📝 保存验证记录到内存 (降级): {status}")
        record_key = f"validation_{token_id}_{datetime.now().timestamp()}"
        self.data_store[record_key] = {
            'token_id': token_id,
            'status': status,
            'response_time': response_time,
            'error_message': error_message,
            'created_at': datetime.now().isoformat()
        }
        return hash(record_key) % 1000000  # 模拟ID
    
    def get_validation_statistics(self) -> Dict[str, Any]:
        """降级的验证统计获取"""
        logger.debug("📊 获取验证统计 (降级)")
        # 简单的内存统计
        total = 0
        success = 0
        response_times = []
        
        for key, value in self.data_store.items():
            if key.startswith("validation_"):
                total += 1
                if value.get('status') == 'success':
                    success += 1
                if value.get('response_time'):
                    response_times.append(value['response_time'])
        
        return {
            'total_validations': total,
            'successful_validations': success,
            'success_rate': success / total if total > 0 else 0,
            'average_response_time': sum(response_times) / len(response_times) if response_times else 0,
            'message': '统计来自内存存储（降级实现）'
        }
    
    def save_statistics(self, metric_name: str, value: float, 
                        metadata: Optional[Dict[str, Any]] = None) -> int:
        """降级的统计数据保存"""
        logger.debug(f"📊 保存统计数据到内存 (降级): {metric_name} = {value}")
        stat_key = f"stat_{metric_name}_{datetime.now().timestamp()}"
        self.data_store[stat_key] = {
            'metric_name': metric_name,
            'value': value,
            'metadata': metadata,
            'timestamp': datetime.now().isoformat()
        }
        return hash(stat_key) % 1000000  # 模拟ID
    
    def get_statistics(self, metric_name: Optional[str] = None, 
                      limit: int = 100) -> List[Dict[str, Any]]:
        """降级的统计数据获取"""
        logger.debug("📈 获取统计数据 (降级)")
        stats = []
        for key, value in self.data_store.items():
            if key.startswith("stat_"):
                if metric_name is None or value.get('metric_name') == metric_name:
                    stats.append(value)
        return stats[-limit:]  # 返回最新的limit条记录
    
    def is_healthy(self) -> bool:
        """降级的健康检查"""
        return True  # 内存存储总是"健康"
    
    def cleanup(self):
        """降级的资源清理"""
        logger.debug("🧹 清理内存数据存储 (降级)")
        self.data_store.clear()