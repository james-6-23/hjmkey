@echo off
REM HAJIMI KING V4.0 启动脚本 (Windows)
REM 支持扩展搜索功能

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

REM 主程序开始
:main
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
echo ║                    Extended Search Edition                    ║
echo ╚═══════════════════════════════════════════════════════════════╝
echo %NC%
echo.

REM 检查 Python
call :print_info "检查 Python 版本..."
python --version >nul 2>&1
if %errorlevel% neq 0 (
    call :print_error "未找到 Python，请确保已安装 Python 3.8+"
    pause
    exit /b 1
)

REM 获取 Python 版本
for /f "tokens=2" %%i in ('python --version 2^>^&1') do set PYTHON_VERSION=%%i
call :print_success "Python 版本: %PYTHON_VERSION%"

REM 检查虚拟环境
if exist "venv\Scripts\activate.bat" (
    call :print_info "激活虚拟环境..."
    call venv\Scripts\activate.bat
    call :print_success "虚拟环境已激活"
) else (
    call :print_warning "未找到虚拟环境"
    set /p CREATE_VENV="是否创建虚拟环境? (y/n): "
    if /i "!CREATE_VENV!"=="y" (
        call :print_info "创建虚拟环境..."
        python -m venv venv
        call venv\Scripts\activate.bat
        call :print_success "虚拟环境已创建并激活"
    )
)

REM 检查依赖
call :print_info "检查依赖..."
if not exist "requirements.txt" (
    call :print_error "未找到 requirements.txt"
    pause
    exit /b 1
)

REM 安装/更新依赖
call :print_info "安装/更新依赖..."
pip install -r requirements.txt --quiet
if %errorlevel% neq 0 (
    call :print_error "依赖安装失败"
    pause
    exit /b 1
)
call :print_success "依赖安装完成"

REM 检查环境配置
call :print_info "检查环境配置..."
if not exist ".env" (
    call :print_warning "未找到 .env 文件"
    if exist ".env.example" (
        call :print_info "从 .env.example 创建 .env 文件..."
        copy .env.example .env >nul
        call :print_warning "请编辑 .env 文件并配置必要的环境变量"
        notepad .env
    ) else (
        call :print_error "未找到 .env.example 文件"
        pause
        exit /b 1
    )
)

REM 创建必要的目录
call :print_info "创建必要的目录..."
if not exist "data\runs" mkdir "data\runs"
if not exist "data\reports" mkdir "data\reports"
if not exist "data\cache" mkdir "data\cache"
if not exist "logs" mkdir "logs"
call :print_success "目录创建完成"

:menu
echo.
echo %PURPLE%╔════════════════════════════════════════╗%NC%
echo %PURPLE%║       HAJIMI KING V4.0 启动菜单        ║%NC%
echo %PURPLE%╠════════════════════════════════════════╣%NC%
echo %PURPLE%║  1. 运行完整版 (GitHub + 扩展搜索)     ║%NC%
echo %PURPLE%║  2. 仅运行 GitHub 搜索                 ║%NC%
echo %PURPLE%║  3. 仅运行扩展搜索                     ║%NC%
echo %PURPLE%║  4. 运行测试模式                       ║%NC%
echo %PURPLE%║  5. 查看配置信息                       ║%NC%
echo %PURPLE%║  6. 编辑配置文件                       ║%NC%
echo %PURPLE%║  7. 查看日志                           ║%NC%
echo %PURPLE%║  8. 退出                               ║%NC%
echo %PURPLE%╚════════════════════════════════════════╝%NC%
echo.

set /p choice="请选择操作 (1-8): "

if "%choice%"=="1" goto run_full
if "%choice%"=="2" goto run_github_only
if "%choice%"=="3" goto run_extended_only
if "%choice%"=="4" goto run_test
if "%choice%"=="5" goto show_config
if "%choice%"=="6" goto edit_config
if "%choice%"=="7" goto view_logs
if "%choice%"=="8" goto exit

call :print_error "无效的选项"
goto menu

:run_full
call :print_info "启动 HAJIMI KING V4.0 (完整版)..."
python -m app.main_v4
goto menu_pause

:run_github_only
call :print_info "启动 HAJIMI KING V4.0 (仅 GitHub)..."
set ENABLE_EXTENDED_SEARCH=false
python -m app.main_v4
goto menu_pause

:run_extended_only
call :print_info "启动 HAJIMI KING V4.0 (仅扩展搜索)..."
call :print_warning "此功能正在开发中..."
goto menu_pause

:run_test
call :print_info "启动测试模式..."
python -m pytest tests/ -v
goto menu_pause

:show_config
call :print_info "显示配置信息..."
python -c "from app.services.config_service import get_config_service; config = get_config_service(); print('当前配置:'); [print(f'  {k}: {\"***\" if \"TOKEN\" in k or \"KEY\" in k else v}') for k, v in sorted(config.get_all().items())]"
goto menu_pause

:edit_config
call :print_info "打开配置文件..."
if exist ".env" (
    notepad .env
) else (
    call :print_error ".env 文件不存在"
)
goto menu

:view_logs
call :print_info "查看最新日志..."
if exist "logs" (
    dir /b /o-d logs\*.log | findstr /n "^" | findstr "^1:" > temp.txt
    for /f "tokens=2 delims=:" %%a in (temp.txt) do set LATEST_LOG=%%a
    del temp.txt
    if defined LATEST_LOG (
        call :print_info "打开日志文件: logs\!LATEST_LOG!"
        notepad "logs\!LATEST_LOG!"
    ) else (
        call :print_warning "没有找到日志文件"
    )
) else (
    call :print_warning "日志目录不存在"
)
goto menu

:menu_pause
echo.
pause
goto menu

:exit
call :print_info "退出程序"
exit /b 0