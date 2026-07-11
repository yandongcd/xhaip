@echo off
title xhaip - 康复医学科智能体 (:8812)
cd /d %~dp0..
set PYTHONPATH=packages/haip-core;packages/haip-hospital
echo Starting 康复医学科智能体 on http://127.0.0.1:8812
python -m uvicorn haip.web_server:app --host 127.0.0.1 --port 8812
pause
