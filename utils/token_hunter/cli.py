#!/usr/bin/env python
"""
Token Hunter 命令行工具
用于搜索、验证和管理GitHub tokens
"""

import os
import argparse
import json
import logging
import sys
from pathlib import Path
from dotenv import load_dotenv

# 添加项目根目录到Python路径
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

# 加载.env文件
load_dotenv()

from utils.token_hunter import TokenHunter, TokenManager, TokenValidator

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)s | %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

logger = logging.getLogger(__name__)


def get_proxy_config():
    """
    从环境变量获取代理配置
    
    Returns:
        代理配置字典或None
    """
    # 尝试从PROXY环境变量读取
    proxy_str = os.getenv("PROXY", "").strip()
    
    if proxy_str:
        # 如果有多个代理，选择第一个
        proxies = [p.strip() for p in proxy_str.split(',') if p.strip()]
        if proxies:
            proxy_url = proxies[0]
            logger.info(f"🌐 使用代理: {proxy_url}")
            return {
                'http': proxy_url,
                'https': proxy_url
            }
    
    # 也支持标准的HTTP_PROXY和HTTPS_PROXY环境变量
    http_proxy = os.getenv("HTTP_PROXY") or os.getenv("http_proxy")
    https_proxy = os.getenv("HTTPS_PROXY") or os.getenv("https_proxy")
    
    if http_proxy or https_proxy:
        proxy_config = {}
        if http_proxy:
            proxy_config['http'] = http_proxy
            logger.info(f"🌐 使用HTTP代理: {http_proxy}")
        if https_proxy:
            proxy_config['https'] = https_proxy
            logger.info(f"🌐 使用HTTPS代理: {https_proxy}")
        return proxy_config
    
    return None


def search_tokens(args):
    """搜索tokens"""
    print("🔍 开始搜索GitHub Tokens...")
    
    # 获取代理配置（如果有）
    proxy = get_proxy_config() if not args.no_proxy else None
    
    hunter = TokenHunter(
        github_token=args.github_token,
        tokens_file=args.tokens_file,
        auto_save=args.auto_save,
        proxy=proxy
    )
    
    results = hunter.hunt_tokens(
        mode=args.mode,
        validate=args.validate,
        max_results=args.max_results
    )
    
    # 显示结果
    print(f"\n📊 搜索结果:")
    print(f"  总共找到: {results['statistics']['total_found']} 个tokens")
    
    if args.validate:
        print(f"  有效tokens: {results['statistics'].get('valid_count', 0)} 个")
        print(f"  无效tokens: {results['statistics'].get('invalid_count', 0)} 个")
        
        if results['valid_tokens'] and args.show_tokens:
            print("\n✅ 有效tokens:")
            for i, token in enumerate(results['valid_tokens'], 1):
                print(f"  {i}. {token[:20]}...")
    
    if args.output:
        # 保存结果到文件
        with open(args.output, 'w') as f:
            json.dump(results, f, indent=2, ensure_ascii=False)
        print(f"\n💾 结果已保存到: {args.output}")


def validate_tokens(args):
    """验证tokens"""
    print("🔐 开始验证tokens...")
    
    if args.input_file:
        # 从文件读取tokens
        tokens = []
        with open(args.input_file, 'r') as f:
            for line in f:
                token = line.strip()
                if token and not token.startswith('#'):
                    tokens.append(token)
        print(f"从 {args.input_file} 加载了 {len(tokens)} 个tokens")
    else:
        # 验证管理器中的tokens
        manager = TokenManager(args.tokens_file)
        tokens = manager.tokens
        print(f"从 {args.tokens_file} 加载了 {len(tokens)} 个tokens")
    
    if not tokens:
        print("❌ 没有找到tokens")
        return
    
    # 获取代理配置（如果有）
    proxy = get_proxy_config() if not args.no_proxy else None
    
    # 验证tokens
    validator = TokenValidator(proxy=proxy)
    valid_count = 0
    invalid_count = 0
    
    print(f"\n验证进度:")
    for i, token in enumerate(tokens, 1):
        result = validator.validate(token)
        
        if result.valid:
            valid_count += 1
            status = "✅ 有效"
            extra = f"用户: {result.user}, 额度: {result.rate_limit.remaining}/{result.rate_limit.limit}" if result.rate_limit else ""
        else:
            invalid_count += 1
            status = "❌ 无效"
            extra = f"原因: {result.reason}"
        
        print(f"  [{i}/{len(tokens)}] {token[:20]}... - {status} {extra}")
    
    print(f"\n📊 验证结果:")
    print(f"  有效: {valid_count} 个")
    print(f"  无效: {invalid_count} 个")


def manage_tokens(args):
    """管理tokens"""
    manager = TokenManager(args.tokens_file)
    
    if args.action == 'list':
        # 列出所有tokens
        print(f"📋 当前有 {len(manager.tokens)} 个tokens:")
        for i, token in enumerate(manager.tokens, 1):
            print(f"  {i}. {token[:20]}...")
    
    elif args.action == 'add':
        # 添加token
        if args.token:
            success = manager.add_token(args.token, validate=not args.no_validate)
            if success:
                print(f"✅ 成功添加token")
            else:
                print(f"❌ 添加token失败")
        else:
            print("❌ 请提供要添加的token")
    
    elif args.action == 'remove':
        # 移除token
        if args.token:
            success = manager.remove_token(args.token)
            if success:
                print(f"✅ 成功移除token")
            else:
                print(f"❌ 移除token失败")
        else:
            print("❌ 请提供要移除的token")
    
    elif args.action == 'status':
        # 显示状态
        status = manager.get_status()
        print(f"\n📊 Token管理器状态:")
        print(f"  总tokens数: {status['total_tokens']}")
        print(f"  当前索引: {status['current_index']}")
        print(f"  文件路径: {status['tokens_file']}")
        
        if status['stats']:
            print(f"\n  各token额度状态:")
            for token_key, info in status['stats'].items():
                if 'remaining' in info:
                    print(f"    {token_key}: {info['remaining']}/{info['limit']} (使用率: {info['usage']})")
                else:
                    print(f"    {token_key}: {info['status']}")
    
    elif args.action == 'validate':
        # 验证所有tokens
        print("🔐 验证所有tokens...")
        results = manager.validate_all_tokens()
        
        valid_count = sum(1 for r in results.values() if r.valid)
        print(f"\n📊 验证结果:")
        print(f"  有效: {valid_count}/{len(results)} 个")
        
        for token_key, result in results.items():
            if result.valid:
                print(f"  ✅ {token_key}: 有效")
            else:
                print(f"  ❌ {token_key}: {result.reason}")
    
    elif args.action == 'clear':
        # 清空所有tokens
        if input("⚠️ 确定要清空所有tokens吗？(yes/no): ").lower() == 'yes':
            manager.clear_all_tokens()
            print("✅ 已清空所有tokens")
        else:
            print("❌ 操作已取消")


def hunt_and_add(args):
    """搜索并自动添加tokens"""
    print("🎯 开始搜索并添加tokens...")
    
    # 获取代理配置（如果有）
    proxy = get_proxy_config() if not args.no_proxy else None
    
    hunter = TokenHunter(
        github_token=args.github_token,
        tokens_file=args.tokens_file,
        auto_save=True,
        proxy=proxy
    )
    
    results = hunter.hunt_and_add(
        mode=args.mode,
        max_results=args.max_results
    )
    
    print(f"\n📊 操作结果:")
    print(f"  找到tokens: {results['statistics']['total_found']} 个")
    print(f"  有效tokens: {results['statistics'].get('valid_count', 0)} 个")
    
    if 'add_results' in results:
        success_count = sum(1 for v in results['add_results'].values() if v)
        print(f"  成功添加: {success_count} 个")


def main():
    """主函数"""
    parser = argparse.ArgumentParser(
        description='Token Hunter - GitHub Token搜索和管理工具',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  # 搜索本地tokens
  python cli.py search --mode local
  
  # 搜索GitHub并验证
  python cli.py search --mode github --validate --github-token YOUR_TOKEN
  
  # 验证tokens文件
  python cli.py validate --input-file tokens.txt
  
  # 管理tokens
  python cli.py manage list
  python cli.py manage add --token ghp_xxxxx
  python cli.py manage status
  
  # 搜索并自动添加
  python cli.py hunt --mode all --max-results 50
        """
    )
    
    subparsers = parser.add_subparsers(dest='command', help='可用命令')
    
    # search命令
    search_parser = subparsers.add_parser('search', help='搜索tokens')
    search_parser.add_argument('--mode', choices=['github', 'local', 'all'], default='all',
                              help='搜索模式 (默认: all)')
    search_parser.add_argument('--validate', action='store_true',
                              help='验证找到的tokens')
    search_parser.add_argument('--max-results', type=int, default=100,
                              help='最大结果数 (默认: 100)')
    search_parser.add_argument('--github-token', help='用于GitHub搜索的token')
    search_parser.add_argument('--tokens-file', default='data/github_tokens.txt',
                              help='tokens保存文件 (默认: data/github_tokens.txt)')
    search_parser.add_argument('--auto-save', action='store_true',
                              help='自动保存有效tokens')
    search_parser.add_argument('--show-tokens', action='store_true',
                              help='显示找到的tokens')
    search_parser.add_argument('--output', help='保存结果到JSON文件')
    search_parser.add_argument('--no-proxy', action='store_true',
                              help='不使用代理（即使环境变量中配置了代理）')
    
    # validate命令
    validate_parser = subparsers.add_parser('validate', help='验证tokens')
    validate_parser.add_argument('--input-file', help='要验证的tokens文件')
    validate_parser.add_argument('--tokens-file', default='data/github_tokens.txt',
                                help='tokens文件 (默认: data/github_tokens.txt)')
    validate_parser.add_argument('--no-proxy', action='store_true',
                                help='不使用代理（即使环境变量中配置了代理）')
    
    # manage命令
    manage_parser = subparsers.add_parser('manage', help='管理tokens')
    manage_parser.add_argument('action', choices=['list', 'add', 'remove', 'status', 'validate', 'clear'],
                              help='管理操作')
    manage_parser.add_argument('--token', help='要操作的token')
    manage_parser.add_argument('--tokens-file', default='data/github_tokens.txt',
                              help='tokens文件 (默认: data/github_tokens.txt)')
    manage_parser.add_argument('--no-validate', action='store_true',
                              help='添加时不验证token')
    
    # hunt命令 (搜索并添加)
    hunt_parser = subparsers.add_parser('hunt', help='搜索并自动添加tokens')
    hunt_parser.add_argument('--mode', choices=['github', 'local', 'all'], default='all',
                            help='搜索模式 (默认: all)')
    hunt_parser.add_argument('--max-results', type=int, default=50,
                            help='最大结果数 (默认: 50)')
    hunt_parser.add_argument('--github-token', help='用于GitHub搜索的token')
    hunt_parser.add_argument('--tokens-file', default='data/github_tokens.txt',
                            help='tokens文件 (默认: data/github_tokens.txt)')
    hunt_parser.add_argument('--no-proxy', action='store_true',
                            help='不使用代理（即使环境变量中配置了代理）')
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    try:
        if args.command == 'search':
            search_tokens(args)
        elif args.command == 'validate':
            validate_tokens(args)
        elif args.command == 'manage':
            manage_tokens(args)
        elif args.command == 'hunt':
            hunt_and_add(args)
    except KeyboardInterrupt:
        print("\n⛔ 操作被用户中断")
    except Exception as e:
        logger.error(f"❌ 发生错误: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()