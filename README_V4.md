# HAJIMI KING V4.0 🎯

> **扩展搜索版本** - 在原有 GitHub 搜索基础上新增多平台密钥搜索能力

[![Python](https://img.shields.io/badge/Python-3.8+-blue.svg)](https://python.org)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Version](https://img.shields.io/badge/Version-4.0.0-red.svg)](CHANGELOG.md)

## 🚀 V4 新特性

### 🌐 多平台搜索支持
- **GitHub 搜索** - 原有的强大 GitHub 代码搜索
- **Web 搜索** - 通过 Google、Bing、DuckDuckGo 搜索泄露密钥
- **GitLab 搜索** - 搜索 GitLab 仓库中的敏感信息
- **Docker Hub 搜索** - 扫描 Docker 镜像中的密钥泄露

### ⚡ 增强功能
- **统一搜索管理** - 一键启动所有搜索引擎
- **智能结果去重** - 自动识别和合并重复结果
- **批量密钥验证** - 使用 AI 验证找到的密钥有效性
- **详细报告生成** - 生成包含所有平台结果的综合报告

## 📋 快速开始

### 1. 自动安装（推荐）

**Linux/Mac:**
```bash
chmod +x install_v4.sh
./install_v4.sh
```

**Windows:**
```cmd
install_v4.bat
```

### 2. 手动安装

```bash
# 1. 克隆仓库
git clone https://github.com/your-repo/hajimi-king.git
cd hajimi-king

# 2. 创建虚拟环境
python3 -m venv venv
source venv/bin/activate  # Linux/Mac
# venv\Scripts\activate   # Windows

# 3. 安装依赖
pip install -r requirements.txt

# 4. 配置环境
cp .env.v4.example .env
# 编辑 .env 文件，配置必要的 Token
```

### 3. 运行程序

**使用启动脚本（推荐）:**
```bash
./run_v4.sh      # Linux/Mac
run_v4.bat       # Windows
```

**直接运行:**
```bash
python -m app.main_v4
```

## ⚙️ 配置说明

### 必需配置

```env
# GitHub Token（至少一个）
GITHUB_TOKENS=ghp_your_token_here

# Gemini API Key（用于验证密钥）
GEMINI_API_KEY=your_gemini_api_key_here
```

### V4 扩展搜索配置

```env
# 启用扩展搜索
ENABLE_EXTENDED_SEARCH=true

# Web 搜索配置
ENABLE_WEB_SEARCH=true
GOOGLE_API_KEY=your_google_api_key
GOOGLE_CSE_ID=your_cse_id
BING_API_KEY=your_bing_api_key

# GitLab 搜索配置
ENABLE_GITLAB_SEARCH=true
GITLAB_TOKEN=your_gitlab_token
GITLAB_URL=https://gitlab.com

# Docker 搜索配置
ENABLE_DOCKER_SEARCH=true
DOCKER_HUB_TOKEN=your_docker_token
```

## 🎯 使用示例

### 启动菜单

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
```

### 搜索结果示例

```
╔════════════════════════════════════════════════════════════════════════════╗
║                          执行结果统计                                        ║
╠════════════════════════════════════════════════════════════════════════════╣
║  运行 ID      : run_20250112_164530_abc123                                ║
║  执行时间     : 45.2 秒                                                    ║
║  查询进度     : 5/5                                                        ║
╠════════════════════════════════════════════════════════════════════════════╣
║                          GitHub 密钥统计                                     ║
╠════════════════════════════════════════════════════════════════════════════╣
║  有效密钥     : 23 个                                                      ║
║    - 免费版   : 18 个                                                      ║
║    - 付费版   : 5 个                                                       ║
║  限流密钥     : 2 个                                                       ║
║  无效密钥     : 7 个                                                       ║
╠════════════════════════════════════════════════════════════════════════════╣
║                          扩展搜索统计                                        ║
╠════════════════════════════════════════════════════════════════════════════╣
║  总结果数     : 156 个                                                     ║
║  有效密钥     : 34 个                                                      ║
║  无效密钥     : 122 个                                                     ║
╚════════════════════════════════════════════════════════════════════════════╝
```

## 📁 项目结构

```
hajimi-king/
├── app/
│   ├── main_v4.py                    # V4 主程序
│   ├── features/
│   │   └── extended_search/          # 扩展搜索模块
│   │       ├── manager.py            # 搜索管理器
│   │       ├── web_searcher.py       # Web 搜索器
│   │       ├── gitlab_searcher.py    # GitLab 搜索器
│   │       └── docker_searcher.py    # Docker 搜索器
│   └── ...
├── utils/
│   └── token_hunter_v4/              # V4 工具包
│       ├── hunter_v4.py              # 主搜索类
│       └── __init__.py
├── docs/
│   ├── V4_QUICK_START.md             # 快速开始指南
│   ├── V4_COMPLETE_IMPLEMENTATION_GUIDE.md  # 完整实现指南
│   └── V4_TROUBLESHOOTING.md         # 故障排除指南
├── run_v4.sh                         # Linux/Mac 启动脚本
├── run_v4.bat                        # Windows 启动脚本
├── install_v4.sh                     # Linux/Mac 安装脚本
├── install_v4.bat                    # Windows 安装脚本
├── test_v4.py                        # V4 功能测试脚本
├── .env.v4.example                   # V4 配置示例
└── requirements.txt                  # 依赖列表
```

## 🔍 支持的密钥类型

- **GitHub Tokens** - `ghp_`, `github_pat_`, `ghs_`
- **Google API Keys** - `AIzaSy`
- **OpenAI Keys** - `sk-`
- **GitLab Tokens** - `glpat-`
- **AWS Keys** - `AKIA`, `aws_access_key_id`
- **更多类型** - 支持自定义正则表达式

## 📊 性能基准

| 搜索类型 | 平均耗时 | 结果数量 | 并发支持 |
|---------|---------|---------|---------|
| GitHub  | 30-60秒 | 100-500 | ✅ |
| Web     | 10-20秒 | 20-100  | ✅ |
| GitLab  | 20-40秒 | 50-200  | ✅ |
| Docker  | 15-30秒 | 30-150  | ✅ |

## 🛠️ 高级功能

### 1. 智能搜索策略
- **自适应令牌池** - 自动优化 Token 使用
- **智能去重** - 基于内容相似度的结果去重
- **模式识别** - AI 辅助的密钥模式识别

### 2. 监控和报告
- **实时进度显示** - Rich 库提供的美观进度条
- **详细统计报告** - 包含所有平台的综合统计
- **HTML 报告生成** - 可视化的搜索结果报告

### 3. 安全特性
- **自动脱敏** - 日志中自动隐藏敏感信息
- **加密存储** - 支持密钥加密存储
- **安全传输** - 所有 API 调用使用 HTTPS

## 🧪 测试和验证

### 运行测试
```bash
# 运行 V4 功能测试
python test_v4.py

# 运行完整测试套件
python -m pytest tests/ -v
```

### 验证安装
```bash
# 检查依赖
pip list | grep -E "(docker|selenium|beautifulsoup4)"

# 验证配置
python -c "from app.services.config_service import get_config_service; print('配置正常')"
```

## 🔧 故障排除

### 常见问题

1. **ModuleNotFoundError: No module named 'docker'**
   ```bash
   pip install docker>=7.0.0
   ```

2. **GitHub API 速率限制**
   ```env
   # 添加更多 Token
   GITHUB_TOKENS=token1,token2,token3,token4
   ```

3. **网络连接问题**
   ```env
   # 配置代理
   HTTP_PROXY=http://proxy.example.com:8080
   HTTPS_PROXY=http://proxy.example.com:8080
   ```

更多问题请查看 [故障排除指南](docs/V4_TROUBLESHOOTING.md)

## 📚 文档

- 📖 [快速开始指南](docs/V4_QUICK_START.md)
- 🔧 [完整实现指南](docs/V4_COMPLETE_IMPLEMENTATION_GUIDE.md)
- 🐛 [故障排除指南](docs/V4_TROUBLESHOOTING.md)
- 📋 [实现计划](docs/V4_IMPLEMENTATION_PLAN.md)

## 🤝 贡献

欢迎贡献代码！请遵循以下步骤：

1. Fork 本仓库
2. 创建功能分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 打开 Pull Request

## 📄 许可证

本项目采用 MIT 许可证。详见 [LICENSE](LICENSE) 文件。

## 🆘 获取帮助

- 🐛 [提交问题](https://github.com/your-repo/hajimi-king/issues)
- 💬 [讨论区](https://github.com/your-repo/hajimi-king/discussions)
- 📧 [联系我们](mailto:support@example.com)

## 🎉 致谢

感谢所有贡献者和开源社区的支持！

---

**⚠️ 免责声明**

本工具仅用于安全研究和教育目的。请遵守相关法律法规，不要用于非法用途。使用本工具产生的任何后果由使用者自行承担。

**Happy Hunting! 🎯**