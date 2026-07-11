@echo off
title xhaip - 药剂科智能体 (:8770)
cd /d %~dp0..
set PYTHONPATH=packages/haip-core;packages/haip-hospital
echo Starting 药剂科智能体 on http://127.0.0.1:8770
python -m uvicorn haip.web_server:app --host 127.0.0.1 --port 8770
pause
