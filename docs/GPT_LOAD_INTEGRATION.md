# GPT Load集成指南

## 概述

Hajimi King项目现已支持将找到的Gemini API密钥自动同步到GPT Load Balancer系统。这个功能允许您将搜索到的有效密钥自动分发到多个GPT Load组中，实现密钥的集中管理和负载均衡。

**新功能**：智能分组同步机制，可根据密钥类型（有效、429限流、付费版、免费版）自动分配到不同的专属组，实现精细化的资源管理。

## 功能特点

- ✅ **自动同步**: 找到有效密钥后自动添加到同步队列
- ✅ **批量发送**: 定期批量发送密钥到GPT Load系统
- ✅ **多组支持**: 支持同时发送到多个GPT Load组
- ✅ **失败重试**: 发送失败的密钥会保留在队列中等待重试
- ✅ **双系统支持**: 同时支持Gemini Balancer和GPT Load Balancer
- ✅ **智能分组**: 根据密钥类型自动分配到专属组（新功能）
- ✅ **资源隔离**: 付费密钥、429密钥、免费密钥分组管理

## 配置说明

### 1. 基础配置

在`.env`文件或`data/config.txt`中添加以下配置：

```env
# GPT Load Balancer基础配置
GPT_LOAD_SYNC_ENABLED=true                    # 启用GPT Load同步
GPT_LOAD_URL=https://your-gpt-load-server.com # GPT Load服务器地址
GPT_LOAD_AUTH=your-bearer-token               # Bearer认证令牌
GPT_LOAD_GROUP_NAME=group1,group2,group3      # 目标组名（传统模式使用）
```

### 2. 智能分组配置（推荐）

启用智能分组功能，实现密钥的自动分类和精细化管理：

```env
# 智能分组配置
GPT_LOAD_SMART_GROUP_ENABLED=true    # 启用智能分组

# 各类型密钥对应的组名
GPT_LOAD_GROUP_VALID=production      # 有效密钥组
GPT_LOAD_GROUP_429=rate_limited      # 429限流密钥专属组
GPT_LOAD_GROUP_PAID=paid            # 付费版密钥专属组
GPT_LOAD_GROUP_FREE=free            # 免费版密钥专属组

# 双重同步策略（可选）
GPT_LOAD_429_TO_VALID=true          # 429密钥也同步到valid组
GPT_LOAD_PAID_TO_VALID=true         # 付费密钥也同步到valid组
```

### 3. 配置文件示例

`data/config.txt`:
```
# GitHub Tokens (每行一个)
ghp_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
ghp_yyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyy

# GPT Load基础配置
GPT_LOAD_SYNC_ENABLED=true
GPT_LOAD_URL=https://api.gptload.com
GPT_LOAD_AUTH=Bearer_1234567890abcdef

# 传统模式（所有密钥发送到相同组）
GPT_LOAD_GROUP_NAME=production,staging,development

# 智能分组模式（推荐）
GPT_LOAD_SMART_GROUP_ENABLED=true
GPT_LOAD_GROUP_VALID=production
GPT_LOAD_GROUP_429=rate_limited
GPT_LOAD_GROUP_PAID=paid_users
GPT_LOAD_GROUP_FREE=free_users
```

## 工作流程

### 智能分组工作流程

```mermaid
graph TD
    A[发现密钥] --> B{密钥类型?}
    B -->|有效| C[Valid组]
    B -->|429限流| D[429专属组]
    B -->|付费版| E[Paid专属组]
    B -->|免费版| F[Free组]
    
    D -->|可选| C
    E -->|可选| C
```

### 1. 实时同步模式

当搜索到有效的Gemini密钥时，系统会：

1. **验证密钥**: 使用Gemini API验证密钥有效性
2. **保存本地**: 将密钥保存到`data/keys/`目录
3. **添加队列**: 将有效密钥和429密钥都添加到GPT Load同步队列
4. **批量发送**: 每60秒批量发送队列中的密钥

**重要说明**: 429（限流）状态的密钥很可能是有效的，只是暂时被限流，因此也会被同步到GPT Load系统。

```python
# 代码示例 - orchestrator.py
if val_result.is_valid:
    # 保存有效密钥
    self.valid_keys_found.add(val_result.key)
    self._save_valid_key(val_result.key)
    
    # 添加到GPT Load同步队列
    if self.gpt_load_enabled:
        sync_utils.add_keys_to_queue([val_result.key])
        
elif val_result.is_rate_limited:
    # 保存429密钥（可能是有效的）
    self.rate_limited_keys_found.add(val_result.key)
    self._save_rate_limited_key(val_result.key)
    
    # 429密钥也添加到GPT Load同步队列
    if self.gpt_load_enabled:
        sync_utils.add_keys_to_queue([val_result.key])
```

### 2. 批量同步模式

在搜索完成后，系统会：

1. **汇总密钥**: 收集所有找到的有效密钥和429密钥
2. **批量同步**: 一次性将所有密钥发送到GPT Load
3. **生成报告**: 保存同步结果到日志文件

```python
# 批量同步所有有效密钥和429密钥
if self.gpt_load_enabled:
    all_keys_to_sync = list(self.valid_keys_found) + list(self.rate_limited_keys_found)
    if all_keys_to_sync:
        logger.info(f"🔄 批量同步密钥到GPT Load...")
        logger.info(f"   ✅ 有效密钥: {len(self.valid_keys_found)} 个")
        logger.info(f"   ⚠️ 429密钥: {len(self.rate_limited_keys_found)} 个")
        sync_utils.add_keys_to_queue(all_keys_to_sync)
```

## API接口

### 1. 获取组列表

```http
GET /api/groups
Authorization: Bearer {token}
```

响应示例：
```json
{
  "code": 0,
  "data": [
    {"id": 1, "name": "production"},
    {"id": 2, "name": "staging"}
  ]
}
```

### 2. 添加密钥

```http
POST /api/keys/add-async
Authorization: Bearer {token}
Content-Type: application/json

{
  "group_id": 1,
  "keys_text": "AIzaSy...,AIzaSy..."
}
```

响应示例：
```json
{
  "code": 0,
  "data": {
    "task_type": "add_keys",
    "is_running": true,
    "total": 10,
    "group_name": "production"
  }
}
```

## 日志输出

### 成功同步示例

```
# 传统模式
✅ VALID: AIzaSyABC...
🔄 添加密钥到GPT Load同步队列: AIzaSyABC...
⚠️ RATE LIMITED: AIzaSyXYZ...
🔄 添加429密钥到GPT Load同步队列: AIzaSyXYZ...

# 智能分组模式
✅ VALID: AIzaSyABC...
🏷️ 标记为有效密钥: AIzaSyABC...
⚠️ RATE LIMITED: AIzaSyXYZ...
🏷️ 标记为429限流密钥: AIzaSyXYZ...
💎 PAID VERSION: AIzaSyDEF...
🏷️ 标记为付费版密钥: AIzaSyDEF...

# 批量同步（智能分组）
🤖 使用智能分组模式批量同步密钥...
📤 同步 15 个密钥到组 'production'
   ✅ 成功添加到 'production' 组队列
📤 同步 10 个密钥到组 'rate_limited'
   ✅ 成功添加到 'rate_limited' 组队列
📤 同步 3 个密钥到组 'paid'
   ✅ 成功添加到 'paid' 组队列
📊 智能同步统计:
   production: 15 个密钥
   rate_limited: 10 个密钥
   paid: 3 个密钥
   总计: 28 个密钥
```

### 失败处理示例

```
❌ Failed to get group ID for 'unknown-group'
❌ Failed to add keys to group 'production': HTTP 401 - Unauthorized
❌ GPT load balancer queue processing failed with code: partial_failure
```

## 队列管理

### 查看队列状态

队列状态保存在`data/checkpoint.json`中：

```json
{
  "wait_send_balancer": ["AIzaSy..."],
  "wait_send_gpt_load": ["AIzaSy..."]
}
```

### 手动触发同步

```python
from utils.sync_utils import sync_utils

# 手动添加密钥到队列
keys = ["AIzaSy...", "AIzaSy..."]
sync_utils.add_keys_to_queue(keys)

# 手动触发批量发送
sync_utils._batch_send_worker()
```

## 测试功能

运行测试脚本验证GPT Load集成：

```bash
python test_gpt_load_integration.py
```

测试内容包括：
- 配置验证
- 队列管理
- API连接
- 批量发送
- 错误处理

## 故障排除

### 1. 连接失败

**问题**: `Connection failed to GPT load balancer`

**解决方案**:
- 检查GPT_LOAD_URL是否正确
- 确认服务器可访问
- 检查防火墙设置

### 2. 认证失败

**问题**: `HTTP 401 - Unauthorized`

**解决方案**:
- 验证GPT_LOAD_AUTH令牌
- 确认令牌格式正确（Bearer token）
- 检查令牌是否过期

### 3. 组不存在

**问题**: `Group 'xxx' not found in groups list`

**解决方案**:
- 使用正确的组名
- 先调用/api/groups获取可用组列表
- 检查GPT_LOAD_GROUP_NAME配置

### 4. 队列堆积

**问题**: 密钥在队列中堆积，未发送

**解决方案**:
- 检查sync_utils是否正常运行
- 查看日志中的错误信息
- 手动触发批量发送

## 性能优化

### 1. 批量大小

默认每60秒发送一次，可以调整：

```python
# sync_utils.py
self.batch_interval = 60  # 调整发送间隔（秒）
```

### 2. 并发控制

```python
# 限制并发请求数
self.executor = ThreadPoolExecutor(max_workers=2)
```

### 3. 缓存优化

组ID缓存15分钟，减少API调用：

```python
self.group_id_cache_ttl = 15 * 60  # 15分钟缓存
```

## 监控指标

### 关键指标

- **队列长度**: `wait_send_gpt_load`队列中的密钥数
- **发送成功率**: 成功发送的密钥比例
- **API响应时间**: GPT Load API的响应时间
- **错误率**: 发送失败的频率

### 日志文件

- **发送结果**: `data/logs/keys_send_result_YYYYMMDD.txt`
- **错误日志**: `data/logs/error.log`
- **调试日志**: `data/logs/debug.log`

## 安全建议

1. **令牌安全**: 不要在代码中硬编码认证令牌
2. **HTTPS通信**: 始终使用HTTPS连接GPT Load服务器
3. **权限控制**: 限制令牌的权限范围
4. **日志脱敏**: 日志中只显示密钥前10个字符
5. **定期轮换**: 定期更换认证令牌

## 常见问题

### Q: 密钥会重复发送吗？

A: 不会。系统会检查密钥是否已存在，避免重复添加。

### Q: 发送失败的密钥会丢失吗？

A: 不会。失败的密钥会保留在队列中，等待下次重试。

### Q: 可以同时使用Gemini Balancer和GPT Load吗？

A: 可以。两个系统独立工作，互不影响。

### Q: 如何禁用GPT Load同步？

A: 设置`GPT_LOAD_SYNC_ENABLED=false`即可。

## 更新日志

### v1.0.0 (2024-01-10)
- ✨ 初始版本发布
- ✅ 支持自动同步到GPT Load
- ✅ 支持多组发送
- ✅ 实现队列管理和批量发送
- ✅ 添加失败重试机制

## 联系支持

如有问题或建议，请提交Issue或联系开发团队。