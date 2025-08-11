"""
安全工具模块 - 密钥脱敏、权限控制、安全存储
"""

import os
import hashlib
import hmac
import json
import re
from pathlib import Path
from typing import Optional, Dict, Any, List, Tuple
import logging
import tempfile
from functools import wraps

logger = logging.getLogger(__name__)

# 敏感信息模式列表
SENSITIVE_PATTERNS: List[Tuple[str, str]] = [
    (r'AIzaSy[A-Za-z0-9_-]{33}', 'GEMINI_KEY'),  # Gemini API keys
    (r'github_pat_[A-Za-z0-9_]{82}', 'GITHUB_PAT'),  # GitHub PAT tokens
    (r'ghp_[A-Za-z0-9]{36}', 'GITHUB_TOKEN'),  # GitHub tokens
    (r'ghs_[A-Za-z0-9]{36}', 'GITHUB_SECRET'),  # GitHub secrets
    (r'Bearer [A-Za-z0-9\-._~+/]+=*', 'BEARER_TOKEN'),  # Bearer tokens
    (r'sk-[A-Za-z0-9]{48}', 'OPENAI_KEY'),  # OpenAI keys
    (r'token=[A-Za-z0-9_\-]{20,}', 'API_TOKEN'),  # Generic API tokens
    (r'api[_-]?key=[A-Za-z0-9_\-]{20,}', 'API_KEY'),  # Generic API keys
]


class SecurityConfig:
    """安全配置"""
    MASK_PATTERN = "{prefix}…{suffix}"  # 脱敏模式
    PREFIX_LENGTH = 6  # 前缀长度
    SUFFIX_LENGTH = 4  # 后缀长度
    MIN_KEY_LENGTH = 12  # 最小密钥长度（低于此长度全部遮蔽）
    SECRETS_DIR_MODE = 0o700  # secrets目录权限
    SECRETS_FILE_MODE = 0o600  # secrets文件权限
    ALLOW_PLAINTEXT = False  # 是否允许明文存储
    HMAC_SALT = os.environ.get("HMAC_SALT", "default_salt_change_me")  # HMAC盐值


def mask_key(key: str, prefix_len: int = None, suffix_len: int = None) -> str:
    """
    脱敏密钥
    
    Args:
        key: 原始密钥
        prefix_len: 前缀长度（默认使用配置）
        suffix_len: 后缀长度（默认使用配置）
        
    Returns:
        脱敏后的密钥
    """
    if not key:
        return ""
    
    prefix_len = prefix_len or SecurityConfig.PREFIX_LENGTH
    suffix_len = suffix_len or SecurityConfig.SUFFIX_LENGTH
    
    # 如果密钥太短，全部遮蔽
    if len(key) < SecurityConfig.MIN_KEY_LENGTH:
        return "***MASKED***"
    
    # 确保不会暴露太多信息
    if prefix_len + suffix_len >= len(key) - 3:
        # 如果前后缀加起来几乎是整个密钥，减少暴露
        prefix_len = min(3, len(key) // 3)
        suffix_len = min(2, len(key) // 3)
    
    prefix = key[:prefix_len]
    suffix = key[-suffix_len:] if suffix_len > 0 else ""
    
    return f"{prefix}…{suffix}"


def mask_sensitive_data(text: str, patterns: List[Tuple[str, str]] = None) -> str:
    """
    自动检测并脱敏文本中的敏感信息
    
    Args:
        text: 原始文本
        patterns: 自定义敏感模式列表
        
    Returns:
        脱敏后的文本
    """
    if not text:
        return text
    
    patterns = patterns or SENSITIVE_PATTERNS
    masked_text = text
    
    for pattern, label in patterns:
        regex = re.compile(pattern, re.IGNORECASE)
        matches = regex.findall(masked_text)
        for match in matches:
            # 保留前6个字符用于识别
            if len(match) > 12:
                masked = match[:6] + '***' + match[-4:]
            else:
                masked = match[:3] + '***' if len(match) > 3 else '***'
            masked_text = masked_text.replace(match, f"[{label}:{masked}]")
    
    return masked_text


def mask_dict(data: Dict[str, Any], sensitive_keys: List[str] = None) -> Dict[str, Any]:
    """
    递归脱敏字典中的敏感字段
    
    Args:
        data: 原始字典
        sensitive_keys: 敏感字段名列表
        
    Returns:
        脱敏后的字典
    """
    if sensitive_keys is None:
        sensitive_keys = [
            'key', 'token', 'password', 'secret', 'api_key', 
            'apikey', 'auth', 'credential', 'private'
        ]
    
    def is_sensitive(key_name: str) -> bool:
        """判断字段名是否敏感"""
        key_lower = key_name.lower()
        return any(sensitive in key_lower for sensitive in sensitive_keys)
    
    def mask_value(value: Any) -> Any:
        """递归脱敏值"""
        if isinstance(value, str):
            return value  # 字符串值由外层决定是否脱敏
        elif isinstance(value, dict):
            return mask_dict(value, sensitive_keys)
        elif isinstance(value, list):
            return [mask_value(item) for item in value]
        else:
            return value
    
    masked = {}
    for key, value in data.items():
        if is_sensitive(key) and isinstance(value, str):
            masked[key] = mask_key(value)
        else:
            masked[key] = mask_value(value)
    
    return masked


def compute_hmac(key: str, salt: str = None) -> str:
    """
    计算密钥的 HMAC
    
    Args:
        key: 原始密钥
        salt: 盐值（默认使用配置）
        
    Returns:
        HMAC 值（十六进制）
    """
    salt = salt or SecurityConfig.HMAC_SALT
    return hmac.new(
        salt.encode('utf-8'),
        key.encode('utf-8'),
        hashlib.sha256
    ).hexdigest()


def secure_write_file(path: Path, content: str, mode: int = None) -> None:
    """
    安全写入文件（设置权限）
    
    Args:
        path: 文件路径
        content: 文件内容
        mode: 文件权限（默认 0o600）
    """
    mode = mode or SecurityConfig.SECRETS_FILE_MODE
    
    # 确保父目录存在且权限正确
    path.parent.mkdir(parents=True, exist_ok=True)
    
    # 如果是 secrets 目录，设置目录权限
    if 'secrets' in path.parts:
        secrets_dir = path.parent
        os.chmod(secrets_dir, SecurityConfig.SECRETS_DIR_MODE)
    
    # 原子写入
    with tempfile.NamedTemporaryFile(
        mode='w',
        delete=False,
        dir=str(path.parent),
        encoding='utf-8'
    ) as tf:
        tf.write(content)
        temp_path = Path(tf.name)
    
    # 设置权限
    os.chmod(temp_path, mode)
    
    # 原子替换
    os.replace(temp_path, path)
    
    logger.debug(f"Securely wrote file: {path} (mode: {oct(mode)})")


class SecureKeyStorage:
    """安全密钥存储"""
    
    def __init__(self, run_dir: Path, allow_plaintext: bool = None):
        """
        初始化安全存储
        
        Args:
            run_dir: 运行目录
            allow_plaintext: 是否允许明文（默认使用配置）
        """
        self.run_dir = run_dir
        self.secrets_dir = run_dir / "secrets"
        self.allow_plaintext = (
            allow_plaintext if allow_plaintext is not None 
            else SecurityConfig.ALLOW_PLAINTEXT
        )
        
        # 创建 secrets 目录
        self.secrets_dir.mkdir(parents=True, exist_ok=True)
        os.chmod(self.secrets_dir, SecurityConfig.SECRETS_DIR_MODE)
    
    def save_keys(self, keys_by_status: Dict[str, List[str]]) -> Dict[str, Path]:
        """
        保存密钥（根据配置决定明文或 HMAC）
        
        Args:
            keys_by_status: 按状态分组的密钥
            
        Returns:
            保存的文件路径字典
        """
        saved_files = {}
        
        for status, keys in keys_by_status.items():
            if not keys:
                continue
            
            if self.allow_plaintext:
                # 明文模式（仅在 secrets 目录，严格权限）
                file_path = self.secrets_dir / f"keys_{status.lower()}.txt"
                content = "\n".join(sorted(keys))
                secure_write_file(file_path, content)
                saved_files[status] = file_path
                logger.info(f"💾 Saved {len(keys)} {status} keys (plaintext) to: {file_path}")
            else:
                # HMAC 模式（可以存在普通目录）
                file_path = self.run_dir / f"keys_{status.lower()}_hmac.json"
                hmac_data = {
                    "count": len(keys),
                    "hmacs": [compute_hmac(key) for key in sorted(keys)],
                    "masked_samples": [mask_key(key) for key in sorted(keys)[:3]]  # 前3个样本
                }
                
                with open(file_path, 'w', encoding='utf-8') as f:
                    json.dump(hmac_data, f, indent=2)
                
                saved_files[status] = file_path
                logger.info(f"🔒 Saved {len(keys)} {status} keys (HMAC) to: {file_path}")
        
        return saved_files
    
    def save_masked_summary(self, keys_by_status: Dict[str, List[str]]) -> Path:
        """
        保存脱敏摘要（始终脱敏，可公开）
        
        Args:
            keys_by_status: 按状态分组的密钥
            
        Returns:
            摘要文件路径
        """
        summary_file = self.run_dir / "keys_summary.json"
        
        summary = {}
        for status, keys in keys_by_status.items():
            summary[status] = {
                "count": len(keys),
                "masked_keys": [mask_key(key) for key in sorted(keys)]
            }
        
        with open(summary_file, 'w', encoding='utf-8') as f:
            json.dump(summary, f, indent=2, ensure_ascii=False)
        
        logger.info(f"📋 Saved masked summary to: {summary_file}")
        return summary_file


class SecureLogger:
    """安全日志装饰器"""
    
    @staticmethod
    def mask_args(*mask_positions, **mask_kwargs):
        """
        装饰器：自动脱敏函数参数
        
        Args:
            mask_positions: 需要脱敏的位置参数索引
            mask_kwargs: 需要脱敏的关键字参数名
        """
        def decorator(func):
            @wraps(func)
            def wrapper(*args, **kwargs):
                # 脱敏位置参数
                masked_args = list(args)
                for pos in mask_positions:
                    if pos < len(masked_args) and isinstance(masked_args[pos], str):
                        masked_args[pos] = mask_key(masked_args[pos])
                
                # 脱敏关键字参数
                masked_kwargs = kwargs.copy()
                for kwarg in mask_kwargs:
                    if kwarg in masked_kwargs and isinstance(masked_kwargs[kwarg], str):
                        masked_kwargs[kwarg] = mask_key(masked_kwargs[kwarg])
                
                # 记录脱敏后的调用
                logger.debug(f"Calling {func.__name__} with masked args: {masked_args}, kwargs: {masked_kwargs}")
                
                # 调用原函数（使用原始参数）
                return func(*args, **kwargs)
            
            return wrapper
        return decorator


def setup_secure_logging():
    """设置安全日志（全局配置）"""
    
    class MaskingFormatter(logging.Formatter):
        """脱敏格式化器"""
        
        def format(self, record):
            # 检查消息中是否包含密钥模式
            msg = super().format(record)
            
            # 使用增强的脱敏功能
            msg = mask_sensitive_data(msg)
            
            return msg
    
    # 应用到所有处理器
    for handler in logging.root.handlers:
        handler.setFormatter(MaskingFormatter(
            '%(asctime)s | %(levelname)s | %(name)s | %(message)s'
        ))
    
    logger.info("🔒 Secure logging configured")


class SecureLogFilter(logging.Filter):
    """
    安全日志过滤器，自动脱敏敏感信息
    """
    
    def filter(self, record: logging.LogRecord) -> bool:
        """
        过滤日志记录，脱敏敏感信息
        
        Args:
            record: 日志记录
            
        Returns:
            是否允许记录
        """
        # 脱敏消息中的密钥
        if hasattr(record, 'msg'):
            record.msg = mask_sensitive_data(str(record.msg))
        
        # 脱敏参数中的密钥
        if hasattr(record, 'args') and record.args:
            record.args = tuple(
                mask_sensitive_data(str(arg)) if isinstance(arg, str) else arg
                for arg in record.args
            )
        
        return True


def validate_environment():
    """验证安全环境配置"""
    warnings = []
    
    # 检查 HMAC 盐值
    if SecurityConfig.HMAC_SALT == "default_salt_change_me":
        warnings.append("⚠️ Using default HMAC salt - set HMAC_SALT environment variable")
    
    # 检查文件权限（仅 Unix）
    if os.name == 'posix':
        umask = os.umask(0)
        os.umask(umask)
        if umask & 0o077 != 0o077:
            warnings.append(f"⚠️ Insecure umask: {oct(umask)} - recommend 0o077")
    
    # 检查明文配置
    if SecurityConfig.ALLOW_PLAINTEXT:
        warnings.append("⚠️ Plaintext storage enabled - keys will be saved unencrypted")
    
    # 检查是否有硬编码的密钥
    if Path("config").exists():
        for config_file in Path("config").glob("*.json"):
            try:
                with open(config_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                    # 使用更严格的检测
                    for pattern, label in SENSITIVE_PATTERNS:
                        if re.search(pattern, content, re.IGNORECASE):
                            warnings.append(f"⚠️ Config file {config_file} may contain hardcoded {label}")
                            break
            except Exception as e:
                logger.debug(f"Could not check {config_file}: {e}")
    
    # 检查日志文件中的敏感信息
    log_dir = Path("logs")
    if log_dir.exists():
        for log_file in log_dir.glob("*.log"):
            try:
                with open(log_file, 'r', encoding='utf-8', errors='ignore') as f:
                    # 只读前100KB避免内存问题
                    content = f.read(1024 * 100)
                    for pattern, label in SENSITIVE_PATTERNS:
                        if re.search(pattern, content, re.IGNORECASE):
                            warnings.append(f"⚠️ Log file {log_file} contains unmasked {label}")
                            # 自动脱敏日志文件
                            logger.info(f"🔒 Sanitizing log file {log_file}...")
                            sanitize_log_file(log_file)
                            break
            except Exception as e:
                logger.debug(f"Could not check {log_file}: {e}")
    
    if warnings:
        for warning in warnings:
            logger.warning(warning)
    else:
        logger.info("✅ Security environment validated")
    
    return len(warnings) == 0


def sanitize_log_file(log_path: Path, backup: bool = True):
    """
    脱敏日志文件中的敏感信息
    
    Args:
        log_path: 日志文件路径
        backup: 是否备份原文件
    """
    try:
        # 读取文件内容
        with open(log_path, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
        
        # 脱敏内容
        sanitized_content = mask_sensitive_data(content)
        
        # 如果内容没有变化，跳过
        if content == sanitized_content:
            logger.debug(f"No sensitive data found in {log_path}")
            return
        
        # 备份原文件
        if backup:
            backup_path = log_path.with_suffix('.log.bak')
            counter = 1
            while backup_path.exists():
                backup_path = log_path.with_suffix(f'.log.bak{counter}')
                counter += 1
            log_path.rename(backup_path)
            logger.info(f"📁 Original log backed up to {backup_path}")
        
        # 写入脱敏后的内容
        with open(log_path, 'w', encoding='utf-8') as f:
            f.write(sanitized_content)
        
        logger.info(f"✅ Log file sanitized: {log_path}")
        
    except Exception as e:
        logger.error(f"Failed to sanitize log file {log_path}: {e}")


def install_global_filter():
    """
    安装全局日志过滤器，自动脱敏所有日志
    """
    # 创建安全过滤器
    secure_filter = SecureLogFilter()
    
    # 添加到根日志器
    logging.root.addFilter(secure_filter)
    
    # 添加到所有现有的处理器
    for handler in logging.root.handlers:
        handler.addFilter(secure_filter)
    
    logger.info("🔒 Global secure log filter installed")


# 使用示例
if __name__ == "__main__":
    # 配置日志
    logging.basicConfig(level=logging.DEBUG)
    
    # 设置安全日志
    setup_secure_logging()
    
    # 验证环境
    validate_environment()
    
    # 测试脱敏
    test_key = "AIzaSyBxZJpQpK0H4lI7YkVr_lZdj9Ns8VYK1co"
    print(f"Original: {test_key}")
    print(f"Masked: {mask_key(test_key)}")
    
    # 测试 HMAC
    print(f"HMAC: {compute_hmac(test_key)}")
    
    # 测试安全存储
    test_dir = Path("test_secure_storage")
    storage = SecureKeyStorage(test_dir, allow_plaintext=False)
    
    test_keys = {
        "VALID_FREE": [test_key, "AIzaSyC9dbBQZDWpOHFDk7tz_DAacoWOBKBuQmY"],
        "VALID_PAID": ["AIzaSyCCivpqHJ-TLG_4lIKyWMFQHZNBr7O7GuY"]
    }
    
    storage.save_keys(test_keys)
    storage.save_masked_summary(test_keys)