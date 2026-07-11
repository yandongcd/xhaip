@echo off
title xhaip - 妇产科智能体 (:8803)
cd /d %~dp0..
set PYTHONPATH=packages/haip-core;packages/haip-hospital
echo Starting 妇产科智能体 on http://127.0.0.1:8803
python -m uvicorn haip.web_server:app --host 127.0.0.1 --port 8803
pause
