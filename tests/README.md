# 🧪 Hajimi King 测试脚本

本目录包含用于测试Hajimi King模块化功能的各种测试脚本。

## 📋 测试脚本列表

### 1. 特性管理器测试
- **文件**: `test_feature_manager.py`
- **功能**: 测试模块化架构的核心组件
- **运行**: `python tests/test_feature_manager.py`

### 2. 异步验证功能测试
- **文件**: `test_async_validation.py`
- **功能**: 测试10倍性能提升的验证功能
- **运行**: `python tests/test_async_validation.py`

### 3. 监控告警功能测试
- **文件**: `test_monitoring.py`
- **功能**: 测试系统健康和性能洞察功能
- **运行**: `python tests/test_monitoring.py`

### 4. 插件系统测试
- **文件**: `test_plugins.py`
- **功能**: 测试动态加载和热重载功能
- **运行**: `python tests/test_plugins.py`

### 5. 综合功能测试
- **文件**: `test_all_features.py`
- **功能**: 展示所有模块化功能的集成使用
- **运行**: `python tests/test_all_features.py`

## 🚀 使用方法

1. **设置环境变量**（可选）:
   ```bash
   # 复制完整配置文件
   cp env.full .env
   # 编辑 .env 文件启用/禁用功能
   ```

2. **运行单个测试**:
   ```bash
   # 测试特性管理器
   python tests/test_feature_manager.py
   
   # 测试异步验证功能
   python tests/test_async_validation.py
   
   # 测试监控功能
   python tests/test_monitoring.py
   
   # 测试插件系统
   python tests/test_plugins.py
   ```

3. **运行综合测试**:
   ```bash
   # 运行所有功能的综合测试
   python tests/test_all_features.py
   ```

## 📝 注意事项

1. **依赖项**: 确保已安装所有必要的依赖项
   ```bash
   pip install -r requirements.full.txt
   ```

2. **数据目录**: 某些测试可能需要创建数据目录
   ```bash
   mkdir -p data logs
   ```

3. **数据库测试**: 数据库功能测试会创建测试数据库文件
   ```bash
   # 测试完成后清理
   rm data/test.db
   ```

4. **异步功能**: 包含异步功能的测试需要使用`asyncio.run()`

## 🧩 功能模块测试说明

### 异步批量验证模块
- 测试并发验证性能
- 验证GitHub Token和Gemini API Key
- 测试超时和重试机制

### 进度显示模块
- 测试各种进度显示样式
- 验证进度跟踪功能
- 测试完成回调机制

### 结构化日志模块
- 测试多种日志格式（JSON/XML/YAML）
- 验证日志轮转功能
- 测试日志导出功能

### 连接池优化模块
- 测试连接复用机制
- 验证超时和重试处理
- 测试连接池健康检查

### 数据库支持模块
- 测试多种数据库后端
- 验证CRUD操作
- 测试连接池管理

### 插件系统模块
- 测试动态加载功能
- 验证热重载机制
- 测试插件生命周期管理

### 监控告警模块
- 测试指标收集功能
- 验证告警触发机制
- 测试健康检查功能

## 📊 预期输出

运行测试脚本时，您应该看到类似以下的输出：

```
🎪 Hajimi King 模块化功能综合测试
==================================================
🧪 测试特性管理器集成...
📋 所有功能状态:
  ✅ async_validation: active
  ✅ monitoring: active
  ✅ structured_logging: active
  ...

✅ 特性管理器集成测试完成

🧪 测试结构化日志功能...
  ✅ 日志记录测试完成
  📋 最近日志数量: 3
...

🎉 所有测试完成!
```

## 🔧 故障排除

1. **导入错误**:
   - 确保在项目根目录运行测试脚本
   - 检查Python路径设置

2. **依赖缺失**:
   - 运行 `pip install -r requirements.full.txt`

3. **权限问题**:
   - 确保有写入data和logs目录的权限

4. **数据库连接失败**:
   - 检查数据库配置
   - 确保SQLite支持可用

## 📈 测试覆盖范围

这些测试脚本覆盖了以下方面：

- [x] 功能模块初始化
- [x] 健康检查机制
- [x] 降级实现
- [x] 核心功能测试
- [x] 集成测试
- [x] 异常处理
- [x] 配置验证