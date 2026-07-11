@echo off
title xhaip - 烧伤整形科智能体 (:8798)
cd /d %~dp0..
set PYTHONPATH=packages/haip-core;packages/haip-hospital
echo Starting 烧伤整形科智能体 on http://127.0.0.1:8798
python -m uvicorn haip.web_server:app --host 127.0.0.1 --port 8798
pause
