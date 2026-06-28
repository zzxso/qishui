@echo off
chcp 65001 >nul
title 汽水音乐下载器
echo ========================================
echo   汽水音乐下载器
echo   浏览器将自动打开 http://localhost:5000
echo   关闭此窗口可停止服务
echo ========================================
start http://localhost:5000
python app.py
pause
