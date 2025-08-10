"""
安全工具模块
提供密钥脱敏、加密存储等安全功能
"""

import hashlib
import re
from typing import Any, Dict, List, Optional, Union
from pathlib import Path
import json


class KeyMasker:
    """
    密钥脱敏工具类
    用于在日志、输出和存储中保护敏感信息
    """
    
    # 敏感字段名称列表
    SENSITIVE_FIELDS = [
        'key', 'api_key', 'apikey', 'api-key',
        'token', 'access_token', 'auth_token',
        'password', 'passwd', 'pwd',
        'secret', 'secret_key', 'client_secret',
        'credential', 'credentials',
        'authorization', 'auth'
    ]
    
    # API密钥正则模式
    API_KEY_PATTERNS = [
        r'AIzaSy[A-Za-z0-9_-]{33}',  # Google/Gemini API Key
        r'sk-[A-Za-z0-9]{48}',        # OpenAI API Key
        r'ghp_[A-Za-z0-9]{36}',        # GitHub Personal Access Token
        r'ghs_[A-Za-z0-9]{36}',        # GitHub Secret
        r'Bearer\s+[A-Za-z0-9_-]+',   # Bearer Token
    ]
    
    def __init__(self, show_start: int = 6, show_end: int = 4):
        """
        初始化脱敏器
        
        Args:
            show_start: 显示开头的字符数
            show_end: 显示结尾的字符数
        """
        self.show_start = show_start
        self.show_end = show_end
    
    def mask(self, key: str, custom_start: Optional[int] = None, 
             custom_end: Optional[int] = None) -> str:
        """
        对单个密钥进行脱敏
        
        Args:
            key: 要脱敏的密钥
            custom_start: 自定义显示开头字符数
            custom_end: 自定义显示结尾字符数
            
        Returns:
            脱敏后的密钥
            
        Examples:
            >>> masker = KeyMasker()
            >>> masker.mask("AIzaSyBx3K9sdPqM1x2y3F4z5A6b7C8d9E0fGhI")
            'AIzaSy...fGhI'
        """
        if not key:
            return "***"
        
        start = custom_start if custom_start is not None else self.show_start
        end = custom_end if custom_end is not None else self.show_end
        
        # 如果密钥太短，完全隐藏
        if len(key) <= start + end:
            return "*" * len(key)
        
        # 保留开头和结尾，中间用省略号
        return f"{key[:start]}...{key[-end:]}"
    
    def mask_in_text(self, text: str) -> str:
        """
        自动识别并脱敏文本中的API密钥
        
        Args:
            text: 包含密钥的文本
            
        Returns:
            脱敏后的文本
        """
        result = text
        
        # 对每个API密钥模式进行替换
        for pattern in self.API_KEY_PATTERNS:
            matches = re.finditer(pattern, result)
            for match in matches:
                original = match.group(0)
                # 如果是Bearer token，特殊处理
                if original.startswith('Bearer'):
                    masked = f"Bearer {self.mask(original[7:])}"
                else:
                    masked = self.mask(original)
                result = result.replace(original, masked)
        
        return result
    
    def mask_dict(self, data: Dict[str, Any], recursive: bool = True) -> Dict[str, Any]:
        """
        对字典中的敏感字段进行脱敏
        
        Args:
            data: 要脱敏的字典
            recursive: 是否递归处理嵌套字典
            
        Returns:
            脱敏后的字典副本
        """
        if not isinstance(data, dict):
            return data
        
        result = {}
        for key, value in data.items():
            # 检查是否是敏感字段
            is_sensitive = any(
                sensitive in key.lower() 
                for sensitive in self.SENSITIVE_FIELDS
            )
            
            if is_sensitive and isinstance(value, str):
                # 脱敏字符串值
                result[key] = self.mask(value)
            elif recursive and isinstance(value, dict):
                # 递归处理嵌套字典
                result[key] = self.mask_dict(value, recursive)
            elif recursive and isinstance(value, list):
                # 处理列表
                result[key] = self.mask_list(value, recursive)
            else:
                # 保持原值
                result[key] = value
        
        return result
    
    def mask_list(self, data: List[Any], recursive: bool = True) -> List[Any]:
        """
        对列表中的元素进行脱敏
        
        Args:
            data: 要脱敏的列表
            recursive: 是否递归处理
            
        Returns:
            脱敏后的列表副本
        """
        result = []
        for item in data:
            if isinstance(item, str):
                # 检查是否像API密钥
                if any(re.match(pattern, item) for pattern in self.API_KEY_PATTERNS):
                    result.append(self.mask(item))
                else:
                    result.append(item)
            elif recursive and isinstance(item, dict):
                result.append(self.mask_dict(item, recursive))
            elif recursive and isinstance(item, list):
                result.append(self.mask_list(item, recursive))
            else:
                result.append(item)
        
        return result
    
    def mask_json(self, json_str: str) -> str:
        """
        对JSON字符串中的敏感信息进行脱敏
        
        Args:
            json_str: JSON字符串
            
        Returns:
            脱敏后的JSON字符串
        """
        try:
            data = json.loads(json_str)
            masked_data = self.mask_dict(data) if isinstance(data, dict) else self.mask_list(data)
            return json.dumps(masked_data, ensure_ascii=False, indent=2)
        except json.JSONDecodeError:
            # 如果不是有效的JSON，尝试文本脱敏
            return self.mask_in_text(json_str)
    
    def hash_key(self, key: str) -> str:
        """
        生成密钥的SHA256哈希值（用于存储和比较）
        
        Args:
            key: 原始密钥
            
        Returns:
            SHA256哈希值
        """
        return hashlib.sha256(key.encode()).hexdigest()
    
    def get_key_identifier(self, key: str) -> str:
        """
        获取密钥的唯一标识符（脱敏版本+哈希前8位）
        
        Args:
            key: 原始密钥
            
        Returns:
            密钥标识符
            
        Example:
            "AIzaSy...fGhI#a3b4c5d6"
        """
        masked = self.mask(key)
        hash_prefix = self.hash_key(key)[:8]
        return f"{masked}#{hash_prefix}"


class SecureLogger:
    """
    安全日志记录器
    自动脱敏日志中的敏感信息
    """
    
    def __init__(self, logger, masker: Optional[KeyMasker] = None):
        """
        初始化安全日志记录器
        
        Args:
            logger: 原始日志记录器
            masker: 密钥脱敏器实例
        """
        self.logger = logger
        self.masker = masker or KeyMasker()
    
    def _mask_message(self, msg: str) -> str:
        """脱敏日志消息"""
        return self.masker.mask_in_text(msg)
    
    def _mask_args(self, args: tuple) -> tuple:
        """脱敏日志参数"""
        masked_args = []
        for arg in args:
            if isinstance(arg, str):
                masked_args.append(self._mask_message(arg))
            elif isinstance(arg, dict):
                masked_args.append(self.masker.mask_dict(arg))
            elif isinstance(arg, list):
                masked_args.append(self.masker.mask_list(arg))
            else:
                masked_args.append(arg)
        return tuple(masked_args)
    
    def debug(self, msg: str, *args, **kwargs):
        """记录DEBUG级别日志（自动脱敏）"""
        self.logger.debug(self._mask_message(msg), *self._mask_args(args), **kwargs)
    
    def info(self, msg: str, *args, **kwargs):
        """记录INFO级别日志（自动脱敏）"""
        self.logger.info(self._mask_message(msg), *self._mask_args(args), **kwargs)
    
    def warning(self, msg: str, *args, **kwargs):
        """记录WARNING级别日志（自动脱敏）"""
        self.logger.warning(self._mask_message(msg), *self._mask_args(args), **kwargs)
    
    def error(self, msg: str, *args, **kwargs):
        """记录ERROR级别日志（自动脱敏）"""
        self.logger.error(self._mask_message(msg), *self._mask_args(args), **kwargs)
    
    def critical(self, msg: str, *args, **kwargs):
        """记录CRITICAL级别日志（自动脱敏）"""
        self.logger.critical(self._mask_message(msg), *self._mask_args(args), **kwargs)


class SecureFileManager:
    """
    安全文件管理器
    提供密钥的安全存储功能
    """
    
    def __init__(self, masker: Optional[KeyMasker] = None):
        """
        初始化安全文件管理器
        
        Args:
            masker: 密钥脱敏器实例
        """
        self.masker = masker or KeyMasker()
    
    def save_keys_secure(self, keys: List[str], filepath: Path, 
                        include_hash: bool = True) -> None:
        """
        安全保存密钥列表（包含脱敏标识）
        
        Args:
            keys: 密钥列表
            filepath: 保存路径
            include_hash: 是否包含哈希值用于验证
        """
        filepath = Path(filepath)
        filepath.parent.mkdir(parents=True, exist_ok=True)
        
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write("# 密钥列表（已脱敏）\n")
            f.write("# 格式: 脱敏密钥#哈希前缀\n")
            f.write("# 警告: 完整密钥已被安全存储，此文件仅用于识别\n\n")
            
            for key in keys:
                if include_hash:
                    identifier = self.masker.get_key_identifier(key)
                else:
                    identifier = self.masker.mask(key)
                f.write(f"{identifier}\n")
        
        # 设置文件权限（仅所有者可读写）
        try:
            import os
            os.chmod(filepath, 0o600)
        except:
            pass  # Windows可能不支持
    
    def create_secure_report(self, stats: Dict[str, Any], filepath: Path) -> None:
        """
        创建安全的统计报告（自动脱敏敏感信息）
        
        Args:
            stats: 统计信息字典
            filepath: 报告保存路径
        """
        filepath = Path(filepath)
        filepath.parent.mkdir(parents=True, exist_ok=True)
        
        # 脱敏统计信息
        secure_stats = self.masker.mask_dict(stats)
        
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write("# 安全统计报告\n")
            f.write("# 所有敏感信息已脱敏\n\n")
            f.write(json.dumps(secure_stats, ensure_ascii=False, indent=2))


# 创建全局实例
key_masker = KeyMasker()