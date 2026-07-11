@echo off
title xhaip - 眼科智能体 (:8805)
cd /d %~dp0..
set PYTHONPATH=packages/haip-core;packages/haip-hospital
echo Starting 眼科智能体 on http://127.0.0.1:8805
python -m uvicorn haip.web_server:app --host 127.0.0.1 --port 8805
pause
