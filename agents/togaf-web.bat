@echo off
title xhaip - TOGAF架构治理智能体 (:8750)
cd /d %~dp0..
set PYTHONPATH=packages/haip-core;packages/haip-hospital
echo Starting TOGAF架构治理智能体 on http://127.0.0.1:8750
python -m uvicorn haip.web_server:app --host 127.0.0.1 --port 8750
pause
