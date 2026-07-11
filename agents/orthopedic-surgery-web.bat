@echo off
title xhaip - 创伤骨科智能体 (:8765)
cd /d %~dp0..
set PYTHONPATH=packages/haip-core;packages/haip-hospital
echo Starting 创伤骨科智能体 on http://127.0.0.1:8765
python -m uvicorn haip.web_server:app --host 127.0.0.1 --port 8765
pause
