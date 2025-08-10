"""
GitHub 客户端 V2 - 集成 TokenPool 的增强版
"""

import base64
import random
import time
import logging
from typing import Dict, List, Optional, Any, Tuple
import requests
from utils.token_pool import TokenPool, TokenSelectionStrategy
from utils.security_utils import mask_key

logger = logging.getLogger(__name__)


class GitHubClientV2:
    """增强版 GitHub 客户端，集成 TokenPool"""
    
    GITHUB_API_URL = "https://api.github.com/search/code"
    
    def __init__(self, token_pool: TokenPool):
        """
        初始化客户端
        
        Args:
            token_pool: TokenPool 实例
        """
        self.token_pool = token_pool
        self.session = requests.Session()
        
        # 统计
        self.total_requests = 0
        self.successful_requests = 0
        self.failed_requests = 0
        
        logger.info(f"🌐 GitHub Client V2 initialized with token pool")
    
    def search_for_keys(self, query: str, max_retries: int = 5) -> Dict[str, Any]:
        """
        搜索密钥
        
        Args:
            query: 搜索查询
            max_retries: 最大重试次数
            
        Returns:
            搜索结果
        """
        all_items = []
        total_count = 0
        expected_total = None
        pages_processed = 0
        
        # 添加失败页面重试队列
        failed_pages = []
        max_page_retries = 2
        
        # 统计信息
        total_requests = 0
        failed_requests = 0
        rate_limit_hits = 0
        
        for page in range(1, 11):  # 最多10页
            page_result = None
            page_success = False
            
            for attempt in range(1, max_retries + 1):
                # 从 TokenPool 获取令牌
                token = self.token_pool.select_token()
                if not token:
                    logger.error("❌ No available tokens in pool")
                    time.sleep(5)  # 等待令牌恢复
                    continue
                
                # 构建请求
                headers = {
                    "Accept": "application/vnd.github.v3+json",
                    "User-Agent": "Mozilla/5.0 (compatible; HajimiKing/2.0)",
                    "Authorization": f"token {token}"
                }
                
                params = {
                    "q": query,
                    "per_page": 100,
                    "page": page
                }
                
                try:
                    total_requests += 1
                    self.total_requests += 1
                    
                    # 发送请求
                    start_time = time.time()
                    response = self.session.get(
                        self.GITHUB_API_URL, 
                        headers=headers, 
                        params=params, 
                        timeout=30
                    )
                    response_time = time.time() - start_time
                    
                    # 更新 TokenPool
                    self.token_pool.update_token_status(token, {
                        'status_code': response.status_code,
                        'headers': dict(response.headers),
                        'response_time': response_time
                    })
                    
                    # 检查响应
                    if response.status_code == 200:
                        page_result = response.json()
                        page_success = True
                        self.successful_requests += 1
                        
                        # 记录限流信息
                        remaining = response.headers.get('X-RateLimit-Remaining')
                        if remaining and int(remaining) < 5:
                            logger.warning(f"⚠️ Low quota: {remaining} remaining for {mask_key(token)}")
                        
                        break
                    
                    elif response.status_code in (403, 429):
                        # 限流
                        rate_limit_hits += 1
                        self.failed_requests += 1
                        logger.warning(f"🚫 Rate limited (attempt {attempt}/{max_retries})")
                        
                        # 快速切换令牌
                        if attempt < max_retries:
                            time.sleep(1)  # 短暂等待
                            continue
                    
                    else:
                        # 其他错误
                        self.failed_requests += 1
                        logger.error(f"❌ HTTP {response.status_code} (attempt {attempt}/{max_retries})")
                        
                        if attempt < max_retries:
                            time.sleep(min(2 ** attempt, 10))
                            continue
                
                except requests.exceptions.RequestException as e:
                    failed_requests += 1
                    self.failed_requests += 1
                    
                    if attempt == max_retries:
                        logger.error(f"❌ Request failed after {max_retries} attempts: {type(e).__name__}")
                    
                    time.sleep(min(2 ** attempt, 10))
                    continue
            
            # 处理页面结果
            if not page_success or not page_result:
                if page == 1:
                    logger.error(f"❌ First page failed for query: {query[:50]}...")
                    break
                else:
                    # 加入重试队列
                    failed_pages.append({'page': page, 'retry_count': 0})
                    logger.debug(f"📝 Page {page} added to retry queue")
                continue
            
            pages_processed += 1
            
            # 处理第一页
            if page == 1:
                total_count = page_result.get("total_count", 0)
                expected_total = min(total_count, 1000)  # GitHub 限制最多1000个结果
                logger.info(f"🔍 Query: {query} - Total results: {total_count}")
            
            # 收集项目
            items = page_result.get("items", [])
            current_page_count = len(items)
            
            if current_page_count == 0:
                break
            
            all_items.extend(items)
            
            # 检查是否完成
            if expected_total and len(all_items) >= expected_total:
                break
            
            # 页面间延迟
            if page < 10:
                sleep_time = random.uniform(0.5, 1.5)
                logger.debug(f"⏳ Page {page} complete, sleeping {sleep_time:.1f}s")
                time.sleep(sleep_time)
        
        # 重试失败的页面
        if failed_pages and expected_total:
            logger.info(f"🔄 Retrying {len(failed_pages)} failed pages...")
            
            for failed_page_info in failed_pages[:]:
                if failed_page_info['retry_count'] >= max_page_retries:
                    continue
                
                page = failed_page_info['page']
                failed_page_info['retry_count'] += 1
                
                # 等待后重试
                time.sleep(2 * failed_page_info['retry_count'])
                
                # 简化的重试逻辑
                token = self.token_pool.select_token()
                if token:
                    try:
                        headers = {
                            "Accept": "application/vnd.github.v3+json",
                            "Authorization": f"token {token}"
                        }
                        params = {"q": query, "per_page": 100, "page": page}
                        
                        response = self.session.get(
                            self.GITHUB_API_URL, 
                            headers=headers, 
                            params=params, 
                            timeout=30
                        )
                        
                        if response.status_code == 200:
                            retry_result = response.json()
                            items = retry_result.get("items", [])
                            if items:
                                all_items.extend(items)
                                pages_processed += 1
                                failed_pages.remove(failed_page_info)
                                logger.info(f"✅ Recovered page {page} with {len(items)} items")
                    
                    except Exception as e:
                        logger.debug(f"Failed to recover page {page}: {type(e).__name__}")
        
        # 计算数据完整性
        final_count = len(all_items)
        if expected_total and final_count < expected_total:
            completeness = (final_count / expected_total) * 100
            if completeness < 90:
                logger.warning(f"⚠️ Data completeness: {completeness:.1f}% ({final_count}/{expected_total})")
        
        # 记录摘要
        logger.info(
            f"🔍 Search complete: query={query[:30]}... | "
            f"pages={pages_processed} | items={final_count}/{expected_total or '?'} | "
            f"requests={total_requests} | rate_limits={rate_limit_hits}"
        )
        
        return {
            "total_count": total_count,
            "incomplete_results": final_count < expected_total if expected_total else False,
            "items": all_items,
            "statistics": {
                "pages_processed": pages_processed,
                "total_requests": total_requests,
                "failed_requests": failed_requests,
                "rate_limit_hits": rate_limit_hits
            }
        }
    
    def get_file_content(self, item: Dict[str, Any]) -> Optional[str]:
        """
        获取文件内容
        
        Args:
            item: 搜索结果项
            
        Returns:
            文件内容或 None
        """
        repo_full_name = item["repository"]["full_name"]
        file_path = item["path"]
        metadata_url = f"https://api.github.com/repos/{repo_full_name}/contents/{file_path}"
        
        # 获取令牌
        token = self.token_pool.select_token()
        if not token:
            logger.error("❌ No available token for file content")
            return None
        
        headers = {
            "Accept": "application/vnd.github.v3+json",
            "Authorization": f"token {token}"
        }
        
        try:
            logger.debug(f"📄 Fetching: {metadata_url}")
            
            # 获取文件元数据
            start_time = time.time()
            metadata_response = self.session.get(metadata_url, headers=headers, timeout=15)
            response_time = time.time() - start_time
            
            # 更新 TokenPool
            self.token_pool.update_token_status(token, {
                'status_code': metadata_response.status_code,
                'headers': dict(metadata_response.headers),
                'response_time': response_time
            })
            
            if metadata_response.status_code != 200:
                logger.warning(f"⚠️ Failed to fetch metadata: HTTP {metadata_response.status_code}")
                return None
            
            file_metadata = metadata_response.json()
            
            # 尝试 base64 内容
            encoding = file_metadata.get("encoding")
            content = file_metadata.get("content")
            
            if encoding == "base64" and content:
                try:
                    decoded_content = base64.b64decode(content).decode('utf-8')
                    return decoded_content
                except Exception as e:
                    logger.debug(f"Base64 decode failed: {e}")
            
            # 使用 download_url
            download_url = file_metadata.get("download_url")
            if download_url:
                content_response = self.session.get(download_url, headers=headers, timeout=15)
                if content_response.status_code == 200:
                    return content_response.text
            
            return None
            
        except requests.exceptions.RequestException as e:
            logger.error(f"❌ Failed to fetch file content: {type(e).__name__}")
            return None
    
    def get_statistics(self) -> Dict[str, Any]:
        """获取客户端统计"""
        return {
            "total_requests": self.total_requests,
            "successful_requests": self.successful_requests,
            "failed_requests": self.failed_requests,
            "success_rate": (
                self.successful_requests / self.total_requests 
                if self.total_requests > 0 else 0
            ),
            "token_pool_status": self.token_pool.get_pool_status()
        }
    
    def close(self):
        """关闭客户端"""
        self.session.close()
        logger.info("🔌 GitHub Client V2 closed")


# 工厂函数
def create_github_client_v2(tokens: List[str], 
                           strategy: str = "ADAPTIVE") -> GitHubClientV2:
    """
    创建 GitHub 客户端 V2
    
    Args:
        tokens: GitHub 令牌列表
        strategy: TokenPool 策略
        
    Returns:
        GitHubClientV2 实例
    """
    # 创建 TokenPool
    strategy_enum = TokenSelectionStrategy[strategy.upper()]
    token_pool = TokenPool(tokens, strategy=strategy_enum)
    
    # 创建客户端
    return GitHubClientV2(token_pool)


# 使用示例
if __name__ == "__main__":
    import os
    
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s | %(levelname)s | %(name)s | %(message)s'
    )
    
    # 测试令牌
    test_tokens = [
        "github_pat_11AAAAAAA" + "A" * 74,
        "github_pat_11BBBBBBBB" + "B" * 74,
    ]
    
    # 创建客户端
    client = create_github_client_v2(test_tokens, strategy="ADAPTIVE")
    
    # 测试搜索
    result = client.search_for_keys("test query", max_retries=3)
    
    # 显示统计
    stats = client.get_statistics()
    print("\n📊 Client Statistics:")
    for key, value in stats.items():
        if key != "token_pool_status":
            print(f"  {key}: {value}")
    
    # 关闭
    client.close()