@echo off
title xhaip - 惠侨医疗中心智能体 (:8814)
cd /d %~dp0..
set PYTHONPATH=packages/haip-core;packages/haip-hospital
echo Starting 惠侨医疗中心智能体 on http://127.0.0.1:8814
python -m uvicorn haip.web_server:app --host 127.0.0.1 --port 8814
pause
