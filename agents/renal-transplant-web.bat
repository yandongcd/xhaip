@echo off
title xhaip - 肾移植科智能体 (:8796)
cd /d %~dp0..
set PYTHONPATH=packages/haip-core;packages/haip-hospital
echo Starting 肾移植科智能体 on http://127.0.0.1:8796
python -m uvicorn haip.web_server:app --host 127.0.0.1 --port 8796
pause
