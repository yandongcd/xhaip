@echo off
title xhaip - 整形美容科智能体 (:8799)
cd /d %~dp0..
set PYTHONPATH=packages/haip-core;packages/haip-hospital
echo Starting 整形美容科智能体 on http://127.0.0.1:8799
python -m uvicorn haip.web_server:app --host 127.0.0.1 --port 8799
pause
