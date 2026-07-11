@echo off
title xhaip - 儿科智能体 (:8820)
cd /d %~dp0..
set PYTHONPATH=packages/haip-core;packages/haip-hospital
echo Starting 儿科智能体 on http://127.0.0.1:8820
python -m uvicorn haip.web_server:app --host 127.0.0.1 --port 8820
pause
