# HAJIMI KING V4.0 完整实施指南

## 📋 总览

本指南提供了从 V2 版本创建独立 V4 版本的完整步骤，包括所有新功能的集成和测试方法。

## 🏗️ 实施步骤清单

### 第一阶段：准备工作

- [ ] 1. 备份现有 V2 版本代码
- [ ] 2. 创建 V4 版本的目录结构
- [ ] 3. 复制必要的基础文件
- [ ] 4. 安装新的依赖包

### 第二阶段：创建核心文件

- [ ] 5. 创建 `app/main_v4.py`
- [ ] 6. 创建 `app/core/orchestrator_v4.py`
- [ ] 7. 创建扩展搜索模块目录结构
- [ ] 8. 实现所有搜索器类

### 第三阶段：集成和配置

- [ ] 9. 创建 V4 配置文件
- [ ] 10. 更新环境变量
- [ ] 11. 集成到现有系统
- [ ] 12. 配置外部服务

### 第四阶段：测试和验证

- [ ] 13. 运行单元测试
- [ ] 14. 运行集成测试
- [ ] 15. 性能测试
- [ ] 16. 生产环境部署

## 📁 详细文件创建步骤

### 1. 创建目录结构

```bash
# 创建 V4 特定目录
mkdir -p app/features/extended_search
mkdir -p utils/token_hunter_v4
mkdir -p tests/v4
mkdir -p data/v4

# 创建 __init__.py 文件
touch app/features/extended_search/__init__.py
touch utils/token_hunter_v4/__init__.py
```

### 2. 复制和修改主程序文件

```bash
# 复制 V2 主程序作为基础
cp app/main_v2.py app/main_v4.py

# 复制协调器
cp app/core/orchestrator_v2.py app/core/orchestrator_v4.py
```

### 3. 创建所有新文件

按照以下顺序创建文件：

#### 3.1 扩展搜索模块

1. `app/features/extended_search/__init__.py`
2. `app/features/extended_search/manager.py`
3. `app/features/extended_search/web_searcher.py`
4. `app/features/extended_search/gitlab_searcher.py`
5. `app/features/extended_search/docker_searcher.py`

#### 3.2 Token Hunter V4

1. `utils/token_hunter_v4/__init__.py`
2. `utils/token_hunter_v4/hunter_v4.py`
3. `utils/token_hunter_v4/integration.py`

#### 3.3 配置文件

1. `.env.v4.example`
2. `config/v4_config.yaml`

#### 3.4 测试文件

1. `test_v4_extended_search.py`
2. `tests/v4/test_web_searcher.py`
3. `tests/v4/test_gitlab_searcher.py`
4. `tests/v4/test_docker_searcher.py`

## 🔧 代码修改指南

### 修改 `app/main_v4.py`

在文件开头添加导入：

```python
# 导入扩展搜索功能
from app.features.extended_search import ExtendedSearchManager
from utils.token_hunter_v4 import TokenHunterV4
```

在 `main()` 函数中添加：

```python
# 在初始化特性管理器之后添加
if config.get("EXTENDED_SEARCH_ENABLED", False):
    # 运行扩展搜索
    extended_search_results = await run_extended_search(config)
    
    # 将结果添加到查询列表
    if extended_search_results:
        for platform, keys in extended_search_results.items():
            logger.info(f"从 {platform} 添加 {len(keys)} 个密钥到搜索队列")
            # 转换为查询
            for key in keys[:10]:  # 每个平台最多10个
                queries.append(f"{key[:20]} in:file")
```

### 修改 `app/core/orchestrator_v4.py`

```python
from app.core.orchestrator_v2 import OrchestratorV2
from app.features.extended_search import ExtendedSearchManager

class OrchestratorV4(OrchestratorV2):
    """协调器 V4 - 支持扩展搜索"""
    
    def __init__(self):
        super().__init__()
        self.version = "4.0.0"
        self.extended_search_manager = None
        
    async def initialize_extended_search(self, config):
        """初始化扩展搜索"""
        if config.get("EXTENDED_SEARCH_ENABLED", False):
            self.extended_search_manager = ExtendedSearchManager(config)
            logger.info("✅ 扩展搜索管理器已初始化")
```

## 🧪 测试方法

### 1. 单元测试

创建 `tests/v4/test_web_searcher.py`：

```python
import unittest
from app.features.extended_search import WebSearcher

class TestWebSearcher(unittest.TestCase):
    def setUp(self):
        self.searcher = WebSearcher()
    
    def test_extract_tokens(self):
        """测试token提取功能"""
        text = "Here is a token: ghp_1234567890abcdef1234567890abcdef1234"
        tokens = self.searcher._extract_tokens_from_text(text)
        self.assertEqual(len(tokens), 1)
        self.assertIn("ghp_1234567890abcdef1234567890abcdef1234", tokens)
    
    def test_filter_placeholders(self):
        """测试占位符过滤"""
        text = "ghp_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"
        tokens = self.searcher._extract_tokens_from_text(text)
        self.assertEqual(len(tokens), 0)

if __name__ == '__main__':
    unittest.main()
```

### 2. 集成测试

运行完整的集成测试：

```bash
# 设置测试环境变量
export EXTENDED_SEARCH_ENABLED=true
export WEB_SEARCH_ENABLED=true
export GITLAB_SEARCH_ENABLED=true
export DOCKER_SEARCH_ENABLED=true

# 运行测试
python test_v4_extended_search.py
```

### 3. 性能测试

创建 `tests/v4/test_performance.py`：

```python
import asyncio
import time
from app.features.extended_search import ExtendedSearchManager

async def test_search_performance():
    """测试搜索性能"""
    config = {
        "EXTENDED_SEARCH_ENABLED": True,
        "MAX_RESULTS_PER_PLATFORM": 10
    }
    
    manager = ExtendedSearchManager(config)
    
    start_time = time.time()
    results = await manager.search_all_platforms(['web', 'gitlab'])
    end_time = time.time()
    
    print(f"搜索耗时: {end_time - start_time:.2f} 秒")
    print(f"找到密钥: {sum(len(v) for v in results.values())} 个")
    
    manager.cleanup()

if __name__ == "__main__":
    asyncio.run(test_search_performance())
```

## 🚀 部署步骤

### 1. 开发环境部署

```bash
# 1. 安装依赖
pip install -r requirements.txt
pip install docker requests beautifulsoup4

# 2. 配置环境变量
cp .env.v4.example .env
# 编辑 .env 文件

# 3. 运行测试
python test_v4_extended_search.py

# 4. 运行主程序
python app/main_v4.py
```

### 2. Docker 部署

创建 `Dockerfile.v4`：

```dockerfile
FROM python:3.9-slim

WORKDIR /app

# 安装系统依赖
RUN apt-get update && apt-get install -y \
    git \
    curl \
    && rm -rf /var/lib/apt/lists/*

# 复制依赖文件
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
RUN pip install --no-cache-dir docker requests

# 复制应用代码
COPY . .

# 设置环境变量
ENV PYTHONUNBUFFERED=1
ENV VERSION=4.0.0

# 运行 V4 版本
CMD ["python", "app/main_v4.py"]
```

创建 `docker-compose.v4.yml`：

```yaml
version: '3.8'

services:
  hajimi-king-v4:
    build:
      context: .
      dockerfile: Dockerfile.v4
    container_name: hajimi-king-v4
    restart: unless-stopped
    env_file:
      - .env
    volumes:
      - ./data:/app/data
      - /var/run/docker.sock:/var/run/docker.sock  # 用于Docker搜索
    environment:
      - EXTENDED_SEARCH_ENABLED=true
      - WEB_SEARCH_ENABLED=true
      - GITLAB_SEARCH_ENABLED=true
      - DOCKER_SEARCH_ENABLED=true
    networks:
      - hajimi-network

networks:
  hajimi-network:
    driver: bridge
```

### 3. 生产环境配置

#### 3.1 性能优化配置

```bash
# .env.production
# 基础配置
ENVIRONMENT=production
LOG_LEVEL=WARNING

# 性能配置
MAX_CONCURRENT_VALIDATIONS=100
VALIDATION_BATCH_SIZE=200
CONNECTION_POOL_SIZE=50

# 搜索限制
MAX_RESULTS_PER_PLATFORM=100
SEARCH_TIMEOUT_SECONDS=60
SEARCH_DELAY_SECONDS=2

# 缓存配置
ENABLE_CACHE=true
CACHE_TTL=3600
```

#### 3.2 监控配置

```yaml
# prometheus.yml
global:
  scrape_interval: 15s

scrape_configs:
  - job_name: 'hajimi-king-v4'
    static_configs:
      - targets: ['localhost:9090']
```

## 📊 验证和监控

### 1. 健康检查

创建 `health_check.py`：

```python
import requests
import sys

def check_health():
    """检查 V4 服务健康状态"""
    try:
        # 检查主服务
        response = requests.get("http://localhost:8080/health")
        if response.status_code != 200:
            return False
        
        # 检查扩展搜索
        data = response.json()
        if not data.get("extended_search_enabled"):
            print("警告: 扩展搜索未启用")
        
        return True
    except Exception as e:
        print(f"健康检查失败: {e}")
        return False

if __name__ == "__main__":
    if check_health():
        print("✅ 服务运行正常")
        sys.exit(0)
    else:
        print("❌ 服务异常")
        sys.exit(1)
```

### 2. 日志监控

```bash
# 实时查看日志
tail -f data/logs/hajimi_king_v4.log

# 查看错误日志
grep ERROR data/logs/hajimi_king_v4.log

# 查看扩展搜索统计
grep "扩展搜索完成" data/logs/hajimi_king_v4.log
```

### 3. 性能监控

```python
# 创建 monitor_v4.py
import psutil
import time

def monitor_resources():
    """监控资源使用"""
    process = psutil.Process()
    
    while True:
        cpu_percent = process.cpu_percent(interval=1)
        memory_mb = process.memory_info().rss / 1024 / 1024
        
        print(f"CPU: {cpu_percent:.1f}% | Memory: {memory_mb:.1f} MB")
        
        time.sleep(5)

if __name__ == "__main__":
    monitor_resources()
```

## ✅ 完成检查清单

### 功能验证

- [ ] Web搜索器正常工作
- [ ] GitLab搜索器正常工作
- [ ] Docker搜索器正常工作
- [ ] 扩展搜索管理器并发正常
- [ ] 密钥验证功能正常
- [ ] 结果保存正确

### 性能验证

- [ ] 搜索响应时间 < 30秒
- [ ] 内存使用 < 2GB
- [ ] CPU使用率正常
- [ ] 无内存泄漏

### 安全验证

- [ ] API密钥已加密存储
- [ ] 日志中无敏感信息
- [ ] 代理配置正确
- [ ] 访问控制正常

## 🎉 总结

恭喜！您已经成功创建了 HAJIMI KING V4.0 版本，具有以下新功能：

1. **多平台搜索** - 支持 Web、GitLab、Docker 等平台
2. **并发搜索** - 提高搜索效率
3. **智能过滤** - 减少误报
4. **完全独立** - 不影响 V2 稳定版本

V4 版本保持了与 V2 的兼容性，同时提供了强大的扩展功能。您可以根据需要启用或禁用特定的搜索平台，灵活配置以满足不同的使用场景。

## 📚 相关文档

- [V4 实施计划](./V4_IMPLEMENTATION_PLAN.md)
- [搜索器实现代码](./V4_SEARCHER_IMPLEMENTATIONS.md)
- [Docker搜索器和测试](./V4_DOCKER_SEARCHER_AND_TESTING.md)
- [V2 版本文档](../README.md)

---

**版本**: 4.0.0  
**更新日期**: 2025-01-12  
**作者**: HAJIMI KING Team