@echo off
title xhaip - 胸外科智能体 (:8794)
cd /d %~dp0..
set PYTHONPATH=packages/haip-core;packages/haip-hospital
echo Starting 胸外科智能体 on http://127.0.0.1:8794
python -m uvicorn haip.web_server:app --host 127.0.0.1 --port 8794
pause
