# 🚀 HAJIMI KING V2.0 - 快速启动指南

## 📋 目录
1. [系统要求](#系统要求)
2. [快速安装](#快速安装)
3. [配置设置](#配置设置)
4. [运行测试](#运行测试)
5. [启动系统](#启动系统)
6. [查看结果](#查看结果)
7. [故障排查](#故障排查)

---

## 系统要求

- Python 3.8+
- 2GB+ RAM
- 网络连接
- GitHub 令牌（至少 3 个）
- Gemini API 密钥（用于验证）

## 快速安装

### 1. 克隆仓库
```bash
git clone https://github.com/yourusername/hajimi-king.git
cd hajimi-king
```

### 2. 创建虚拟环境
```bash
python -m venv venv

# Linux/Mac
source venv/bin/activate

# Windows
venv\Scripts\activate
```

### 3. 安装依赖
```bash
pip install -r requirements.txt
```

## 配置设置

### 1. 复制配置模板
```bash
cp env.v2.example .env
```

### 2. 编辑配置文件
```bash
# 使用你喜欢的编辑器
nano .env
# 或
vim .env
```

### 3. 必须配置的项目

#### GitHub 令牌
创建文件 `data/github_tokens.txt`，每行一个令牌：
```
github_pat_11XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX
github_pat_11YYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYY
github_pat_11ZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZ
```

#### 环境变量
编辑 `.env` 文件：
```bash
# GitHub 配置
GITHUB_TOKENS_FILE=data/github_tokens.txt
TOKEN_POOL_STRATEGY=ADAPTIVE

# Gemini 配置
GEMINI_API_KEY=your_gemini_api_key_here

# 安全配置（生产环境）
ALLOW_PLAINTEXT=false
HMAC_SALT=your_strong_secret_key_here

# 功能开关
ENABLE_ASYNC_VALIDATION=true
ENABLE_PROGRESS_DISPLAY=true
ENABLE_CONNECTION_POOL=true
```

### 4. 创建查询文件（可选）
创建 `data/queries.txt`：
```
# Gemini API 密钥搜索
AIzaSy in:file
AIzaSy in:file filename:.env
AIzaSy in:file filename:config
AIzaSy in:file extension:json
AIzaSy in:file extension:yaml
```

## 运行测试

### 1. 运行集成测试
```bash
python test_integration_v2.py
```

预期输出：
```
============================================================
🧪 HAJIMI KING V2.0 - INTEGRATION TEST SUITE
============================================================
🧪 Running test: Stats Model
✅ Stats Model: PASSED
🧪 Running test: Security Utils
✅ Security Utils: PASSED
...
============================================================
📊 TEST SUMMARY
============================================================
Total: 7
Passed: 7 ✅
Failed: 0 ❌
Success Rate: 100.0%
```

### 2. 测试单个组件
```bash
# 测试 TokenPool
python -m utils.token_pool

# 测试安全工具
python -m utils.security_utils

# 测试文件工具
python -m utils.file_utils
```

## 启动系统

### 1. 基本运行
```bash
python app/main_v2.py
```

### 2. 后台运行（Linux/Mac）
```bash
nohup python app/main_v2.py > output.log 2>&1 &
```

### 3. 使用 Docker（可选）
```bash
docker build -t hajimi-king-v2 .
docker run -v $(pwd)/data:/app/data hajimi-king-v2
```

## 查看结果

### 1. 实时日志
运行时会显示详细日志：
```
2025-08-10 18:23:11 | INFO | 🚀 HAJIMI KING V2.0 - INITIALIZING
2025-08-10 18:23:11 | INFO | 📁 Run ID: 20250810_182311_1234
2025-08-10 18:23:11 | INFO | 🔍 Processing query: AIzaSy in:file
2025-08-10 18:23:15 | INFO | ✅ VALID (VALID_FREE): AIzaSy...1co
```

### 2. 查看报告
报告保存在 `data/runs/{run_id}/` 目录：

```bash
# 查看最新运行
ls -la data/latest/

# 查看最终报告
cat data/latest/reports/final_report.md

# 查看找到的密钥（已脱敏）
cat data/latest/keys_summary.json
```

### 3. 报告结构
```
data/runs/20250810_182311_1234/
├── reports/
│   ├── final_report.json      # JSON 格式报告
│   └── final_report.md         # Markdown 格式报告
├── secrets/                    # 密钥存储（受保护）
│   ├── keys_valid_free.txt     # 免费版密钥
│   └── keys_valid_paid.txt     # 付费版密钥
├── artifacts/                  # 中间产物
│   └── token_pool_final.json   # TokenPool 最终状态
├── checkpoints/                # 检查点
│   └── checkpoint_*.json       # 运行检查点
└── keys_summary.json           # 脱敏的密钥摘要
```

## 故障排查

### 问题 1：No running event loop
**解决方案**：已在 V2 中修复，确保使用 `main_v2.py`

### 问题 2：Rate limit 频繁触发
**解决方案**：
1. 增加 GitHub 令牌数量
2. 调整 TokenPool 策略为 ADAPTIVE
3. 降低 `GITHUB_QPS_MAX` 值

### 问题 3：数据丢失严重
**解决方案**：
1. 检查网络连接
2. 增加 `GITHUB_PAGE_RETRY_MAX`
3. 启用数据补偿机制

### 问题 4：密钥验证失败
**解决方案**：
1. 检查 Gemini API 密钥是否有效
2. 确认网络可以访问 Google API
3. 查看 `data/errors/` 目录的错误日志

### 问题 5：权限错误
**解决方案**（Linux/Mac）：
```bash
# 设置正确的权限
chmod 700 data/runs/*/secrets/
chmod 600 data/runs/*/secrets/*
```

## 高级配置

### 1. 性能优化
```bash
# .env 文件
MAX_CONCURRENT_SEARCHES=10      # 增加并发搜索
MAX_CONCURRENT_VALIDATIONS=20   # 增加并发验证
CONNECTION_POOL_SIZE=100         # 增大连接池
```

### 2. 监控设置
```bash
# 启用 Prometheus 指标
ENABLE_PROMETHEUS=true
PROMETHEUS_PORT=9090

# 访问指标
curl http://localhost:9090/metrics
```

### 3. 告警配置
```bash
# Webhook 通知
WEBHOOK_URL=https://hooks.slack.com/services/xxx
WEBHOOK_ON_SUCCESS=true
WEBHOOK_ON_FAILURE=true
ALERT_DATA_LOSS_THRESHOLD=0.3
```

## 生产部署建议

### 1. 安全检查清单
- [ ] 设置 `ALLOW_PLAINTEXT=false`
- [ ] 更改 `HMAC_SALT` 为强密码
- [ ] 设置文件权限（umask 077）
- [ ] 使用独立的运行用户
- [ ] 启用日志脱敏
- [ ] 定期轮换令牌

### 2. 性能优化
- [ ] 使用至少 10 个 GitHub 令牌
- [ ] 启用所有异步功能
- [ ] 配置合适的连接池大小
- [ ] 使用 SSD 存储
- [ ] 确保稳定的网络连接

### 3. 监控和维护
- [ ] 设置日志轮转
- [ ] 配置监控告警
- [ ] 定期清理旧运行数据
- [ ] 备份重要密钥
- [ ] 监控 API 配额使用

## 常用命令

```bash
# 查看最新运行结果
cat data/latest/reports/final_report.md

# 统计找到的密钥
jq '.keys' data/latest/reports/final_report.json

# 查看 TokenPool 状态
jq '.token_pool_status' data/latest/artifacts/token_pool_final.json

# 清理旧数据（保留最近 7 天）
find data/runs -type d -mtime +7 -exec rm -rf {} \;

# 验证配置
python -c "from app.services.config_service import get_config_service; print(get_config_service().to_dict())"
```

## 获取帮助

- 📖 [完整文档](./IMPLEMENTATION_SUMMARY.md)
- 🐛 [问题反馈](https://github.com/yourusername/hajimi-king/issues)
- 💬 [讨论区](https://github.com/yourusername/hajimi-king/discussions)

---

## 🎉 恭喜！

您已经成功配置并运行了 HAJIMI KING V2.0！

系统现在具有：
- ✅ 统一的统计模型
- ✅ 完整的安全机制
- ✅ 智能的令牌调度
- ✅ 优雅的停机处理
- ✅ 原子化的文件操作

祝您使用愉快！🚀