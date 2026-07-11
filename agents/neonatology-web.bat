@echo off
title xhaip - 新生儿科智能体 (:8804)
cd /d %~dp0..
set PYTHONPATH=packages/haip-core;packages/haip-hospital
echo Starting 新生儿科智能体 on http://127.0.0.1:8804
python -m uvicorn haip.web_server:app --host 127.0.0.1 --port 8804
pause
