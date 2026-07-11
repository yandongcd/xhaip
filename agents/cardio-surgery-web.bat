@echo off
title xhaip - 心血管外科智能体 (:8768)
cd /d %~dp0..
set PYTHONPATH=packages/haip-core;packages/haip-hospital
echo Starting 心血管外科智能体 on http://127.0.0.1:8768
python -m uvicorn haip.web_server:app --host 127.0.0.1 --port 8768
pause
