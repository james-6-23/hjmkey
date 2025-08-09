"""
本地Token搜索器
搜索本地系统中存储的GitHub tokens
"""

import os
import re
import json
import configparser
from pathlib import Path
from typing import List, Set, Dict, Any, Optional
import logging
import platform

logger = logging.getLogger(__name__)


class LocalSearcher:
    """
    本地Token搜索器
    搜索系统环境变量、配置文件等位置的tokens
    """
    
    # Token正则模式
    TOKEN_PATTERNS = [
        re.compile(r'ghp_[a-zA-Z0-9]{36}'),  # Personal access token (classic)
        re.compile(r'github_pat_[a-zA-Z0-9]{22}_[a-zA-Z0-9]{59}'),  # Fine-grained token
        re.compile(r'ghs_[a-zA-Z0-9]{36}'),  # GitHub App token
    ]
    
    # 常见的token环境变量名
    ENV_VAR_NAMES = [
        'GITHUB_TOKEN',
        'GH_TOKEN',
        'GITHUB_ACCESS_TOKEN',
        'GITHUB_PAT',
        'GH_PAT',
        'GITHUB_API_TOKEN',
        'GH_API_TOKEN',
        'GITHUB_PERSONAL_ACCESS_TOKEN',
    ]
    
    def __init__(self):
        """初始化本地搜索器"""
        self.home_dir = Path.home()
        self.system = platform.system()
        
        # 根据操作系统设置搜索路径
        self.search_paths = self._get_search_paths()
    
    def _get_search_paths(self) -> List[Path]:
        """
        获取需要搜索的文件路径
        
        Returns:
            搜索路径列表
        """
        paths = []
        
        # 通用配置文件
        common_files = [
            '.env',
            '.env.local',
            '.env.development',
            '.env.production',
            '.gitconfig',
            '.npmrc',
            '.yarnrc',
        ]
        
        for file in common_files:
            path = self.home_dir / file
            if path.exists():
                paths.append(path)
        
        # Shell配置文件
        if self.system in ['Linux', 'Darwin']:  # Linux或macOS
            shell_files = [
                '.bashrc',
                '.bash_profile',
                '.zshrc',
                '.zprofile',
                '.profile',
                '.config/fish/config.fish',
            ]
            for file in shell_files:
                path = self.home_dir / file
                if path.exists():
                    paths.append(path)
        
        # Windows配置
        elif self.system == 'Windows':
            # PowerShell配置
            ps_profile = Path(os.environ.get('USERPROFILE', '')) / 'Documents' / 'WindowsPowerShell' / 'Microsoft.PowerShell_profile.ps1'
            if ps_profile.exists():
                paths.append(ps_profile)
        
        # GitHub CLI配置
        gh_config_paths = [
            self.home_dir / '.config' / 'gh' / 'hosts.yml',
            self.home_dir / '.config' / 'gh' / 'config.yml',
        ]
        for path in gh_config_paths:
            if path.exists():
                paths.append(path)
        
        # VSCode配置
        vscode_paths = self._get_vscode_config_paths()
        paths.extend(vscode_paths)
        
        # Git凭据存储
        git_creds = self.home_dir / '.git-credentials'
        if git_creds.exists():
            paths.append(git_creds)
        
        # Docker配置
        docker_config = self.home_dir / '.docker' / 'config.json'
        if docker_config.exists():
            paths.append(docker_config)
        
        # 项目目录中的.env文件
        project_dirs = self._find_project_directories()
        for project_dir in project_dirs:
            env_file = project_dir / '.env'
            if env_file.exists():
                paths.append(env_file)
        
        return paths
    
    def _get_vscode_config_paths(self) -> List[Path]:
        """获取VSCode配置文件路径"""
        paths = []
        
        if self.system == 'Windows':
            vscode_dir = Path(os.environ.get('APPDATA', '')) / 'Code' / 'User'
        elif self.system == 'Darwin':  # macOS
            vscode_dir = self.home_dir / 'Library' / 'Application Support' / 'Code' / 'User'
        else:  # Linux
            vscode_dir = self.home_dir / '.config' / 'Code' / 'User'
        
        settings_file = vscode_dir / 'settings.json'
        if settings_file.exists():
            paths.append(settings_file)
        
        return paths
    
    def _find_project_directories(self, max_depth: int = 2) -> List[Path]:
        """
        查找可能包含项目的目录
        
        Args:
            max_depth: 最大搜索深度
            
        Returns:
            项目目录列表
        """
        project_dirs = []
        
        # 常见的项目根目录
        search_roots = [
            self.home_dir / 'Documents',
            self.home_dir / 'Projects',
            self.home_dir / 'projects',
            self.home_dir / 'workspace',
            self.home_dir / 'Workspace',
            self.home_dir / 'dev',
            self.home_dir / 'Development',
            self.home_dir / 'code',
            self.home_dir / 'Code',
            self.home_dir / 'repos',
            self.home_dir / 'github',
            self.home_dir / 'GitHub',
        ]
        
        for root in search_roots:
            if not root.exists():
                continue
            
            # 搜索包含.git目录的项目
            try:
                for path in root.rglob('.git'):
                    if path.is_dir():
                        project_dir = path.parent
                        if project_dir not in project_dirs:
                            project_dirs.append(project_dir)
                        
                        # 限制数量避免搜索过多
                        if len(project_dirs) >= 20:
                            return project_dirs
            except Exception as e:
                logger.debug(f"搜索项目目录时出错: {e}")
        
        return project_dirs
    
    def search(self) -> List[str]:
        """
        搜索本地系统中的tokens
        
        Returns:
            找到的token列表
        """
        logger.info("🔍 开始搜索本地系统中的GitHub tokens...")
        
        all_tokens = set()
        
        # 1. 搜索环境变量
        env_tokens = self._search_environment_variables()
        all_tokens.update(env_tokens)
        logger.info(f"从环境变量找到 {len(env_tokens)} 个tokens")
        
        # 2. 搜索配置文件
        file_tokens = self._search_config_files()
        all_tokens.update(file_tokens)
        logger.info(f"从配置文件找到 {len(file_tokens)} 个tokens")
        
        # 3. 搜索命令历史
        history_tokens = self._search_command_history()
        all_tokens.update(history_tokens)
        logger.info(f"从命令历史找到 {len(history_tokens)} 个tokens")
        
        logger.info(f"✅ 本地搜索完成，共找到 {len(all_tokens)} 个潜在tokens")
        return list(all_tokens)
    
    def _search_environment_variables(self) -> Set[str]:
        """搜索环境变量中的tokens"""
        tokens = set()
        
        # 搜索特定的环境变量名
        for var_name in self.ENV_VAR_NAMES:
            value = os.environ.get(var_name)
            if value:
                # 检查是否匹配token格式
                for pattern in self.TOKEN_PATTERNS:
                    matches = pattern.findall(value)
                    tokens.update(matches)
        
        # 搜索所有环境变量
        for key, value in os.environ.items():
            if 'TOKEN' in key.upper() or 'GITHUB' in key.upper() or 'GH_' in key.upper():
                for pattern in self.TOKEN_PATTERNS:
                    matches = pattern.findall(value)
                    tokens.update(matches)
        
        return tokens
    
    def _search_config_files(self) -> Set[str]:
        """搜索配置文件中的tokens"""
        tokens = set()
        
        for file_path in self.search_paths:
            try:
                logger.debug(f"搜索文件: {file_path}")
                
                # 根据文件类型选择解析方法
                if file_path.suffix in ['.json']:
                    file_tokens = self._search_json_file(file_path)
                elif file_path.suffix in ['.yml', '.yaml']:
                    file_tokens = self._search_yaml_file(file_path)
                elif file_path.suffix in ['.ini', '.cfg']:
                    file_tokens = self._search_ini_file(file_path)
                else:
                    # 文本文件
                    file_tokens = self._search_text_file(file_path)
                
                tokens.update(file_tokens)
                
            except Exception as e:
                logger.debug(f"搜索文件 {file_path} 时出错: {e}")
        
        return tokens
    
    def _search_text_file(self, file_path: Path) -> Set[str]:
        """搜索文本文件中的tokens"""
        tokens = set()
        
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
                
                # 搜索token模式
                for pattern in self.TOKEN_PATTERNS:
                    matches = pattern.findall(content)
                    tokens.update(matches)
                    
        except Exception as e:
            logger.debug(f"读取文件 {file_path} 失败: {e}")
        
        return tokens
    
    def _search_json_file(self, file_path: Path) -> Set[str]:
        """搜索JSON文件中的tokens"""
        tokens = set()
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                
                # 递归搜索JSON结构
                tokens.update(self._extract_tokens_from_dict(data))
                
        except Exception as e:
            logger.debug(f"解析JSON文件 {file_path} 失败: {e}")
        
        return tokens
    
    def _search_yaml_file(self, file_path: Path) -> Set[str]:
        """搜索YAML文件中的tokens"""
        # 简单的文本搜索，避免引入yaml依赖
        return self._search_text_file(file_path)
    
    def _search_ini_file(self, file_path: Path) -> Set[str]:
        """搜索INI配置文件中的tokens"""
        tokens = set()
        
        try:
            config = configparser.ConfigParser()
            config.read(file_path, encoding='utf-8')
            
            # 搜索所有section和option
            for section in config.sections():
                for option, value in config.items(section):
                    if value:
                        for pattern in self.TOKEN_PATTERNS:
                            matches = pattern.findall(value)
                            tokens.update(matches)
                            
        except Exception as e:
            logger.debug(f"解析INI文件 {file_path} 失败: {e}")
        
        return tokens
    
    def _extract_tokens_from_dict(self, data: Any) -> Set[str]:
        """从字典或列表中递归提取tokens"""
        tokens = set()
        
        if isinstance(data, dict):
            for key, value in data.items():
                if isinstance(value, str):
                    for pattern in self.TOKEN_PATTERNS:
                        matches = pattern.findall(value)
                        tokens.update(matches)
                elif isinstance(value, (dict, list)):
                    tokens.update(self._extract_tokens_from_dict(value))
                    
        elif isinstance(data, list):
            for item in data:
                if isinstance(item, str):
                    for pattern in self.TOKEN_PATTERNS:
                        matches = pattern.findall(item)
                        tokens.update(matches)
                elif isinstance(item, (dict, list)):
                    tokens.update(self._extract_tokens_from_dict(item))
        
        return tokens
    
    def _search_command_history(self) -> Set[str]:
        """搜索命令历史中的tokens"""
        tokens = set()
        
        history_files = []
        
        # Bash历史
        bash_history = self.home_dir / '.bash_history'
        if bash_history.exists():
            history_files.append(bash_history)
        
        # Zsh历史
        zsh_history = self.home_dir / '.zsh_history'
        if zsh_history.exists():
            history_files.append(zsh_history)
        
        # Fish历史
        fish_history = self.home_dir / '.local' / 'share' / 'fish' / 'fish_history'
        if fish_history.exists():
            history_files.append(fish_history)
        
        # 搜索历史文件
        for history_file in history_files:
            try:
                with open(history_file, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()
                    
                    # 搜索token模式
                    for pattern in self.TOKEN_PATTERNS:
                        matches = pattern.findall(content)
                        tokens.update(matches)
                        
            except Exception as e:
                logger.debug(f"读取历史文件 {history_file} 失败: {e}")
        
        return tokens


def main():
    """测试函数"""
    # 创建搜索器
    searcher = LocalSearcher()
    
    # 显示搜索路径
    print("将搜索以下位置:")
    for path in searcher.search_paths[:10]:  # 只显示前10个
        print(f"  - {path}")
    if len(searcher.search_paths) > 10:
        print(f"  ... 以及其他 {len(searcher.search_paths) - 10} 个位置")
    
    print("\n开始搜索...")
    
    # 搜索tokens
    tokens = searcher.search()
    
    print(f"\n找到 {len(tokens)} 个潜在tokens:")
    for i, token in enumerate(tokens, 1):
        print(f"{i}. {token[:20]}...")


if __name__ == "__main__":
    main()