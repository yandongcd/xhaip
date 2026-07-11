@echo off
title xhaip - 肿瘤科智能体 (:8788)
cd /d %~dp0..
set PYTHONPATH=packages/haip-core;packages/haip-hospital
echo Starting 肿瘤科智能体 on http://127.0.0.1:8788
python -m uvicorn haip.web_server:app --host 127.0.0.1 --port 8788
pause
