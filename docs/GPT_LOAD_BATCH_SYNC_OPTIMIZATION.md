# GPT Load 批量同步优化

## 问题描述

在原始的 `orchestrator_v2.py` 实现中，每验证一个密钥就会立即调用 `_sync_key_to_gpt_load` 方法进行同步。这种方式存在以下问题：

1. **性能影响**：每个密钥都触发一次同步操作，增加了系统开销
2. **网络请求频繁**：可能导致过多的 API 调用
3. **效率低下**：无法利用批量操作的优势

## 优化方案

### 1. 批量缓冲机制

在 `OrchestratorV2` 类中添加了查询级别的同步缓冲区：

```python
# 批量同步缓冲区 - 用于收集每个查询的密钥
self.query_sync_buffer = {
    KeyStatus.VALID_FREE: [],
    KeyStatus.VALID_PAID: [],
    KeyStatus.RATE_LIMITED: []
}
```

### 2. 收集密钥而非立即同步

修改了密钥处理逻辑，将立即同步改为添加到缓冲区：

```python
# 原来的代码：
if self.gpt_load_enabled:
    self._sync_key_to_gpt_load(val_result.key, status)

# 优化后的代码：
if self.gpt_load_enabled:
    self.query_sync_buffer[status].append(val_result.key)
```

### 3. 查询结束后批量同步

在每个查询处理完成后，批量同步所有收集的密钥：

```python
# 批量同步本查询收集的所有密钥到 GPT Load
if self.gpt_load_enabled:
    self._batch_sync_query_keys()
```

### 4. 新增批量同步方法

实现了 `_batch_sync_query_keys` 方法，支持：

- 统计各类型密钥数量
- 一次性同步所有密钥
- 支持智能分组和传统模式
- 同步后清空缓冲区

## 性能提升

### 优化前
- 每个密钥验证后立即同步
- 假设一个查询找到 100 个密钥，会触发 100 次同步操作

### 优化后
- 每个查询结束后批量同步
- 同样 100 个密钥，只需要 1 次批量同步操作
- **性能提升：100倍**（在同步操作数量上）

## 使用示例

优化后的代码使用方式不变，但内部执行更高效：

```python
# 初始化协调器
orchestrator = OrchestratorV2()

# 运行查询
queries = ["AIzaSy in:file", "gemini api key"]
stats = await orchestrator.run(queries)

# 同步操作会在每个查询结束后自动批量执行
```

## 日志示例

优化后的日志输出：

```
🔍 [1/2] Processing query: AIzaSy in:file
...
🔑 Found 50 suspected keys
✅ VALID (VALID_FREE): AIza...
✅ VALID (VALID_PAID): AIza...
...
🔄 Batch syncing 45 keys to GPT Load...
   Free: 40, Paid: 3, Rate Limited: 2
✅ Successfully batch synced 45 keys to GPT Load (smart group)
```

## 配置说明

优化后的批量同步仍然受以下配置控制：

- `GPT_LOAD_SYNC_ENABLED`: 是否启用 GPT Load 同步
- `GPT_LOAD_SMART_GROUP_ENABLED`: 是否使用智能分组

## 注意事项

1. **内存使用**：缓冲区会暂存密钥，但每个查询结束后会清空
2. **错误处理**：批量同步失败时会记录错误并更新失败统计
3. **最终同步**：程序结束时仍会执行最终的批量同步，确保所有密钥都被同步

## 总结

这个优化显著减少了 GPT Load 同步操作的次数，从每个密钥一次同步改为每个查询一次批量同步，大幅提升了程序运行效率。