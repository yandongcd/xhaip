@echo off
title xhaip - 血液内科智能体 (:8784)
cd /d %~dp0..
set PYTHONPATH=packages/haip-core;packages/haip-hospital
echo Starting 血液内科智能体 on http://127.0.0.1:8784
python -m uvicorn haip.web_server:app --host 127.0.0.1 --port 8784
pause
