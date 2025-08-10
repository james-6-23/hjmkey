"""
Gemini API密钥验证工具
可以验证密钥是否有效，以及是否为付费版本
"""

import sys
import time
from pathlib import Path
from typing import Optional, Dict, Any

# 添加项目根目录到Python路径
sys.path.insert(0, str(Path(__file__).parent))

import google.generativeai as genai
from google.api_core import exceptions as google_exceptions


class GeminiKeyChecker:
    """
    Gemini密钥检查器
    可以验证密钥的有效性和付费状态
    """
    
    def __init__(self, api_key: str):
        """
        初始化检查器
        
        Args:
            api_key: Gemini API密钥
        """
        self.api_key = api_key
        genai.configure(api_key=api_key)
    
    def check_basic_validity(self) -> Dict[str, Any]:
        """
        基础有效性检查
        
        Returns:
            检查结果字典
        """
        result = {
            "valid": False,
            "message": "",
            "error": None
        }
        
        try:
            # 尝试使用最基础的模型进行简单调用
            # 首先尝试新的gemini-1.5-flash模型
            try:
                model = genai.GenerativeModel('gemini-1.5-flash')
                response = model.generate_content("Say 'test'")
                result["valid"] = True
                result["message"] = "✅ 密钥有效 (gemini-1.5-flash)"
                return result
            except google_exceptions.NotFound:
                # 如果新模型不存在，回退到旧的gemini-pro模型
                model = genai.GenerativeModel('gemini-pro')
                response = model.generate_content("Say 'test'")
                result["valid"] = True
                result["message"] = "✅ 密钥有效 (gemini-pro)"
                return result
            
        except google_exceptions.PermissionDenied:
            result["message"] = "❌ 密钥无效或未授权"
            result["error"] = "PERMISSION_DENIED"
        except google_exceptions.TooManyRequests:
            result["message"] = "⚠️ 达到速率限制"
            result["error"] = "RATE_LIMIT"
        except google_exceptions.NotFound:
            result["message"] = "❌ 模型不存在，请检查API版本"
            result["error"] = "MODEL_NOT_FOUND"
        except Exception as e:
            error_str = str(e)
            if "403" in error_str or "SERVICE_DISABLED" in error_str:
                result["message"] = "❌ API服务未启用"
                result["error"] = "SERVICE_DISABLED"
            elif "429" in error_str or "quota" in error_str.lower():
                result["message"] = "⚠️ 配额已用尽"
                result["error"] = "QUOTA_EXCEEDED"
            else:
                result["message"] = f"❌ 未知错误: {error_str[:100]}"
                result["error"] = "UNKNOWN"
        
        return result
    
    def check_model_access(self) -> Dict[str, Any]:
        """
        检查可访问的模型
        判断是否为付费版本
        
        Returns:
            模型访问信息
        """
        models_info = {
            "available_models": [],
            "is_paid": False,
            "paid_features": []
        }
        
        # 测试不同的模型
        test_models = [
            ("gemini-1.5-flash", "快速模型"),
            ("gemini-1.5-pro", "高级模型 (付费)"),
            ("gemini-pro", "基础模型"),
            ("gemini-pro-vision", "视觉模型"),
            ("gemini-2.0-flash-exp", "实验模型"),
        ]
        
        for model_name, description in test_models:
            try:
                model = genai.GenerativeModel(model_name)
                # 尝试一个简单的调用
                response = model.generate_content("1+1=?", 
                    generation_config=genai.types.GenerationConfig(
                        max_output_tokens=10,
                        temperature=0
                    ))
                
                models_info["available_models"].append({
                    "name": model_name,
                    "description": description,
                    "status": "✅ 可用"
                })
                
                # 如果能访问高级模型，可能是付费版本
                if "1.5-pro" in model_name or "2.0" in model_name:
                    models_info["is_paid"] = True
                    models_info["paid_features"].append(f"访问 {model_name}")
                    
            except Exception as e:
                error_str = str(e)
                if "not found" in error_str.lower():
                    status = "❌ 模型不存在"
                elif "403" in error_str or "permission" in error_str.lower():
                    status = "🔒 无权限"
                elif "429" in error_str or "quota" in error_str.lower():
                    status = "⚠️ 配额限制"
                else:
                    status = "❌ 不可用"
                
                models_info["available_models"].append({
                    "name": model_name,
                    "description": description,
                    "status": status
                })
        
        return models_info
    
    def check_rate_limits(self) -> Dict[str, Any]:
        """
        检查速率限制
        付费版本通常有更高的限制
        
        Returns:
            速率限制信息
        """
        limits_info = {
            "requests_per_minute": None,
            "tokens_per_minute": None,
            "is_high_tier": False
        }
        
        try:
            # 快速连续发送几个请求来测试速率限制
            model = genai.GenerativeModel('gemini-pro')
            successful_requests = 0
            
            for i in range(5):  # 减少测试请求数量以提高速度
                try:
                    response = model.generate_content(f"Count: {i}", 
                        generation_config=genai.types.GenerationConfig(
                            max_output_tokens=5,
                            temperature=0
                        ))
                    successful_requests += 1
                    time.sleep(0.05)  # 更短的延迟
                except google_exceptions.TooManyRequests:
                    break
            
            # 根据成功的请求数判断速率限制级别
            if successful_requests >= 5:
                limits_info["requests_per_minute"] = "60+ (高级)"
                limits_info["is_high_tier"] = True
            elif successful_requests >= 3:
                limits_info["requests_per_minute"] = "15-60 (标准)"
            else:
                limits_info["requests_per_minute"] = f"<15 (基础，成功{successful_requests}个)"
            
        except Exception as e:
            limits_info["error"] = str(e)[:100]
        
        return limits_info
    
    def get_full_report(self) -> Dict[str, Any]:
        """
        获取完整的密钥检查报告
        
        Returns:
            完整报告
        """
        print("🔍 开始检查Gemini API密钥...")
        print(f"密钥: {self.api_key[:10]}...{self.api_key[-4:]}")
        print("-" * 50)
        
        # 1. 基础有效性检查
        print("\n1️⃣ 基础有效性检查...")
        validity = self.check_basic_validity()
        print(f"   {validity['message']}")
        
        if not validity["valid"]:
            return {
                "api_key": f"{self.api_key[:10]}...{self.api_key[-4:]}",
                "valid": False,
                "error": validity["error"],
                "message": validity["message"]
            }
        
        # 2. 模型访问检查
        print("\n2️⃣ 模型访问检查...")
        models = self.check_model_access()
        for model in models["available_models"]:
            print(f"   {model['status']} {model['name']} - {model['description']}")
        
        # 3. 速率限制检查
        print("\n3️⃣ 速率限制检查...")
        limits = self.check_rate_limits()
        if limits.get("requests_per_minute"):
            print(f"   请求限制: {limits['requests_per_minute']}")
        
        # 4. 判断是否为付费版本
        print("\n4️⃣ 账户类型判断...")
        is_paid = models["is_paid"] or limits.get("is_high_tier", False)
        
        if is_paid:
            print("   💎 这可能是一个付费版本的密钥！")
            print("   付费特征:")
            for feature in models.get("paid_features", []):
                print(f"     • {feature}")
            if limits.get("is_high_tier"):
                print(f"     • 高速率限制")
        else:
            print("   🆓 这看起来是一个免费版本的密钥")
        
        return {
            "api_key": f"{self.api_key[:10]}...{self.api_key[-4:]}",
            "valid": True,
            "is_paid": is_paid,
            "models": models,
            "rate_limits": limits,
            "summary": "付费版本" if is_paid else "免费版本"
        }


def test_single_key(api_key: str):
    """
    测试单个密钥
    
    Args:
        api_key: Gemini API密钥
    """
    checker = GeminiKeyChecker(api_key)
    report = checker.get_full_report()
    
    print("\n" + "=" * 50)
    print("📊 检查报告总结:")
    print(f"   密钥状态: {'✅ 有效' if report.get('valid') else '❌ 无效'}")
    if report.get('valid'):
        print(f"   账户类型: {'💎 ' + report['summary'] if report.get('is_paid') else '🆓 ' + report['summary']}")
    print("=" * 50)
    
    return report


def test_keys_from_file(filename: str = "data/gemini_keys.txt"):
    """
    从文件测试多个密钥
    
    Args:
        filename: 包含密钥的文件路径
    """
    try:
        with open(filename, 'r') as f:
            keys = [line.strip() for line in f if line.strip() and not line.startswith('#')]
        
        print(f"📋 从 {filename} 加载了 {len(keys)} 个密钥")
        print("=" * 50)
        
        paid_keys = []
        free_keys = []
        invalid_keys = []
        
        for i, key in enumerate(keys, 1):
            print(f"\n🔑 测试密钥 {i}/{len(keys)}")
            try:
                report = test_single_key(key)
                if not report.get('valid'):
                    invalid_keys.append(key)
                elif report.get('is_paid'):
                    paid_keys.append(key)
                else:
                    free_keys.append(key)
                
                # 减少延迟避免速率限制，但仍保持一定的延迟以避免被限制
                if i < len(keys):
                    time.sleep(0.5)  # 将延迟从2秒减少到0.5秒
                    
            except Exception as e:
                print(f"❌ 测试失败: {e}")
                invalid_keys.append(key)
        
        # 最终统计
        print("\n" + "=" * 50)
        print("📊 最终统计:")
        print(f"   💎 付费密钥: {len(paid_keys)} 个")
        print(f"   🆓 免费密钥: {len(free_keys)} 个")
        print(f"   ❌ 无效密钥: {len(invalid_keys)} 个")
        print("=" * 50)
        
        # 保存付费密钥
        if paid_keys:
            output_file = "data/paid_gemini_keys.txt"
            with open(output_file, 'w') as f:
                f.write("# 付费版本的Gemini API密钥\n")
                f.write(f"# 发现时间: {time.strftime('%Y-%m-%d %H:%M:%S')}\n\n")
                for key in paid_keys:
                    f.write(f"{key}\n")
            print(f"\n💾 付费密钥已保存到: {output_file}")
            
    except FileNotFoundError:
        print(f"❌ 文件不存在: {filename}")
    except Exception as e:
        print(f"❌ 错误: {e}")


def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Gemini API密钥验证工具')
    parser.add_argument('--key', type=str, help='要测试的单个密钥')
    parser.add_argument('--file', type=str, default='data/gemini_keys.txt', 
                       help='包含密钥的文件路径')
    parser.add_argument('--mode', type=str, choices=['single', 'batch'], 
                       default='single', help='测试模式')
    
    args = parser.parse_args()
    
    print("🎯 Gemini API密钥验证工具")
    print("=" * 50)
    
    if args.mode == 'single' and args.key:
        test_single_key(args.key)
    elif args.mode == 'batch':
        test_keys_from_file(args.file)
    else:
        # 交互式输入
        print("请输入要测试的Gemini API密钥:")
        api_key = input().strip()
        if api_key:
            test_single_key(api_key)
        else:
            print("❌ 未输入密钥")


if __name__ == "__main__":
    main()