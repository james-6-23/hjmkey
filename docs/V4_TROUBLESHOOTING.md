# HAJIMI KING V4.0 故障排除指南

## 🚨 常见错误及解决方案

### 1. 模块导入错误

#### 错误信息：`ModuleNotFoundError: No module named 'docker'`

**原因：** 缺少 Docker 模块依赖

**解决方案：**
```bash
# 激活虚拟环境
source venv/bin/activate  # Linux/Mac
# 或
venv\Scripts\activate     # Windows

# 安装 Docker 模块
pip install docker>=7.0.0
```

#### 错误信息：`ModuleNotFoundError: No module named 'selenium'`

**原因：** 缺少 Selenium 模块

**解决方案：**
```bash
pip install selenium>=4.15.0
```

**注意：** 还需要安装 ChromeDriver：
- **Ubuntu/Debian:** `sudo apt-get install chromium-chromedriver`
- **macOS:** `brew install chromedriver`
- **Windows:** 从 [ChromeDriver 官网](https://chromedriver.chromium.org/) 下载

#### 错误信息：`ModuleNotFoundError: No module named 'google.generativeai'`

**原因：** 缺少 Google Generative AI 模块

**解决方案：**
```bash
pip install google-generativeai>=0.8.5
```

### 2. 配置相关错误

#### 错误信息：`未找到 .env 文件`

**解决方案：**
```bash
# 复制示例配置文件
cp .env.v4.example .env

# 编辑配置文件
nano .env  # Linux/Mac
notepad .env  # Windows
```

#### 错误信息：`未配置 GITHUB_TOKENS`

**解决方案：**
1. 获取 GitHub Personal Access Token：
   - 访问 https://github.com/settings/tokens
   - 点击 "Generate new token (classic)"
   - 选择适当的权限（至少需要 `public_repo`）
   - 复制生成的 token

2. 在 `.env` 文件中配置：
```env
GITHUB_TOKENS=ghp_your_token_here,ghp_another_token_here
```

#### 错误信息：`Gemini API Key 未配置`

**解决方案：**
1. 获取 Gemini API Key：
   - 访问 https://makersuite.google.com/app/apikey
   - 创建新的 API Key

2. 在 `.env` 文件中配置：
```env
GEMINI_API_KEY=your_gemini_api_key_here
```

### 3. 网络连接问题

#### 错误信息：`连接超时` 或 `网络错误`

**解决方案：**

1. **检查网络连接：**
```bash
ping github.com
ping google.com
```

2. **配置代理（如果需要）：**
```env
HTTP_PROXY=http://proxy.example.com:8080
HTTPS_PROXY=http://proxy.example.com:8080
NO_PROXY=localhost,127.0.0.1
```

3. **增加超时时间：**
```env
REQUEST_TIMEOUT=60
MAX_RETRIES=5
```

#### 错误信息：`SSL 证书验证失败`

**解决方案：**
```env
# 临时禁用 SSL 验证（不推荐用于生产环境）
SSL_VERIFY=false
```

### 4. Docker 相关问题

#### 错误信息：`Docker daemon 连接失败`

**解决方案：**

1. **确保 Docker 服务运行：**
```bash
# Linux
sudo systemctl start docker
sudo systemctl enable docker

# macOS
# 启动 Docker Desktop

# Windows
# 启动 Docker Desktop
```

2. **检查 Docker 权限：**
```bash
# Linux - 将用户添加到 docker 组
sudo usermod -aG docker $USER
# 重新登录或重启
```

3. **如果无法使用 Docker，程序会自动回退到 API 模式**

#### 错误信息：`Docker 镜像拉取失败`

**解决方案：**
1. **检查网络连接**
2. **配置 Docker 代理（如果需要）**
3. **使用国内镜像源：**
```bash
# 编辑 /etc/docker/daemon.json
{
  "registry-mirrors": [
    "https://docker.mirrors.ustc.edu.cn",
    "https://hub-mirror.c.163.com"
  ]
}

# 重启 Docker
sudo systemctl restart docker
```

### 5. 权限问题

#### 错误信息：`权限被拒绝`

**解决方案：**

1. **文件权限：**
```bash
# 给脚本执行权限
chmod +x run_v4.sh
chmod +x install_v4.sh
```

2. **目录权限：**
```bash
# 确保数据目录可写
chmod -R 755 data/
chmod -R 755 logs/
```

### 6. 内存不足

#### 错误信息：`内存不足` 或程序崩溃

**解决方案：**

1. **减少并发数：**
```env
WORKER_COUNT=2
```

2. **启用缓存：**
```env
ENABLE_CACHE=true
CACHE_SIZE_MB=50
```

3. **限制搜索结果：**
```env
WEB_SEARCH_RESULTS=5
DOCKER_SEARCH_LIMIT=10
```

### 7. API 限制问题

#### 错误信息：`API 速率限制` 或 `403 Forbidden`

**解决方案：**

1. **增加更多 Token：**
```env
GITHUB_TOKENS=token1,token2,token3,token4,token5
```

2. **调整速率限制：**
```env
GITHUB_RATE_LIMIT=1000
WEB_SEARCH_RATE_LIMIT=50
```

3. **使用不同的 Token 策略：**
```env
TOKEN_POOL_STRATEGY=ROUND_ROBIN
```

### 8. 搜索结果问题

#### 问题：搜索结果太少

**解决方案：**

1. **检查查询配置：**
```bash
# 编辑 data/queries.txt
nano data/queries.txt
```

2. **启用更多搜索源：**
```env
ENABLE_WEB_SEARCH=true
ENABLE_GITLAB_SEARCH=true
ENABLE_DOCKER_SEARCH=true
```

3. **增加搜索范围：**
```env
WEB_SEARCH_RESULTS=20
DOCKER_SEARCH_LIMIT=30
```

#### 问题：搜索结果质量差

**解决方案：**

1. **优化查询模式：**
```text
# 更具体的查询
AIzaSy in:file filename:.env
aws_access_key_id in:file path:config
```

2. **启用 AI 增强：**
```env
ENABLE_AI_SEARCH=true
ENABLE_PATTERN_RECOGNITION=true
```

## 🔧 调试技巧

### 1. 启用调试模式

```env
DEBUG=true
LOG_LEVEL=DEBUG
```

### 2. 查看详细日志

```bash
# 实时查看日志
tail -f logs/hajimi_king_$(date +%Y-%m-%d).log

# Windows
type logs\hajimi_king_2025-01-12.log
```

### 3. 测试单个模块

```bash
# 测试 GitHub 搜索
python -c "from app.core.scanner import Scanner; s = Scanner(); print('GitHub 搜索正常')"

# 测试扩展搜索
python -c "from app.features.extended_search.manager import ExtendedSearchManager; print('扩展搜索正常')"
```

### 4. 检查配置

```bash
# 显示当前配置
python -c "
from app.services.config_service import get_config_service
config = get_config_service()
for k, v in sorted(config.get_all().items()):
    if 'TOKEN' in k or 'KEY' in k:
        v = '***' if v else 'Not Set'
    print(f'{k}: {v}')
"
```

## 📊 性能优化

### 1. 系统资源优化

```env
# 根据系统配置调整
WORKER_COUNT=4  # CPU 核心数
CACHE_SIZE_MB=200  # 可用内存的 10%
REQUEST_TIMEOUT=30
```

### 2. 网络优化

```env
# 启用连接池
ENABLE_CONNECTION_POOL=true

# 调整并发数
MAX_CONCURRENT_REQUESTS=10
```

### 3. 存储优化

```env
# 启用压缩
ENABLE_COMPRESSION=true

# 定期清理
AUTO_CLEANUP_DAYS=7
```

## 🆘 获取帮助

### 1. 检查日志文件
- `logs/hajimi_king_YYYY-MM-DD.log` - 主日志
- `logs/error_YYYY-MM-DD.log` - 错误日志
- `logs/debug_YYYY-MM-DD.log` - 调试日志

### 2. 运行诊断脚本
```bash
# 创建诊断脚本
cat > diagnose.py << 'EOF'
import sys
import os
from pathlib import Path

print("=== HAJIMI KING V4.0 诊断报告 ===")
print(f"Python 版本: {sys.version}")
print(f"工作目录: {os.getcwd()}")
print(f"虚拟环境: {sys.prefix}")

# 检查关键文件
files = ['.env', 'requirements.txt', 'app/main_v4.py']
for file in files:
    exists = "✅" if Path(file).exists() else "❌"
    print(f"{exists} {file}")

# 检查关键模块
modules = ['requests', 'aiohttp', 'google.generativeai', 'docker']
for module in modules:
    try:
        __import__(module)
        print(f"✅ {module}")
    except ImportError:
        print(f"❌ {module}")

print("=== 诊断完成 ===")
EOF

python diagnose.py
```

### 3. 社区支持
- 📖 [完整文档](V4_COMPLETE_IMPLEMENTATION_GUIDE.md)
- 🐛 [提交问题](https://github.com/your-repo/hajimi-king/issues)
- 💬 [讨论区](https://github.com/your-repo/hajimi-king/discussions)

---

**如果问题仍然存在，请提供以下信息：**
1. 错误的完整堆栈跟踪
2. 系统信息（操作系统、Python 版本）
3. 配置文件内容（隐藏敏感信息）
4. 相关日志文件内容