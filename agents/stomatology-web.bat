@echo off
title xhaip - 口腔科智能体 (:8807)
cd /d %~dp0..
set PYTHONPATH=packages/haip-core;packages/haip-hospital
echo Starting 口腔科智能体 on http://127.0.0.1:8807
python -m uvicorn haip.web_server:app --host 127.0.0.1 --port 8807
pause
