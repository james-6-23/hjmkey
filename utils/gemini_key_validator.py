"""
Gemini密钥验证器
在程序退出时批量验证所有有效密钥，识别付费版本
"""

import asyncio
import aiohttp
import json
import logging
from pathlib import Path
from typing import List, Dict, Any, Tuple
from datetime import datetime
import time

logger = logging.getLogger(__name__)


class GeminiKeyValidator:
    """
    Gemini密钥验证器
    使用Cache API来判断是否为付费版本
    """
    
    # API端点
    GENERATE_API = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash-exp:generateContent"
    CACHE_API = "https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:cacheContent"
    
    def __init__(self, concurrency: int = 5):
        """
        初始化验证器
        
        Args:
            concurrency: 并发验证数量
        """
        self.concurrency = concurrency
        self.valid_keys = []
        self.paid_keys = []
        self.free_keys = []
    
    async def test_generate_content_api(self, session: aiohttp.ClientSession, api_key: str) -> bool:
        """
        测试基础生成API
        
        Args:
            session: aiohttp会话
            api_key: 要测试的密钥
            
        Returns:
            是否有效
        """
        url = f"{self.GENERATE_API}?key={api_key}"
        
        # 简单的测试请求体
        test_body = {
            "contents": [{
                "parts": [{
                    "text": "Hi"
                }]
            }],
            "generationConfig": {
                "temperature": 0,
                "maxOutputTokens": 1
            }
        }
        
        try:
            async with session.post(url, json=test_body, timeout=10) as response:
                if response.status == 200:
                    logger.info(f"✅ VALID - {api_key[:10]}... - 基础API测试通过")
                    return True
                elif response.status in [401, 403]:
                    logger.warning(f"❌ INVALID - {api_key[:10]}... - 无效密钥")
                    return False
                elif response.status == 429:
                    logger.warning(f"⚠️ RATE LIMITED - {api_key[:10]}... - 速率限制")
                    return True  # 速率限制说明密钥是有效的
                else:
                    logger.error(f"❌ ERROR - {api_key[:10]}... - HTTP {response.status}")
                    return False
        except asyncio.TimeoutError:
            logger.error(f"⏱️ TIMEOUT - {api_key[:10]}...")
            return False
        except Exception as e:
            logger.error(f"❌ ERROR - {api_key[:10]}... - {e}")
            return False
    
    async def test_cache_content_api(self, session: aiohttp.ClientSession, api_key: str) -> bool:
        """
        测试Cache API（付费版功能）
        
        Args:
            session: aiohttp会话
            api_key: 要测试的密钥
            
        Returns:
            是否为付费版
        """
        url = f"{self.CACHE_API}?key={api_key}"
        
        # Cache API需要较长的内容（至少1024个tokens）
        long_text = "You are an expert at analyzing transcripts. " * 150
        
        cache_body = {
            "model": "models/gemini-1.5-flash",
            "contents": [{
                "parts": [{
                    "text": long_text
                }],
                "role": "user"
            }],
            "ttl": "300s"
        }
        
        try:
            async with session.post(url, json=cache_body, timeout=10) as response:
                if response.status == 200:
                    logger.info(f"💎 PAID KEY - {api_key[:10]}... - Cache API可访问")
                    return True
                elif response.status == 429:
                    logger.info(f"🆓 FREE KEY - {api_key[:10]}... - Cache API速率限制")
                    return False
                else:
                    logger.debug(f"Cache API响应: {api_key[:10]}... - HTTP {response.status}")
                    return False
        except Exception as e:
            logger.debug(f"Cache API错误: {api_key[:10]}... - {e}")
            return False
    
    async def validate_key(self, session: aiohttp.ClientSession, api_key: str) -> Tuple[bool, bool]:
        """
        验证单个密钥
        
        Args:
            session: aiohttp会话
            api_key: 要验证的密钥
            
        Returns:
            (是否有效, 是否付费版)
        """
        # 第一步：测试基础API
        is_valid = await self.test_generate_content_api(session, api_key)
        
        if not is_valid:
            return False, False
        
        # 第二步：测试Cache API（判断是否付费版）
        is_paid = await self.test_cache_content_api(session, api_key)
        
        return True, is_paid
    
    async def validate_keys_batch(self, keys: List[str]) -> Dict[str, Any]:
        """
        批量验证密钥
        
        Args:
            keys: 密钥列表
            
        Returns:
            验证结果
        """
        start_time = time.time()
        logger.info(f"🔍 开始批量验证 {len(keys)} 个密钥...")
        
        # 创建aiohttp会话
        async with aiohttp.ClientSession() as session:
            # 创建验证任务
            tasks = []
            for key in keys:
                task = self.validate_key(session, key)
                tasks.append((key, task))
            
            # 限制并发数量
            semaphore = asyncio.Semaphore(self.concurrency)
            
            async def validate_with_limit(key, task):
                async with semaphore:
                    is_valid, is_paid = await task
                    return key, is_valid, is_paid
            
            # 执行所有任务
            results = await asyncio.gather(
                *[validate_with_limit(key, task) for key, task in tasks],
                return_exceptions=True
            )
            
            # 处理结果
            for result in results:
                if isinstance(result, Exception):
                    logger.error(f"验证异常: {result}")
                    continue
                
                key, is_valid, is_paid = result
                
                if is_valid:
                    self.valid_keys.append(key)
                    if is_paid:
                        self.paid_keys.append(key)
                    else:
                        self.free_keys.append(key)
        
        elapsed_time = time.time() - start_time
        
        return {
            "total": len(keys),
            "valid": len(self.valid_keys),
            "paid": len(self.paid_keys),
            "free": len(self.free_keys),
            "invalid": len(keys) - len(self.valid_keys),
            "elapsed_time": elapsed_time
        }
    
    async def save_results(self, output_dir: str = "data/keys"):
        """
        保存验证结果到文件
        
        Args:
            output_dir: 输出目录
        """
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        
        date_str = datetime.now().strftime('%Y%m%d')
        
        # 保存付费密钥
        if self.paid_keys:
            paid_file = output_path / f"keys_paid_{date_str}.txt"
            with open(paid_file, 'w', encoding='utf-8') as f:
                f.write(f"# 付费版Gemini密钥\n")
                f.write(f"# 验证时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
                for key in self.paid_keys:
                    f.write(f"{key}\n")
            logger.info(f"💎 保存 {len(self.paid_keys)} 个付费密钥到: {paid_file}")
        
        # 保存免费密钥
        if self.free_keys:
            free_file = output_path / f"keys_free_{date_str}.txt"
            with open(free_file, 'w', encoding='utf-8') as f:
                f.write(f"# 免费版Gemini密钥\n")
                f.write(f"# 验证时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
                for key in self.free_keys:
                    f.write(f"{key}\n")
            logger.info(f"🆓 保存 {len(self.free_keys)} 个免费密钥到: {free_file}")
        
        # 保存汇总报告
        summary_file = output_path / f"keys_validation_summary_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        with open(summary_file, 'w', encoding='utf-8') as f:
            f.write(f"# Gemini密钥验证汇总\n")
            f.write(f"# 验证时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"# 总计: {len(self.valid_keys)} 个有效密钥\n")
            f.write(f"# 付费版: {len(self.paid_keys)} 个\n")
            f.write(f"# 免费版: {len(self.free_keys)} 个\n\n")
            
            if self.paid_keys:
                f.write("## 💎 付费版密钥\n")
                for key in self.paid_keys:
                    f.write(f"{key}\n")
                f.write("\n")
            
            if self.free_keys:
                f.write("## 🆓 免费版密钥\n")
                for key in self.free_keys:
                    f.write(f"{key}\n")
        
        logger.info(f"📊 验证汇总已保存到: {summary_file}")


async def validate_keys_from_file(file_path: str, concurrency: int = 5) -> Dict[str, Any]:
    """
    从文件验证密钥
    
    Args:
        file_path: 密钥文件路径
        concurrency: 并发数量
        
    Returns:
        验证结果
    """
    # 读取密钥
    keys = []
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#'):
                    keys.append(line)
    except FileNotFoundError:
        logger.error(f"文件不存在: {file_path}")
        return {}
    
    if not keys:
        logger.warning("没有找到有效密钥")
        return {}
    
    logger.info(f"📋 从 {file_path} 加载了 {len(keys)} 个密钥")
    
    # 创建验证器并验证
    validator = GeminiKeyValidator(concurrency=concurrency)
    results = await validator.validate_keys_batch(keys)
    
    # 保存结果
    await validator.save_results()
    
    return results


def run_validation_on_exit():
    """
    在程序退出时运行验证
    这个函数应该在主程序退出时调用
    """
    import glob
    
    # 查找今天的有效密钥文件
    date_str = datetime.now().strftime('%Y%m%d')
    valid_keys_pattern = f"data/keys/keys_valid_{date_str}.txt"
    
    files = glob.glob(valid_keys_pattern)
    if not files:
        logger.info("没有找到今天的有效密钥文件")
        return
    
    logger.info("=" * 60)
    logger.info("🔍 程序退出，开始验证所有有效密钥...")
    logger.info("=" * 60)
    
    # 运行异步验证
    for file_path in files:
        results = asyncio.run(validate_keys_from_file(file_path, concurrency=10))
        
        if results:
            logger.info("=" * 60)
            logger.info("📊 验证完成统计:")
            logger.info(f"   总计验证: {results['total']} 个")
            logger.info(f"   💎 付费版: {results['paid']} 个")
            logger.info(f"   🆓 免费版: {results['free']} 个")
            logger.info(f"   ❌ 无效: {results['invalid']} 个")
            logger.info(f"   ⏱️ 耗时: {results['elapsed_time']:.2f} 秒")
            logger.info("=" * 60)


if __name__ == "__main__":
    # 设置日志
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s | %(levelname)s | %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # 测试验证
    import sys
    if len(sys.argv) > 1:
        file_path = sys.argv[1]
        results = asyncio.run(validate_keys_from_file(file_path))
        print(json.dumps(results, indent=2))
    else:
        run_validation_on_exit()