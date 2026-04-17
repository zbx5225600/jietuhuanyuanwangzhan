@echo off
echo ========================================
echo 处理 task_0001
echo ========================================
echo.
echo 请确保已设置 OPENAI_API_KEY 环境变量
echo 如果未设置，请运行: set OPENAI_API_KEY=your-key
echo.
pause
python process_single.py task_0001
pause
