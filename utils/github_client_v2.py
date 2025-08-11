"""
GitHub 客户端 V2 - 集成 TokenPool 的增强版
"""

import os
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
    
    def __init__(self, token_pool: TokenPool, proxy_config: Optional[Dict[str, str]] = None):
        """
        初始化客户端
        
        Args:
            token_pool: TokenPool 实例
            proxy_config: 代理配置字典 (可选)
        """
        self.token_pool = token_pool
        self.session = requests.Session()
        
        # 配置代理
        self.proxy_config = proxy_config or self._get_proxy_from_env()
        if self.proxy_config:
            self.session.proxies.update(self.proxy_config)
            proxy_url = self.proxy_config.get('http') or self.proxy_config.get('https')
            logger.info(f"🌐 Using proxy: {proxy_url}")
        
        # 统计
        self.total_requests = 0
        self.successful_requests = 0
        self.failed_requests = 0
        
        logger.info(f"🌐 GitHub Client V2 initialized with token pool")
    
    def _get_proxy_from_env(self) -> Optional[Dict[str, str]]:
        """
        从环境变量获取代理配置
        
        Returns:
            代理配置字典或 None
        """
        proxy_config = {}
        
        # 检查 HTTP_PROXY 和 HTTPS_PROXY
        http_proxy = os.getenv('HTTP_PROXY') or os.getenv('http_proxy')
        https_proxy = os.getenv('HTTPS_PROXY') or os.getenv('https_proxy')
        
        if http_proxy:
            proxy_config['http'] = http_proxy
            logger.debug(f"Found HTTP proxy: {http_proxy}")
        
        if https_proxy:
            proxy_config['https'] = https_proxy
            logger.debug(f"Found HTTPS proxy: {https_proxy}")
        
        # 检查 NO_PROXY
        no_proxy = os.getenv('NO_PROXY') or os.getenv('no_proxy')
        if no_proxy:
            # requests 库会自动处理 NO_PROXY
            os.environ['NO_PROXY'] = no_proxy
            logger.debug(f"NO_PROXY set: {no_proxy}")
        
        return proxy_config if proxy_config else None
    
    def search_for_keys(self, query: str, max_retries: int = 5) -> Dict[str, Any]:
        """
        搜索密钥（改进版：增强数据完整性）
        
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
        
        # 改进：增加失败页面重试机制
        failed_pages = []
        max_page_retries = 3  # 增加重试次数
        
        # 统计信息
        total_requests = 0
        failed_requests = 0
        rate_limit_hits = 0
        successful_pages = set()  # 记录成功的页面
        
        # 改进：动态计算需要获取的页数
        max_pages = 10  # GitHub API限制最多1000个结果（100个/页 * 10页）
        
        for page in range(1, max_pages + 1):
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
                    
                    # 发送请求（使用配置的代理）
                    start_time = time.time()
                    response = self.session.get(
                        self.GITHUB_API_URL,
                        headers=headers,
                        params=params,
                        timeout=30,
                        proxies=self.proxy_config  # 显式传递代理配置
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
                    # 改进：第一页失败也尝试重试
                    if max_retries > 0:
                        failed_pages.append({'page': page, 'retry_count': 0})
                    else:
                        break
                else:
                    # 加入重试队列
                    failed_pages.append({'page': page, 'retry_count': 0})
                    logger.debug(f"📝 Page {page} added to retry queue")
                continue
            
            pages_processed += 1
            successful_pages.add(page)  # 记录成功页面
            
            # 处理第一页
            if page == 1:
                total_count = page_result.get("total_count", 0)
                expected_total = min(total_count, 1000)  # GitHub 限制最多1000个结果
                logger.info(f"🔍 Query: {query} - Total results: {total_count}")
                
                # 动态调整最大页数
                if expected_total > 0:
                    needed_pages = min((expected_total + 99) // 100, 10)  # 向上取整
                    max_pages = min(needed_pages, max_pages)
                    logger.debug(f"📊 Adjusted max pages to {max_pages} based on total count")
            
            # 收集项目
            items = page_result.get("items", [])
            current_page_count = len(items)
            
            if current_page_count == 0:
                logger.debug(f"📄 Page {page} returned 0 items, stopping pagination")
                break
            
            all_items.extend(items)
            logger.debug(f"✅ Page {page}: collected {current_page_count} items (total: {len(all_items)})")
            
            # 检查是否完成
            if expected_total and len(all_items) >= expected_total:
                logger.info(f"✅ Collected all expected items ({len(all_items)}/{expected_total})")
                break
            
            # 页面间延迟（自适应）
            if page < max_pages:
                # 根据剩余配额调整延迟
                if rate_limit_hits > 0:
                    sleep_time = random.uniform(2.0, 3.0)  # 限流时增加延迟
                else:
                    sleep_time = random.uniform(0.5, 1.0)  # 正常延迟
                logger.debug(f"⏳ Page {page} complete, sleeping {sleep_time:.1f}s")
                time.sleep(sleep_time)
        
        # 改进的重试失败页面逻辑
        retry_attempts = 0
        max_retry_rounds = 2  # 最多进行2轮重试
        
        while failed_pages and retry_attempts < max_retry_rounds:
            retry_attempts += 1
            logger.info(f"🔄 Retry round {retry_attempts}: {len(failed_pages)} failed pages")
            
            # 复制失败页面列表用于迭代
            pages_to_retry = failed_pages[:]
            failed_pages = []  # 清空原列表
            
            for failed_page_info in pages_to_retry:
                page = failed_page_info['page']
                
                # 跳过已成功的页面
                if page in successful_pages:
                    continue
                    
                if failed_page_info['retry_count'] >= max_page_retries:
                    logger.warning(f"⚠️ Page {page} exceeded max retries")
                    continue
                
                failed_page_info['retry_count'] += 1
                
                # 指数退避延迟
                delay = min(2 ** failed_page_info['retry_count'], 10)
                time.sleep(delay)
                
                # 重试获取页面
                token = self.token_pool.select_token()
                if not token:
                    logger.warning(f"⚠️ No token available for retry of page {page}")
                    failed_pages.append(failed_page_info)
                    continue
                
                try:
                    headers = {
                        "Accept": "application/vnd.github.v3+json",
                        "Authorization": f"token {token}",
                        "User-Agent": "Mozilla/5.0 (compatible; HajimiKing/2.0)"
                    }
                    params = {
                        "q": query,
                        "per_page": 100,
                        "page": page,
                        "sort": "indexed",  # 添加排序以提高一致性
                        "order": "desc"
                    }
                    
                    response = self.session.get(
                        self.GITHUB_API_URL,
                        headers=headers,
                        params=params,
                        timeout=30,
                        proxies=self.proxy_config
                    )
                    
                    # 更新令牌状态
                    self.token_pool.update_token_status(token, {
                        'status_code': response.status_code,
                        'headers': dict(response.headers),
                        'response_time': 0
                    })
                    
                    if response.status_code == 200:
                        retry_result = response.json()
                        items = retry_result.get("items", [])
                        if items:
                            # 去重：避免重复添加
                            existing_urls = {item.get('html_url') for item in all_items}
                            new_items = [item for item in items if item.get('html_url') not in existing_urls]
                            
                            if new_items:
                                all_items.extend(new_items)
                                pages_processed += 1
                                successful_pages.add(page)
                                logger.info(f"✅ Recovered page {page}: {len(new_items)} new items")
                            else:
                                logger.debug(f"📝 Page {page} recovered but no new items")
                    else:
                        # 重试失败，重新加入队列
                        if failed_page_info['retry_count'] < max_page_retries:
                            failed_pages.append(failed_page_info)
                        logger.debug(f"❌ Retry failed for page {page}: HTTP {response.status_code}")
                
                except Exception as e:
                    # 异常时重新加入队列
                    if failed_page_info['retry_count'] < max_page_retries:
                        failed_pages.append(failed_page_info)
                    logger.debug(f"❌ Exception retrying page {page}: {type(e).__name__}")
        
        # 改进的数据完整性计算
        final_count = len(all_items)
        completeness = 100.0
        completeness_status = "COMPLETE"
        
        if expected_total and expected_total > 0:
            completeness = (final_count / expected_total) * 100
            
            if completeness >= 95:
                completeness_status = "EXCELLENT"
            elif completeness >= 80:
                completeness_status = "GOOD"
            elif completeness >= 60:
                completeness_status = "ACCEPTABLE"
            elif completeness >= 40:
                completeness_status = "POOR"
            else:
                completeness_status = "CRITICAL"
            
            # 详细的完整性日志
            if completeness < 95:
                missing_pages = [p for p in range(1, max_pages + 1) if p not in successful_pages]
                if missing_pages:
                    logger.warning(f"⚠️ Missing pages: {missing_pages[:10]}{'...' if len(missing_pages) > 10 else ''}")
                
                logger.warning(
                    f"⚠️ Data completeness: {completeness:.1f}% ({final_count}/{expected_total}) - {completeness_status}"
                )
            else:
                logger.info(f"✅ Data completeness: {completeness:.1f}% - {completeness_status}")
        
        # 记录详细摘要
        logger.info(
            f"🔍 Search complete: query={query[:30]}... | "
            f"pages={pages_processed}/{max_pages} | items={final_count}/{expected_total or '?'} | "
            f"completeness={completeness:.1f}% | "
            f"requests={total_requests} | rate_limits={rate_limit_hits}"
        )
        
        return {
            "total_count": total_count,
            "incomplete_results": final_count < expected_total if expected_total else False,
            "items": all_items,
            "completeness_percentage": completeness,
            "completeness_status": completeness_status,
            "statistics": {
                "pages_processed": pages_processed,
                "pages_attempted": max_pages,
                "successful_pages": len(successful_pages),
                "total_requests": total_requests,
                "failed_requests": failed_requests,
                "rate_limit_hits": rate_limit_hits,
                "items_collected": final_count,
                "expected_items": expected_total
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
            
            # 获取文件元数据（使用配置的代理）
            start_time = time.time()
            metadata_response = self.session.get(
                metadata_url,
                headers=headers,
                timeout=15,
                proxies=self.proxy_config  # 显式传递代理配置
            )
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
                content_response = self.session.get(
                    download_url,
                    headers=headers,
                    timeout=15,
                    proxies=self.proxy_config  # 显式传递代理配置
                )
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
                           strategy: str = "ADAPTIVE",
                           proxy_config: Optional[Dict[str, str]] = None) -> GitHubClientV2:
    """
    创建 GitHub 客户端 V2
    
    Args:
        tokens: GitHub 令牌列表
        strategy: TokenPool 策略
        proxy_config: 代理配置字典 (可选)
        
    Returns:
        GitHubClientV2 实例
    """
    # 创建 TokenPool
    strategy_enum = TokenSelectionStrategy[strategy.upper()]
    token_pool = TokenPool(tokens, strategy=strategy_enum)
    
    # 创建客户端（传递代理配置）
    return GitHubClientV2(token_pool, proxy_config)


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
    
    # 测试代理配置
    proxy_config = None
    if os.getenv('HTTP_PROXY'):
        proxy_config = {
            'http': os.getenv('HTTP_PROXY'),
            'https': os.getenv('HTTPS_PROXY', os.getenv('HTTP_PROXY'))
        }
        print(f"🌐 Using proxy configuration: {proxy_config}")
    
    # 创建客户端
    client = create_github_client_v2(test_tokens, strategy="ADAPTIVE", proxy_config=proxy_config)
    
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