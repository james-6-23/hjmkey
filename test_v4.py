#!/usr/bin/env python3
"""
HAJIMI KING V4.0 测试脚本
用于验证 V4 功能是否正常工作
"""

import asyncio
import sys
import os
from pathlib import Path
import logging

# 添加项目根目录到 Python 路径
sys.path.insert(0, str(Path(__file__).parent))

# 设置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)s | %(message)s'
)
logger = logging.getLogger(__name__)


def test_imports():
    """测试模块导入"""
    logger.info("🧪 测试模块导入...")
    
    try:
        # 测试核心模块
        from app.services.config_service import get_config_service
        logger.info("✅ 配置服务导入成功")
        
        from app.core.orchestrator_v2 import OrchestratorV2
        logger.info("✅ 协调器导入成功")
        
        from app.features.feature_manager import get_feature_manager
        logger.info("✅ 功能管理器导入成功")
        
        # 测试 V4 扩展模块
        from app.features.extended_search.manager import ExtendedSearchManager
        logger.info("✅ 扩展搜索管理器导入成功")
        
        from utils.token_hunter_v4.hunter_v4 import TokenHunterV4
        logger.info("✅ TokenHunterV4 导入成功")
        
        return True
        
    except ImportError as e:
        logger.error(f"❌ 模块导入失败: {e}")
        return False


def test_config():
    """测试配置加载"""
    logger.info("🧪 测试配置加载...")
    
    try:
        from app.services.config_service import get_config_service
        
        config = get_config_service()
        
        # 检查基本配置
        environment = config.get("ENVIRONMENT", "development")
        logger.info(f"✅ 环境: {environment}")
        
        # 检查 GitHub tokens
        tokens = config.get("GITHUB_TOKENS_LIST", [])
        if tokens:
            logger.info(f"✅ GitHub tokens: {len(tokens)} 个")
        else:
            logger.warning("⚠️ 未配置 GitHub tokens")
        
        # 检查 V4 配置
        extended_search = config.get("ENABLE_EXTENDED_SEARCH", True)
        logger.info(f"✅ 扩展搜索: {'启用' if extended_search else '禁用'}")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ 配置加载失败: {e}")
        return False


def test_directories():
    """测试目录结构"""
    logger.info("🧪 测试目录结构...")
    
    required_dirs = [
        "data",
        "data/runs",
        "data/reports",
        "data/cache",
        "logs"
    ]
    
    all_exist = True
    for dir_path in required_dirs:
        path = Path(dir_path)
        if path.exists():
            logger.info(f"✅ {dir_path}")
        else:
            logger.warning(f"⚠️ {dir_path} 不存在，将自动创建")
            path.mkdir(parents=True, exist_ok=True)
            all_exist = False
    
    return all_exist


async def test_extended_search():
    """测试扩展搜索功能"""
    logger.info("🧪 测试扩展搜索功能...")
    
    try:
        from app.features.extended_search.manager import ExtendedSearchManager
        from app.services.config_service import get_config_service
        
        config = get_config_service()
        
        if not config.get("ENABLE_EXTENDED_SEARCH", True):
            logger.info("ℹ️ 扩展搜索已禁用，跳过测试")
            return True
        
        # 创建管理器
        manager = ExtendedSearchManager()
        
        # 测试初始化各个搜索器
        if config.get("ENABLE_WEB_SEARCH", True):
            try:
                await manager.initialize_searcher("web")
                logger.info("✅ Web 搜索器初始化成功")
            except Exception as e:
                logger.warning(f"⚠️ Web 搜索器初始化失败: {e}")
        
        if config.get("ENABLE_GITLAB_SEARCH", True):
            try:
                await manager.initialize_searcher("gitlab")
                logger.info("✅ GitLab 搜索器初始化成功")
            except Exception as e:
                logger.warning(f"⚠️ GitLab 搜索器初始化失败: {e}")
        
        if config.get("ENABLE_DOCKER_SEARCH", True):
            try:
                await manager.initialize_searcher("docker")
                logger.info("✅ Docker 搜索器初始化成功")
            except Exception as e:
                logger.warning(f"⚠️ Docker 搜索器初始化失败: {e}")
        
        # 清理
        await manager.cleanup()
        
        return True
        
    except Exception as e:
        logger.error(f"❌ 扩展搜索测试失败: {e}")
        return False


async def test_token_hunter_v4():
    """测试 TokenHunterV4"""
    logger.info("🧪 测试 TokenHunterV4...")
    
    try:
        from utils.token_hunter_v4.hunter_v4 import TokenHunterV4
        from app.features.extended_search.manager import ExtendedSearchManager
        
        # 创建扩展搜索管理器
        manager = ExtendedSearchManager()
        
        # 创建 TokenHunterV4
        hunter = TokenHunterV4(manager)
        
        logger.info("✅ TokenHunterV4 创建成功")
        
        # 清理
        await manager.cleanup()
        
        return True
        
    except Exception as e:
        logger.error(f"❌ TokenHunterV4 测试失败: {e}")
        return False


def test_optional_dependencies():
    """测试可选依赖"""
    logger.info("🧪 测试可选依赖...")
    
    optional_modules = {
        'docker': 'Docker 支持',
        'selenium': 'Selenium WebDriver',
        'GPUtil': 'GPU 监控',
        'beautifulsoup4': 'HTML 解析',
        'python-gitlab': 'GitLab API'
    }
    
    for module, description in optional_modules.items():
        try:
            __import__(module)
            logger.info(f"✅ {description} ({module})")
        except ImportError:
            logger.warning(f"⚠️ {description} ({module}) 未安装")
    
    return True


async def run_basic_search_test():
    """运行基础搜索测试"""
    logger.info("🧪 运行基础搜索测试...")
    
    try:
        from app.core.orchestrator_v2 import OrchestratorV2
        
        # 创建协调器
        orchestrator = OrchestratorV2()
        
        # 使用简单的测试查询
        test_queries = ["test in:file filename:.env"]
        
        logger.info("开始基础搜索测试（限制 1 个循环）...")
        
        # 运行搜索（限制循环数）
        stats = await orchestrator.run(test_queries, max_loops=1)
        
        summary = stats.summary()
        logger.info(f"✅ 基础搜索测试完成")
        logger.info(f"   查询数: {summary['queries']['completed']}")
        logger.info(f"   执行时间: {summary['duration_seconds']:.1f} 秒")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ 基础搜索测试失败: {e}")
        return False


async def main():
    """主测试函数"""
    logger.info("🚀 开始 HAJIMI KING V4.0 功能测试")
    logger.info("=" * 60)
    
    tests = [
        ("模块导入", test_imports),
        ("配置加载", test_config),
        ("目录结构", test_directories),
        ("可选依赖", test_optional_dependencies),
        ("扩展搜索", test_extended_search),
        ("TokenHunterV4", test_token_hunter_v4),
    ]
    
    # 运行同步测试
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        logger.info(f"\n📋 {test_name} 测试:")
        try:
            if asyncio.iscoroutinefunction(test_func):
                result = await test_func()
            else:
                result = test_func()
            
            if result:
                passed += 1
                logger.info(f"✅ {test_name} 测试通过")
            else:
                logger.error(f"❌ {test_name} 测试失败")
        except Exception as e:
            logger.error(f"❌ {test_name} 测试异常: {e}")
    
    # 可选的基础搜索测试
    logger.info(f"\n📋 基础搜索测试:")
    try:
        if await run_basic_search_test():
            passed += 1
            total += 1
            logger.info("✅ 基础搜索测试通过")
        else:
            total += 1
            logger.error("❌ 基础搜索测试失败")
    except Exception as e:
        total += 1
        logger.error(f"❌ 基础搜索测试异常: {e}")
    
    # 显示结果
    logger.info("=" * 60)
    logger.info(f"📊 测试结果: {passed}/{total} 通过")
    
    if passed == total:
        logger.info("🎉 所有测试通过！V4 功能正常")
        return 0
    else:
        logger.warning(f"⚠️ {total - passed} 个测试失败，请检查配置和依赖")
        return 1


if __name__ == "__main__":
    try:
        exit_code = asyncio.run(main())
        sys.exit(exit_code)
    except KeyboardInterrupt:
        logger.info("\n⌨️ 测试被中断")
        sys.exit(130)
    except Exception as e:
        logger.error(f"💥 测试异常: {e}")
        sys.exit(1)