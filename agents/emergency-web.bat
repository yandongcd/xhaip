@echo off
title xhaip - 急诊科智能体 (:8808)
cd /d %~dp0..
set PYTHONPATH=packages/haip-core;packages/haip-hospital
echo Starting 急诊科智能体 on http://127.0.0.1:8808
python -m uvicorn haip.web_server:app --host 127.0.0.1 --port 8808
pause
