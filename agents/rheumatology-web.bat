@echo off
title xhaip - 风湿免疫科智能体 (:8786)
cd /d %~dp0..
set PYTHONPATH=packages/haip-core;packages/haip-hospital
echo Starting 风湿免疫科智能体 on http://127.0.0.1:8786
python -m uvicorn haip.web_server:app --host 127.0.0.1 --port 8786
pause
