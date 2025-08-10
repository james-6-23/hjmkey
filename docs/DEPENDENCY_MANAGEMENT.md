# 📦 依赖管理策略说明

## 📋 概述

Hajimi King 项目同时使用 `pyproject.toml` 和 `requirements.txt` 两个文件来管理依赖，这是现代 Python 项目的常见做法。这两种方式各有优势，适用于不同的场景。

## 📄 pyproject.toml

### 作用
`pyproject.toml` 是现代 Python 项目的标准配置文件，主要用于：
- 项目元数据定义
- 构建系统配置
- 核心依赖声明
- 开发工具配置

### 内容示例
```toml
[project]
name = "hajimi-king"
version = "0.0.1-beta"
description = "Add your description here"
readme = "README.md"
requires-python = ">=3.11"
dependencies = [
    "google-generativeai>=0.8.5",
    "python-dotenv>=1.1.1",
    "requests>=2.32.4",
]
```

### 优势
1. **标准化**: 符合 PEP 621 标准，是 Python 官方推荐的项目配置方式
2. **元数据完整**: 包含项目名称、版本、描述等完整元数据
3. **构建友好**: 与现代构建工具（如 Poetry、setuptools）兼容性好
4. **工具集成**: 可以配置多种开发工具（如 black、pylint 等）

## 📄 requirements.txt

### 作用
`requirements.txt` 是传统的 Python 依赖管理文件，主要用于：
- 详细依赖列表
- 开发/测试/生产环境区分
- 精确版本控制
- 快速环境搭建

### 内容示例
```
# Core Dependencies
google-generativeai>=0.8.5
python-dotenv>=1.1.1
requests>=2.32.4

# Async Support
aiohttp>=3.9.0
aiofiles>=23.2.1

# Testing Dependencies
pytest>=8.0.0
pytest-cov>=4.1.0
pytest-asyncio>=0.23.0
```

### 优势
1. **简单直观**: 格式简单，易于理解和维护
2. **环境隔离**: 可以为不同环境创建不同的 requirements 文件
3. **精确控制**: 可以指定精确的版本号和依赖关系
4. **广泛支持**: 几乎所有 Python 工具都支持 requirements.txt

## 🤝 两者并存的好处

### 1. **分工明确**
- `pyproject.toml`: 管理核心依赖和项目元数据
- `requirements.txt`: 管理开发依赖和详细配置

### 2. **灵活性**
- 可以使用不同的工具来管理不同类型的依赖
- 支持多种安装方式：
  ```bash
  # 使用 pip 安装 requirements.txt
  pip install -r requirements.txt
  
  # 使用构建工具安装 pyproject.toml
  pip install .
  ```

### 3. **兼容性**
- 兼顾传统和现代 Python 开发实践
- 支持不同的开发工作流和部署方式

### 4. **环境管理**
```
requirements.txt          # 生产环境依赖
requirements-dev.txt      # 开发环境依赖
requirements-test.txt     # 测试环境依赖
pyproject.toml           # 核心依赖和项目配置
```

## 🛠️ 实际使用建议

### 安装依赖
```bash
# 安装核心依赖（从 pyproject.toml）
pip install .

# 安装开发依赖（从 requirements.txt）
pip install -r requirements.txt

# 或者一次性安装所有依赖
pip install -r requirements.txt
pip install -e .  # 以可编辑模式安装项目
```

### 更新依赖
```bash
# 更新 requirements.txt 中的依赖
pip install -r requirements.txt --upgrade

# 更新 pyproject.toml 中的依赖（需要使用相应工具）
# 例如使用 Poetry:
poetry update
```

## 📊 依赖管理对比

| 特性 | pyproject.toml | requirements.txt |
|------|----------------|------------------|
| 标准化程度 | 高 (PEP 621) | 中等 |
| 元数据支持 | 完整 | 有限 |
| 版本控制 | 支持 | 完整支持 |
| 环境区分 | 有限 | 完整支持 |
| 工具兼容性 | 现代工具 | 所有工具 |
| 可读性 | 结构化 | 简单直观 |

## 🎯 最佳实践

1. **核心依赖放在 pyproject.toml**
   - 项目运行必需的最小依赖集
   - 保证项目可以被正确打包和分发

2. **开发依赖放在 requirements.txt**
   - 测试、文档、代码质量工具等
   - 可以按环境细分（dev/test/prod）

3. **保持同步**
   - 确保两个文件中的依赖版本不冲突
   - 定期更新和同步依赖版本

4. **文档说明**
   - 在 README 中说明依赖安装方式
   - 提供不同环境的安装指南

## 📝 总结

同时使用 `pyproject.toml` 和 `requirements.txt` 是一种成熟的依赖管理策略，它结合了两种方式的优势：

- **pyproject.toml** 提供了标准化的项目配置和核心依赖管理
- **requirements.txt** 提供了灵活的依赖列表和环境管理

这种组合方式既符合现代 Python 开发标准，又保持了足够的灵活性来满足不同场景的需求。