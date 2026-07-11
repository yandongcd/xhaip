@echo off
title xhaip - 内分泌科智能体 (:8785)
cd /d %~dp0..
set PYTHONPATH=packages/haip-core;packages/haip-hospital
echo Starting 内分泌科智能体 on http://127.0.0.1:8785
python -m uvicorn haip.web_server:app --host 127.0.0.1 --port 8785
pause
