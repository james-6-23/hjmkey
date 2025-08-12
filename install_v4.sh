#!/bin/bash

# HAJIMI KING V4.0 安装脚本
# 自动安装所有必要的依赖

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

print_step() {
    echo -e "${PURPLE}[STEP]${NC} $1"
}

# 显示横幅
show_banner() {
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
    echo "║                    V4.0 安装脚本                              ║"
    echo "╚═══════════════════════════════════════════════════════════════╝"
    echo -e "${NC}"
    echo
}

# 检查系统要求
check_system() {
    print_step "检查系统要求..."
    
    # 检查操作系统
    OS=$(uname -s)
    print_info "操作系统: $OS"
    
    # 检查 Python
    if command -v python3 &> /dev/null; then
        PYTHON_VERSION=$(python3 -c 'import sys; print(".".join(map(str, sys.version_info[:2])))')
        print_success "Python 版本: $PYTHON_VERSION"
        
        # 检查版本是否 >= 3.8
        if python3 -c 'import sys; exit(0 if sys.version_info >= (3, 8) else 1)'; then
            print_success "Python 版本满足要求 (>= 3.8)"
        else
            print_error "需要 Python 3.8 或更高版本"
            return 1
        fi
    else
        print_error "未找到 Python 3"
        print_info "请先安装 Python 3.8+"
        return 1
    fi
    
    # 检查 pip
    if command -v pip3 &> /dev/null; then
        print_success "pip3 可用"
    else
        print_error "未找到 pip3"
        return 1
    fi
    
    # 检查 Git
    if command -v git &> /dev/null; then
        print_success "Git 可用"
    else
        print_warning "未找到 Git（可选）"
    fi
    
    return 0
}

# 创建虚拟环境
setup_venv() {
    print_step "设置虚拟环境..."
    
    if [ -d "venv" ]; then
        print_info "虚拟环境已存在"
        read -p "是否重新创建虚拟环境? (y/n) " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            print_info "删除现有虚拟环境..."
            rm -rf venv
        else
            print_info "使用现有虚拟环境"
            source venv/bin/activate
            return 0
        fi
    fi
    
    print_info "创建虚拟环境..."
    python3 -m venv venv
    
    if [ $? -eq 0 ]; then
        print_success "虚拟环境创建成功"
        source venv/bin/activate
        print_success "虚拟环境已激活"
    else
        print_error "虚拟环境创建失败"
        return 1
    fi
    
    return 0
}

# 升级 pip
upgrade_pip() {
    print_step "升级 pip..."
    
    pip install --upgrade pip
    
    if [ $? -eq 0 ]; then
        print_success "pip 升级成功"
    else
        print_warning "pip 升级失败，继续安装..."
    fi
}

# 安装基础依赖
install_basic_deps() {
    print_step "安装基础依赖..."
    
    print_info "安装核心依赖包..."
    pip install -r requirements.txt
    
    if [ $? -eq 0 ]; then
        print_success "基础依赖安装成功"
    else
        print_error "基础依赖安装失败"
        return 1
    fi
    
    return 0
}

# 安装可选依赖
install_optional_deps() {
    print_step "安装可选依赖..."
    
    # Docker 支持
    read -p "是否安装 Docker 支持? (推荐) (y/n) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        print_info "安装 Docker 支持..."
        pip install docker>=7.0.0
        if [ $? -eq 0 ]; then
            print_success "Docker 支持安装成功"
        else
            print_warning "Docker 支持安装失败"
        fi
    fi
    
    # Selenium WebDriver
    read -p "是否安装 Selenium WebDriver 支持? (用于高级 Web 搜索) (y/n) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        print_info "安装 Selenium 支持..."
        pip install selenium>=4.15.0
        if [ $? -eq 0 ]; then
            print_success "Selenium 支持安装成功"
            
            # 检查是否需要安装 ChromeDriver
            if ! command -v chromedriver &> /dev/null; then
                print_warning "未找到 ChromeDriver"
                print_info "请手动安装 ChromeDriver 或使用以下命令:"
                print_info "  Ubuntu/Debian: sudo apt-get install chromium-chromedriver"
                print_info "  macOS: brew install chromedriver"
                print_info "  或从 https://chromedriver.chromium.org/ 下载"
            fi
        else
            print_warning "Selenium 支持安装失败"
        fi
    fi
    
    # GPU 支持
    read -p "是否安装 GPU 监控支持? (可选) (y/n) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        print_info "安装 GPU 支持..."
        pip install GPUtil>=1.4.0
        if [ $? -eq 0 ]; then
            print_success "GPU 支持安装成功"
        else
            print_warning "GPU 支持安装失败"
        fi
    fi
}

# 创建配置文件
setup_config() {
    print_step "设置配置文件..."
    
    if [ ! -f ".env" ]; then
        if [ -f ".env.v4.example" ]; then
            print_info "从示例创建 .env 文件..."
            cp .env.v4.example .env
            print_success ".env 文件创建成功"
            print_warning "请编辑 .env 文件并配置必要的 Token"
        else
            print_warning "未找到 .env.v4.example 文件"
        fi
    else
        print_info ".env 文件已存在"
    fi
    
    # 创建必要的目录
    print_info "创建必要的目录..."
    mkdir -p data/{runs,reports,cache,keys,logs}
    mkdir -p logs
    print_success "目录创建完成"
}

# 验证安装
verify_installation() {
    print_step "验证安装..."
    
    print_info "检查核心模块..."
    python3 -c "
import sys
modules = [
    'requests', 'aiohttp', 'google.generativeai', 
    'dotenv', 'rich', 'psutil'
]

failed = []
for module in modules:
    try:
        __import__(module)
        print(f'✅ {module}')
    except ImportError:
        print(f'❌ {module}')
        failed.append(module)

if failed:
    print(f'\\n失败的模块: {failed}')
    sys.exit(1)
else:
    print('\\n✅ 所有核心模块检查通过')
"
    
    if [ $? -eq 0 ]; then
        print_success "核心模块验证成功"
    else
        print_error "核心模块验证失败"
        return 1
    fi
    
    # 检查可选模块
    print_info "检查可选模块..."
    python3 -c "
optional_modules = ['docker', 'selenium', 'GPUtil']

for module in optional_modules:
    try:
        __import__(module)
        print(f'✅ {module} (可选)')
    except ImportError:
        print(f'⚠️  {module} (可选，未安装)')
"
    
    return 0
}

# 显示完成信息
show_completion() {
    print_success "安装完成！"
    echo
    echo -e "${GREEN}╔════════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${GREEN}║                        安装成功！                              ║${NC}"
    echo -e "${GREEN}╠════════════════════════════════════════════════════════════════╣${NC}"
    echo -e "${GREEN}║  下一步:                                                      ║${NC}"
    echo -e "${GREEN}║  1. 编辑 .env 文件，配置必要的 Token                           ║${NC}"
    echo -e "${GREEN}║  2. 运行 ./run_v4.sh 启动程序                                  ║${NC}"
    echo -e "${GREEN}║  3. 或直接运行 python -m app.main_v4                          ║${NC}"
    echo -e "${GREEN}╚════════════════════════════════════════════════════════════════╝${NC}"
    echo
    echo -e "${BLUE}重要提醒:${NC}"
    echo "• 请确保配置至少一个 GitHub Token"
    echo "• 建议配置 Gemini API Key 用于密钥验证"
    echo "• 查看 docs/V4_QUICK_START.md 获取详细使用说明"
    echo
}

# 主函数
main() {
    show_banner
    
    # 检查系统要求
    if ! check_system; then
        print_error "系统要求检查失败"
        exit 1
    fi
    
    # 设置虚拟环境
    if ! setup_venv; then
        print_error "虚拟环境设置失败"
        exit 1
    fi
    
    # 升级 pip
    upgrade_pip
    
    # 安装基础依赖
    if ! install_basic_deps; then
        print_error "基础依赖安装失败"
        exit 1
    fi
    
    # 安装可选依赖
    install_optional_deps
    
    # 设置配置文件
    setup_config
    
    # 验证安装
    if ! verify_installation; then
        print_error "安装验证失败"
        exit 1
    fi
    
    # 显示完成信息
    show_completion
}

# 运行主函数
main "$@"