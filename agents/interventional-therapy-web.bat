@echo off
title xhaip - 介入治疗科智能体 (:8802)
cd /d %~dp0..
set PYTHONPATH=packages/haip-core;packages/haip-hospital
echo Starting 介入治疗科智能体 on http://127.0.0.1:8802
python -m uvicorn haip.web_server:app --host 127.0.0.1 --port 8802
pause
