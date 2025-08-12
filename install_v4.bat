@echo off
REM HAJIMI KING V4.0 安装脚本 (Windows)
REM 自动安装所有必要的依赖

setlocal enabledelayedexpansion

REM 设置控制台代码页为 UTF-8
chcp 65001 >nul

REM 颜色定义
set "RED=[91m"
set "GREEN=[92m"
set "YELLOW=[93m"
set "BLUE=[94m"
set "PURPLE=[95m"
set "CYAN=[96m"
set "NC=[0m"

REM 显示横幅
:show_banner
cls
echo %CYAN%
echo ╔═══════════════════════════════════════════════════════════════╗
echo ║                                                               ║
echo ║   ██╗  ██╗ █████╗      ██╗██╗███╗   ███╗██╗    ██╗   ██╗██╗ ║
echo ║   ██║  ██║██╔══██╗     ██║██║████╗ ████║██║    ██║   ██║██║ ║
echo ║   ███████║███████║     ██║██║██╔████╔██║██║    ██║   ██║███║ ║
echo ║   ██╔══██║██╔══██║██   ██║██║██║╚██╔╝██║██║    ╚██╗ ██╔╝╚██║ ║
echo ║   ██║  ██║██║  ██║╚█████╔╝██║██║ ╚═╝ ██║██║     ╚████╔╝  ██║ ║
echo ║   ╚═╝  ╚═╝╚═╝  ╚═╝ ╚════╝ ╚═╝╚═╝     ╚═╝╚═╝      ╚═══╝   ╚═╝ ║
echo ║                                                               ║
echo ║                    V4.0 安装脚本                              ║
echo ╚═══════════════════════════════════════════════════════════════╝
echo %NC%
echo.
goto :main

REM 打印函数
:print_info
echo %BLUE%[INFO]%NC% %~1
goto :eof

:print_success
echo %GREEN%[SUCCESS]%NC% %~1
goto :eof

:print_warning
echo %YELLOW%[WARNING]%NC% %~1
goto :eof

:print_error
echo %RED%[ERROR]%NC% %~1
goto :eof

:print_step
echo %PURPLE%[STEP]%NC% %~1
goto :eof

REM 检查系统要求
:check_system
call :print_step "检查系统要求..."

REM 检查 Python
python --version >nul 2>&1
if %errorlevel% neq 0 (
    call :print_error "未找到 Python"
    call :print_info "请从 https://python.org 下载并安装 Python 3.8+"
    pause
    exit /b 1
)

REM 获取 Python 版本
for /f "tokens=2" %%i in ('python --version 2^>^&1') do set PYTHON_VERSION=%%i
call :print_success "Python 版本: %PYTHON_VERSION%"

REM 检查 pip
pip --version >nul 2>&1
if %errorlevel% neq 0 (
    call :print_error "未找到 pip"
    pause
    exit /b 1
)
call :print_success "pip 可用"

REM 检查 Git (可选)
git --version >nul 2>&1
if %errorlevel% equ 0 (
    call :print_success "Git 可用"
) else (
    call :print_warning "未找到 Git (可选)"
)

goto :eof

REM 设置虚拟环境
:setup_venv
call :print_step "设置虚拟环境..."

if exist "venv" (
    call :print_info "虚拟环境已存在"
    set /p RECREATE="是否重新创建虚拟环境? (y/n): "
    if /i "!RECREATE!"=="y" (
        call :print_info "删除现有虚拟环境..."
        rmdir /s /q venv
    ) else (
        call :print_info "使用现有虚拟环境"
        call venv\Scripts\activate.bat
        goto :eof
    )
)

call :print_info "创建虚拟环境..."
python -m venv venv

if %errorlevel% equ 0 (
    call :print_success "虚拟环境创建成功"
    call venv\Scripts\activate.bat
    call :print_success "虚拟环境已激活"
) else (
    call :print_error "虚拟环境创建失败"
    pause
    exit /b 1
)

goto :eof

REM 升级 pip
:upgrade_pip
call :print_step "升级 pip..."

python -m pip install --upgrade pip
if %errorlevel% equ 0 (
    call :print_success "pip 升级成功"
) else (
    call :print_warning "pip 升级失败，继续安装..."
)

goto :eof

REM 安装基础依赖
:install_basic_deps
call :print_step "安装基础依赖..."

if not exist "requirements.txt" (
    call :print_error "未找到 requirements.txt"
    pause
    exit /b 1
)

call :print_info "安装核心依赖包..."
pip install -r requirements.txt

if %errorlevel% equ 0 (
    call :print_success "基础依赖安装成功"
) else (
    call :print_error "基础依赖安装失败"
    pause
    exit /b 1
)

goto :eof

REM 安装可选依赖
:install_optional_deps
call :print_step "安装可选依赖..."

REM Docker 支持
set /p INSTALL_DOCKER="是否安装 Docker 支持? (推荐) (y/n): "
if /i "!INSTALL_DOCKER!"=="y" (
    call :print_info "安装 Docker 支持..."
    pip install docker>=7.0.0
    if %errorlevel% equ 0 (
        call :print_success "Docker 支持安装成功"
    ) else (
        call :print_warning "Docker 支持安装失败"
    )
)

REM Selenium WebDriver
set /p INSTALL_SELENIUM="是否安装 Selenium WebDriver 支持? (用于高级 Web 搜索) (y/n): "
if /i "!INSTALL_SELENIUM!"=="y" (
    call :print_info "安装 Selenium 支持..."
    pip install selenium>=4.15.0
    if %errorlevel% equ 0 (
        call :print_success "Selenium 支持安装成功"
        call :print_warning "请确保安装了 ChromeDriver"
        call :print_info "下载地址: https://chromedriver.chromium.org/"
    ) else (
        call :print_warning "Selenium 支持安装失败"
    )
)

REM GPU 支持
set /p INSTALL_GPU="是否安装 GPU 监控支持? (可选) (y/n): "
if /i "!INSTALL_GPU!"=="y" (
    call :print_info "安装 GPU 支持..."
    pip install GPUtil>=1.4.0
    if %errorlevel% equ 0 (
        call :print_success "GPU 支持安装成功"
    ) else (
        call :print_warning "GPU 支持安装失败"
    )
)

goto :eof

REM 设置配置文件
:setup_config
call :print_step "设置配置文件..."

if not exist ".env" (
    if exist ".env.v4.example" (
        call :print_info "从示例创建 .env 文件..."
        copy .env.v4.example .env >nul
        call :print_success ".env 文件创建成功"
        call :print_warning "请编辑 .env 文件并配置必要的 Token"
    ) else (
        call :print_warning "未找到 .env.v4.example 文件"
    )
) else (
    call :print_info ".env 文件已存在"
)

REM 创建必要的目录
call :print_info "创建必要的目录..."
if not exist "data" mkdir "data"
if not exist "data\runs" mkdir "data\runs"
if not exist "data\reports" mkdir "data\reports"
if not exist "data\cache" mkdir "data\cache"
if not exist "data\keys" mkdir "data\keys"
if not exist "data\logs" mkdir "data\logs"
if not exist "logs" mkdir "logs"
call :print_success "目录创建完成"

goto :eof

REM 验证安装
:verify_installation
call :print_step "验证安装..."

call :print_info "检查核心模块..."
python -c "
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

if %errorlevel% equ 0 (
    call :print_success "核心模块验证成功"
) else (
    call :print_error "核心模块验证失败"
    pause
    exit /b 1
)

REM 检查可选模块
call :print_info "检查可选模块..."
python -c "
optional_modules = ['docker', 'selenium', 'GPUtil']

for module in optional_modules:
    try:
        __import__(module)
        print(f'✅ {module} (可选)')
    except ImportError:
        print(f'⚠️  {module} (可选，未安装)')
"

goto :eof

REM 显示完成信息
:show_completion
call :print_success "安装完成！"
echo.
echo %GREEN%╔════════════════════════════════════════════════════════════════╗%NC%
echo %GREEN%║                        安装成功！                              ║%NC%
echo %GREEN%╠════════════════════════════════════════════════════════════════╣%NC%
echo %GREEN%║  下一步:                                                      ║%NC%
echo %GREEN%║  1. 编辑 .env 文件，配置必要的 Token                           ║%NC%
echo %GREEN%║  2. 运行 run_v4.bat 启动程序                                   ║%NC%
echo %GREEN%║  3. 或直接运行 python -m app.main_v4                          ║%NC%
echo %GREEN%╚════════════════════════════════════════════════════════════════╝%NC%
echo.
echo %BLUE%重要提醒:%NC%
echo • 请确保配置至少一个 GitHub Token
echo • 建议配置 Gemini API Key 用于密钥验证
echo • 查看 docs\V4_QUICK_START.md 获取详细使用说明
echo.

goto :eof

REM 主函数
:main
call :show_banner

REM 检查系统要求
call :check_system
if %errorlevel% neq 0 exit /b 1

REM 设置虚拟环境
call :setup_venv
if %errorlevel% neq 0 exit /b 1

REM 升级 pip
call :upgrade_pip

REM 安装基础依赖
call :install_basic_deps
if %errorlevel% neq 0 exit /b 1

REM 安装可选依赖
call :install_optional_deps

REM 设置配置文件
call :setup_config

REM 验证安装
call :verify_installation
if %errorlevel% neq 0 exit /b 1

REM 显示完成信息
call :show_completion

pause
exit /b 0