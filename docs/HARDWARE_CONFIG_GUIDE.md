# 硬件配置建议指南

## 1. CPU核心数配置建议

### 1.1 配置计算公式

```
推荐并发搜索数 = MIN(CPU核心数 × 2, 20)
推荐并发验证数 = CPU核心数 × 10
推荐连接池大小 = MIN(CPU核心数 × 15, 内存(GB) × 10)
推荐数据库连接池 = MIN(CPU核心数 × 2, 内存(GB))
```

### 1.2 不同CPU核心数的推荐配置

| CPU核心数 | 并发搜索数 | 并发验证数 | 连接池大小 | 数据库连接池 |
|-----------|------------|------------|------------|--------------|
| 2核 | 4 | 20 | 30 | 4 |
| 4核 | 8 | 40 | 60 | 8 |
| 8核 | 16 | 80 | 120 | 16 |
| 16核 | 20 | 160 | 200 | 32 |

### 1.3 配置示例

#### 2核CPU配置
```env
MAX_CONCURRENT_SEARCHES=4
MAX_CONCURRENT_VALIDATIONS=20
MAX_CONNECTIONS=30
DATABASE_POOL_SIZE=4
```

#### 4核CPU配置
```env
MAX_CONCURRENT_SEARCHES=8
MAX_CONCURRENT_VALIDATIONS=40
MAX_CONNECTIONS=60
DATABASE_POOL_SIZE=8
```

#### 8核CPU配置
```env
MAX_CONCURRENT_SEARCHES=16
MAX_CONCURRENT_VALIDATIONS=80
MAX_CONNECTIONS=120
DATABASE_POOL_SIZE=16
```

#### 16核CPU配置
```env
MAX_CONCURRENT_SEARCHES=20
MAX_CONCURRENT_VALIDATIONS=160
MAX_CONNECTIONS=200
DATABASE_POOL_SIZE=32
```

## 2. 内存容量配置建议

### 2.1 配置计算公式

```
推荐数据库连接池 = MIN(CPU核心数 × 2, 内存(GB))
推荐日志缓冲区 = 内存(GB) × 10MB
推荐插件缓存大小 = 内存(GB) × 5MB
```

### 2.2 不同内存容量的推荐配置

| 内存容量 | 数据库连接池 | 日志缓冲区 | 插件缓存大小 |
|----------|--------------|------------|--------------|
| 4GB | 5 | 40MB | 20MB |
| 8GB | 10 | 80MB | 40MB |
| 16GB | 20 | 160MB | 80MB |
| 32GB | 40 | 320MB | 160MB |

### 2.3 配置示例

#### 4GB内存配置
```env
DATABASE_POOL_SIZE=5
# 日志配置建议使用默认值
# 插件系统建议使用默认缓存
```

#### 8GB内存配置
```env
DATABASE_POOL_SIZE=10
# 可适当增加日志缓冲区
# 插件系统可使用较大缓存
```

#### 16GB内存配置
```env
DATABASE_POOL_SIZE=20
# 可使用较大的日志缓冲区
# 插件系统可使用大缓存提升性能
```

#### 32GB内存配置
```env
DATABASE_POOL_SIZE=40
# 可使用非常大的日志缓冲区
# 插件系统可使用最大缓存
```

## 3. 存储配置建议

### 3.1 日志存储

```
日志文件大小限制 = 内存(GB) × 100MB
日志文件备份数量 = 5-10个
```

### 3.2 数据库存储

```
数据库文件大小限制 = 内存(GB) × 500MB
数据库备份数量 = 3-5个
```

## 4. 网络配置建议

### 4.1 带宽利用率

```
推荐网络带宽 = 并发连接数 × 平均请求大小 × 2
```

### 4.2 连接超时配置

```
连接超时时间 = 网络延迟 × 3 + 5秒
```

## 5. 生产环境 vs 开发环境配置

### 5.1 生产环境配置

```env
# 高性能配置
MAX_CONCURRENT_SEARCHES=20
MAX_CONCURRENT_VALIDATIONS=160
MAX_CONNECTIONS=200
DATABASE_POOL_SIZE=40

# 完整日志记录
LOG_TO_FILE=true
LOG_TO_CONSOLE=false
LOG_LEVEL=INFO

# 启用所有监控
ENABLE_MONITORING=true
MONITORING_ENABLED=true

# 连接池优化
CONNECTION_TIMEOUT=30
CONNECTION_RETRIES=3
```

### 5.2 开发环境配置

```env
# 低资源消耗配置
MAX_CONCURRENT_SEARCHES=2
MAX_CONCURRENT_VALIDATIONS=10
MAX_CONNECTIONS=20
DATABASE_POOL_SIZE=5

# 详细日志输出
LOG_TO_FILE=true
LOG_TO_CONSOLE=true
LOG_LEVEL=DEBUG

# 启用监控便于调试
ENABLE_MONITORING=true
MONITORING_ENABLED=true

# 快速失败配置
CONNECTION_TIMEOUT=15
CONNECTION_RETRIES=1
```

## 6. 性能调优建议

### 6.1 监控关键指标

1. **CPU使用率**：保持在70%以下
2. **内存使用率**：保持在80%以下
3. **磁盘I/O**：避免持续高负载
4. **网络带宽**：避免饱和

### 6.2 调优步骤

1. **基准测试**：使用默认配置进行基准测试
2. **逐步调整**：每次只调整一个参数
3. **监控效果**：观察调整后的性能变化
4. **记录结果**：记录每次调整的效果
5. **优化配置**：根据测试结果优化配置

### 6.3 常见问题及解决方案

1. **CPU使用率过高**：
   - 减少并发数
   - 增加超时时间
   - 优化验证算法

2. **内存不足**：
   - 减少数据库连接池大小
   - 减少日志缓冲区
   - 优化数据结构

3. **网络超时**：
   - 增加超时时间
   - 减少并发连接数
   - 检查网络连接

通过以上硬件配置建议，您可以根据实际的硬件环境合理配置系统参数，实现最佳的性能和稳定性。