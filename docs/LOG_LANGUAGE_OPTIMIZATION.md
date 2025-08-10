# 日志语言优化规范

## 概述
HAJIMI KING V2.0 的日志系统采用中英文混合策略，为用户提供友好的体验同时保持专业性。

## 语言使用原则

### 1. 中文日志（用户友好）
用于程序的开始和结束，让用户快速理解程序状态：

| 位置 | 示例 |
|------|------|
| **程序启动** | `🚀 HAJIMI KING V2.0 - 增强版协调器` |
| **运行信息** | `📁 运行ID: 20250810_220053` |
| **运行目录** | `📂 运行目录: /root/hjmkey/data/runs/20250810_220053` |
| **最终统计** | `📊 最终统计` |
| **Token池统计** | `📊 Token池统计` |

### 2. 英文日志（专业操作）
用于所有常规操作和技术细节：

| 操作类型 | 示例 |
|----------|------|
| **查询处理** | `Processing query: AIzaSy in:file` |
| **文件发现** | `Found 65 files` |
| **密钥验证** | `VALID (FREE)`, `VALID (PAID)`, `INVALID`, `RATE LIMITED` |
| **文件保存** | `Key saved to keys_valid_free.txt` |
| **错误信息** | `Query failed`, `Failed to save key` |
| **状态更新** | `All queries completed`, `No results found` |

## 图标系统

### 密钥状态图标
- ✅ **Valid (Free)** - 免费有效密钥
- 💎 **Valid (Paid)** - 付费有效密钥（突出显示高价值）
- ⚠️ **Rate Limited** - 限流密钥（429状态）
- ❌ **Invalid** - 无效密钥

### 操作状态图标
- 🔑 **Found** - 发现密钥
- 💾 **Saved** - 保存文件
- 📦 **Files** - 文件数量
- 📭 **Empty** - 无结果
- 🔍 **Search** - 搜索操作
- 📊 **Statistics** - 统计信息
- ⏱️ **Duration** - 耗时
- 🎯 **Token Status** - Token状态

## 查询统计格式

### 美化的查询完成统计（英文）
```
╔══════════════════════════════════════════════════════════╗
║ 📊 Query Complete: AIzaSy in:file                       ║
╠══════════════════════════════════════════════════════════╣
║ ⏱️  Duration: 140.9s                                     ║
║ 🔑 Keys found: 65                                       ║
║    ├─ ✅ Valid (Free): +4                               ║
║    ├─ 💎 Valid (Paid): +3                               ║
║    ├─ ⚠️  Rate Limited: +3                              ║
║    └─ ❌ Invalid: +55                                   ║
╠══════════════════════════════════════════════════════════╣
║ 📈 Total Statistics:                                     ║
║    Total Valid: 7                                       ║
║    Total Rate Limited: 5                                ║
║    Total Invalid: 96                                    ║
╠══════════════════════════════════════════════════════════╣
║ 🎯 Token Status: 16 OK, 0 Limited, 1 Exhausted          ║
║    Quota: 480/510 (5.9%)                                ║
╚══════════════════════════════════════════════════════════╝
```

### 最终统计格式（中文）
```
============================================================
📊 最终统计
============================================================
Run ID: 20250810_220053
Duration: 231.8 seconds
Queries: 2/28
Items processed: 108
Valid keys (total/free/paid): 7/4/3
Rate limited: 5
Invalid: 96
============================================================
📊 Token池统计
Total tokens: 17
Healthy/Limited/Exhausted: 16/0/1
Utilization: 5.9%
============================================================
```

## 实现文件
- **主要实现**: `app/core/orchestrator_v2.py`
- **日志配置**: `utils/security_utils.py`
- **主程序**: `app/main_v2.py`

## 优势
1. **用户友好**: 中文开头结尾，用户快速理解程序状态
2. **专业规范**: 英文技术日志，便于国际化和调试
3. **视觉突出**: 💎 图标突出显示付费密钥的价值
4. **格式美观**: 使用框线和缩进，信息层次清晰
5. **信息完整**: 包含所有关键指标和状态

## 配置建议
```python
# 日志级别配置
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)s | %(name)s | %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
```

## 注意事项
1. 保持日志简洁，避免冗余信息
2. 敏感信息（如密钥）必须脱敏显示
3. 错误信息应包含足够的上下文
4. 统计信息应实时更新，反映真实状态
5. 使用北京时间（GMT+8）显示所有时间戳