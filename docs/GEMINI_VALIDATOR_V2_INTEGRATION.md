# Gemini Validator V2 集成指南

## 概述

本文档介绍如何将高性能的 `utils/gemini_key_validator_v2.py` 集成到您的项目中，实现并发密钥验证，获得 10-20 倍的性能提升。

## 性能对比

| 验证器 | 并发数 | 5个密钥耗时 | 速度 | 特点 |
|--------|--------|-------------|------|------|
| 原始 validator.py | 1 (串行) | 4秒 | 1.25 keys/秒 | 简单但慢 |
| Gemini Validator V2 | 50-100 | 0.5秒 | 10-20 keys/秒 | 高性能并发 |

## 核心特性

### 1. **两阶段验证策略**
- 第一阶段：使用 generateContent API 验证密钥有效性
- 第二阶段：使用 cachedContents API 识别付费密钥

### 2. **高性能设计**
- 异步并发验证（50-100 并发）
- 连接池复用
- DNS 缓存
- 智能重试机制

### 3. **安全性增强**
- 使用 `X-goog-api-key` 请求头（更安全）
- 严格的密钥格式验证
- 日志脱敏

## 快速集成

### 方法 1：使用适配器（推荐）

```python
# 1. 导入适配器
from app.core.gemini_validator_adapter import create_gemini_validator

# 2. 创建验证器
validator = create_gemini_validator(concurrency=100)

# 3. 在 orchestrator 中使用
orchestrator = OrchestratorV2(
    scanner=Scanner(),
    validator=validator  # 使用高性能验证器
)
```

### 方法 2：直接使用验证器

```python
from utils.gemini_key_validator_v2 import GeminiKeyValidatorV2, ValidatorConfig

# 配置
config = ValidatorConfig(
    concurrency=100,      # 并发数
    timeout_sec=15,       # 超时时间
    max_retries=2,        # 重试次数
    enable_http2=True     # 启用 HTTP/2
)

# 使用
async with GeminiKeyValidatorV2(config) as validator:
    stats = await validator.validate_keys_batch(keys)
    await validator.save_results()  # 保存结果到文件
```

### 方法 3：修改现有 orchestrator_v2.py

在 `app/core/orchestrator_v2.py` 中修改：

```python
# 1. 添加导入
from app.core.gemini_validator_adapter import create_gemini_validator

# 2. 修改 __init__ 方法（第93-100行）
if validator:
    self.validator = validator
else:
    # 使用高性能的 Gemini Validator V2
    self.validator = create_gemini_validator(concurrency=50)

# 3. 在 _cleanup_resources 方法中添加清理
if hasattr(self.validator, 'cleanup'):
    asyncio.create_task(self.validator.cleanup())
```

## 使用示例

### 基础示例

```python
import asyncio
from app.core.gemini_validator_adapter import create_gemini_validator

async def validate_keys():
    # 创建验证器
    validator = create_gemini_validator(concurrency=100)
    
    # 密钥列表
    keys = [
        "AIzaSyA1234567890abcdefghijklmnopqrstuv",
        "AIzaSyB1234567890abcdefghijklmnopqrstuv",
        # ... 更多密钥
    ]
    
    # 验证
    results = await validator.validate_batch_async(keys)
    
    # 处理结果
    for result in results:
        if result.is_valid:
            tier = "PAID" if result.tier.value == "paid" else "FREE"
            print(f"✅ Valid {tier}: {result.key[:20]}...")
        else:
            print(f"❌ Invalid: {result.key[:20]}...")
    
    # 清理资源
    await validator.cleanup()

# 运行
asyncio.run(validate_keys())
```

### 完整集成示例

```python
from app.core.orchestrator_v2 import OrchestratorV2
from app.core.scanner import Scanner
from app.core.gemini_validator_adapter import create_gemini_validator

async def main():
    # 创建组件
    scanner = Scanner()
    validator = create_gemini_validator(concurrency=100)
    
    # 创建 orchestrator
    orchestrator = OrchestratorV2(
        scanner=scanner,
        validator=validator
    )
    
    # 搜索查询
    queries = [
        "AIzaSy in:file extension:env",
        "AIzaSy in:file filename:config"
    ]
    
    # 运行
    stats = await orchestrator.run(queries, max_loops=1)
    
    print(f"找到有效密钥: {stats.valid_total}")

asyncio.run(main())
```

## 配置选项

### ValidatorConfig 参数

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `api_host` | `https://generativelanguage.googleapis.com/` | API 主机地址 |
| `timeout_sec` | 15 | 请求超时时间（秒） |
| `max_retries` | 2 | 最大重试次数 |
| `concurrency` | 50 | 并发请求数 |
| `enable_http2` | True | 是否启用 HTTP/2 |
| `proxy` | None | 代理设置 |
| `log_level` | "INFO" | 日志级别 |
| `output_dir` | "data/keys" | 输出目录 |
| `save_backup` | True | 是否保存备份 |

### 性能调优建议

1. **并发数设置**
   - 一般网络：50-100
   - 高速网络：100-200
   - 受限环境：20-50

2. **超时设置**
   - 正常情况：15秒
   - 网络不稳定：20-30秒

3. **重试策略**
   - 生产环境：2-3次
   - 测试环境：0-1次

## 输出文件

验证器会自动保存结果到以下文件：

```
data/keys/
├── keys_paid_20241211.txt      # 付费密钥
├── keys_free_20241211.txt      # 免费密钥
├── keys_backup_20241211_143022.txt  # 所有有效密钥备份
└── keys_validation_report_20241211_143022.json  # 详细报告
```

## 故障排除

### 1. 导入错误
```python
# 确保添加项目根目录到 Python 路径
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
```

### 2. 异步上下文错误
```python
# 确保在异步上下文中使用
async def main():
    validator = create_gemini_validator()
    results = await validator.validate_batch_async(keys)
    await validator.cleanup()

asyncio.run(main())
```

### 3. 性能未提升
- 检查并发数设置
- 确认网络连接正常
- 查看日志中的错误信息

## 最佳实践

1. **使用适配器模式**：通过 `gemini_validator_adapter.py` 集成，保持代码整洁
2. **合理设置并发数**：根据网络和 API 限制调整
3. **处理验证结果**：检查 `tier` 属性区分免费/付费密钥
4. **资源清理**：使用完毕后调用 `cleanup()` 方法
5. **错误处理**：捕获并处理验证过程中的异常

## 总结

通过集成 Gemini Validator V2，您可以：
- 获得 10-20 倍的验证速度提升
- 准确识别付费和免费密钥
- 自动保存验证结果
- 享受更好的错误处理和重试机制

立即开始使用，让您的密钥验证飞起来！ 🚀