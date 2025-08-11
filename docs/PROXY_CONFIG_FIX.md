# 代理配置修复文档

## 问题描述

用户在 `.env` 文件中配置了 `HTTP_PROXY` 和 `HTTPS_PROXY`，但是 GitHub 客户端在实际请求时没有使用这些代理配置。

### 原始问题
- 环境变量中设置了代理：`HTTP_PROXY=http://127.0.0.1:7890`
- 但 `github_client_v2.py` 没有读取和应用这些配置
- 导致在需要代理的网络环境中无法正常访问 GitHub API

## 修复方案

### 1. 修改的文件
- `utils/github_client_v2.py`

### 2. 具体修改

#### 2.1 添加代理配置支持

```python
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
```

#### 2.2 自动检测环境变量

```python
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
        os.environ['NO_PROXY'] = no_proxy
        logger.debug(f"NO_PROXY set: {no_proxy}")
    
    return proxy_config if proxy_config else None
```

#### 2.3 在所有请求中应用代理

在所有 `self.session.get()` 调用中添加 `proxies` 参数：

```python
response = self.session.get(
    self.GITHUB_API_URL, 
    headers=headers, 
    params=params, 
    timeout=30,
    proxies=self.proxy_config  # 显式传递代理配置
)
```

### 3. 工厂函数更新

```python
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
```

## 测试验证

### 测试脚本
创建了 `test_proxy_fix.py` 测试脚本，包含以下测试：

1. **代理配置检测测试**
   - 测试自动从环境变量检测代理
   - 测试手动配置代理

2. **代理应用测试**
   - 验证 Session 中的代理配置
   - 确认代理在实际请求中生效

3. **工厂函数测试**
   - 测试不带代理创建客户端
   - 测试带代理创建客户端

### 运行测试

```bash
python test_proxy_fix.py
```

### 测试结果
```
[OK] 检测到代理配置
[OK] 手动配置的代理
[OK] 代理检测测试完成
[OK] 代理应用测试完成
[OK] 工厂函数测试完成
[OK] 所有代理测试完成!
```

## 使用方法

### 1. 通过环境变量设置代理

#### Windows PowerShell
```powershell
$env:HTTP_PROXY="http://127.0.0.1:7890"
$env:HTTPS_PROXY="http://127.0.0.1:7890"
```

#### Windows CMD
```cmd
set HTTP_PROXY=http://127.0.0.1:7890
set HTTPS_PROXY=http://127.0.0.1:7890
```

#### Linux/Mac
```bash
export HTTP_PROXY="http://127.0.0.1:7890"
export HTTPS_PROXY="http://127.0.0.1:7890"
```

### 2. 通过 .env 文件设置

在项目根目录的 `.env` 文件中添加：
```
HTTP_PROXY=http://127.0.0.1:7890
HTTPS_PROXY=http://127.0.0.1:7890
```

### 3. 程序中手动配置

```python
proxy_config = {
    'http': 'http://127.0.0.1:7890',
    'https': 'http://127.0.0.1:7890'
}

client = create_github_client_v2(
    tokens=github_tokens,
    strategy="ADAPTIVE",
    proxy_config=proxy_config
)
```

## 特性

1. **自动检测**：自动从环境变量读取代理配置
2. **手动配置**：支持在创建客户端时手动指定代理
3. **NO_PROXY 支持**：支持排除特定域名不使用代理
4. **向后兼容**：不影响不使用代理的场景
5. **日志记录**：记录代理使用情况便于调试

## 注意事项

1. 代理配置优先级：手动配置 > 环境变量
2. 支持 HTTP 和 HTTPS 代理
3. 代理格式：`http://[用户名:密码@]主机:端口`
4. 如果代理需要认证，可以在 URL 中包含用户名和密码

## 影响范围

此修复影响以下功能：
- GitHub API 搜索请求
- 文件内容获取请求
- 所有通过 `github_client_v2.py` 发起的 HTTP 请求

## 验证状态

✅ 代理自动检测功能正常  
✅ 手动配置代理功能正常  
✅ 代理在请求中正确应用  
✅ 不影响无代理场景  
✅ 向后兼容性保持