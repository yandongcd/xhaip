@echo off
title xhaip - 精神心理科智能体 (:8811)
cd /d %~dp0..
set PYTHONPATH=packages/haip-core;packages/haip-hospital
echo Starting 精神心理科智能体 on http://127.0.0.1:8811
python -m uvicorn haip.web_server:app --host 127.0.0.1 --port 8811
pause
