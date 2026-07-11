@echo off
title xhaip - 重症医学科智能体 (:8809)
cd /d %~dp0..
set PYTHONPATH=packages/haip-core;packages/haip-hospital
echo Starting 重症医学科智能体 on http://127.0.0.1:8809
python -m uvicorn haip.web_server:app --host 127.0.0.1 --port 8809
pause
