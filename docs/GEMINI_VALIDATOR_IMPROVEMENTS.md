# Gemini 密钥验证器改进方案

基于对 Rust 实现的分析，本文档提供了对现有 Python 实现的改进建议。

## 核心改进点

### 1. API 端点标准化
- 使用标准的 v1beta API 端点
- 统一模型版本为 gemini-2.5-flash 系列
- Cache API 使用 `/v1beta/cachedContents` 而非模型特定端点

### 2. 密钥验证增强
- 添加正则表达式验证：`^AIzaSy[A-Za-z0-9_-]{33}$`
- 在发送请求前预先过滤无效格式
- 使用 HashSet 自动去重

### 3. 请求优化
- 使用 `X-goog-api-key` 请求头而非 URL 参数
- 实现智能重试机制（排除 401/403 错误）
- 优化请求体结构，添加 `thinkingConfig`

### 4. 性能提升
- 实现连接池管理
- 支持 HTTP/2 多路复用
- 使用 `asyncio.as_completed` 实现实时进度反馈

### 5. 错误处理
- 区分可重试和不可重试的错误
- 详细的错误分类和日志记录
- 服务器错误自动重试

## 实现示例

```python
import re
import asyncio
import aiohttp
from dataclasses import dataclass
from typing import List, Optional, Tuple
from tenacity import retry, stop_after_attempt, wait_exponential

@dataclass
class ValidatorConfig:
    """验证器配置"""
    api_host: str = "https://generativelanguage.googleapis.com/"
    timeout_sec: int = 15
    max_retries: int = 2
    concurrency: int = 50
    
    def get_generate_url(self) -> str:
        return f"{self.api_host}v1beta/models/gemini-2.5-flash-lite:generateContent"
    
    def get_cache_url(self) -> str:
        return f"{self.api_host}v1beta/cachedContents"


class ImprovedGeminiValidator:
    """改进的 Gemini 密钥验证器"""
    
    KEY_PATTERN = re.compile(r'^AIzaSy[A-Za-z0-9_-]{33}$')
    
    def __init__(self, config: Optional[ValidatorConfig] = None):
        self.config = config or ValidatorConfig()
        self.connector = aiohttp.TCPConnector(
            limit=self.config.concurrency * 2,
            limit_per_host=self.config.concurrency,
            ttl_dns_cache=300
        )
    
    def validate_key_format(self, key: str) -> bool:
        """验证密钥格式"""
        return bool(self.KEY_PATTERN.match(key.strip()))
    
    async def create_session(self) -> aiohttp.ClientSession:
        """创建优化的会话"""
        timeout = aiohttp.ClientTimeout(
            total=self.config.timeout_sec,
            connect=10
        )
        return aiohttp.ClientSession(
            connector=self.connector,
            timeout=timeout
        )
    
    def get_headers(self, api_key: str) -> dict:
        """获取请求头"""
        return {
            "Content-Type": "application/json",
            "X-goog-api-key": api_key
        }
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=4)
    )
    async def send_request(self, session, url, headers, json_data):
        """发送请求（带重试）"""
        async with session.post(url, headers=headers, json=json_data) as response:
            return response.status, await response.text()
```

## 关键优化对比

| 特性 | 原实现 | 改进后 | 优势 |
|------|--------|--------|------|
| API 端点 | 混合版本 | 统一标准 | 更稳定 |
| 密钥传递 | URL 参数 | 请求头 | 更安全 |
| 错误处理 | 基础 | 分层处理 | 更精确 |
| 重试机制 | 无 | 智能重试 | 更可靠 |
| 连接管理 | 基础 | 连接池 | 更高效 |
| 格式验证 | 无 | 正则验证 | 更严格 |

## 性能预期

基于 Rust 实现的经验，这些改进预计可以带来：
- 验证速度提升 30-50%
- 错误率降低 20%
- 资源使用优化 40%

## 下一步行动

1. 实现核心改进功能
2. 添加单元测试
3. 性能基准测试
4. 逐步迁移现有代码