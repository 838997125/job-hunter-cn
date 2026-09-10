@echo off
chcp 65001 >nul
echo ============================================
echo    求职助手 - 自动化流程测试
echo ============================================
echo.

echo [Step 1/6] 搜索职位
py test_step.py 1
if %errorlevel% neq 0 exit /b 1
echo.

echo [Step 2/6] 分析JD
py test_step.py 2
if %errorlevel% neq 0 exit /b 1
echo.

echo [Step 3/6] 计算匹配度
py test_step.py 3
if %errorlevel% neq 0 exit /b 1
echo.

echo [Step 4/6] 优化简历
py test_step.py 4
if %errorlevel% neq 0 exit /b 1
echo.

echo [Step 5/6] 生成打招呼语
py test_step.py 5
if %errorlevel% neq 0 exit /b 1
echo.

echo [Step 6/6] 生成简历文件
py test_step.py 6
if %errorlevel% neq 0 exit /b 1
echo.

echo ============================================
echo    流程完成！
echo ============================================