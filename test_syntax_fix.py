#!/usr/bin/env python3
"""
测试 orchestrator_v2.py 语法修复
"""

import sys
import ast
from pathlib import Path

def test_syntax():
    """测试文件语法是否正确"""
    file_path = Path("app/core/orchestrator_v2.py")
    
    print(f"🔍 检查文件: {file_path}")
    
    try:
        # 读取文件内容
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 尝试编译代码
        compile(content, str(file_path), 'exec')
        
        # 使用 AST 解析
        ast.parse(content)
        
        print("✅ 语法检查通过！文件没有语法错误。")
        return True
        
    except SyntaxError as e:
        print(f"❌ 语法错误: {e}")
        print(f"   文件: {e.filename}")
        print(f"   行号: {e.lineno}")
        print(f"   位置: {e.offset}")
        print(f"   文本: {e.text}")
        return False
    except IndentationError as e:
        print(f"❌ 缩进错误: {e}")
        print(f"   文件: {e.filename}")
        print(f"   行号: {e.lineno}")
        print(f"   位置: {e.offset}")
        print(f"   文本: {e.text}")
        return False
    except Exception as e:
        print(f"❌ 其他错误: {e}")
        return False

def test_import():
    """测试是否可以成功导入模块"""
    print("\n🔍 测试导入 orchestrator_v2 模块...")
    
    try:
        # 添加项目根目录到 Python 路径
        project_root = Path(__file__).parent
        if str(project_root) not in sys.path:
            sys.path.insert(0, str(project_root))
        
        # 尝试导入模块
        from app.core.orchestrator_v2 import OrchestratorV2
        
        print("✅ 模块导入成功！")
        print(f"   OrchestratorV2 类已成功加载")
        return True
        
    except ImportError as e:
        print(f"❌ 导入错误: {e}")
        return False
    except Exception as e:
        print(f"❌ 其他错误: {e}")
        return False

def main():
    """主函数"""
    print("=" * 60)
    print("📝 Orchestrator V2 语法修复测试")
    print("=" * 60)
    
    # 测试语法
    syntax_ok = test_syntax()
    
    # 如果语法正确，测试导入
    if syntax_ok:
        import_ok = test_import()
    else:
        import_ok = False
    
    print("\n" + "=" * 60)
    print("📊 测试结果汇总")
    print("=" * 60)
    print(f"语法检查: {'✅ 通过' if syntax_ok else '❌ 失败'}")
    print(f"导入测试: {'✅ 通过' if import_ok else '❌ 失败'}")
    
    if syntax_ok and import_ok:
        print("\n🎉 所有测试通过！文件已成功修复。")
        return 0
    else:
        print("\n⚠️ 存在问题需要进一步检查。")
        return 1

if __name__ == "__main__":
    sys.exit(main())