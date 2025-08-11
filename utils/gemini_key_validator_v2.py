"""
Gemini密钥验证器 V2 - 改进版本
基于 Rust 实现的最佳实践进行优化
"""

import asyncio
import aiohttp
import re
import json
import logging
import time
from pathlib import Path
from typing import List, Dict, Any, Tuple, Optional, Set
from datetime import datetime
from dataclasses import dataclass, field
from enum import Enum
import hashlib

# 尝试导入可选依赖
try:
    from tqdm.asyncio import tqdm
    TQDM_AVAILABLE = True
except ImportError:
    TQDM_AVAILABLE = False
    
try:
    from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
    TENACITY_AVAILABLE = True
except ImportError:
    TENACITY_AVAILABLE = False

logger = logging.getLogger(__name__)


class KeyTier(Enum):
    """密钥等级枚举"""
    FREE = "free"
    PAID = "paid"
    INVALID = "invalid"


@dataclass
class ValidatorConfig:
    """验证器配置类"""
    api_host: str = "https://generativelanguage.googleapis.com/"
    timeout_sec: int = 15
    max_retries: int = 2
    concurrency: int = 50
    enable_http2: bool = True
    proxy: Optional[str] = None
    log_level: str = "INFO"
    
    # 输出配置
    output_dir: str = "data/keys"
    save_backup: bool = True
    
    def get_generate_url(self) -> str:
        """获取生成内容API URL"""
        return f"{self.api_host}v1beta/models/gemini-2.0-flash-exp:generateContent"
    
    def get_cache_url(self) -> str:
        """获取缓存API URL"""
        return f"{self.api_host}v1beta/cachedContents"


@dataclass
class ValidatedKey:
    """验证后的密钥"""
    key: str
    tier: KeyTier
    validation_time: datetime = field(default_factory=datetime.now)
    error_message: Optional[str] = None
    
    def __hash__(self):
        return hash(self.key)


class GeminiKeyValidatorV2:
    """
    改进的 Gemini 密钥验证器
    
    主要改进：
    1. 严格的密钥格式验证
    2. 使用请求头传递密钥（更安全）
    3. 智能重试机制
    4. 连接池优化
    5. 实时进度反馈
    6. 更好的错误处理
    """
    
    # 密钥格式正则表达式
    KEY_PATTERN = re.compile(r'^AIzaSy[A-Za-z0-9_-]{33}$')
    
    def __init__(self, config: Optional[ValidatorConfig] = None):
        """
        初始化验证器
        
        Args:
            config: 验证器配置
        """
        self.config = config or ValidatorConfig()
        self.validated_keys: List[ValidatedKey] = []
        
        # 创建优化的连接器
        self.connector = aiohttp.TCPConnector(
            limit=self.config.concurrency * 2,  # 总连接数
            limit_per_host=self.config.concurrency,  # 每个主机的连接数
            ttl_dns_cache=300,  # DNS缓存时间
            enable_cleanup_closed=True  # 自动清理关闭的连接
        )
        
        # 设置日志级别
        logger.setLevel(getattr(logging, self.config.log_level.upper()))
    
    def validate_key_format(self, key: str) -> bool:
        """
        验证密钥格式
        
        Args:
            key: 待验证的密钥
            
        Returns:
            是否符合格式
        """
        return bool(self.KEY_PATTERN.match(key.strip()))
    
    def create_session(self) -> aiohttp.ClientSession:
        """
        创建优化的HTTP会话
        
        Returns:
            配置好的会话对象
        """
        timeout = aiohttp.ClientTimeout(
            total=self.config.timeout_sec,
            connect=10,
            sock_read=self.config.timeout_sec
        )
        
        # 会话配置
        session_kwargs = {
            'connector': self.connector,
            'timeout': timeout,
            'headers': {
                'User-Agent': 'GeminiKeyValidator/2.0'
            }
        }
        
        # 代理配置
        if self.config.proxy:
            session_kwargs['trust_env'] = False
            
        return aiohttp.ClientSession(**session_kwargs)
    
    def get_headers(self, api_key: str) -> Dict[str, str]:
        """
        获取请求头
        
        Args:
            api_key: API密钥
            
        Returns:
            请求头字典
        """
        return {
            "Content-Type": "application/json",
            "X-goog-api-key": api_key
        }
    
    def get_generate_test_body(self) -> Dict[str, Any]:
        """
        获取生成内容测试请求体
        
        Returns:
            请求体字典
        """
        return {
            "contents": [{
                "parts": [{
                    "text": "Hi"
                }]
            }],
            "generationConfig": {
                "temperature": 0,
                "maxOutputTokens": 1,
                "candidateCount": 1
            }
        }
    
    def get_cache_test_body(self) -> Dict[str, Any]:
        """
        获取缓存测试请求体
        
        Returns:
            请求体字典
        """
        # 使用与 Rust 实现相同的策略
        long_text = "You are an expert at analyzing transcripts." * 150
        
        return {
            "model": "models/gemini-1.5-flash",
            "contents": [{
                "parts": [{
                    "text": long_text
                }],
                "role": "user"
            }],
            "ttl": "30s"  # 短TTL，仅用于测试
        }
    
    async def send_request(self, session: aiohttp.ClientSession, url: str, 
                          headers: Dict[str, str], json_data: Dict[str, Any],
                          max_retries: int = None) -> Tuple[int, str]:
        """
        发送HTTP请求（带重试）
        
        Args:
            session: HTTP会话
            url: 请求URL
            headers: 请求头
            json_data: JSON数据
            max_retries: 最大重试次数
            
        Returns:
            (状态码, 响应文本)
        """
        max_retries = max_retries or self.config.max_retries
        
        if TENACITY_AVAILABLE and max_retries > 0:
            # 使用 tenacity 进行重试
            @retry(
                stop=stop_after_attempt(max_retries + 1),
                wait=wait_exponential(multiplier=1, min=1, max=4),
                retry=retry_if_exception_type((aiohttp.ClientError, asyncio.TimeoutError))
            )
            async def _send():
                async with session.post(url, headers=headers, json=json_data) as response:
                    return response.status, await response.text()
            
            return await _send()
        else:
            # 简单重试逻辑
            last_error = None
            for attempt in range(max_retries + 1):
                try:
                    async with session.post(url, headers=headers, json=json_data) as response:
                        return response.status, await response.text()
                except (aiohttp.ClientError, asyncio.TimeoutError) as e:
                    last_error = e
                    if attempt < max_retries:
                        await asyncio.sleep(2 ** attempt)  # 指数退避
                    continue
            
            raise last_error
    
    async def test_generate_content_api(self, session: aiohttp.ClientSession, 
                                      api_key: str) -> Tuple[bool, Optional[str]]:
        """
        测试基础生成API
        
        Args:
            session: HTTP会话
            api_key: 要测试的密钥
            
        Returns:
            (是否有效, 错误信息)
        """
        url = self.config.get_generate_url()
        headers = self.get_headers(api_key)
        body = self.get_generate_test_body()
        
        try:
            status, response_text = await self.send_request(
                session, url, headers, body,
                max_retries=self.config.max_retries
            )
            
            if status == 200:
                logger.info(f"✅ VALID - {api_key[:10]}... - 基础API测试通过")
                return True, None
            elif status == 400:
                logger.warning(f"❌ BAD REQUEST - {api_key[:10]}... - 请求格式错误")
                return False, f"HTTP 400: Bad Request"
            elif status in [401, 403]:
                logger.warning(f"❌ UNAUTHORIZED - {api_key[:10]}... - 密钥无效")
                return False, f"HTTP {status}: Unauthorized/Forbidden"
            elif status == 429:
                # 429 对于基础API仍然表示密钥有效
                logger.info(f"⚠️ RATE LIMITED - {api_key[:10]}... - 速率限制但密钥有效")
                return True, None
            elif 500 <= status < 600:
                logger.error(f"❌ SERVER ERROR - {api_key[:10]}... - HTTP {status}")
                return False, f"HTTP {status}: Server Error"
            else:
                logger.error(f"❌ UNKNOWN ERROR - {api_key[:10]}... - HTTP {status}")
                return False, f"HTTP {status}: Unknown Error"
                
        except asyncio.TimeoutError:
            logger.error(f"⏱️ TIMEOUT - {api_key[:10]}...")
            return False, "Request Timeout"
        except Exception as e:
            logger.error(f"❌ ERROR - {api_key[:10]}... - {type(e).__name__}: {e}")
            return False, f"{type(e).__name__}: {str(e)}"
    
    async def test_cache_content_api(self, session: aiohttp.ClientSession, 
                                   api_key: str) -> bool:
        """
        测试Cache API（付费版功能）
        
        Args:
            session: HTTP会话
            api_key: 要测试的密钥
            
        Returns:
            是否为付费版
        """
        url = self.config.get_cache_url()
        headers = self.get_headers(api_key)
        body = self.get_cache_test_body()
        
        try:
            # Cache API 不需要重试，因为我们只是检查访问权限
            status, _ = await self.send_request(
                session, url, headers, body, max_retries=0
            )
            
            if status == 200:
                logger.info(f"💎 PAID KEY - {api_key[:10]}... - Cache API可访问")
                return True
            elif status == 429:
                logger.info(f"🆓 FREE KEY - {api_key[:10]}... - Cache API速率限制")
                return False
            else:
                logger.debug(f"Cache API响应: {api_key[:10]}... - HTTP {status}")
                return False
                
        except Exception as e:
            logger.debug(f"Cache API错误: {api_key[:10]}... - {e}")
            return False
    
    async def validate_key(self, session: aiohttp.ClientSession, 
                          api_key: str) -> ValidatedKey:
        """
        验证单个密钥
        
        Args:
            session: HTTP会话
            api_key: 要验证的密钥
            
        Returns:
            验证结果
        """
        # 格式验证
        if not self.validate_key_format(api_key):
            logger.warning(f"❌ INVALID FORMAT - {api_key[:10]}...")
            return ValidatedKey(key=api_key, tier=KeyTier.INVALID, 
                              error_message="Invalid key format")
        
        # 第一步：测试基础API
        is_valid, error_msg = await self.test_generate_content_api(session, api_key)
        
        if not is_valid:
            return ValidatedKey(key=api_key, tier=KeyTier.INVALID, 
                              error_message=error_msg)
        
        # 第二步：测试Cache API（判断是否付费版）
        is_paid = await self.test_cache_content_api(session, api_key)
        
        tier = KeyTier.PAID if is_paid else KeyTier.FREE
        return ValidatedKey(key=api_key, tier=tier)
    
    async def validate_keys_batch(self, keys: List[str], 
                                show_progress: bool = True) -> Dict[str, Any]:
        """
        批量验证密钥
        
        Args:
            keys: 密钥列表
            show_progress: 是否显示进度条
            
        Returns:
            验证结果统计
        """
        start_time = time.time()
        
        # 去重和格式预验证
        unique_keys = list(set(key.strip() for key in keys if key.strip()))
        logger.info(f"🔍 开始批量验证 {len(unique_keys)} 个唯一密钥...")
        
        # 清空之前的结果
        self.validated_keys.clear()
        
        async with self.create_session() as session:
            # 创建验证任务
            tasks = [self.validate_key(session, key) for key in unique_keys]
            
            # 根据是否有tqdm决定如何显示进度
            if show_progress and TQDM_AVAILABLE:
                # 使用tqdm显示进度
                results = []
                async for task in tqdm.as_completed(tasks, total=len(tasks), 
                                                   desc="验证进度"):
                    result = await task
                    results.append(result)
                    self.validated_keys.append(result)
            else:
                # 使用 asyncio.as_completed 实现简单进度
                results = []
                completed = 0
                for task in asyncio.as_completed(tasks):
                    result = await task
                    results.append(result)
                    self.validated_keys.append(result)
                    completed += 1
                    if show_progress and completed % 10 == 0:
                        logger.info(f"进度: {completed}/{len(tasks)}")
        
        # 统计结果
        paid_keys = [vk for vk in self.validated_keys if vk.tier == KeyTier.PAID]
        free_keys = [vk for vk in self.validated_keys if vk.tier == KeyTier.FREE]
        invalid_keys = [vk for vk in self.validated_keys if vk.tier == KeyTier.INVALID]
        
        elapsed_time = time.time() - start_time
        
        stats = {
            "total": len(unique_keys),
            "valid": len(paid_keys) + len(free_keys),
            "paid": len(paid_keys),
            "free": len(free_keys),
            "invalid": len(invalid_keys),
            "elapsed_time": elapsed_time,
            "keys_per_second": len(unique_keys) / elapsed_time if elapsed_time > 0 else 0
        }
        
        logger.info(f"✅ 验证完成: {stats['valid']}/{stats['total']} 有效 "
                   f"({stats['paid']} 付费, {stats['free']} 免费) - "
                   f"耗时 {elapsed_time:.2f}秒")
        
        return stats
    
    async def save_results(self, output_dir: Optional[str] = None):
        """
        保存验证结果到文件
        
        Args:
            output_dir: 输出目录
        """
        output_dir = output_dir or self.config.output_dir
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        
        timestamp = datetime.now()
        date_str = timestamp.strftime('%Y%m%d')
        datetime_str = timestamp.strftime('%Y%m%d_%H%M%S')
        
        # 分类保存
        paid_keys = [vk for vk in self.validated_keys if vk.tier == KeyTier.PAID]
        free_keys = [vk for vk in self.validated_keys if vk.tier == KeyTier.FREE]
        valid_keys = paid_keys + free_keys
        
        # 保存付费密钥
        if paid_keys:
            paid_file = output_path / f"keys_paid_{date_str}.txt"
            with open(paid_file, 'w', encoding='utf-8') as f:
                f.write(f"# 付费版Gemini密钥\n")
                f.write(f"# 验证时间: {timestamp.strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write(f"# 总计: {len(paid_keys)} 个\n\n")
                for vk in paid_keys:
                    f.write(f"{vk.key}\n")
            logger.info(f"💎 保存 {len(paid_keys)} 个付费密钥到: {paid_file}")
        
        # 保存免费密钥
        if free_keys:
            free_file = output_path / f"keys_free_{date_str}.txt"
            with open(free_file, 'w', encoding='utf-8') as f:
                f.write(f"# 免费版Gemini密钥\n")
                f.write(f"# 验证时间: {timestamp.strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write(f"# 总计: {len(free_keys)} 个\n\n")
                for vk in free_keys:
                    f.write(f"{vk.key}\n")
            logger.info(f"🆓 保存 {len(free_keys)} 个免费密钥到: {free_file}")
        
        # 保存备份（所有有效密钥）
        if self.config.save_backup and valid_keys:
            backup_file = output_path / f"keys_backup_{datetime_str}.txt"
            with open(backup_file, 'w', encoding='utf-8') as f:
                f.write(f"# 所有有效Gemini密钥备份\n")
                f.write(f"# 验证时间: {timestamp.strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write(f"# 总计: {len(valid_keys)} 个 ({len(paid_keys)} 付费, {len(free_keys)} 免费)\n\n")
                for vk in valid_keys:
                    f.write(f"{vk.key}\n")
            logger.info(f"💾 保存备份到: {backup_file}")
        
        # 保存详细报告（JSON格式）
        report_file = output_path / f"keys_validation_report_{datetime_str}.json"
        report_data = {
            "validation_time": timestamp.isoformat(),
            "statistics": {
                "total_validated": len(self.validated_keys),
                "valid": len(valid_keys),
                "paid": len(paid_keys),
                "free": len(free_keys),
                "invalid": len(self.validated_keys) - len(valid_keys)
            },
            "keys": {
                "paid": [vk.key for vk in paid_keys],
                "free": [vk.key for vk in free_keys],
                "invalid": [
                    {
                        "key": vk.key[:10] + "...",  # 隐藏部分密钥
                        "error": vk.error_message
                    } 
                    for vk in self.validated_keys if vk.tier == KeyTier.INVALID
                ]
            }
        }
        
        with open(report_file, 'w', encoding='utf-8') as f:
            json.dump(report_data, f, indent=2, ensure_ascii=False)
        logger.info(f"📊 保存详细报告到: {report_file}")
    
    async def __aenter__(self):
        """异步上下文管理器入口"""
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """异步上下文管理器退出"""
        await self.connector.close()


async def validate_keys_from_file(file_path: str, 
                                config: Optional[ValidatorConfig] = None,
                                save_results: bool = True) -> Dict[str, Any]:
    """
    从文件验证密钥的便捷函数
    
    Args:
        file_path: 密钥文件路径
        config: 验证器配置
        save_results: 是否保存结果
        
    Returns:
        验证结果统计
    """
    # 读取密钥
    keys = []
    file_path = Path(file_path)
    
    if not file_path.exists():
        logger.error(f"文件不存在: {file_path}")
        return {}
    
    with open(file_path, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#'):
                keys.append(line)
    
    if not keys:
        logger.warning("没有找到有效密钥")
        return {}
    
    logger.info(f"📋 从 {file_path} 加载了 {len(keys)} 个密钥")
    
    # 创建验证器并验证
    async with GeminiKeyValidatorV2(config) as validator:
        stats = await validator.validate_keys_batch(keys)
        
        if save_results:
            await validator.save_results()
    
    return stats


def setup_logging(level: str = "INFO"):
    """
    设置日志配置
    
    Args:
        level: 日志级别
    """
    logging.basicConfig(
        level=getattr(logging, level.upper()),
        format='%(asctime)s | %(name)s | %(levelname)s | %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )


if __name__ == "__main__":
    import sys
    
    # 设置日志
    setup_logging("INFO")
    
    # 命令行使用
    if len(sys.argv) > 1:
        file_path = sys.argv[1]
        
        # 可选配置
        config = ValidatorConfig(
            concurrency=100,  # 高并发
            timeout_sec=20,
            max_retries=2
        )
        
        # 运行验证
        stats = asyncio.run(validate_keys_from_file(file_path, config))
        
        if stats:
            print("\n" + "="*60)
            print("验证结果统计:")
            print(f"  总计: {stats['total']} 个")
            print(f"  有效: {stats['valid']} 个")
            print(f"  💎 付费: {stats['paid']} 个")
            print(f"  🆓 免费: {stats['free']} 个")
            print(f"  ❌ 无效: {stats['invalid']} 个")
            print(f"  ⏱️  耗时: {stats['elapsed_time']:.2f} 秒")
            print(f"  🚀 速度: {stats['keys_per_second']:.2f} 个/秒")
            print("="*60)
    else:
        print("使用方法: python gemini_key_validator_v2.py <密钥文件路径>")
        print("示例: python gemini_key_validator_v2.py keys.txt")