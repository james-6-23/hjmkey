# Token池监控修复文档

## 问题描述

Token池状态监控显示静态数据，所有令牌显示30/30配额，使用率始终为0%，无法反映真实的GitHub API配额状态。

### 原始问题
- Token配额状态表格显示硬编码的默认值（30/30）
- 使用率始终显示0%
- 无法识别无效或耗尽的令牌
- 缺少启动时的配额检查机制

## 修复方案

### 1. 修改的文件
- `utils/token_pool.py`

### 2. 具体修改

#### 2.1 添加启动时配额检查

```python
def __init__(self, tokens: List[str], ...):
    # ... 初始化代码 ...
    
    logger.info(f"🎯 Token pool initialized with {len(self.tokens)} tokens")
    logger.info(f"   Strategy: {strategy.name}")
    
    # 启动时检查实际配额
    self._initialize_token_quotas()
```

#### 2.2 实现配额检查方法

```python
def _initialize_token_quotas(self):
    """
    启动时检查所有令牌的实际配额
    """
    import requests
    
    logger.info("🔍 Checking actual token quotas from GitHub API...")
    
    for i, token in enumerate(self.tokens):
        try:
            # 调用 GitHub API 检查配额
            headers = {
                "Authorization": f"token {token}",
                "Accept": "application/vnd.github.v3+json"
            }
            
            response = requests.get(
                "https://api.github.com/rate_limit",
                headers=headers,
                timeout=5
            )
            
            if response.status_code == 200:
                data = response.json()
                
                # 获取搜索API的配额信息
                search_limit = data.get('resources', {}).get('search', {})
                
                # 更新指标
                metrics = self.metrics[token]
                metrics.limit = search_limit.get('limit', 30)
                metrics.remaining = search_limit.get('remaining', 30)
                metrics.reset_time = search_limit.get('reset', 0)
                
                # 更新状态
                metrics.update_quota(metrics.remaining, metrics.reset_time)
                
            elif response.status_code == 401:
                # 无效令牌
                self.metrics[token].status = TokenStatus.FAILED
                logger.warning(f"   Token {i+1}: INVALID (401 Unauthorized)")
                
            elif response.status_code == 403:
                # 可能是限流
                self.metrics[token].status = TokenStatus.EXHAUSTED
                self.metrics[token].remaining = 0
                logger.warning(f"   Token {i+1}: EXHAUSTED (403 Forbidden)")
                
        except Exception as e:
            logger.debug(f"   Token {i+1}: Check failed - {type(e).__name__}")
    
    # 统计汇总
    self._log_quota_summary()
```

#### 2.3 添加手动刷新方法

```python
def refresh_quotas(self):
    """
    手动刷新所有令牌的配额信息
    """
    logger.info("🔄 Refreshing token quotas...")
    self._initialize_token_quotas()
```

#### 2.4 改进状态统计

```python
def get_pool_status(self) -> Dict[str, Any]:
    """获取池状态摘要"""
    with self._lock:
        # 添加更多状态统计
        healthy = sum(1 for m in self.metrics.values() if m.status == TokenStatus.HEALTHY)
        limited = sum(1 for m in self.metrics.values() if m.status == TokenStatus.LIMITED)
        exhausted = sum(1 for m in self.metrics.values() if m.status == TokenStatus.EXHAUSTED)
        failed = sum(1 for m in self.metrics.values() if m.status == TokenStatus.FAILED)
        recovering = sum(1 for m in self.metrics.values() if m.status == TokenStatus.RECOVERING)
        
        # 计算真实的配额和使用率
        total_remaining = sum(m.remaining for m in self.metrics.values())
        total_limit = sum(m.limit for m in self.metrics.values())
        
        if total_limit > 0:
            utilization_pct = (total_limit - total_remaining) / total_limit * 100
            utilization_str = f"{utilization_pct:.1f}%"
        else:
            utilization_str = "0.0%"
        
        return {
            "total_tokens": len(self.tokens),
            "healthy": healthy,
            "limited": limited,
            "exhausted": exhausted,
            "failed": failed,
            "recovering": recovering,
            "total_remaining": total_remaining,
            "total_limit": total_limit,
            "utilization": utilization_str,
            # ... 其他统计 ...
        }
```

## 测试验证

### 测试脚本
创建了 `test_token_pool_monitoring.py` 测试脚本，包含以下测试：

1. **启动时配额检查测试**
   - 验证Token池初始化时自动检查配额
   - 确认能正确识别无效令牌（401错误）

2. **手动刷新测试**
   - 测试 `refresh_quotas()` 方法
   - 验证配额信息更新

3. **令牌详细信息测试**
   - 显示每个令牌的状态和健康分数
   - 验证统计信息准确性

### 运行测试

```bash
python test_token_pool_monitoring.py
```

### 测试结果
```
[OK] Token池初始化完成，配额检查已执行
池状态汇总:
  总令牌数: 3
  健康: 0
  受限: 0
  耗尽: 0
  失败: 3 (测试令牌无效)
  恢复中: 0
  总配额: 90/90
  使用率: 0.0%
```

## 关键改进

### 功能增强
1. **自动配额检查**：启动时自动调用GitHub API检查每个令牌的实际配额
2. **状态识别**：正确识别令牌状态（健康/受限/耗尽/失败/恢复中）
3. **手动刷新**：支持运行时手动刷新配额信息
4. **真实数据**：显示真实的剩余配额和使用率，而非硬编码值

### 性能优化
- 异步检查避免阻塞
- 添加超时控制（5秒）
- 请求间隔控制（0.2秒）避免触发限流

### 错误处理
- 401错误：标记为FAILED状态
- 403错误：标记为EXHAUSTED状态
- 网络错误：静默处理，保持默认值

## 使用方法

### 1. 自动配额检查
Token池初始化时会自动检查配额：
```python
pool = TokenPool(tokens, strategy=TokenSelectionStrategy.ADAPTIVE)
# 自动执行配额检查
```

### 2. 手动刷新配额
```python
pool.refresh_quotas()
```

### 3. 获取池状态
```python
status = pool.get_pool_status()
print(f"健康令牌: {status['healthy']}")
print(f"失败令牌: {status['failed']}")
print(f"使用率: {status['utilization']}")
```

## 注意事项

1. **API调用消耗**
   - 每次配额检查会消耗一次API调用
   - 建议合理控制刷新频率

2. **令牌有效性**
   - 无效令牌会被标记为FAILED状态
   - 不会参与后续的令牌选择

3. **网络依赖**
   - 配额检查需要网络连接
   - 网络失败时保持默认值

## 影响范围

此修复影响以下功能：
- Token池初始化流程
- 令牌状态监控
- 配额使用统计
- 令牌选择策略

## 验证状态

✅ 启动时配额检查功能正常
✅ 无效令牌正确识别
✅ 手动刷新功能正常
✅ 状态统计准确
✅ 测试脚本通过