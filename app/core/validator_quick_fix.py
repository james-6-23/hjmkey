"""
验证器快速修复
提供一个简单的并发验证包装器，无需修改现有代码结构
"""

import asyncio
import time
import logging
from typing import List
from concurrent.futures import ThreadPoolExecutor, as_completed
from app.core.validator import GeminiKeyValidator, ValidationResult

logger = logging.getLogger(__name__)


class QuickFixValidator(GeminiKeyValidator):
    """
    快速修复的验证器
    通过线程池实现并发验证，无需修改现有接口
    """
    
    def __init__(
        self,
        model_name: str = "gemini-2.0-flash-exp",
        proxy_config: dict = None,
        delay_range: tuple = (0.1, 0.2),  # 更短的延迟
        max_workers: int = 10  # 并发线程数
    ):
        # 使用更短的延迟初始化父类
        super().__init__(model_name, proxy_config, delay_range)
        self.max_workers = max_workers
        self._executor = ThreadPoolExecutor(max_workers=max_workers)
    
    def validate_batch(self, keys: List[str]) -> List[ValidationResult]:
        """
        并发批量验证密钥
        
        Args:
            keys: API密钥列表
            
        Returns:
            验证结果列表（保持原始顺序）
        """
        if not keys:
            return []
        
        if len(keys) == 1:
            # 单个密钥直接验证
            return [self.validate(keys[0])]
        
        start_time = time.time()
        results = [None] * len(keys)  # 预分配结果列表以保持顺序
        
        # 提交所有验证任务到线程池
        future_to_index = {}
        for i, key in enumerate(keys):
            future = self._executor.submit(self.validate, key)
            future_to_index[future] = i
        
        # 收集结果
        completed = 0
        for future in as_completed(future_to_index):
            index = future_to_index[future]
            try:
                result = future.result()
                results[index] = result
                completed += 1
                
                # 更新统计
                self.validation_count += 1
                if result.status.value in ["network_error", "unknown_error"]:
                    self.error_count += 1
                    
                # 进度日志
                if completed % 10 == 0 or completed == len(keys):
                    elapsed = time.time() - start_time
                    rate = completed / elapsed if elapsed > 0 else 0
                    logger.info(f"验证进度: {completed}/{len(keys)} ({rate:.1f} keys/sec)")
                    
            except Exception as e:
                logger.error(f"验证失败 (index {index}): {e}")
                # 创建错误结果
                results[index] = ValidationResult(
                    key=keys[index],
                    status="unknown_error",
                    message=f"Validation error: {str(e)}"
                )
        
        elapsed = time.time() - start_time
        logger.info(f"⚡ 批量验证完成: {len(keys)} 个密钥, 耗时 {elapsed:.2f}秒 ({len(keys)/elapsed:.1f} keys/sec)")
        
        return results
    
    def __del__(self):
        """清理资源"""
        if hasattr(self, '_executor'):
            self._executor.shutdown(wait=False)


def patch_orchestrator_validator():
    """
    猴子补丁：替换 orchestrator 中的验证器
    这是一个临时解决方案，可以快速应用而不修改原始代码
    """
    import app.core.validator
    
    # 保存原始类（如果需要）
    app.core.validator.OriginalGeminiKeyValidator = app.core.validator.GeminiKeyValidator
    
    # 替换为快速修复版本
    app.core.validator.GeminiKeyValidator = QuickFixValidator
    app.core.validator.KeyValidator = QuickFixValidator
    
    logger.info("✅ 验证器已打补丁，启用并发验证")


# 使用示例
if __name__ == "__main__":
    import asyncio
    
    # 设置日志
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s | %(levelname)s | %(message)s'
    )
    
    # 测试快速修复验证器
    validator = QuickFixValidator(max_workers=5)
    
    # 生成测试密钥
    test_keys = [f"AIzaSy{'X' * 30}{i:03d}" for i in range(10)]
    
    # 测试验证
    print("测试并发验证...")
    start = time.time()
    results = validator.validate_batch(test_keys)
    elapsed = time.time() - start
    
    print(f"\n验证完成:")
    print(f"  总数: {len(results)}")
    print(f"  耗时: {elapsed:.2f} 秒")
    print(f"  速度: {len(results)/elapsed:.1f} keys/sec")
    
    # 应用补丁
    print("\n应用补丁...")
    patch_orchestrator_validator()
    print("现在 orchestrator 将使用并发验证！")