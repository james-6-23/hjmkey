#!/bin/bash

# Hajimi King - Initialization Script
# 用于在本地开发环境初始化项目

set -e  # 遇到错误时停止执行

# 颜色输出函数
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'

uv venv

source .venv/bin/activate

# Install base dependencies from pyproject.toml (uses uv.lock if present)
uv sync

# Install development and testing dependencies
uv pip install -r requirements.txt
