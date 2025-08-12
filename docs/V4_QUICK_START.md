# HAJIMI KING V4.0 快速开始指南

## 🚀 概述

HAJIMI KING V4.0 是一个增强版的密钥搜索工具，在原有 GitHub 搜索功能的基础上，新增了扩展搜索功能，支持：

- 🌐 **Web 搜索**：通过 Google、Bing、DuckDuckGo 搜索泄露的密钥
- 🦊 **GitLab 搜索**：搜索 GitLab 仓库中的密钥
- 🐳 **Docker Hub 搜索**：搜索 Docker 镜像中的密钥

## 📋 前置要求

- Python 3.8+
- Git
- 至少一个 GitHub Token
- （可选）Google API Key（用于 Web 搜索）
- （可选）GitLab Token（用于 GitLab 搜索）
- （可选）Docker Hub Token（用于 Docker 搜索）

## 🛠️ 安装步骤

### 1. 克隆仓库

```bash
git clone https://github.com/your-repo/hajimi-king.git
cd hajimi-king
```

### 2. 创建虚拟环境

```bash
# Linux/Mac
python3 -m venv venv
source venv/bin/activate

# Windows
python -m venv venv
venv\Scripts\activate
```

### 3. 安装依赖

```bash
pip install -r requirements.txt
```

### 4. 配置环境变量

```bash
# 复制环境配置示例
cp .env.v4.example .env

# 编辑配置文件
# Linux/Mac
nano .env

# Windows
notepad .env
```

**必须配置的项目：**

```env
# GitHub Token（至少一个）
GITHUB_TOKENS=ghp_your_token_here

# Gemini API Key（用于验证密钥）
GEMINI_API_KEY=your_gemini_api_key_here
```

**可选配置（扩展搜索）：**

```env
# 启用扩展搜索
ENABLE_EXTENDED_SEARCH=true

# Web 搜索
ENABLE_WEB_SEARCH=true
GOOGLE_API_KEY=your_google_api_key
GOOGLE_CSE_ID=your_cse_id

# GitLab 搜索
ENABLE_GITLAB_SEARCH=true
GITLAB_TOKEN=your_gitlab_token

# Docker 搜索
ENABLE_DOCKER_SEARCH=true
DOCKER_HUB_TOKEN=your_docker_token
```

## 🚀 快速运行

### 方式一：使用启动脚本

**Linux/Mac:**
```bash
chmod +x run_v4.sh
./run_v4.sh
```

**Windows:**
```cmd
run_v4.bat
```

### 方式二：直接运行

```bash
# 运行完整版（GitHub + 扩展搜索）
python -m app.main_v4

# 仅运行 GitHub 搜索
ENABLE_EXTENDED_SEARCH=false python -m app.main_v4

# Windows 下设置环境变量
set ENABLE_EXTENDED_SEARCH=false
python -m app.main_v4
```

## 📝 配置搜索查询

创建或编辑 `data/queries.txt` 文件：

```text
# HAJIMI KING V4.0 搜索查询配置
# 每行一个查询，以 # 开头的行将被忽略

# Google Maps API Keys
AIzaSy in:file
AIzaSy in:file filename:.env
AIzaSy in:file filename:config

# AWS Keys
AKIA in:file
aws_access_key_id in:file
aws_secret_access_key in:file

# 其他 API Keys
api_key in:file extension:json
apikey in:file extension:yml
secret_key in:file path:config
```

## 🎯 使用示例

### 1. 基础使用

启动程序后，选择菜单选项：

```
╔════════════════════════════════════════╗
║       HAJIMI KING V4.0 启动菜单        ║
╠════════════════════════════════════════╣
║  1. 运行完整版 (GitHub + 扩展搜索)     ║
║  2. 仅运行 GitHub 搜索                 ║
║  3. 仅运行扩展搜索                     ║
║  4. 运行测试模式                       ║
║  5. 查看配置信息                       ║
║  6. 退出                               ║
╚════════════════════════════════════════╝

请选择操作 (1-6): 1
```

### 2. 查看结果

运行完成后，结果将保存在：

```
data/
├── runs/
│   └── 2025-01-12_16-30-45_abc123/
│       ├── github_results.json
│       ├── web_results.json
│       ├── gitlab_results.json
│       ├── docker_results.json
│       └── summary_report.html
└── reports/
    └── 2025-01-12_report.html
```

### 3. 查看报告

打开生成的 HTML 报告查看详细结果：

```bash
# Linux/Mac
open data/reports/2025-01-12_report.html

# Windows
start data/reports/2025-01-12_report.html
```

## 🔧 高级配置

### 1. 配置代理

如果需要使用代理：

```env
HTTP_PROXY=http://proxy.example.com:8080
HTTPS_PROXY=http://proxy.example.com:8080
NO_PROXY=localhost,127.0.0.1
```

### 2. 配置通知

配置 Webhook 通知：

```env
ENABLE_NOTIFICATIONS=true
WEBHOOK_URL=https://hooks.slack.com/services/YOUR/WEBHOOK/URL
```

### 3. 性能优化

```env
# 增加并发数
WORKER_COUNT=10

# 启用缓存
ENABLE_CACHE=true
CACHE_TTL=3600

# 调整超时
REQUEST_TIMEOUT=60
```

## 🐛 故障排除

### 1. 常见问题

**问题：** ImportError: No module named 'xxx'
**解决：** 确保已激活虚拟环境并安装所有依赖

```bash
pip install -r requirements.txt
```

**问题：** GitHub API 速率限制
**解决：** 添加更多 GitHub Token

```env
GITHUB_TOKENS=token1,token2,token3,token4
```

**问题：** 连接超时
**解决：** 检查网络连接或配置代理

### 2. 调试模式

启用调试模式查看详细日志：

```env
DEBUG=true
LOG_LEVEL=DEBUG
```

### 3. 查看日志

日志文件位置：

```
logs/
├── hajimi_king_2025-01-12.log
├── error_2025-01-12.log
└── debug_2025-01-12.log
```

## 📊 性能基准

在标准配置下的性能表现：

| 搜索类型 | 平均耗时 | 结果数量 |
|---------|---------|---------|
| GitHub  | 30-60秒 | 100-500 |
| Web     | 10-20秒 | 20-100  |
| GitLab  | 20-40秒 | 50-200  |
| Docker  | 15-30秒 | 30-150  |

## 🔒 安全建议

1. **保护你的 Token**
   - 不要将 `.env` 文件提交到版本控制
   - 定期轮换 Token
   - 使用最小权限原则

2. **加密存储**
   ```env
   ALLOW_PLAINTEXT=false
   ENCRYPTION_KEY=your_strong_encryption_key
   ```

3. **安全日志**
   ```env
   SECURE_LOGGING=true
   ```

## 🤝 贡献指南

欢迎贡献代码！请查看 [CONTRIBUTING.md](CONTRIBUTING.md) 了解详情。

## 📄 许可证

本项目采用 MIT 许可证。详见 [LICENSE](LICENSE) 文件。

## 🆘 获取帮助

- 📖 [完整文档](V4_COMPLETE_IMPLEMENTATION_GUIDE.md)
- 🐛 [提交问题](https://github.com/your-repo/hajimi-king/issues)
- 💬 [讨论区](https://github.com/your-repo/hajimi-king/discussions)

---

**Happy Hunting! 🎯**