@echo off
echo ============================================
echo 安装MAS项目依赖
echo ============================================
echo.

echo 激活虚拟环境...
call Scripts\activate.bat

echo.
echo 当前Python路径:
where python

echo.
echo 升级pip...
python -m pip install --upgrade pip

echo.
echo 安装项目依赖...
pip install -r requirements.txt

echo.
echo 验证安装...
python -c "import requests; print('✓ requests 模块已安装')"
python -c "import fastapi; print('✓ fastapi 模块已安装')"
python -c "import chromadb; print('✓ chromadb 模块已安装')"

echo.
echo 安装完成！
pause
