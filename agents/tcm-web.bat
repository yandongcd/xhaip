@echo off
title xhaip - 中医科智能体 (:8789)
cd /d %~dp0..
set PYTHONPATH=packages/haip-core;packages/haip-hospital
echo Starting 中医科智能体 on http://127.0.0.1:8789
python -m uvicorn haip.web_server:app --host 127.0.0.1 --port 8789
pause
