@echo off
title xhaip - 肝胆外科智能体 (:8792)
cd /d %~dp0..
set PYTHONPATH=packages/haip-core;packages/haip-hospital
echo Starting 肝胆外科智能体 on http://127.0.0.1:8792
python -m uvicorn haip.web_server:app --host 127.0.0.1 --port 8792
pause
