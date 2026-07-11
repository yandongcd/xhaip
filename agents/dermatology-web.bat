@echo off
title xhaip - 皮肤科智能体 (:8810)
cd /d %~dp0..
set PYTHONPATH=packages/haip-core;packages/haip-hospital
echo Starting 皮肤科智能体 on http://127.0.0.1:8810
python -m uvicorn haip.web_server:app --host 127.0.0.1 --port 8810
pause
