# Gemini 密钥验证器 V2 使用指南

## 概述

Gemini 密钥验证器 V2 是基于 Rust 实现最佳实践的改进版本，提供了更高的性能、更好的可靠性和更丰富的功能。

## 主要特性

- ✅ **严格的密钥格式验证**：使用正则表达式 `^AIzaSy[A-Za-z0-9_-]{33}$`
- 🔒 **安全的密钥传递**：使用 `X-goog-api-key` 请求头
- 🔄 **智能重试机制**：自动重试可恢复的错误
- 🚀 **高性能并发**：支持自定义并发级别和连接池优化
- 📊 **实时进度反馈**：可选的进度条显示
- 💎 **付费密钥识别**：通过 Cache API 自动识别付费版本
- 📁 **灵活的输出格式**：支持分类保存和 JSON 报告

## 安装依赖

```bash
# 基础依赖
pip install aiohttp

# 可选依赖（推荐安装）
pip install tqdm  # 进度条显示
pip install tenacity  # 高级重试机制
```

## 快速开始

### 1. 基本使用

```python
import asyncio
from utils.gemini_key_validator_v2 import GeminiKeyValidatorV2, ValidatorConfig

async def validate_my_keys():
    # 创建配置
    config = ValidatorConfig(
        concurrency=50,  # 并发数
        timeout_sec=15,  # 超时时间
        max_retries=2    # 重试次数
    )
    
    # 要验证的密钥
    keys = [
        "AIzaSyABCDEFGHIJKLMNOPQRSTUVWXYZ1234567",
        "AIzaSyZYXWVUTSRQPONMLKJIHGFEDCBA9876543"
    ]
    
    # 创建验证器并验证
    async with GeminiKeyValidatorV2(config) as validator:
        stats = await validator.validate_keys_batch(keys)
        
        # 保存结果
        await validator.save_results()
        
        print(f"验证完成: {stats}")

# 运行
asyncio.run(validate_my_keys())
```

### 2. 从文件验证

```python
import asyncio
from utils.gemini_key_validator_v2 import validate_keys_from_file, ValidatorConfig

async def main():
    # 自定义配置
    config = ValidatorConfig(
        concurrency=100,     # 高并发
        timeout_sec=20,      # 较长超时
        output_dir="results" # 自定义输出目录
    )
    
    # 从文件验证
    stats = await validate_keys_from_file(
        "keys.txt",
        config=config,
        save_results=True
    )
    
    if stats:
        print(f"验证结果:")
        print(f"  总计: {stats['total']} 个")
        print(f"  付费: {stats['paid']} 个")
        print(f"  免费: {stats['free']} 个")
        print(f"  无效: {stats['invalid']} 个")
        print(f"  速度: {stats['keys_per_second']:.2f} 个/秒")

asyncio.run(main())
```

### 3. 命令行使用

```bash
# 基本使用
python utils/gemini_key_validator_v2.py keys.txt

# 输出示例：
# 2024-01-15 10:30:45 | __main__ | INFO | 📋 从 keys.txt 加载了 100 个密钥
# 2024-01-15 10:30:45 | __main__ | INFO | 🔍 开始批量验证 95 个唯一密钥...
# 验证进度: 100%|████████████| 95/95 [00:15<00:00, 6.21it/s]
# ...
```

## 高级配置

### ValidatorConfig 参数说明

```python
@dataclass
class ValidatorConfig:
    # API配置
    api_host: str = "https://generativelanguage.googleapis.com/"  # API主机
    timeout_sec: int = 15      # 请求超时（秒）
    max_retries: int = 2       # 最大重试次数
    
    # 性能配置
    concurrency: int = 50      # 并发请求数
    enable_http2: bool = True  # 启用HTTP/2
    
    # 代理配置
    proxy: Optional[str] = None  # 代理URL，如 "http://proxy:8080"
    
    # 输出配置
    output_dir: str = "data/keys"  # 输出目录
    save_backup: bool = True       # 是否保存备份
    
    # 日志配置
    log_level: str = "INFO"    # 日志级别：DEBUG, INFO, WARNING, ERROR
```

### 使用代理

```python
config = ValidatorConfig(
    proxy="http://username:password@proxy.example.com:8080"
)
```

### 自定义 API 端点

```python
config = ValidatorConfig(
    api_host="https://your-custom-endpoint.com/"
)
```

## 输出文件说明

验证完成后，会生成以下文件：

1. **keys_paid_YYYYMMDD.txt** - 付费密钥列表
2. **keys_free_YYYYMMDD.txt** - 免费密钥列表
3. **keys_backup_YYYYMMDD_HHMMSS.txt** - 所有有效密钥备份
4. **keys_validation_report_YYYYMMDD_HHMMSS.json** - 详细验证报告

### JSON 报告格式

```json
{
  "validation_time": "2024-01-15T10:30:45.123456",
  "statistics": {
    "total_validated": 100,
    "valid": 85,
    "paid": 10,
    "free": 75,
    "invalid": 15
  },
  "keys": {
    "paid": ["AIzaSy...", "AIzaSy..."],
    "free": ["AIzaSy...", "AIzaSy..."],
    "invalid": [
      {
        "key": "AIzaSyABC...",
        "error": "HTTP 401: Unauthorized"
      }
    ]
  }
}
```

## 集成到现有项目

### 1. 替换原有验证器

```python
# 原代码
from utils.gemini_key_validator import GeminiKeyValidator

# 改为
from utils.gemini_key_validator_v2 import GeminiKeyValidatorV2 as GeminiKeyValidator
```

### 2. 在退出时验证

```python
import atexit
import asyncio
from utils.gemini_key_validator_v2 import validate_keys_from_file

def validate_on_exit():
    """程序退出时验证密钥"""
    # 查找今天的密钥文件
    from datetime import datetime
    date_str = datetime.now().strftime('%Y%m%d')
    keys_file = f"data/keys/keys_valid_{date_str}.txt"
    
    if Path(keys_file).exists():
        # 运行异步验证
        asyncio.run(validate_keys_from_file(keys_file))

# 注册退出处理
atexit.register(validate_on_exit)
```

### 3. 与现有系统集成

```python
class KeyManager:
    def __init__(self):
        self.validator = GeminiKeyValidatorV2(
            ValidatorConfig(concurrency=100)
        )
    
    async def validate_new_keys(self, keys: List[str]):
        """验证新发现的密钥"""
        async with self.validator:
            stats = await self.validator.validate_keys_batch(keys)
            
            # 获取付费密钥
            paid_keys = [
                vk.key for vk in self.validator.validated_keys 
                if vk.tier == KeyTier.PAID
            ]
            
            return paid_keys
```

## 性能优化建议

### 1. 并发级别调整

- **稳定网络**：`concurrency=100-200`
- **普通网络**：`concurrency=50-100`
- **不稳定网络**：`concurrency=20-50`

### 2. 超时设置

- **快速验证**：`timeout_sec=10`
- **标准验证**：`timeout_sec=15`
- **稳定验证**：`timeout_sec=30`

### 3. 批量大小

建议每批处理 500-1000 个密钥，避免内存占用过高：

```python
async def validate_large_file(file_path: str):
    keys = []
    with open(file_path) as f:
        for line in f:
            keys.append(line.strip())
            
            # 每 500 个密钥验证一次
            if len(keys) >= 500:
                await validate_batch(keys)
                keys.clear()
    
    # 验证剩余的密钥
    if keys:
        await validate_batch(keys)
```

## 故障排除

### 1. 连接错误

```python
# 增加超时和重试
config = ValidatorConfig(
    timeout_sec=30,
    max_retries=5
)
```

### 2. 速率限制

```python
# 降低并发数
config = ValidatorConfig(
    concurrency=10  # 降低并发
)
```

### 3. 代理问题

```python
# 测试代理连接
import aiohttp

async def test_proxy():
    proxy = "http://proxy:8080"
    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(
                "https://www.google.com", 
                proxy=proxy
            ) as resp:
                print(f"代理测试: {resp.status}")
        except Exception as e:
            print(f"代理错误: {e}")
```

## 最佳实践

1. **定期验证**：建议每天验证一次密钥状态
2. **备份密钥**：始终保留原始密钥文件的备份
3. **监控日志**：关注验证日志中的错误和警告
4. **渐进式迁移**：先在小批量密钥上测试，再全面部署
5. **错误处理**：妥善处理验证失败的情况

## 与 V1 版本对比

| 特性 | V1 | V2 |
|------|----|----|
| 密钥格式验证 | ❌ | ✅ |
| 请求头传递密钥 | ❌ | ✅ |
| 智能重试 | ❌ | ✅ |
| 连接池优化 | 基础 | 高级 |
| 进度显示 | ❌ | ✅ |
| JSON 报告 | ❌ | ✅ |
| 性能 | 基准 | +50% |

## 总结

Gemini 密钥验证器 V2 提供了企业级的密钥验证解决方案，具有高性能、高可靠性和丰富的功能。通过合理配置和使用，可以大幅提升密钥管理的效率和准确性。