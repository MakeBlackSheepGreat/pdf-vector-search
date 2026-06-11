@echo off
chcp 65001 >nul 2>&1
setlocal enabledelayedexpansion

echo ==========================================
echo   PDF Vector Search - 安装
echo ==========================================
echo.

REM 检查 Python
where python >nul 2>&1
if errorlevel 1 (
    echo ❌ 未找到 Python，请先安装 Python 3.9+
    echo    https://www.python.org/downloads/
    pause
    exit /b 1
)

for /f "tokens=2 delims= " %%v in ('python --version 2^>^&1') do set PYVER=%%v
echo ✓ Python %PYVER%

REM 创建虚拟环境
echo.
echo [1/4] 创建虚拟环境...
if not exist venv (
    python -m venv venv
    if errorlevel 1 (
        echo ❌ 创建虚拟环境失败
        pause
        exit /b 1
    )
    echo   ✓ 创建完成
) else (
    echo   ✓ 已存在
)

REM 安装依赖
echo [2/4] 安装依赖...
call venv\Scripts\activate.bat
pip install --quiet -r requirements.txt
if errorlevel 1 (
    echo ❌ 安装依赖失败
    pause
    exit /b 1
)
echo   ✓ 依赖安装完成

REM 配置 .env
echo [3/4] 通用配置...
if not exist .env (
    copy .env.example .env >nul
    echo   ✓ 已创建 .env
) else (
    echo   ✓ .env 已存在
)

REM 配置 API Key
echo [4/4] API Key 配置...
if not exist .api_key (
    copy .api_key.example .api_key >nul
    echo   请输入你的硅基流动 API Key
    echo   获取地址: https://siliconflow.cn/
    set /p USER_KEY="  API Key (直接回车跳过，稍后手动编辑 .api_key): "
    if defined USER_KEY (
        echo SILICONFLOW_API_KEY=!USER_KEY!> .api_key
        echo   ✓ API Key 已保存到 .api_key
    ) else (
        echo   ⚠  已跳过，请稍后编辑 .api_key 填入 Key
    )
) else (
    echo   ✓ .api_key 已存在
)

echo.
echo ==========================================
echo   ✅ 安装完成！
echo ==========================================
echo.
echo 下一步:
echo   1. 如未填入 Key，请编辑 .api_key
echo   2. 构建索引:  python build_index.py --pdf your-book.pdf
echo   3. 开始搜索:  python interactive_search.py --pdf your-book.pdf
echo.
pause
