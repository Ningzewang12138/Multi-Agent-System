@echo off
echo ===========================================
echo 测试错误处理和元数据处理修复
echo ===========================================
echo.

echo 请确保服务器正在运行中...
echo 如果服务器未运行，请在另一个终端执行：
echo   cd server
echo   python main.py
echo.

echo 按任意键开始测试...
pause > nul

cd server\test
python test_error_handling.py

echo.
echo 测试完成！
pause
