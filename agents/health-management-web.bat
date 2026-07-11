@echo off
title xhaip - 健康管理科智能体 (:8813)
cd /d %~dp0..
set PYTHONPATH=packages/haip-core;packages/haip-hospital
echo Starting 健康管理科智能体 on http://127.0.0.1:8813
python -m uvicorn haip.web_server:app --host 127.0.0.1 --port 8813
pause
