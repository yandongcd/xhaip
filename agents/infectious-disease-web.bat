@echo off
title xhaip - 感染内科智能体 (:8787)
cd /d %~dp0..
set PYTHONPATH=packages/haip-core;packages/haip-hospital
echo Starting 感染内科智能体 on http://127.0.0.1:8787
python -m uvicorn haip.web_server:app --host 127.0.0.1 --port 8787
pause
