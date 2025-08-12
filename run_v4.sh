#!/bin/bash

# HAJIMI KING V4.0 启动脚本
# 支持扩展搜索功能

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# 打印带颜色的消息
print_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# 检查 Python 版本
check_python() {
    print_info "检查 Python 版本..."
    
    if command -v python3 &> /dev/null; then
        PYTHON_VERSION=$(python3 -c 'import sys; print(".".join(map(str, sys.version_info[:2])))')
        print_success "Python 版本: $PYTHON_VERSION"
        
        # 检查版本是否 >= 3.8
        if python3 -c 'import sys; exit(0 if sys.version_info >= (3, 8) else 1)'; then
            return 0
        else
            print_error "需要 Python 3.8 或更高版本"
            return 1
        fi
    else
        print_error "未找到 Python 3"
        return 1
    fi
}

# 检查并安装依赖
check_dependencies() {
    print_info "检查依赖..."
    
    # 检查 requirements.txt
    if [ ! -f "requirements.txt" ]; then
        print_error "未找到 requirements.txt"
        return 1
    fi
    
    # 检查虚拟环境
    if [ -d "venv" ]; then
        print_info "激活虚拟环境..."
        source venv/bin/activate
    else
        print_warning "未找到虚拟环境，建议创建虚拟环境"
        read -p "是否创建虚拟环境? (y/n) " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            print_info "创建虚拟环境..."
            python3 -m venv venv
            source venv/bin/activate
            print_success "虚拟环境已创建并激活"
        fi
    fi
    
    # 安装/更新依赖
    print_info "安装/更新依赖..."
    pip install -r requirements.txt --quiet
    print_success "依赖安装完成"
}

# 检查环境变量
check_env() {
    print_info "检查环境配置..."
    
    # 检查 .env 文件
    if [ ! -f ".env" ]; then
        print_warning "未找到 .env 文件"
        
        # 检查示例文件
        if [ -f ".env.example" ]; then
            print_info "从 .env.example 创建 .env 文件..."
            cp .env.example .env
            print_warning "请编辑 .env 文件并配置必要的环境变量"
            return 1
        else
            print_error "未找到 .env.example 文件"
            return 1
        fi
    fi
    
    # 检查关键环境变量
    source .env
    
    if [ -z "$GITHUB_TOKENS" ]; then
        print_error "未配置 GITHUB_TOKENS"
        return 1
    fi
    
    if [ -z "$GEMINI_API_KEY" ]; then
        print_warning "未配置 GEMINI_API_KEY，将无法进行密钥验证"
    fi
    
    # 检查 V4 特有配置
    if [ "$ENABLE_EXTENDED_SEARCH" = "true" ]; then
        print_info "扩展搜索已启用"
        
        if [ "$ENABLE_WEB_SEARCH" = "true" ]; then
            print_info "  - Web 搜索: 启用"
        fi
        
        if [ "$ENABLE_GITLAB_SEARCH" = "true" ]; then
            print_info "  - GitLab 搜索: 启用"
            if [ -z "$GITLAB_TOKEN" ]; then
                print_warning "    未配置 GITLAB_TOKEN"
            fi
        fi
        
        if [ "$ENABLE_DOCKER_SEARCH" = "true" ]; then
            print_info "  - Docker 搜索: 启用"
            if [ -z "$DOCKER_HUB_TOKEN" ]; then
                print_warning "    未配置 DOCKER_HUB_TOKEN"
            fi
        fi
    fi
    
    print_success "环境配置检查完成"
    return 0
}

# 创建必要的目录
create_directories() {
    print_info "创建必要的目录..."
    
    mkdir -p data/runs
    mkdir -p data/reports
    mkdir -p data/cache
    mkdir -p logs
    
    print_success "目录创建完成"
}

# 显示启动菜单
show_menu() {
    echo
    echo -e "${PURPLE}╔════════════════════════════════════════╗${NC}"
    echo -e "${PURPLE}║       HAJIMI KING V4.0 启动菜单        ║${NC}"
    echo -e "${PURPLE}╠════════════════════════════════════════╣${NC}"
    echo -e "${PURPLE}║  1. 运行完整版 (GitHub + 扩展搜索)     ║${NC}"
    echo -e "${PURPLE}║  2. 仅运行 GitHub 搜索                 ║${NC}"
    echo -e "${PURPLE}║  3. 仅运行扩展搜索                     ║${NC}"
    echo -e "${PURPLE}║  4. 运行测试模式                       ║${NC}"
    echo -e "${PURPLE}║  5. 查看配置信息                       ║${NC}"
    echo -e "${PURPLE}║  6. 退出                               ║${NC}"
    echo -e "${PURPLE}╚════════════════════════════════════════╝${NC}"
    echo
}

# 运行主程序
run_main() {
    local mode=$1
    
    case $mode in
        1)
            print_info "启动 HAJIMI KING V4.0 (完整版)..."
            python3 -m app.main_v4
            ;;
        2)
            print_info "启动 HAJIMI KING V4.0 (仅 GitHub)..."
            ENABLE_EXTENDED_SEARCH=false python3 -m app.main_v4
            ;;
        3)
            print_info "启动 HAJIMI KING V4.0 (仅扩展搜索)..."
            print_warning "此功能正在开发中..."
            ;;
        4)
            print_info "启动测试模式..."
            python3 -m pytest tests/ -v
            ;;
        5)
            print_info "显示配置信息..."
            python3 -c "
from app.services.config_service import get_config_service
config = get_config_service()
print('当前配置:')
for key, value in sorted(config.get_all().items()):
    if 'TOKEN' in key or 'KEY' in key:
        value = '***' if value else 'Not Set'
    print(f'  {key}: {value}')
"
            ;;
        *)
            print_error "无效的选项"
            ;;
    esac
}

# 主函数
main() {
    echo -e "${CYAN}"
    echo "╔═══════════════════════════════════════════════════════════════╗"
    echo "║                                                               ║"
    echo "║   ██╗  ██╗ █████╗      ██╗██╗███╗   ███╗██╗    ██╗   ██╗██╗ ║"
    echo "║   ██║  ██║██╔══██╗     ██║██║████╗ ████║██║    ██║   ██║██║ ║"
    echo "║   ███████║███████║     ██║██║██╔████╔██║██║    ██║   ██║███║ ║"
    echo "║   ██╔══██║██╔══██║██   ██║██║██║╚██╔╝██║██║    ╚██╗ ██╔╝╚██║ ║"
    echo "║   ██║  ██║██║  ██║╚█████╔╝██║██║ ╚═╝ ██║██║     ╚████╔╝  ██║ ║"
    echo "║   ╚═╝  ╚═╝╚═╝  ╚═╝ ╚════╝ ╚═╝╚═╝     ╚═╝╚═╝      ╚═══╝   ╚═╝ ║"
    echo "║                                                               ║"
    echo "║                    Extended Search Edition                    ║"
    echo "╚═══════════════════════════════════════════════════════════════╝"
    echo -e "${NC}"
    
    # 检查环境
    if ! check_python; then
        print_error "Python 环境检查失败"
        exit 1
    fi
    
    if ! check_dependencies; then
        print_error "依赖检查失败"
        exit 1
    fi
    
    if ! check_env; then
        print_warning "环境配置需要完善"
        read -p "是否继续? (y/n) " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            exit 1
        fi
    fi
    
    create_directories
    
    # 显示菜单
    while true; do
        show_menu
        read -p "请选择操作 (1-6): " choice
        
        if [ "$choice" = "6" ]; then
            print_info "退出程序"
            break
        fi
        
        run_main $choice
        
        echo
        read -p "按回车键继续..."
    done
}

# 运行主函数
main