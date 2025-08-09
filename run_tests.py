#!/usr/bin/env python
"""
测试运行脚本
运行所有单元测试并生成覆盖率报告
"""

import sys
import subprocess
from pathlib import Path

def run_tests():
    """运行测试套件"""
    print("=" * 60)
    print("🧪 RUNNING HAJIMI KING TEST SUITE")
    print("=" * 60)
    
    # 项目根目录
    root_dir = Path(__file__).parent
    
    # 测试命令
    commands = [
        # 安装测试依赖
        ["pip", "install", "-q", "pytest", "pytest-cov", "pytest-asyncio"],
        
        # 运行单元测试
        ["pytest", "tests/unit/", "-v", "--tb=short"],
        
        # 运行测试并生成覆盖率报告
        ["pytest", "tests/", 
         "--cov=app", 
         "--cov-report=term-missing",
         "--cov-report=html:htmlcov",
         "-v"],
    ]
    
    # 执行命令
    for cmd in commands:
        print(f"\n📌 Running: {' '.join(cmd)}")
        print("-" * 40)
        
        result = subprocess.run(cmd, cwd=root_dir)
        
        if result.returncode != 0:
            print(f"❌ Command failed with exit code {result.returncode}")
            return result.returncode
    
    print("\n" + "=" * 60)
    print("✅ All tests completed successfully!")
    print("📊 Coverage report generated in htmlcov/index.html")
    print("=" * 60)
    
    return 0

if __name__ == "__main__":
    sys.exit(run_tests())