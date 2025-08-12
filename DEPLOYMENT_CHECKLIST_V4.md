# HAJIMI KING V4.0 部署检查清单 ✅

## 📋 部署前检查

### 1. 系统要求 ✅
- [ ] Python 3.8+ 已安装
- [ ] pip 已安装并更新到最新版本
- [ ] Git 已安装（可选）
- [ ] 足够的磁盘空间（至少 1GB）
- [ ] 稳定的网络连接

### 2. 依赖安装 ✅
- [ ] 已运行 `pip install -r requirements.txt`
- [ ] 核心依赖验证通过
- [ ] 可选依赖根据需要安装：
  - [ ] Docker 支持 (`pip install docker>=7.0.0`)
  - [ ] Selenium 支持 (`pip install selenium>=4.15.0`)
  - [ ] GPU 监控 (`pip install GPUtil>=1.4.0`)

### 3. 配置文件 ✅
- [ ] 已复制 `.env.v4.example` 为 `.env`
- [ ] 已配置 `GITHUB_TOKENS`（至少一个）
- [ ] 已配置 `GEMINI_API_KEY`（推荐）
- [ ] V4 扩展搜索配置已设置：
  - [ ] `ENABLE_EXTENDED_SEARCH=true`
  - [ ] Web 搜索配置（如需要）
  - [ ] GitLab 搜索配置（如需要）
  - [ ] Docker 搜索配置（如需要）

### 4. 目录结构 ✅
- [ ] `data/` 目录已创建
- [ ] `data/runs/` 目录已创建
- [ ] `data/reports/` 目录已创建
- [ ] `data/cache/` 目录已创建
- [ ] `logs/` 目录已创建

## 🚀 部署步骤

### 自动部署（推荐）

**Linux/Mac:**
```bash
# 1. 运行安装脚本
chmod +x install_v4.sh
./install_v4.sh

# 2. 编辑配置文件
nano .env

# 3. 运行测试
python test_v4.py

# 4. 启动程序
./run_v4.sh
```

**Windows:**
```cmd
# 1. 运行安装脚本
install_v4.bat

# 2. 编辑配置文件
notepad .env

# 3. 运行测试
python test_v4.py

# 4. 启动程序
run_v4.bat
```

### 手动部署

```bash
# 1. 创建虚拟环境
python3 -m venv venv
source venv/bin/activate  # Linux/Mac
# venv\Scripts\activate   # Windows

# 2. 安装依赖
pip install --upgrade pip
pip install -r requirements.txt

# 3. 配置环境
cp .env.v4.example .env
# 编辑 .env 文件

# 4. 创建目录
mkdir -p data/{runs,reports,cache,keys,logs}
mkdir -p logs

# 5. 运行测试
python test_v4.py

# 6. 启动程序
python -m app.main_v4
```

## 🧪 验证部署

### 1. 运行测试脚本
```bash
python test_v4.py
```

**期望输出：**
```
🚀 开始 HAJIMI KING V4.0 功能测试
📋 模块导入 测试:
✅ 配置服务导入成功
✅ 协调器导入成功
✅ 功能管理器导入成功
✅ 扩展搜索管理器导入成功
✅ TokenHunterV4 导入成功
✅ 模块导入 测试通过

📊 测试结果: 7/7 通过
🎉 所有测试通过！V4 功能正常
```

### 2. 检查配置
```bash
python -c "
from app.services.config_service import get_config_service
config = get_config_service()
print('✅ 配置加载成功')
print(f'GitHub Tokens: {len(config.get(\"GITHUB_TOKENS_LIST\", []))} 个')
print(f'扩展搜索: {\"启用\" if config.get(\"ENABLE_EXTENDED_SEARCH\") else \"禁用\"}')
"
```

### 3. 验证模块导入
```bash
python -c "
try:
    from app.main_v4 import main
    print('✅ V4 主程序导入成功')
    from utils.token_hunter_v4.hunter_v4 import TokenHunterV4
    print('✅ TokenHunterV4 导入成功')
    from app.features.extended_search.manager import ExtendedSearchManager
    print('✅ 扩展搜索管理器导入成功')
    print('🎉 所有核心模块验证通过')
except Exception as e:
    print(f'❌ 模块导入失败: {e}')
"
```

## 🔧 常见部署问题

### 1. 依赖问题
**问题：** `ModuleNotFoundError`
**解决：**
```bash
# 确保虚拟环境已激活
source venv/bin/activate

# 重新安装依赖
pip install -r requirements.txt

# 安装缺失的模块
pip install docker selenium beautifulsoup4
```

### 2. 权限问题
**问题：** 脚本无法执行
**解决：**
```bash
# 给脚本执行权限
chmod +x run_v4.sh install_v4.sh

# 检查目录权限
chmod -R 755 data/ logs/
```

### 3. 配置问题
**问题：** Token 配置错误
**解决：**
```bash
# 检查 .env 文件格式
cat .env | grep GITHUB_TOKENS

# 确保没有多余的空格或引号
GITHUB_TOKENS=token1,token2,token3
```

## 📊 性能优化

### 1. 系统资源配置
```env
# 根据系统配置调整
WORKER_COUNT=4          # CPU 核心数
CACHE_SIZE_MB=200       # 可用内存的 10-20%
REQUEST_TIMEOUT=30      # 网络超时
MAX_RETRIES=3          # 重试次数
```

### 2. 搜索优化
```env
# 限制搜索结果数量
WEB_SEARCH_RESULTS=10
DOCKER_SEARCH_LIMIT=20

# 启用缓存
ENABLE_CACHE=true
CACHE_TTL=3600
```

### 3. 网络优化
```env
# 如果网络较慢
REQUEST_TIMEOUT=60
MAX_CONCURRENT_REQUESTS=5

# 如果有代理
HTTP_PROXY=http://proxy.example.com:8080
HTTPS_PROXY=http://proxy.example.com:8080
```

## 🔒 安全配置

### 1. 密钥安全
```env
# 启用密钥加密存储
ALLOW_PLAINTEXT=false
ENCRYPTION_KEY=your_strong_encryption_key

# 启用安全日志
SECURE_LOGGING=true
```

### 2. 网络安全
```env
# 启用 SSL 验证
SSL_VERIFY=true

# 自定义 User-Agent
USER_AGENT=HAJIMI-KING/4.0 Security-Scanner
```

## 📈 监控配置

### 1. 启用监控
```env
ENABLE_MONITORING=true
METRICS_PORT=9090
```

### 2. 日志配置
```env
LOG_LEVEL=INFO
LOG_FORMAT=json
ENABLE_PROFILING=false
```

## 🚀 生产环境部署

### 1. 环境配置
```env
ENVIRONMENT=production
DEBUG=false
LOG_LEVEL=WARNING
```

### 2. 资源限制
```env
# 生产环境推荐配置
WORKER_COUNT=8
CACHE_SIZE_MB=500
MAX_LOOPS=5
```

### 3. 监控和告警
```env
ENABLE_NOTIFICATIONS=true
WEBHOOK_URL=https://your-webhook-url
NOTIFICATION_EMAIL=admin@example.com
```

## ✅ 部署完成检查

- [ ] 所有测试通过
- [ ] 配置文件正确设置
- [ ] 必要的 Token 已配置
- [ ] 目录权限正确
- [ ] 网络连接正常
- [ ] 日志输出正常
- [ ] 可以成功启动程序
- [ ] 搜索功能正常工作

## 📞 获取支持

如果部署过程中遇到问题：

1. 查看 [故障排除指南](docs/V4_TROUBLESHOOTING.md)
2. 运行诊断脚本：`python test_v4.py`
3. 检查日志文件：`logs/hajimi_king_*.log`
4. 提交问题：[GitHub Issues](https://github.com/your-repo/hajimi-king/issues)

---

**🎉 恭喜！HAJIMI KING V4.0 部署完成！**

现在您可以享受强大的多平台密钥搜索功能了！