import base64
import random
import time
import logging
from typing import Dict, List, Optional, Any

import requests

# 使用标准logging而不是自定义Logger
logger = logging.getLogger(__name__)


class GitHubClient:
    GITHUB_API_URL = "https://api.github.com/search/code"

    def __init__(self, tokens: List[str]):
        self.tokens = [token.strip() for token in tokens if token.strip()]
        self._token_ptr = 0
        # 添加 token 状态跟踪
        self._token_status = {token: {'remaining': 30, 'reset_time': 0, 'failed_count': 0}
                              for token in self.tokens}
        self._exhausted_tokens = set()  # 已耗尽的 token

    def _next_token(self) -> Optional[str]:
        """智能选择下一个可用的 token"""
        if not self.tokens:
            return None
        
        # 检查是否有 token 的限流时间已过
        current_time = time.time()
        for token in list(self._exhausted_tokens):
            if self._token_status[token]['reset_time'] < current_time:
                self._exhausted_tokens.remove(token)
                self._token_status[token]['remaining'] = 30  # 重置配额
                logger.info(f"♻️ Token recovered from rate limit: {token[:20]}...")
        
        # 获取可用的 tokens（未耗尽的）
        available_tokens = [t for t in self.tokens if t not in self._exhausted_tokens]
        
        if not available_tokens:
            # 如果所有 token 都耗尽了，等待最早恢复的 token
            if self._exhausted_tokens:
                min_reset = min(self._token_status[t]['reset_time'] for t in self._exhausted_tokens)
                wait_time = max(0, min_reset - current_time)
                if wait_time > 0:
                    logger.warning(f"⏰ All tokens exhausted, waiting {wait_time:.1f}s for recovery...")
                    time.sleep(wait_time + 1)
                    return self._next_token()  # 递归调用
            return None
        
        # 选择剩余配额最多的 token
        best_token = max(available_tokens,
                        key=lambda t: self._token_status[t]['remaining'])
        
        return best_token.strip() if isinstance(best_token, str) else best_token
    
    def _update_token_status(self, token: str, response: requests.Response):
        """更新 token 的限流状态"""
        if not token or token not in self._token_status:
            return
            
        remaining = response.headers.get('X-RateLimit-Remaining')
        reset_time = response.headers.get('X-RateLimit-Reset')
        
        if remaining is not None:
            self._token_status[token]['remaining'] = int(remaining)
            
        if reset_time is not None:
            self._token_status[token]['reset_time'] = int(reset_time)
        
        # 如果配额耗尽，标记为已耗尽
        if remaining is not None and int(remaining) == 0:
            self._exhausted_tokens.add(token)
            logger.warning(f"🚫 Token exhausted: {token[:20]}... (resets at {time.strftime('%H:%M:%S', time.localtime(int(reset_time)))})")

    def search_for_keys(self, query: str, max_retries: int = 5) -> Dict[str, Any]:
        all_items = []
        total_count = 0
        expected_total = None
        pages_processed = 0
        
        # 添加失败页面重试队列
        failed_pages = []
        max_page_retries = 2  # 每个失败页面最多重试2次

        # 统计信息
        total_requests = 0
        failed_requests = 0
        rate_limit_hits = 0

        for page in range(1, 11):
            page_result = None
            page_success = False

            for attempt in range(1, max_retries + 1):
                current_token = self._next_token()

                headers = {
                    "Accept": "application/vnd.github.v3+json",
                    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/138.0.0.0 Safari/537.36"
                }

                if current_token:
                    current_token = current_token.strip()
                    headers["Authorization"] = f"token {current_token}"

                params = {
                    "q": query,
                    "per_page": 100,
                    "page": page
                }

                try:
                    total_requests += 1
                    # 暂时不使用代理，简化实现
                    response = requests.get(self.GITHUB_API_URL, headers=headers, params=params, timeout=30)
                    
                    # 更新 token 状态
                    if current_token:
                        self._update_token_status(current_token, response)
                    
                    rate_limit_remaining = response.headers.get('X-RateLimit-Remaining')
                    # 只在剩余次数很少时警告
                    if rate_limit_remaining and int(rate_limit_remaining) < 3:
                        logger.warning(f"⚠️ Rate limit low: {rate_limit_remaining} remaining, token: {current_token[:20]}...")
                    
                    response.raise_for_status()
                    page_result = response.json()
                    page_success = True
                    break

                except requests.exceptions.HTTPError as e:
                    status = e.response.status_code if e.response else None
                    failed_requests += 1
                    
                    if status in (403, 429):
                        rate_limit_hits += 1
                        
                        # 标记当前 token 为耗尽
                        if current_token:
                            self._exhausted_tokens.add(current_token)
                            # 从响应头获取重置时间
                            reset_time = e.response.headers.get('X-RateLimit-Reset') if e.response else None
                            if reset_time:
                                self._token_status[current_token]['reset_time'] = int(reset_time)
                                wait_until_reset = int(reset_time) - time.time()
                                if wait_until_reset > 0:
                                    logger.info(f"⏱️ Token {current_token[:20]}... will reset in {wait_until_reset:.0f}s")
                        
                        # 如果还有其他尝试机会，快速切换到下一个 token
                        if attempt < max_retries:
                            wait = min(1 + random.uniform(0, 0.5), 5)  # 减少等待时间
                            logger.debug(f"🔄 Switching token after rate limit (attempt {attempt}/{max_retries})")
                            time.sleep(wait)
                            continue
                        else:
                            logger.error(f"❌ All retries exhausted for page {page}")
                    else:
                        # 其他HTTP错误，只在最后一次尝试时记录
                        if attempt == max_retries:
                            logger.error(f"❌ HTTP {status} error after {max_retries} attempts on page {page}")
                        time.sleep(min(2 ** attempt, 10))
                        continue

                except requests.exceptions.RequestException as e:
                    failed_requests += 1
                    wait = min(2 ** attempt, 30)

                    # 只在最后一次尝试时记录网络错误
                    if attempt == max_retries:
                        logger.error(f"❌ Network error after {max_retries} attempts on page {page}: {type(e).__name__}")

                    time.sleep(wait)
                    continue

            if not page_success or not page_result:
                if page == 1:
                    # 第一页失败是严重问题
                    logger.error(f"❌ First page failed for query: {query[:50]}...")
                    break
                else:
                    # 将失败的页面加入重试队列
                    failed_pages.append({'page': page, 'retry_count': 0})
                    logger.debug(f"📝 Page {page} added to retry queue")
                continue

            pages_processed += 1

            if page == 1:
                total_count = page_result.get("total_count", 0)
                expected_total = min(total_count, 1000)

            items = page_result.get("items", [])
            current_page_count = len(items)

            if current_page_count == 0:
                if expected_total and len(all_items) < expected_total:
                    continue
                else:
                    break

            all_items.extend(items)

            if expected_total and len(all_items) >= expected_total:
                break

            if page < 10:
                sleep_time = random.uniform(0.5, 1.5)
                logger.info(f"⏳ Processing query: 【{query}】,page {page},item count: {current_page_count},expected total: {expected_total},total count: {total_count},random sleep: {sleep_time:.1f}s")
                time.sleep(sleep_time)

        # 重试失败的页面
        if failed_pages and expected_total:
            logger.info(f"🔄 Retrying {len(failed_pages)} failed pages...")
            
            for failed_page_info in failed_pages[:]:  # 使用切片创建副本
                if failed_page_info['retry_count'] >= max_page_retries:
                    continue
                    
                page = failed_page_info['page']
                failed_page_info['retry_count'] += 1
                
                # 等待一段时间后重试
                time.sleep(2 * failed_page_info['retry_count'])
                
                for attempt in range(1, 3):  # 简化的重试逻辑
                    current_token = self._next_token()
                    if not current_token:
                        break
                        
                    headers = {
                        "Accept": "application/vnd.github.v3+json",
                        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
                    }
                    headers["Authorization"] = f"token {current_token}"
                    
                    params = {
                        "q": query,
                        "per_page": 100,
                        "page": page
                    }
                    
                    try:
                        response = requests.get(self.GITHUB_API_URL, headers=headers, params=params, timeout=30)
                        if current_token:
                            self._update_token_status(current_token, response)
                        response.raise_for_status()
                        
                        retry_result = response.json()
                        items = retry_result.get("items", [])
                        if items:
                            all_items.extend(items)
                            pages_processed += 1
                            failed_pages.remove(failed_page_info)
                            logger.info(f"✅ Successfully recovered page {page} with {len(items)} items")
                        break
                        
                    except Exception as e:
                        if attempt == 2:
                            logger.debug(f"⚠️ Failed to recover page {page}: {type(e).__name__}")
                        continue

        final_count = len(all_items)

        # 检查数据完整性
        if expected_total and final_count < expected_total:
            discrepancy = expected_total - final_count
            completeness = (final_count / expected_total) * 100
            
            if discrepancy > expected_total * 0.1:  # 超过10%数据丢失
                logger.warning(f"⚠️ Data completeness: {completeness:.1f}% ({final_count}/{expected_total} items retrieved)")
                
                # 如果数据完整性低于50%，记录更严重的警告
                if completeness < 50:
                    logger.error(f"❌ Severe data loss: Only {completeness:.1f}% of expected data retrieved")
            else:
                logger.info(f"✅ Good data completeness: {completeness:.1f}%")

        # 主要成功日志 - 一条日志包含所有关键信息
        failed_pages_count = len(failed_pages)
        logger.info(f"🔍 GitHub search complete: query:【{query}】 | pages:{pages_processed}/{10} | items:{final_count}/{expected_total or '?'} | failed pages:{failed_pages_count}")

        result = {
            "total_count": total_count,
            "incomplete_results": final_count < expected_total if expected_total else False,
            "items": all_items
        }

        return result

    def get_file_content(self, item: Dict[str, Any]) -> Optional[str]:
        repo_full_name = item["repository"]["full_name"]
        file_path = item["path"]

        metadata_url = f"https://api.github.com/repos/{repo_full_name}/contents/{file_path}"
        headers = {
            "Accept": "application/vnd.github.v3+json",
        }

        token = self._next_token()
        if token:
            headers["Authorization"] = f"token {token}"

        try:
            logger.info(f"🔍 Processing file: {metadata_url}")
            # 暂时不使用代理，简化实现
            metadata_response = requests.get(metadata_url, headers=headers, timeout=15)
            
            # 更新 token 状态
            if token:
                self._update_token_status(token, metadata_response)
            
            metadata_response.raise_for_status()
            file_metadata = metadata_response.json()

            # 检查是否有base64编码的内容
            encoding = file_metadata.get("encoding")
            content = file_metadata.get("content")
            
            if encoding == "base64" and content:
                try:
                    # 解码base64内容
                    decoded_content = base64.b64decode(content).decode('utf-8')
                    return decoded_content
                except Exception as e:
                    logger.warning(f"⚠️ Failed to decode base64 content: {e}, falling back to download_url")
            
            # 如果没有base64内容或解码失败，使用原有的download_url逻辑
            download_url = file_metadata.get("download_url")
            if not download_url:
                logger.warning(f"⚠️ No download URL found for file: {metadata_url}")
                return None

            # 暂时不使用代理，简化实现
            content_response = requests.get(download_url, headers=headers)
            logger.info(f"⏳ checking for keys from:  {download_url},status: {content_response.status_code}")
            content_response.raise_for_status()
            return content_response.text

        except requests.exceptions.RequestException as e:
            logger.error(f"❌ Failed to fetch file content: {metadata_url}, {type(e).__name__}")
            return None

    @staticmethod
    def create_instance(tokens: List[str]) -> 'GitHubClient':
        return GitHubClient(tokens)
