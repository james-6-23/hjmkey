"""
GPT Load 启动验证模块
在系统启动时验证 GPT Load 服务连接和配置
"""

import os
import time
import json
import logging
import requests
from typing import Dict, Any, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime

logger = logging.getLogger(__name__)


@dataclass
class GPTLoadConfig:
    """GPT Load 配置"""
    api_url: str
    api_key: str
    group_id: str
    timeout: int = 10
    retry_count: int = 3
    retry_delay: int = 2


class GPTLoadValidator:
    """GPT Load 验证器"""
    
    # 测试API密钥（用于验证）
    TEST_API_KEY = "test_gemini_key_AIzaSyBxZJpQpK0H4lI7YkVr"
    
    def __init__(self, config: Optional[GPTLoadConfig] = None):
        """
        初始化验证器
        
        Args:
            config: GPT Load 配置，如果为None则从环境变量读取
        """
        self.config = config or self._load_config_from_env()
        self.validation_results = {}
        self.start_time = None
        self.end_time = None
        
    def _load_config_from_env(self) -> GPTLoadConfig:
        """从环境变量加载配置"""
        return GPTLoadConfig(
            api_url=os.getenv('GPT_LOAD_API_URL', 'http://localhost:8080'),
            api_key=os.getenv('GPT_LOAD_API_KEY', ''),
            group_id=os.getenv('GPT_LOAD_GROUP_ID', 'default'),
            timeout=int(os.getenv('GPT_LOAD_TIMEOUT', '10')),
            retry_count=int(os.getenv('GPT_LOAD_RETRY_COUNT', '3')),
            retry_delay=int(os.getenv('GPT_LOAD_RETRY_DELAY', '2'))
        )
    
    def validate_startup(self) -> Tuple[bool, Dict[str, Any]]:
        """
        执行启动验证
        
        Returns:
            (是否成功, 验证结果详情)
        """
        logger.info("🚀 Starting GPT Load validation...")
        self.start_time = datetime.now()
        
        # 执行4步验证
        steps = [
            ("connectivity", self._check_connectivity),
            ("authentication", self._check_authentication),
            ("api_key_management", self._test_api_key_management),
            ("group_validation", self._validate_group)
        ]
        
        all_success = True
        
        for step_name, step_func in steps:
            logger.info(f"📋 Step: {step_name}")
            try:
                success, details = step_func()
                self.validation_results[step_name] = {
                    "success": success,
                    "details": details,
                    "timestamp": datetime.now().isoformat()
                }
                
                if success:
                    logger.info(f"  ✅ {step_name}: PASSED")
                else:
                    logger.warning(f"  ❌ {step_name}: FAILED - {details.get('error', 'Unknown error')}")
                    all_success = False
                    
            except Exception as e:
                logger.error(f"  ❌ {step_name}: ERROR - {str(e)}")
                self.validation_results[step_name] = {
                    "success": False,
                    "details": {"error": str(e)},
                    "timestamp": datetime.now().isoformat()
                }
                all_success = False
        
        self.end_time = datetime.now()
        duration = (self.end_time - self.start_time).total_seconds()
        
        # 生成总结
        summary = {
            "overall_success": all_success,
            "duration_seconds": duration,
            "start_time": self.start_time.isoformat(),
            "end_time": self.end_time.isoformat(),
            "steps": self.validation_results,
            "config": {
                "api_url": self.config.api_url,
                "group_id": self.config.group_id,
                "has_api_key": bool(self.config.api_key)
            }
        }
        
        # 记录结果
        self._save_validation_report(summary)
        
        if all_success:
            logger.info(f"✅ GPT Load validation completed successfully in {duration:.2f}s")
        else:
            logger.warning(f"⚠️ GPT Load validation completed with failures in {duration:.2f}s")
        
        return all_success, summary
    
    def _check_connectivity(self) -> Tuple[bool, Dict[str, Any]]:
        """
        步骤1: 检查服务连接性
        """
        url = f"{self.config.api_url}/health"
        
        for attempt in range(self.config.retry_count):
            try:
                response = requests.get(
                    url,
                    timeout=self.config.timeout
                )
                
                if response.status_code == 200:
                    return True, {
                        "status_code": response.status_code,
                        "response_time_ms": response.elapsed.total_seconds() * 1000,
                        "endpoint": url
                    }
                else:
                    if attempt < self.config.retry_count - 1:
                        time.sleep(self.config.retry_delay)
                        continue
                    
                    return False, {
                        "error": f"HTTP {response.status_code}",
                        "endpoint": url
                    }
                    
            except requests.exceptions.ConnectionError:
                if attempt < self.config.retry_count - 1:
                    time.sleep(self.config.retry_delay)
                    continue
                    
                return False, {
                    "error": "Connection failed",
                    "endpoint": url,
                    "suggestion": "Check if GPT Load service is running"
                }
                
            except requests.exceptions.Timeout:
                if attempt < self.config.retry_count - 1:
                    time.sleep(self.config.retry_delay)
                    continue
                    
                return False, {
                    "error": f"Timeout after {self.config.timeout}s",
                    "endpoint": url
                }
                
            except Exception as e:
                return False, {
                    "error": str(e),
                    "endpoint": url
                }
        
        return False, {"error": "Max retries exceeded"}
    
    def _check_authentication(self) -> Tuple[bool, Dict[str, Any]]:
        """
        步骤2: 验证API认证
        """
        if not self.config.api_key:
            return False, {
                "error": "No API key configured",
                "suggestion": "Set GPT_LOAD_API_KEY environment variable"
            }
        
        url = f"{self.config.api_url}/api/groups"
        headers = {
            "Authorization": f"Bearer {self.config.api_key}",
            "Content-Type": "application/json"
        }
        
        try:
            response = requests.get(
                url,
                headers=headers,
                timeout=self.config.timeout
            )
            
            if response.status_code == 200:
                groups = response.json()
                return True, {
                    "authenticated": True,
                    "groups_count": len(groups) if isinstance(groups, list) else 0
                }
            elif response.status_code == 401:
                return False, {
                    "error": "Authentication failed",
                    "status_code": 401,
                    "suggestion": "Check API key validity"
                }
            else:
                return False, {
                    "error": f"Unexpected status code: {response.status_code}",
                    "response": response.text[:200]
                }
                
        except Exception as e:
            return False, {
                "error": str(e),
                "type": type(e).__name__
            }
    
    def _test_api_key_management(self) -> Tuple[bool, Dict[str, Any]]:
        """
        步骤3: 测试API密钥管理功能
        """
        url = f"{self.config.api_url}/api/groups/{self.config.group_id}/keys"
        headers = {
            "Authorization": f"Bearer {self.config.api_key}",
            "Content-Type": "application/json"
        }
        
        # 添加测试密钥
        test_key_data = {
            "key": self.TEST_API_KEY,
            "provider": "gemini",
            "model": "gemini-1.5-flash",
            "tag": "startup_test",
            "added_at": datetime.now().isoformat()
        }
        
        try:
            # 尝试添加测试密钥
            response = requests.post(
                url,
                headers=headers,
                json=test_key_data,
                timeout=self.config.timeout
            )
            
            if response.status_code in (200, 201):
                # 成功添加，尝试删除
                self._cleanup_test_key()
                return True, {
                    "add_key": "success",
                    "test_key_prefix": self.TEST_API_KEY[:20] + "..."
                }
            elif response.status_code == 409:
                # 密钥已存在
                return True, {
                    "add_key": "already_exists",
                    "note": "Test key already in system"
                }
            else:
                return False, {
                    "error": f"Failed to add test key",
                    "status_code": response.status_code,
                    "response": response.text[:200]
                }
                
        except Exception as e:
            return False, {
                "error": str(e),
                "operation": "add_test_key"
            }
    
    def _validate_group(self) -> Tuple[bool, Dict[str, Any]]:
        """
        步骤4: 验证组配置
        """
        url = f"{self.config.api_url}/api/groups/{self.config.group_id}"
        headers = {
            "Authorization": f"Bearer {self.config.api_key}",
            "Content-Type": "application/json"
        }
        
        try:
            response = requests.get(
                url,
                headers=headers,
                timeout=self.config.timeout
            )
            
            if response.status_code == 200:
                group_info = response.json()
                return True, {
                    "group_id": self.config.group_id,
                    "group_name": group_info.get("name", "Unknown"),
                    "keys_count": len(group_info.get("keys", [])),
                    "settings": group_info.get("settings", {})
                }
            elif response.status_code == 404:
                # 组不存在，尝试创建
                return self._create_group()
            else:
                return False, {
                    "error": f"Failed to get group info",
                    "status_code": response.status_code
                }
                
        except Exception as e:
            return False, {
                "error": str(e),
                "operation": "get_group"
            }
    
    def _create_group(self) -> Tuple[bool, Dict[str, Any]]:
        """创建默认组"""
        url = f"{self.config.api_url}/api/groups"
        headers = {
            "Authorization": f"Bearer {self.config.api_key}",
            "Content-Type": "application/json"
        }
        
        group_data = {
            "id": self.config.group_id,
            "name": f"Group {self.config.group_id}",
            "description": "Auto-created by startup validation",
            "created_at": datetime.now().isoformat()
        }
        
        try:
            response = requests.post(
                url,
                headers=headers,
                json=group_data,
                timeout=self.config.timeout
            )
            
            if response.status_code in (200, 201):
                return True, {
                    "group_created": True,
                    "group_id": self.config.group_id
                }
            else:
                return False, {
                    "error": "Failed to create group",
                    "status_code": response.status_code
                }
                
        except Exception as e:
            return False, {
                "error": str(e),
                "operation": "create_group"
            }
    
    def _cleanup_test_key(self):
        """清理测试密钥"""
        try:
            url = f"{self.config.api_url}/api/groups/{self.config.group_id}/keys/{self.TEST_API_KEY}"
            headers = {
                "Authorization": f"Bearer {self.config.api_key}"
            }
            
            requests.delete(
                url,
                headers=headers,
                timeout=self.config.timeout
            )
        except:
            pass  # 忽略清理错误
    
    def _save_validation_report(self, summary: Dict[str, Any]):
        """保存验证报告"""
        try:
            report_dir = "logs/gpt_load_validation"
            os.makedirs(report_dir, exist_ok=True)
            
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            report_file = f"{report_dir}/validation_{timestamp}.json"
            
            with open(report_file, 'w', encoding='utf-8') as f:
                json.dump(summary, f, indent=2, ensure_ascii=False)
            
            logger.info(f"📄 Validation report saved to: {report_file}")
            
        except Exception as e:
            logger.warning(f"Failed to save validation report: {e}")


def run_startup_validation() -> bool:
    """
    运行启动验证（供外部调用）
    
    Returns:
        是否验证成功
    """
    validator = GPTLoadValidator()
    success, results = validator.validate_startup()
    return success


# 使用示例
if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s | %(levelname)s | %(name)s | %(message)s'
    )
    
    # 运行验证
    success = run_startup_validation()
    
    if success:
        print("\n✅ GPT Load is ready!")
    else:
        print("\n❌ GPT Load validation failed. Please check the configuration.")
        print("\nSuggestions:")
        print("1. Ensure GPT Load service is running")
        print("2. Check GPT_LOAD_API_URL environment variable")
        print("3. Verify GPT_LOAD_API_KEY is valid")
        print("4. Review the validation report in logs/gpt_load_validation/")