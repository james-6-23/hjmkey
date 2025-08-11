"""
Gemini 验证器集成示例
展示如何将 V2 验证器集成到现有项目中
"""

import asyncio
import logging
from pathlib import Path
from typing import List, Optional, Dict, Any
from datetime import datetime
import atexit

from utils.gemini_key_validator_v2 import (
    GeminiKeyValidatorV2,
    ValidatorConfig,
    ValidatedKey,
    KeyTier,
    validate_keys_from_file
)

logger = logging.getLogger(__name__)


class GeminiKeyManager:
    """
    Gemini 密钥管理器
    提供密钥验证的高级接口
    """
    
    def __init__(self, config: Optional[ValidatorConfig] = None):
        """
        初始化密钥管理器
        
        Args:
            config: 验证器配置
        """
        self.config = config or ValidatorConfig()
        self.validator = None
        self._validated_cache = {}  # 缓存验证结果
        
    async def __aenter__(self):
        """异步上下文管理器入口"""
        self.validator = GeminiKeyValidatorV2(self.config)
        await self.validator.__aenter__()
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """异步上下文管理器退出"""
        if self.validator:
            await self.validator.__aexit__(exc_type, exc_val, exc_tb)
    
    async def validate_single_key(self, key: str) -> ValidatedKey:
        """
        验证单个密钥（带缓存）
        
        Args:
            key: 要验证的密钥
            
        Returns:
            验证结果
        """
        # 检查缓存
        if key in self._validated_cache:
            logger.debug(f"使用缓存结果: {key[:10]}...")
            return self._validated_cache[key]
        
        # 验证密钥
        async with self.validator.create_session() as session:
            result = await self.validator.validate_key(session, key)
            
        # 缓存结果
        self._validated_cache[key] = result
        return result
    
    async def validate_and_classify(self, keys: List[str]) -> Dict[str, List[str]]:
        """
        验证并分类密钥
        
        Args:
            keys: 密钥列表
            
        Returns:
            分类后的密钥字典
        """
        stats = await self.validator.validate_keys_batch(keys)
        
        # 分类结果
        result = {
            "paid": [],
            "free": [],
            "invalid": []
        }
        
        for vk in self.validator.validated_keys:
            if vk.tier == KeyTier.PAID:
                result["paid"].append(vk.key)
            elif vk.tier == KeyTier.FREE:
                result["free"].append(vk.key)
            else:
                result["invalid"].append(vk.key)
        
        logger.info(f"验证完成 - 付费: {len(result['paid'])}, "
                   f"免费: {len(result['free'])}, "
                   f"无效: {len(result['invalid'])}")
        
        return result
    
    async def get_best_keys(self, keys: List[str], prefer_paid: bool = True) -> List[str]:
        """
        获取最佳可用密钥
        
        Args:
            keys: 密钥列表
            prefer_paid: 是否优先返回付费密钥
            
        Returns:
            排序后的有效密钥列表
        """
        classified = await self.validate_and_classify(keys)
        
        if prefer_paid:
            # 付费密钥优先
            return classified["paid"] + classified["free"]
        else:
            # 免费密钥优先
            return classified["free"] + classified["paid"]
    
    async def save_validation_report(self, output_file: Optional[str] = None):
        """
        保存验证报告
        
        Args:
            output_file: 输出文件路径
        """
        if not self.validator.validated_keys:
            logger.warning("没有验证结果可保存")
            return
        
        await self.validator.save_results(
            output_dir=str(Path(output_file).parent) if output_file else None
        )


class AutoValidator:
    """
    自动验证器
    在程序退出时自动验证今天收集的密钥
    """
    
    def __init__(self, keys_dir: str = "data/keys", auto_register: bool = True):
        """
        初始化自动验证器
        
        Args:
            keys_dir: 密钥文件目录
            auto_register: 是否自动注册退出处理
        """
        self.keys_dir = Path(keys_dir)
        self.config = ValidatorConfig(
            concurrency=100,
            output_dir=str(self.keys_dir / "validated")
        )
        
        if auto_register:
            atexit.register(self.validate_on_exit)
    
    def validate_on_exit(self):
        """程序退出时验证密钥"""
        logger.info("=" * 60)
        logger.info("🔍 程序退出，开始验证今天的密钥...")
        logger.info("=" * 60)
        
        # 查找今天的密钥文件
        date_str = datetime.now().strftime('%Y%m%d')
        patterns = [
            f"keys_valid_{date_str}.txt",
            f"keys_{date_str}.txt",
            f"*_{date_str}.txt"
        ]
        
        for pattern in patterns:
            files = list(self.keys_dir.glob(pattern))
            if files:
                for file in files:
                    logger.info(f"验证文件: {file}")
                    try:
                        # 运行异步验证
                        asyncio.run(self._validate_file(file))
                    except Exception as e:
                        logger.error(f"验证失败: {e}")
                break
        else:
            logger.info("没有找到今天的密钥文件")
    
    async def _validate_file(self, file_path: Path):
        """异步验证文件"""
        stats = await validate_keys_from_file(
            str(file_path),
            config=self.config,
            save_results=True
        )
        
        if stats:
            logger.info("=" * 60)
            logger.info("📊 验证完成统计:")
            logger.info(f"   总计验证: {stats['total']} 个")
            logger.info(f"   💎 付费版: {stats['paid']} 个")
            logger.info(f"   🆓 免费版: {stats['free']} 个")
            logger.info(f"   ❌ 无效: {stats['invalid']} 个")
            logger.info(f"   ⏱️  耗时: {stats['elapsed_time']:.2f} 秒")
            logger.info(f"   🚀 速度: {stats['keys_per_second']:.2f} 个/秒")
            logger.info("=" * 60)


# 便捷函数
async def quick_validate(keys: List[str]) -> Dict[str, List[str]]:
    """
    快速验证密钥的便捷函数
    
    Args:
        keys: 密钥列表
        
    Returns:
        分类后的密钥
    """
    async with GeminiKeyManager() as manager:
        return await manager.validate_and_classify(keys)


async def validate_and_get_paid(keys: List[str]) -> List[str]:
    """
    验证并获取付费密钥
    
    Args:
        keys: 密钥列表
        
    Returns:
        付费密钥列表
    """
    result = await quick_validate(keys)
    return result["paid"]


# 示例：集成到现有系统
class ExistingSystem:
    """模拟现有系统"""
    
    def __init__(self):
        self.key_manager = GeminiKeyManager(
            ValidatorConfig(concurrency=50)
        )
        self.auto_validator = AutoValidator()
    
    async def process_new_keys(self, new_keys: List[str]):
        """处理新发现的密钥"""
        logger.info(f"处理 {len(new_keys)} 个新密钥")
        
        async with self.key_manager as manager:
            # 获取最佳密钥（付费优先）
            best_keys = await manager.get_best_keys(new_keys)
            
            if best_keys:
                logger.info(f"找到 {len(best_keys)} 个有效密钥")
                # 使用这些密钥...
                return best_keys
            else:
                logger.warning("没有找到有效密钥")
                return []


# 使用示例
async def main():
    """演示集成使用"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s | %(name)s | %(levelname)s | %(message)s'
    )
    
    # 示例1：快速验证
    print("\n=== 示例1：快速验证 ===")
    test_keys = [
        "AIzaSyABCDEFGHIJKLMNOPQRSTUVWXYZ1234567",
        "invalid_key",
    ]
    
    result = await quick_validate(test_keys)
    print(f"验证结果: {result}")
    
    # 示例2：使用密钥管理器
    print("\n=== 示例2：密钥管理器 ===")
    async with GeminiKeyManager() as manager:
        # 验证单个密钥
        vk = await manager.validate_single_key(test_keys[0])
        print(f"单个密钥验证: {vk.key[:10]}... - {vk.tier.value}")
        
        # 获取最佳密钥
        best = await manager.get_best_keys(test_keys)
        print(f"最佳密钥: {len(best)} 个")
    
    # 示例3：集成到现有系统
    print("\n=== 示例3：系统集成 ===")
    system = ExistingSystem()
    await system.process_new_keys(test_keys)
    
    # 示例4：自动验证器（将在程序退出时运行）
    print("\n=== 示例4：自动验证器已注册 ===")
    print("程序退出时将自动验证今天的密钥文件")


if __name__ == "__main__":
    asyncio.run(main())