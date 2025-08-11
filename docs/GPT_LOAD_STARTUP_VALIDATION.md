# GPT Load 启动校验机制设计文档

## 概述
本文档描述了GPT Load服务启动时的健康检查和功能验证机制，确保系统在运行前能够正确连接到GPT Load服务并具备添加API密钥的能力。

## 测试用密钥
- **测试密钥（无效）**: `AIzaSyAwnx8zgkw2aDHcdXmpSC-86RFVWQjEfMs`
- **用途**: 用于验证GPT Load服务的连接性和API添加功能，不会影响实际的密钥配额

## 启动校验流程

### 1. 连接性检查
```python
def check_gpt_load_connectivity():
    """检查GPT Load服务是否可访问"""
    try:
        # 1. 检查配置是否完整
        if not all([GPT_LOAD_URL, GPT_LOAD_AUTH, GPT_LOAD_GROUP_NAME]):
            return False, "配置不完整"
        
        # 2. 尝试访问健康检查端点
        response = requests.get(
            f"{GPT_LOAD_URL}/api/health",
            headers={'Authorization': f'Bearer {GPT_LOAD_AUTH}'},
            timeout=5
        )
        
        if response.status_code == 200:
            return True, "服务连接正常"
        elif response.status_code == 401:
            return False, "认证失败"
        else:
            return False, f"服务异常: HTTP {response.status_code}"
            
    except requests.exceptions.ConnectionError:
        return False, "无法连接到GPT Load服务"
    except requests.exceptions.Timeout:
        return False, "连接超时"
```

### 2. 认证验证
```python
def validate_gpt_load_auth():
    """验证GPT Load认证信息是否有效"""
    try:
        # 获取组列表来验证认证
        response = requests.get(
            f"{GPT_LOAD_URL}/api/groups",
            headers={'Authorization': f'Bearer {GPT_LOAD_AUTH}'},
            timeout=10
        )
        
        if response.status_code == 200:
            groups = response.json()
            logger.info(f"✅ 认证成功，发现 {len(groups)} 个组")
            return True, groups
        elif response.status_code == 401:
            return False, "认证令牌无效"
        else:
            return False, f"认证检查失败: HTTP {response.status_code}"
            
    except Exception as e:
        return False, f"认证验证异常: {str(e)}"
```

### 3. 组存在性检查
```python
def check_group_exists(group_name: str):
    """检查指定的组是否存在"""
    success, result = validate_gpt_load_auth()
    if not success:
        return False, result
    
    groups = result
    for group in groups:
        if group.get('name') == group_name:
            return True, group.get('id')
    
    return False, f"组 '{group_name}' 不存在"
```

### 4. API密钥添加测试
```python
def test_add_api_key(test_key: str = "AIzaSyAwnx8zgkw2aDHcdXmpSC-86RFVWQjEfMs"):
    """测试添加API密钥功能"""
    try:
        # 1. 获取组ID
        success, group_id = check_group_exists(GPT_LOAD_GROUP_NAME)
        if not success:
            return False, f"无法获取组ID: {group_id}"
        
        # 2. 尝试添加测试密钥
        response = requests.post(
            f"{GPT_LOAD_URL}/api/keys/add-async",
            headers={
                'Authorization': f'Bearer {GPT_LOAD_AUTH}',
                'Content-Type': 'application/json'
            },
            json={
                'keys': test_key,
                'groupId': group_id
            },
            timeout=10
        )
        
        if response.status_code in [200, 201]:
            # 3. 验证密钥是否被添加
            task_id = response.json().get('taskId')
            if task_id:
                return True, f"测试密钥添加成功，任务ID: {task_id}"
            else:
                return True, "测试密钥添加成功"
        else:
            return False, f"添加密钥失败: HTTP {response.status_code}"
            
    except Exception as e:
        return False, f"添加密钥测试异常: {str(e)}"
```

## 完整的启动校验器

```python
class GPTLoadStartupValidator:
    """GPT Load启动校验器"""
    
    def __init__(self, config_service):
        self.config = config_service
        self.gpt_load_url = config_service.get('GPT_LOAD_URL', '').rstrip('/')
        self.gpt_load_auth = config_service.get('GPT_LOAD_AUTH', '')
        self.gpt_load_group_name = config_service.get('GPT_LOAD_GROUP_NAME', '')
        self.test_key = "AIzaSyAwnx8zgkw2aDHcdXmpSC-86RFVWQjEfMs"
        
    def run_all_checks(self) -> Tuple[bool, Dict[str, Any]]:
        """运行所有启动检查"""
        results = {
            'connectivity': {'passed': False, 'message': ''},
            'authentication': {'passed': False, 'message': ''},
            'group_check': {'passed': False, 'message': ''},
            'add_key_test': {'passed': False, 'message': ''},
            'overall': {'passed': False, 'message': ''}
        }
        
        logger.info("=" * 60)
        logger.info("🚀 GPT LOAD STARTUP VALIDATION")
        logger.info("=" * 60)
        
        # 1. 连接性检查
        logger.info("1️⃣ Checking connectivity...")
        success, message = self.check_connectivity()
        results['connectivity'] = {'passed': success, 'message': message}
        if not success:
            logger.error(f"   ❌ {message}")
            results['overall']['message'] = "连接失败"
            return False, results
        logger.info(f"   ✅ {message}")
        
        # 2. 认证验证
        logger.info("2️⃣ Validating authentication...")
        success, message = self.validate_auth()
        results['authentication'] = {'passed': success, 'message': message}
        if not success:
            logger.error(f"   ❌ {message}")
            results['overall']['message'] = "认证失败"
            return False, results
        logger.info(f"   ✅ {message}")
        
        # 3. 组存在性检查
        logger.info("3️⃣ Checking group existence...")
        success, message = self.check_group()
        results['group_check'] = {'passed': success, 'message': message}
        if not success:
            logger.error(f"   ❌ {message}")
            results['overall']['message'] = "组不存在"
            return False, results
        logger.info(f"   ✅ {message}")
        
        # 4. 添加密钥测试
        logger.info("4️⃣ Testing key addition...")
        success, message = self.test_add_key()
        results['add_key_test'] = {'passed': success, 'message': message}
        if not success:
            logger.warning(f"   ⚠️ {message}")
            # 这不是致命错误，只是警告
        else:
            logger.info(f"   ✅ {message}")
        
        # 总体结果
        all_critical_passed = (
            results['connectivity']['passed'] and
            results['authentication']['passed'] and
            results['group_check']['passed']
        )
        
        if all_critical_passed:
            results['overall'] = {
                'passed': True,
                'message': "所有关键检查通过，GPT Load服务就绪"
            }
            logger.info("=" * 60)
            logger.info("✅ GPT LOAD SERVICE READY")
            logger.info("=" * 60)
        else:
            logger.error("=" * 60)
            logger.error("❌ GPT LOAD SERVICE NOT READY")
            logger.error("=" * 60)
            
        return all_critical_passed, results
```

## 集成到主程序

### 在程序启动时调用
```python
# app/main.py 或 app/main_v2_with_gemini_v2.py

async def startup_checks():
    """执行启动检查"""
    config_service = get_config_service()
    
    # 检查是否启用GPT Load
    if not config_service.get("GPT_LOAD_SYNC_ENABLED"):
        logger.info("ℹ️ GPT Load sync disabled, skipping validation")
        return True
    
    # 运行GPT Load校验
    validator = GPTLoadStartupValidator(config_service)
    success, results = validator.run_all_checks()
    
    if not success:
        logger.error("❌ GPT Load validation failed!")
        logger.error(f"   Reason: {results['overall']['message']}")
        
        # 可以选择：
        # 1. 继续运行但禁用GPT Load功能
        config_service.set("GPT_LOAD_SYNC_ENABLED", False)
        logger.warning("⚠️ Continuing with GPT Load disabled")
        
        # 2. 或者终止程序
        # sys.exit(1)
    
    return success

# 在main函数中调用
async def main():
    # 执行启动检查
    await startup_checks()
    
    # 继续正常的程序流程
    ...
```

## 错误处理策略

### 1. 连接失败
- **原因**: 网络问题、服务未启动、URL配置错误
- **处理**: 
  - 重试3次，每次间隔5秒
  - 失败后禁用GPT Load功能，继续运行

### 2. 认证失败
- **原因**: Token过期、Token错误
- **处理**:
  - 记录错误日志
  - 禁用GPT Load功能
  - 发送告警通知

### 3. 组不存在
- **原因**: 组名配置错误、组被删除
- **处理**:
  - 尝试创建组（如果有权限）
  - 或使用默认组
  - 或禁用GPT Load功能

### 4. 添加密钥失败
- **原因**: 权限不足、服务异常
- **处理**:
  - 记录警告日志
  - 继续运行，但标记为"功能受限"

## 监控指标

### 启动校验指标
```python
startup_metrics = {
    'validation_time': 0,  # 校验总耗时
    'connectivity_time': 0,  # 连接检查耗时
    'auth_time': 0,  # 认证验证耗时
    'group_check_time': 0,  # 组检查耗时
    'add_key_test_time': 0,  # 添加密钥测试耗时
    'retry_count': 0,  # 重试次数
    'last_check_timestamp': None,  # 最后检查时间
    'last_check_result': None  # 最后检查结果
}
```

## 日志示例

### 成功场景
```
2024-01-11 10:00:00 | INFO | ============================================================
2024-01-11 10:00:00 | INFO | 🚀 GPT LOAD STARTUP VALIDATION
2024-01-11 10:00:00 | INFO | ============================================================
2024-01-11 10:00:00 | INFO | 1️⃣ Checking connectivity...
2024-01-11 10:00:01 | INFO |    ✅ 服务连接正常
2024-01-11 10:00:01 | INFO | 2️⃣ Validating authentication...
2024-01-11 10:00:02 | INFO |    ✅ 认证成功，发现 3 个组
2024-01-11 10:00:02 | INFO | 3️⃣ Checking group existence...
2024-01-11 10:00:02 | INFO |    ✅ 组 'production' 存在 (ID: 1)
2024-01-11 10:00:02 | INFO | 4️⃣ Testing key addition...
2024-01-11 10:00:03 | INFO |    ✅ 测试密钥添加成功，任务ID: task_123
2024-01-11 10:00:03 | INFO | ============================================================
2024-01-11 10:00:03 | INFO | ✅ GPT LOAD SERVICE READY
2024-01-11 10:00:03 | INFO | ============================================================
```

### 失败场景
```
2024-01-11 10:00:00 | INFO | ============================================================
2024-01-11 10:00:00 | INFO | 🚀 GPT LOAD STARTUP VALIDATION
2024-01-11 10:00:00 | INFO | ============================================================
2024-01-11 10:00:00 | INFO | 1️⃣ Checking connectivity...
2024-01-11 10:00:05 | ERROR |    ❌ 连接超时
2024-01-11 10:00:05 | ERROR | ============================================================
2024-01-11 10:00:05 | ERROR | ❌ GPT LOAD SERVICE NOT READY
2024-01-11 10:00:05 | ERROR | ============================================================
2024-01-11 10:00:05 | WARNING | ⚠️ Continuing with GPT Load disabled
```

## 测试建议

1. **单元测试**: 为每个检查函数编写独立的单元测试
2. **集成测试**: 测试完整的启动校验流程
3. **故障注入**: 模拟各种失败场景
4. **性能测试**: 确保校验过程不会显著延长启动时间

## 配置示例

### .env 文件
```env
# GPT Load配置
GPT_LOAD_SYNC_ENABLED=true
GPT_LOAD_URL=https://api.gptload.com
GPT_LOAD_AUTH=your_auth_token_here
GPT_LOAD_GROUP_NAME=production

# 启动校验配置
GPT_LOAD_STARTUP_VALIDATION=true
GPT_LOAD_VALIDATION_TIMEOUT=30
GPT_LOAD_VALIDATION_RETRY=3
GPT_LOAD_TEST_KEY=AIzaSyAwnx8zgkw2aDHcdXmpSC-86RFVWQjEfMs
```

## 总结

通过实施这个启动校验机制，可以：
1. ✅ 确保GPT Load服务在程序启动时可用
2. ✅ 验证认证信息的有效性
3. ✅ 确认目标组的存在
4. ✅ 测试密钥添加功能
5. ✅ 提供清晰的错误信息和恢复策略
6. ✅ 避免运行时出现意外的服务不可用问题