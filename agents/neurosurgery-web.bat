@echo off
title xhaip - 神经外科智能体 (:8793)
cd /d %~dp0..
set PYTHONPATH=packages/haip-core;packages/haip-hospital
echo Starting 神经外科智能体 on http://127.0.0.1:8793
python -m uvicorn haip.web_server:app --host 127.0.0.1 --port 8793
pause
