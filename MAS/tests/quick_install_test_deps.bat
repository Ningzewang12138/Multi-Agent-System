@echo off
echo ============================================
echo 快速安装测试所需依赖
echo ============================================
echo.

REM 检查是否在项目目录
if not exist "requirements.txt" (
    echo 错误：请在MAS项目根目录运行此脚本
    pause
    exit /b 1
)

echo 1. 激活虚拟环境...
if exist "Scripts\activate.bat" (
    call Scripts\activate.bat
    echo    虚拟环境已激活
) else (
    echo    未找到虚拟环境，使用全局Python
)

echo.
echo 2. 安装测试所需的最小依赖...
echo    安装 requests...
python -m pip install requests

echo.
echo 3. 验证安装...
python -c "import requests; print('成功：requests 模块已安装，版本：' + requests.__version__)"

if errorlevel 1 (
    echo.
    echo 安装失败！请尝试以下方法：
    echo 1. 使用管理员权限运行
    echo 2. 使用国内镜像：
    echo    python -m pip install requests -i https://pypi.tuna.tsinghua.edu.cn/simple
    echo 3. 检查网络连接
) else (
    echo.
    echo 安装成功！现在可以运行测试了。
    echo.
    echo 运行测试命令：
    echo    python run_fix_tests.py
    echo 或
    echo    python generate_test_report.py
)

echo.
pause
