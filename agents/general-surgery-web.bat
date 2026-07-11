@echo off
title xhaip - 普通外科智能体 (:8791)
cd /d %~dp0..
set PYTHONPATH=packages/haip-core;packages/haip-hospital
echo Starting 普通外科智能体 on http://127.0.0.1:8791
python -m uvicorn haip.web_server:app --host 127.0.0.1 --port 8791
pause
