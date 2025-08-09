"""
配置服务实现
管理应用程序配置
"""

import os
import json
import random
from typing import Dict, Any, Optional, List
from pathlib import Path
from dotenv import load_dotenv
import logging
import sys

# 添加utils目录到Python路径
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from app.services.interfaces import IConfigService
from utils.token_hunter.manager import TokenManager, NoValidTokenError, NoQuotaError

logger = logging.getLogger(__name__)


class ConfigService(IConfigService):
    """
    配置服务实现类
    从环境变量和配置文件加载配置
    """
    
    # 默认配置值
    DEFAULTS = {
        # GitHub配置
        "GITHUB_TOKENS": "",
        "GITHUB_API_URL": "https://api.github.com/search/code",
        
        # 数据路径配置
        "DATA_PATH": "/app/data",
        "QUERIES_FILE": "queries.txt",
        "SCANNED_SHAS_FILE": "scanned_shas.txt",
        
        # 文件前缀配置
        "VALID_KEY_PREFIX": "keys/keys_valid_",
        "RATE_LIMITED_KEY_PREFIX": "keys/key_429_",
        "KEYS_SEND_PREFIX": "keys/keys_send_",
        "VALID_KEY_DETAIL_PREFIX": "logs/keys_valid_detail_",
        "RATE_LIMITED_KEY_DETAIL_PREFIX": "logs/key_429_detail_",
        "KEYS_SEND_DETAIL_PREFIX": "logs/keys_send_detail_",
        
        # 扫描配置
        "DATE_RANGE_DAYS": "730",
        "FILE_PATH_BLACKLIST": "readme,docs,doc/,.md,example,sample,tutorial,test,spec,demo,mock",
        
        # Gemini配置
        "HAJIMI_CHECK_MODEL": "gemini-2.0-flash-exp",
        
        # 代理配置
        "PROXY": "",
        
        # Gemini Balancer配置
        "GEMINI_BALANCER_SYNC_ENABLED": "false",
        "GEMINI_BALANCER_URL": "",
        "GEMINI_BALANCER_AUTH": "",
        
        # GPT Load配置
        "GPT_LOAD_SYNC_ENABLED": "false",
        "GPT_LOAD_URL": "",
        "GPT_LOAD_AUTH": "",
        "GPT_LOAD_GROUP_NAME": "",
        
        # 性能配置
        "MAX_CONCURRENT_SEARCHES": "5",
        "MAX_CONCURRENT_VALIDATIONS": "10",
        "BATCH_SIZE": "20",
        "CHECKPOINT_INTERVAL": "20",
        "LOOP_DELAY": "10",
    }
    
    def __init__(self, env_file: Optional[str] = None, override: bool = False):
        """
        初始化配置服务
        
        Args:
            env_file: .env文件路径（可选）
            override: 是否覆盖已存在的环境变量
        """
        self._config: Dict[str, Any] = {}
        self._env_file = env_file or ".env"
        self._override = override
        
        # 初始化Token管理器
        self.token_manager: Optional[TokenManager] = None
        self._init_token_manager()
        
        # 加载配置
        self.reload()
        
    def reload(self) -> None:
        """重新加载配置"""
        # 1. 加载默认配置
        self._config = self.DEFAULTS.copy()
        
        # 2. 从.env文件加载配置
        if os.path.exists(self._env_file):
            load_dotenv(self._env_file, override=self._override)
            logger.info(f"Loaded configuration from {self._env_file}")
        
        # 3. 从环境变量更新配置
        for key in self.DEFAULTS:
            env_value = os.getenv(key)
            if env_value is not None:
                self._config[key] = env_value
        
        # 4. 处理特殊配置
        self._process_special_configs()
        
        logger.info(f"Configuration loaded with {len(self._config)} settings")
    
    def _init_token_manager(self) -> None:
        """初始化Token管理器"""
        # 获取tokens文件路径
        data_path = self._config.get("DATA_PATH", "/app/data")
        tokens_file = Path(data_path) / "github_tokens.txt"
        
        try:
            self.token_manager = TokenManager(str(tokens_file), auto_validate=False)
            logger.info(f"✅ Token管理器初始化成功，从 {tokens_file} 加载了 {len(self.token_manager.tokens)} 个tokens")
        except Exception as e:
            logger.error(f"❌ Token管理器初始化失败: {e}")
            self.token_manager = None
    
    def _process_special_configs(self) -> None:
        """处理需要特殊转换的配置"""
        # 从txt文件加载GitHub tokens
        if self.token_manager and self.token_manager.tokens:
            self._config["GITHUB_TOKENS_LIST"] = self.token_manager.tokens
            logger.info(f"✅ 从github_tokens.txt加载了 {len(self.token_manager.tokens)} 个tokens")
        else:
            # 兼容旧方式：从环境变量加载
            tokens_str = self._config.get("GITHUB_TOKENS", "")
            if tokens_str:
                self._config["GITHUB_TOKENS_LIST"] = [
                    token.strip() for token in tokens_str.split(',') if token.strip()
                ]
                logger.info(f"⚠️ 从环境变量加载了 {len(self._config['GITHUB_TOKENS_LIST'])} 个tokens（建议迁移到github_tokens.txt）")
            else:
                self._config["GITHUB_TOKENS_LIST"] = []
                logger.warning("⚠️ 未找到GitHub tokens，请在data/github_tokens.txt中添加tokens")
        
        # 处理代理列表
        proxy_str = self._config.get("PROXY", "")
        if proxy_str:
            self._config["PROXY_LIST"] = [
                proxy.strip() for proxy in proxy_str.split(',') if proxy.strip()
            ]
        else:
            self._config["PROXY_LIST"] = []
        
        # 处理文件路径黑名单
        blacklist_str = self._config.get("FILE_PATH_BLACKLIST", "")
        if blacklist_str:
            self._config["FILE_PATH_BLACKLIST_LIST"] = [
                item.strip().lower() for item in blacklist_str.split(',') if item.strip()
            ]
        else:
            self._config["FILE_PATH_BLACKLIST_LIST"] = []
        
        # 处理GPT Load组名列表
        group_names_str = self._config.get("GPT_LOAD_GROUP_NAME", "")
        if group_names_str:
            self._config["GPT_LOAD_GROUP_NAMES"] = [
                name.strip() for name in group_names_str.split(',') if name.strip()
            ]
        else:
            self._config["GPT_LOAD_GROUP_NAMES"] = []
        
        # 转换数字类型
        for key in ["DATE_RANGE_DAYS", "MAX_CONCURRENT_SEARCHES", "MAX_CONCURRENT_VALIDATIONS",
                    "BATCH_SIZE", "CHECKPOINT_INTERVAL", "LOOP_DELAY"]:
            if key in self._config:
                try:
                    self._config[key] = int(self._config[key])
                except (ValueError, TypeError):
                    logger.warning(f"Failed to convert {key} to int, using default")
                    self._config[key] = int(self.DEFAULTS[key])
        
        # 转换布尔类型
        for key in ["GEMINI_BALANCER_SYNC_ENABLED", "GPT_LOAD_SYNC_ENABLED"]:
            if key in self._config:
                self._config[key] = self._parse_bool(self._config[key])
    
    def _parse_bool(self, value: Any) -> bool:
        """
        解析布尔值
        
        Args:
            value: 要解析的值
            
        Returns:
            布尔值
        """
        if isinstance(value, bool):
            return value
        
        if isinstance(value, str):
            value = value.strip().lower()
            return value in ('true', '1', 'yes', 'on', 'enabled')
        
        if isinstance(value, int):
            return bool(value)
        
        return False
    
    def get(self, key: str, default: Any = None) -> Any:
        """
        获取配置值
        
        Args:
            key: 配置键
            default: 默认值
            
        Returns:
            配置值
        """
        return self._config.get(key, default)
    
    def set(self, key: str, value: Any) -> None:
        """
        设置配置值
        
        Args:
            key: 配置键
            value: 配置值
        """
        self._config[key] = value
        # 同时更新环境变量
        os.environ[key] = str(value)
    
    def get_all(self) -> Dict[str, Any]:
        """
        获取所有配置
        
        Returns:
            配置字典
        """
        return self._config.copy()
    
    def validate(self) -> bool:
        """
        验证配置
        
        Returns:
            配置是否有效
        """
        errors = []
        
        # 检查必需的配置
        if not self.get("GITHUB_TOKENS_LIST"):
            errors.append("❌ 未配置GitHub tokens（请在data/github_tokens.txt中添加）")
        
        # 检查数据路径
        data_path = self.get("DATA_PATH")
        if not data_path:
            errors.append("❌ 未配置数据路径 (DATA_PATH)")
        
        # 检查Gemini Balancer配置
        if self.get("GEMINI_BALANCER_SYNC_ENABLED"):
            if not self.get("GEMINI_BALANCER_URL"):
                errors.append("❌ 未配置Gemini Balancer URL")
            if not self.get("GEMINI_BALANCER_AUTH"):
                errors.append("❌ 未配置Gemini Balancer认证信息")
        
        # 检查GPT Load配置
        if self.get("GPT_LOAD_SYNC_ENABLED"):
            if not self.get("GPT_LOAD_URL"):
                errors.append("❌ 未配置GPT Load URL")
            if not self.get("GPT_LOAD_AUTH"):
                errors.append("❌ 未配置GPT Load认证信息")
            if not self.get("GPT_LOAD_GROUP_NAMES"):
                errors.append("❌ 未配置GPT Load组名")
        
        # 记录错误
        if errors:
            for error in errors:
                logger.error(f"配置错误: {error}")
            return False
        
        logger.info("✅ 配置验证通过")
        return True
    
    def get_random_proxy(self) -> Optional[Dict[str, str]]:
        """
        获取随机代理配置
        
        Returns:
            代理配置字典，如果未配置则返回None
        """
        proxy_list = self.get("PROXY_LIST", [])
        if not proxy_list:
            return None
        
        proxy_url = random.choice(proxy_list)
        return {
            'http': proxy_url,
            'https': proxy_url
        }
    
    def get_github_token(self, index: Optional[int] = None) -> Optional[str]:
        """
        获取GitHub token（使用Token管理器的循环机制）
        
        Args:
            index: token索引（已废弃，保留用于兼容）
            
        Returns:
            GitHub token，如果未配置则返回None
        """
        # 优先使用Token管理器
        if self.token_manager:
            try:
                token = self.token_manager.get_next_token()
                return token
            except (NoValidTokenError, NoQuotaError) as e:
                logger.error(f"❌ 获取token失败: {e}")
                return None
        
        # 兼容旧方式
        tokens = self.get("GITHUB_TOKENS_LIST", [])
        if not tokens:
            logger.error("❌ 没有可用的GitHub tokens")
            return None
        
        if index is not None:
            return tokens[index % len(tokens)]
        
        return random.choice(tokens)
    
    def add_github_token(self, token: str, validate: bool = True) -> bool:
        """
        添加新的GitHub token
        
        Args:
            token: GitHub token
            validate: 是否验证token
            
        Returns:
            是否添加成功
        """
        if self.token_manager:
            success = self.token_manager.add_token(token, validate=validate)
            if success:
                # 更新配置中的token列表
                self._config["GITHUB_TOKENS_LIST"] = self.token_manager.tokens
                logger.info(f"✅ 成功添加新token，当前共 {len(self.token_manager.tokens)} 个tokens")
            return success
        
        logger.error("❌ Token管理器未初始化")
        return False
    
    def validate_all_tokens(self) -> Dict[str, Any]:
        """
        验证所有GitHub tokens
        
        Returns:
            验证结果
        """
        if self.token_manager:
            return self.token_manager.validate_all_tokens()
        
        logger.error("❌ Token管理器未初始化")
        return {}
    
    def get_token_status(self) -> Dict[str, Any]:
        """
        获取Token管理器状态
        
        Returns:
            状态信息
        """
        if self.token_manager:
            return self.token_manager.get_status()
        
        return {"error": "Token管理器未初始化"}
    
    def get_data_path(self, *paths: str) -> Path:
        """
        获取数据目录下的路径
        
        Args:
            *paths: 子路径组件
            
        Returns:
            完整路径
        """
        data_path = Path(self.get("DATA_PATH", "/app/data"))
        if paths:
            return data_path.joinpath(*paths)
        return data_path
    
    def ensure_data_dirs(self) -> None:
        """确保必要的数据目录存在"""
        # 主数据目录
        data_path = self.get_data_path()
        data_path.mkdir(parents=True, exist_ok=True)
        
        # 子目录
        subdirs = ["keys", "logs", "checkpoints"]
        for subdir in subdirs:
            subdir_path = data_path / subdir
            subdir_path.mkdir(parents=True, exist_ok=True)
        
        logger.info(f"Data directories ensured at {data_path}")
    
    def __repr__(self) -> str:
        """字符串表示"""
        token_count = len(self.get("GITHUB_TOKENS_LIST", []))
        proxy_count = len(self.get("PROXY_LIST", []))
        token_source = "txt文件" if self.token_manager else "环境变量"
        return (
            f"ConfigService("
            f"tokens={token_count}({token_source}), "
            f"proxies={proxy_count}, "
            f"data_path={self.get('DATA_PATH')}"
            f")"
        )


# 单例实例
_config_service: Optional[ConfigService] = None


def get_config_service() -> ConfigService:
    """
    获取配置服务单例
    
    Returns:
        配置服务实例
    """
    global _config_service
    if _config_service is None:
        _config_service = ConfigService()
    return _config_service